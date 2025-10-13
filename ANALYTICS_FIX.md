# Analytics Dashboard Fix

## Issue
The analytics dashboard was not working properly for top emitters, trends, and deltas because the backend analytics service was using the old `CarbonEvent` model and `result_kgco2e` field, while the system has been updated to use the `EmissionRecord` model with `emissions_kgco2e` field.

## Root Cause
- **Model Mismatch**: Analytics service was querying `CarbonEvent` table instead of `EmissionRecord` table
- **Field Mismatch**: Using `result_kgco2e` instead of `emissions_kgco2e`
- **Date Field Mismatch**: Using `occurred_at` instead of `date`
- **Relationship Issues**: Trying to join with `Supplier` table when `supplier_name` is directly available in `EmissionRecord`

## Fixes Applied

### 1. Backend Analytics Service (`app/services/analytics.py`)

#### `get_top_emitters()` Function
**Before:**
```python
query = db.query(
    models.Supplier.name.label('supplier_name'),
    func.sum(models.CarbonEvent.result_kgco2e).label('total_kgco2e'),
    func.count(models.CarbonEvent.id).label('event_count'),
    func.avg(models.CarbonEvent.uncertainty_pct).label('avg_uncertainty')
).join(models.CarbonEvent).filter(
    func.date(models.CarbonEvent.occurred_at) >= from_date,
    func.date(models.CarbonEvent.occurred_at) <= to_date
)
```

**After:**
```python
query = db.query(
    models.EmissionRecord.supplier_name,
    func.sum(models.EmissionRecord.emissions_kgco2e).label('total_kgco2e'),
    func.count(models.EmissionRecord.id).label('event_count'),
    func.avg(models.EmissionRecord.uncertainty_pct).label('avg_uncertainty')
).filter(
    models.EmissionRecord.date >= from_date,
    models.EmissionRecord.date <= to_date,
    models.EmissionRecord.emissions_kgco2e.isnot(None)
)
```

#### `get_emission_deltas()` Function
**Before:**
```python
monthly_totals = db.query(
    extract('year', models.CarbonEvent.occurred_at).label('year'),
    extract('month', models.CarbonEvent.occurred_at).label('month'),
    func.sum(models.CarbonEvent.result_kgco2e).label('total_kgco2e')
).filter(
    func.date(models.CarbonEvent.occurred_at) >= from_date,
    func.date(models.CarbonEvent.occurred_at) <= to_date
)
```

**After:**
```python
monthly_totals = db.query(
    extract('year', models.EmissionRecord.date).label('year'),
    extract('month', models.EmissionRecord.date).label('month'),
    func.sum(models.EmissionRecord.emissions_kgco2e).label('total_kgco2e')
).filter(
    models.EmissionRecord.date >= from_date,
    models.EmissionRecord.date <= to_date,
    models.EmissionRecord.emissions_kgco2e.isnot(None)
)
```

#### `get_quality_gaps()` Function
**Before:**
```python
query = db.query(
    models.CarbonEvent.id,
    models.CarbonEvent.occurred_at,
    models.Supplier.name.label('supplier_name'),
    models.CarbonEvent.activity,
    models.CarbonEvent.uncertainty_pct,
    models.CarbonEvent.quality_flags,
    models.CarbonEvent.result_kgco2e
).join(models.Supplier).filter(
    (models.CarbonEvent.uncertainty_pct > 20) |
    (models.CarbonEvent.quality_flags != None)
)
```

**After:**
```python
query = db.query(
    models.EmissionRecord.id,
    models.EmissionRecord.date.label('occurred_at'),
    models.EmissionRecord.supplier_name,
    models.EmissionRecord.activity_type.label('activity'),
    models.EmissionRecord.uncertainty_pct,
    models.EmissionRecord.compliance_flags.label('quality_flags'),
    models.EmissionRecord.emissions_kgco2e.label('result_kgco2e')
).filter(
    (models.EmissionRecord.uncertainty_pct > 20) |
    (models.EmissionRecord.compliance_flags != None) |
    (models.EmissionRecord.data_quality_score < 50)
)
```

#### `get_scope_breakdown()` Function
**Before:**
```python
scope_totals = db.query(
    models.CarbonEvent.scope,
    func.sum(models.CarbonEvent.result_kgco2e).label('total_kgco2e'),
    func.count(models.CarbonEvent.id).label('event_count')
).filter(
    func.date(models.CarbonEvent.occurred_at) >= from_date,
    func.date(models.CarbonEvent.occurred_at) <= to_date
)
```

**After:**
```python
scope_totals = db.query(
    models.EmissionRecord.scope,
    func.sum(models.EmissionRecord.emissions_kgco2e).label('total_kgco2e'),
    func.count(models.EmissionRecord.id).label('event_count')
).filter(
    models.EmissionRecord.date >= from_date,
    models.EmissionRecord.date <= to_date,
    models.EmissionRecord.emissions_kgco2e.isnot(None)
)
```

### 2. Frontend Analytics UI (`ui/components/analytics.py`)

#### Enhanced Error Handling
- Added empty DataFrame checks before processing data
- Improved error messages for better user experience
- Added graceful handling of missing or null data

#### Custom Analysis Fix
**Before:**
```python
# Get events data
response = requests.get(f"{api_base}/api/events", params={"limit": 1000})
# Used 'result_kgco2e' and 'activity' fields
```

**After:**
```python
# Get emission records data
response = requests.get(f"{api_base}/api/emission-records", params={"limit": 10000})
# Uses 'emissions_kgco2e' and 'activity_type' fields
```

#### Data Processing Improvements
- Added null checks for date parsing: `pd.to_datetime(display_df['occurred_at'], errors='coerce')`
- Enhanced quality flags handling: `isinstance(x, list) and x`
- Better filtering for activity comparison analysis

## Key Changes Summary

1. **Model Migration**: All analytics functions now use `EmissionRecord` instead of `CarbonEvent`
2. **Field Updates**: 
   - `result_kgco2e` → `emissions_kgco2e`
   - `occurred_at` → `date`
   - `activity` → `activity_type`
   - `quality_flags` → `compliance_flags`
3. **Relationship Simplification**: Removed unnecessary joins since `supplier_name` is directly available
4. **Data Quality**: Added null checks and better error handling
5. **API Endpoint Updates**: Custom analysis now uses `/api/emission-records` instead of `/api/events`

## Testing
The analytics dashboard should now properly display:
- ✅ Top emitters with correct supplier rankings
- ✅ Monthly emission trends and deltas
- ✅ Quality gaps analysis with proper data
- ✅ Custom activity comparison analysis
- ✅ Proper error handling when no data is available

## Files Modified
- `app/services/analytics.py` - Backend analytics service
- `ui/components/analytics.py` - Frontend analytics UI
- `ANALYTICS_FIX.md` - This documentation file
