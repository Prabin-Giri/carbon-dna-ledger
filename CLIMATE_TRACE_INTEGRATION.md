# 🌍 Climate TRACE Integration

## Overview

The Climate TRACE integration provides compliance verification by cross-checking your organization's emission data against the global Climate TRACE database. This feature helps ensure data accuracy, identify discrepancies, and maintain regulatory compliance.

## Features

### 🔄 **Automatic Cross-Checking**
- Compares your emissions against Climate TRACE sector data
- Identifies discrepancies beyond configurable thresholds
- Provides compliance status: Compliant, At-Risk, or Non-Compliant

### 📊 **Comprehensive Analysis**
- Sector-by-sector emission comparison
- Monthly trend analysis
- Confidence scoring based on data quality
- Remediation suggestions for discrepancies

### 🎯 **Smart Mapping**
- Automatically maps your activity types to Climate TRACE sectors
- Supports 8 major sectors: Power, Oil and Gas, Transportation, Manufacturing, Waste, Agriculture, etc.
- Country-specific region mapping

### ⚙️ **Configurable Thresholds**
- Default 10% threshold for compliance flagging
- Customizable per analysis
- Escalation levels (At-Risk: 10-20%, Non-Compliant: >20%)

## Architecture

### Database Schema

#### New Fields in `emission_records`:
```sql
-- Climate TRACE taxonomy fields
ct_sector text,           -- Climate TRACE sector (e.g., 'Power', 'Oil and Gas')
ct_subsector text,        -- Climate TRACE subsector (e.g., 'Coal', 'Natural Gas')
ct_asset_type text,       -- Climate TRACE asset type
ct_asset_id text,         -- Climate TRACE asset identifier
ct_country_code text,     -- ISO country code for CT mapping
ct_region text            -- Climate TRACE region
```

#### New Table: `ct_crosschecks`
```sql
CREATE TABLE ct_crosschecks(
  id uuid PRIMARY KEY,
  year int NOT NULL,
  month int NOT NULL,
  ct_sector text NOT NULL,
  ct_subsector text,
  ct_emissions_kgco2e numeric(20,6),
  our_emissions_kgco2e numeric(20,6),
  delta_kgco2e numeric(20,6),
  delta_percentage numeric(8,4),
  compliance_status text DEFAULT 'compliant',
  threshold_exceeded boolean DEFAULT false,
  -- ... additional fields
);
```

### Service Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Data Ingestion│    │  Climate TRACE  │    │   Cross-Check   │
│                 │    │   Mapping       │    │   Analysis      │
│                 │    │                 │    │                 │
│ emission_record │───►│ map_activity_   │───►│ run_crosscheck_ │
│                 │    │ to_ct_taxonomy  │    │ analysis()      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       ▼
         │                       │              ┌─────────────────┐
         │                       │              │  Compliance     │
         │                       │              │  Verification   │
         │                       │              │                 │
         │                       │              │ • Compliant     │
         │                       │              │ • At-Risk       │
         │                       │              │ • Non-Compliant │
         │                       │              └─────────────────┘
         │                       │
         ▼                       ▼
┌─────────────────┐    ┌─────────────────┐
│  Background Job │    │  Climate TRACE  │
│                 │    │   API Sync      │
│ • Monthly sync  │    │                 │
│ • Data fetch    │    │ • Sector data   │
│ • Analysis      │    │ • Monthly totals│
└─────────────────┘    └─────────────────┘
```

## Configuration

### Environment Variables

```bash
# Enable Climate TRACE integration
COMPLIANCE_CT_ENABLED=true

