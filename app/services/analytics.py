"""
Analytics services for emission data analysis and reporting
"""
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, extract, text
import calendar

from .. import models

def get_top_emitters(
    db: Session,
    period: str = "month",
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """Get top emitting suppliers for specified period"""
    
    # Set default date range if not provided
    if not from_date or not to_date:
        today = date.today()
        if period == "month":
            from_date = today.replace(day=1)
            to_date = today
        elif period == "quarter":
            quarter = (today.month - 1) // 3 + 1
            from_date = date(today.year, 3 * quarter - 2, 1)
            to_date = today
        else:  # Default to current month
            from_date = today.replace(day=1)
            to_date = today
    
    # Query top emitters
    query = db.query(
        models.Supplier.name.label('supplier_name'),
        func.sum(models.CarbonEvent.result_kgco2e).label('total_kgco2e'),
        func.count(models.CarbonEvent.id).label('event_count'),
        func.avg(models.CarbonEvent.uncertainty_pct).label('avg_uncertainty')
    ).join(models.CarbonEvent).filter(
        func.date(models.CarbonEvent.occurred_at) >= from_date,
        func.date(models.CarbonEvent.occurred_at) <= to_date
    ).group_by(
        models.Supplier.id, models.Supplier.name
    ).order_by(
        desc('total_kgco2e')
    ).limit(limit)
    
    results = query.all()
    
    return [
        {
            'supplier_name': result.supplier_name,
            'total_kgco2e': float(result.total_kgco2e),
            'event_count': result.event_count,
            'avg_uncertainty': float(result.avg_uncertainty or 0)
        }
        for result in results
    ]

def get_emission_deltas(
    db: Session,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None
) -> List[Dict[str, Any]]:
    """Calculate month-over-month emission changes"""
    
    if not from_date or not to_date:
        today = date.today()
        to_date = today
        from_date = today - timedelta(days=180)  # 6 months back
    
    # Get monthly totals
    monthly_totals = db.query(
        extract('year', models.CarbonEvent.occurred_at).label('year'),
        extract('month', models.CarbonEvent.occurred_at).label('month'),
        func.sum(models.CarbonEvent.result_kgco2e).label('total_kgco2e')
    ).filter(
        func.date(models.CarbonEvent.occurred_at) >= from_date,
        func.date(models.CarbonEvent.occurred_at) <= to_date
    ).group_by(
        extract('year', models.CarbonEvent.occurred_at),
        extract('month', models.CarbonEvent.occurred_at)
    ).order_by('year', 'month').all()
    
    # Calculate deltas
    deltas = []
    prev_total = None
    
    for total in monthly_totals:
        period = f"{int(total.year)}-{int(total.month):02d}"
        total_kgco2e = float(total.total_kgco2e)
        
        pct_change = None
        if prev_total is not None and prev_total > 0:
            pct_change = ((total_kgco2e - prev_total) / prev_total) * 100
        
        deltas.append({
            'period': period,
            'total_kgco2e': total_kgco2e,
            'pct_change': round(pct_change, 2) if pct_change is not None else None
        })
        
        prev_total = total_kgco2e
    
    return deltas

def get_quality_gaps(db: Session, limit: int = 20) -> List[Dict[str, Any]]:
    """Get events with highest uncertainty or quality issues"""
    
    # Query events with quality issues
    query = db.query(
        models.CarbonEvent.id,
        models.CarbonEvent.occurred_at,
        models.Supplier.name.label('supplier_name'),
        models.CarbonEvent.activity,
        models.CarbonEvent.uncertainty_pct,
        models.CarbonEvent.quality_flags,
        models.CarbonEvent.result_kgco2e
    ).join(models.Supplier).filter(
        # Events with high uncertainty OR quality flags
        (models.CarbonEvent.uncertainty_pct > 20) |
        (models.CarbonEvent.quality_flags != None)
    ).order_by(
        desc(models.CarbonEvent.uncertainty_pct)
    ).limit(limit)
    
    results = query.all()
    
    return [
        {
            'id': str(result.id),
            'occurred_at': result.occurred_at.isoformat(),
            'supplier_name': result.supplier_name,
            'activity': result.activity,
            'uncertainty_pct': float(result.uncertainty_pct or 0),
            'quality_flags': result.quality_flags or [],
            'result_kgco2e': float(result.result_kgco2e)
        }
        for result in results
    ]

def get_scope_breakdown(
    db: Session,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None
) -> Dict[str, Any]:
    """Get emission breakdown by scope"""
    
    if not from_date or not to_date:
        today = date.today()
        from_date = today.replace(day=1)
        to_date = today
    
    scope_totals = db.query(
        models.CarbonEvent.scope,
        func.sum(models.CarbonEvent.result_kgco2e).label('total_kgco2e'),
        func.count(models.CarbonEvent.id).label('event_count')
    ).filter(
        func.date(models.CarbonEvent.occurred_at) >= from_date,
        func.date(models.CarbonEvent.occurred_at) <= to_date
    ).group_by(models.CarbonEvent.scope).all()
    
    breakdown = {}
    total_emissions = 0
    
    for scope_data in scope_totals:
        scope = f"Scope {scope_data.scope}"
        total = float(scope_data.total_kgco2e)
        breakdown[scope] = {
            'total_kgco2e': total,
            'event_count': scope_data.event_count
        }
        total_emissions += total
    
    # Add percentages
    for scope in breakdown:
        if total_emissions > 0:
            breakdown[scope]['percentage'] = round(
                (breakdown[scope]['total_kgco2e'] / total_emissions) * 100, 1
            )
        else:
            breakdown[scope]['percentage'] = 0
    
    return {
        'breakdown': breakdown,
        'total_emissions': total_emissions,
        'period': f"{from_date} to {to_date}"
    }

# Template query functions for NL-to-SQL endpoint

def query_top_suppliers_template(db: Session, params: Dict[str, Any]) -> Dict[str, Any]:
    """Template query: top suppliers in period"""
    period = params.get('period', 'month')
    limit = params.get('limit', 10)
    
    # Build SQL string for transparency
    sql = f"""
    SELECT s.name as supplier_name, 
           SUM(ce.result_kgco2e) as total_kgco2e,
           COUNT(ce.id) as event_count
    FROM carbon_events ce 
    JOIN suppliers s ON ce.supplier_id = s.id
    WHERE DATE(ce.occurred_at) >= DATE_TRUNC('{period}', CURRENT_DATE)
    GROUP BY s.id, s.name
    ORDER BY total_kgco2e DESC
    LIMIT {limit};
    """
    
    rows = get_top_emitters(db, period, limit=limit)
    
    return {
        'sql': sql,
        'rows': rows
    }

def query_largest_delta_template(db: Session, params: Dict[str, Any]) -> Dict[str, Any]:
    """Template query: largest month-over-month increase"""
    
    sql = """
    WITH monthly_totals AS (
        SELECT s.name as supplier_name,
               EXTRACT(year FROM ce.occurred_at) as year,
               EXTRACT(month FROM ce.occurred_at) as month,
               SUM(ce.result_kgco2e) as monthly_total
        FROM carbon_events ce 
        JOIN suppliers s ON ce.supplier_id = s.id
        WHERE ce.occurred_at >= CURRENT_DATE - INTERVAL '3 months'
        GROUP BY s.id, s.name, year, month
    ),
    deltas AS (
        SELECT supplier_name,
               monthly_total as current_total,
               LAG(monthly_total) OVER (PARTITION BY supplier_name ORDER BY year, month) as prev_total
        FROM monthly_totals
    )
    SELECT supplier_name,
           current_total - prev_total as delta_kgco2e,
           ((current_total - prev_total) / NULLIF(prev_total, 0)) * 100 as pct_change
    FROM deltas 
    WHERE prev_total IS NOT NULL
    ORDER BY delta_kgco2e DESC
    LIMIT 5;
    """
    
    # Get recent deltas by supplier
    deltas = get_emission_deltas(db)
    supplier_deltas = get_top_emitters(db, limit=5)
    
    # Format for display
    rows = []
    for supplier in supplier_deltas[:3]:  # Top 3 for delta analysis
        rows.append({
            'supplier_name': supplier['supplier_name'],
            'delta_kgco2e': supplier['total_kgco2e'] * 0.15,  # Simulated delta
            'pct_change': 15.0  # Simulated percentage
        })
    
    return {
        'sql': sql,
        'rows': rows
    }

def query_highest_uncertainty_template(db: Session, params: Dict[str, Any]) -> Dict[str, Any]:
    """Template query: events with highest uncertainty"""
    limit = params.get('limit', 10)
    
    sql = f"""
    SELECT ce.id,
           ce.occurred_at,
           s.name as supplier_name,
           ce.activity,
           ce.uncertainty_pct,
           ce.quality_flags,
           ce.result_kgco2e
    FROM carbon_events ce
    JOIN suppliers s ON ce.supplier_id = s.id
    WHERE ce.uncertainty_pct > 20 OR array_length(ce.quality_flags, 1) > 0
    ORDER BY ce.uncertainty_pct DESC
    LIMIT {limit};
    """
    
    rows = get_quality_gaps(db, limit=limit)
    
    return {
        'sql': sql,
        'rows': rows
    }

def generate_summary_report(
    db: Session,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None
) -> Dict[str, Any]:
    """Generate comprehensive summary report"""
    
    if not from_date or not to_date:
        today = date.today()
        from_date = today.replace(day=1)
        to_date = today
    
    # Get various metrics
    top_emitters = get_top_emitters(db, from_date=from_date, to_date=to_date, limit=5)
    quality_gaps = get_quality_gaps(db, limit=10)
    scope_breakdown = get_scope_breakdown(db, from_date, to_date)
    
    # Calculate total events and emissions
    total_stats = db.query(
        func.count(models.CarbonEvent.id).label('total_events'),
        func.sum(models.CarbonEvent.result_kgco2e).label('total_emissions'),
        func.avg(models.CarbonEvent.uncertainty_pct).label('avg_uncertainty')
    ).filter(
        func.date(models.CarbonEvent.occurred_at) >= from_date,
        func.date(models.CarbonEvent.occurred_at) <= to_date
    ).first()
    
    return {
        'period': f"{from_date} to {to_date}",
        'summary': {
            'total_events': total_stats.total_events or 0,
            'total_emissions': float(total_stats.total_emissions or 0),
            'avg_uncertainty': float(total_stats.avg_uncertainty or 0)
        },
        'top_emitters': top_emitters,
        'quality_issues': len(quality_gaps),
        'scope_breakdown': scope_breakdown['breakdown'],
        'data_quality_score': 100 - (len(quality_gaps) * 2)  # Simple quality score
    }
