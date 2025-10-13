# Emissions Calculator System

## Overview

The Carbon DNA Ledger now includes a comprehensive emissions calculation system that automatically calculates `emissions_kgco2e` when missing from records. The system supports multiple data sources and calculation methods, including structured data and freeform text extraction using LLM.

## Features

### 🔢 **Multiple Calculation Methods**

1. **Spend-Based Calculation**
   - Formula: `emissions_kgco2e = amount × ef_factor_per_currency`
   - Used when: `amount`, `currency`, and `ef_factor_per_currency` are available
   - Example: $1000 USD × 0.5 kg CO2e/$ = 500 kg CO2e

2. **Activity-Based Calculation**
   - Formula: `emissions_kgco2e = activity_amount × emission_factor_value`
   - Used when: `activity_amount` and `emission_factor_value` are available
   - Example: 100 km × 0.2 kg CO2e/km = 20 kg CO2e

3. **LLM Extraction + Calculation**
   - Uses AI to extract structured data from freeform text
   - Then applies spend-based or activity-based calculation
   - Fallback to default emission factors when database factors unavailable

### 🤖 **AI-Powered Text Extraction**

The system can extract emission-relevant data from freeform text using the existing AI classifier:

- **Amount & Currency**: Extracts monetary values and currency
- **Activity Data**: Extracts activity amounts, units, and types
- **Classification**: Categorizes activities (transportation, energy, waste, etc.)
- **Scope**: Determines emission scope (1=Direct, 2=Indirect, 3=Other)

### 📊 **Batch Processing**

- Process multiple records simultaneously
- Individual error handling per record
- Summary statistics and success rates
- Maintains data integrity with hash chaining

## API Endpoints

### 1. Calculate Emissions (Single Record)
```http
POST /api/calculate-emissions
Content-Type: application/json

{
  "amount": 1000.0,
  "currency": "USD",
  "ef_factor_per_currency": 0.5,
  "supplier_name": "Test Supplier"
}
```

**Response:**
```json
{
  "success": true,
  "calculated_record": {
    "amount": 1000.0,
    "currency": "USD",
    "ef_factor_per_currency": 0.5,
    "supplier_name": "Test Supplier",
    "emissions_kgco2e": 500.0,
    "calculation_method": "spend_based",
    "calculation_details": "1000.0 USD × 0.5 = 500.00 kg CO2e"
  }
}
```

### 2. Calculate Emissions (Batch)
```http
POST /api/calculate-emissions
Content-Type: application/json

{
  "records": [
    {
      "amount": 500.0,
      "currency": "USD",
      "ef_factor_per_currency": 0.5
    },
    {
      "activity_amount": 50.0,
      "activity_unit": "kWh",
      "emission_factor_value": 0.4
    }
  ]
}
```

### 3. Calculate Emissions for Existing Record
```http
POST /api/calculate-emissions/{record_id}
```

### 4. LLM Text Extraction + Calculation
```http
POST /api/calculate-emissions
Content-Type: application/json

{
  "description": "Invoice from ABC Corp for office supplies. Total cost $500 USD.",
  "supplier_name": "ABC Corp"
}
```

## Integration Points

### 1. **CSV/PDF Upload**
- Automatically calculates emissions during ingestion
- Handles both simple (spend-based) and advanced (activity-based) CSV formats
- Updates records with calculated emissions before database insertion

### 2. **AI Classification**
- Calculates emissions after LLM text extraction
- Integrates with human review workflow
- Maintains confidence scores and review flags

### 3. **Human Review**
- Recalculates emissions when humans edit records
- Updates hash chain for data integrity
- Preserves audit trail of changes

## Default Emission Factors

When database factors are unavailable, the system uses intelligent defaults:

### By Currency (Spend-Based)
- **USD**: 0.5 kg CO2e per $1
- **EUR**: 0.45 kg CO2e per €1
- **GBP**: 0.55 kg CO2e per £1
- **CAD**: 0.48 kg CO2e per C$1
- **AUD**: 0.52 kg CO2e per A$1

### By Activity Type (Activity-Based)
- **Transportation**: 0.2 kg CO2e per km
- **Energy**: 0.4 kg CO2e per kWh
- **Waste**: 0.1 kg CO2e per kg
- **Materials**: 0.3 kg CO2e per kg
- **Other**: 0.25 kg CO2e per unit

## Error Handling

The system gracefully handles various error scenarios:

1. **Insufficient Data**: Returns helpful error messages
2. **Calculation Failures**: Logs warnings but continues processing
3. **LLM Extraction Failures**: Falls back to regex-based extraction
4. **Database Errors**: Maintains data integrity with rollbacks

## Usage Examples

### Example 1: Spend-Based Calculation
```python
# Input data
record = {
    "amount": 1000.0,
    "currency": "USD", 
    "ef_factor_per_currency": 0.5,
    "supplier_name": "Office Supplies Inc"
}

# Result
{
    "emissions_kgco2e": 500.0,
    "calculation_method": "spend_based",
    "calculation_details": "1000.0 USD × 0.5 = 500.00 kg CO2e"
}
```

### Example 2: Activity-Based Calculation
```python
# Input data
record = {
    "activity_amount": 200.0,
    "activity_unit": "km",
    "emission_factor_value": 0.2,
    "activity_type": "transportation"
}

# Result
{
    "emissions_kgco2e": 40.0,
    "calculation_method": "activity_based", 
    "calculation_details": "200.0 × 0.2 = 40.00 kg CO2e"
}
```

### Example 3: LLM Extraction
```python
# Input data
record = {
    "description": "Invoice from XYZ Logistics for truck shipment. Distance: 150 km, Weight: 3 tonnes.",
    "supplier_name": "XYZ Logistics"
}

# Result
{
    "emissions_kgco2e": 30.0,
    "calculation_method": "llm_extracted_activity",
    "calculation_details": "LLM extracted: 150.0 × 0.2 = 30.00 kg CO2e",
    "llm_extracted_data": {
        "distance_km": 150.0,
        "activity_type": "transportation",
        "scope": 1
    }
}
```

## Testing

Run the test script to verify functionality:

```bash
python3 test_emissions_calculator.py
```

The test script covers:
- ✅ Spend-based calculations
- ✅ Activity-based calculations  
- ✅ LLM extraction + calculation
- ✅ Batch processing
- ✅ AI classification integration

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Data Input    │───▶│ Emissions Calc   │───▶│  Database       │
│                 │    │                  │    │                 │
│ • CSV/PDF       │    │ • Spend-based    │    │ • Hash Chain    │
│ • AI Text       │    │ • Activity-based │    │ • Audit Trail   │
│ • Manual Entry  │    │ • LLM Extraction │    │ • Integrity     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Benefits

1. **Automated**: No manual emissions calculation required
2. **Flexible**: Supports multiple data sources and formats
3. **Intelligent**: Uses AI for freeform text extraction
4. **Reliable**: Fallback mechanisms and error handling
5. **Auditable**: Maintains data integrity with hash chaining
6. **Scalable**: Batch processing for large datasets

## Future Enhancements

- [ ] Machine learning-based emission factor optimization
- [ ] Real-time emission factor updates from external APIs
- [ ] Advanced activity categorization using NLP
- [ ] Carbon intensity tracking over time
- [ ] Integration with external carbon accounting systems