# Background job configuration
CT_SYNC_INTERVAL_HOURS=24        # Sync every 24 hours
CT_LOOKBACK_MONTHS=12            # Sync last 12 months of data
```

### Activity Type Mapping

The system automatically maps your activity types to Climate TRACE sectors:

| Activity Type | CT Sector | CT Subsector |
|---------------|-----------|--------------|
| electricity | Power | Coal, Natural Gas, Solar, Wind, etc. |
| transportation | Transportation | Road, Aviation, Shipping, Rail |
| oil_production | Oil and Gas | Oil, Natural Gas, Refining |
| manufacturing | Manufacturing | Cement, Steel, Aluminum, etc. |
| waste | Waste | Landfill, Wastewater, Incineration |
| agriculture | Agriculture | Livestock, Rice, Crops |

## API Endpoints

### Status and Configuration
- `GET /api/climate-trace/status` - Get integration status
- `GET /api/climate-trace/sectors` - Get available sectors

### Data Synchronization
- `POST /api/climate-trace/sync` - Manual sync for specific year/month
- `POST /api/climate-trace/crosscheck` - Run cross-check analysis

### Results and Management
- `GET /api/climate-trace/crosschecks` - Get cross-check results
- `POST /api/climate-trace/crosschecks/{id}/acknowledge` - Acknowledge results

## Usage

### 1. Enable Integration

Set the environment variable:
```bash
export COMPLIANCE_CT_ENABLED=true
```

### 2. Data Ingestion

When uploading emission data, the system automatically:
- Maps activity types to Climate TRACE sectors
- Adds taxonomy fields to records
- Prepares data for cross-checking

### 3. Run Analysis

#### Via UI:
1. Navigate to "🌍 Climate TRACE" tab
2. Go to "🔄 Run Analysis" sub-tab
3. Select year/month and threshold
4. Click "Run Cross-Check Analysis"

#### Via API:
```bash
curl -X POST "http://localhost:8000/api/climate-trace/crosscheck" \
  -H "Content-Type: application/json" \
  -d '{"year": 2024, "month": 3, "threshold_percentage": 10.0}'
```

### 4. Review Results

#### Via UI:
1. Go to "📊 Cross-Check Results" sub-tab
2. Filter by year, month, compliance status
3. Review sector-by-sector analysis
4. Acknowledge results as needed

#### Via API:
```bash
curl "http://localhost:8000/api/climate-trace/crosschecks?year=2024&month=3"
```

## Compliance Workflow

### 1. **Data Collection**
- Upload emission records with activity types
- System automatically maps to Climate TRACE taxonomy

### 2. **Cross-Check Analysis**
- Compare your emissions against Climate TRACE data
- Calculate delta percentages
- Flag discrepancies beyond thresholds

### 3. **Compliance Assessment**
- **Compliant**: Delta within threshold (±10%)
- **At-Risk**: Delta exceeds threshold but within 2x threshold
- **Non-Compliant**: Delta exceeds 2x threshold

### 4. **Remediation**
- Review flagged discrepancies
- Investigate data quality issues
- Implement corrective actions
- Acknowledge resolved issues

## Monitoring and Alerts

### Dashboard Metrics
- Total sectors analyzed
- At-risk and non-compliant counts
- Average delta percentage
- Compliance rate trends

### Visualizations
- Sector-by-sector delta charts
- Compliance status distribution
- Historical trend analysis
- Geographic outlier mapping

## Troubleshooting

### Common Issues

#### Integration Disabled
- **Symptom**: "Climate TRACE integration is disabled"
- **Solution**: Set `COMPLIANCE_CT_ENABLED=true` and restart

#### No Cross-Check Results
- **Symptom**: No data appears in results
- **Solution**: Ensure you have emission records with Climate TRACE mapping

#### API Errors
- **Symptom**: "Error fetching Climate TRACE data"
- **Solution**: Check Climate TRACE API availability and rate limits

### Data Requirements

For effective cross-checking, ensure your emission records have:
- `activity_type` - for sector mapping
- `country_code` - for region mapping
- `emissions_kgco2e` - for comparison
- `date` or `date_start` - for time period matching

## Security and Privacy

### Data Handling
- Climate TRACE data is fetched via public API
- Your emission data remains private
- Only aggregated comparisons are stored
- No raw Climate TRACE data is retained

### Compliance
- Follows Climate TRACE API terms of service
- Respects rate limits and usage guidelines
- Maintains data integrity through hash chaining

## Future Enhancements

### Planned Features
- Real-time Climate TRACE data streaming
- Advanced anomaly detection algorithms
- Integration with additional climate databases
- Automated compliance reporting
- Machine learning-based discrepancy prediction

### API Improvements
- Webhook support for real-time updates
- Batch processing for large datasets
- Advanced filtering and search capabilities
- Export functionality for compliance reports

## Support

For technical support or feature requests:
- Check the troubleshooting section above
- Review API documentation
- Contact the development team

---

**Note**: This integration requires an active internet connection to fetch Climate TRACE data. The system gracefully handles API unavailability and provides fallback analysis when needed.
