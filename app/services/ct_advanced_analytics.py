"""
Advanced Climate TRACE Analytics Service
Provides trend analysis, predictive alerts, and ML-powered insights
"""
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc
import json

from ..models import ClimateTraceCrosscheck, EmissionRecord

logger = logging.getLogger(__name__)

@dataclass
class TrendAnalysis:
    """Trend analysis result"""
    sector: str
    trend_direction: str  # 'increasing', 'decreasing', 'stable'
    trend_strength: float  # 0-1, how strong the trend is
    change_rate: float  # percentage change per month
    confidence: float  # 0-1, confidence in the trend
    data_points: int
    last_6_months_avg: float
    prediction_next_month: float
    risk_level: str  # 'low', 'medium', 'high', 'critical'

@dataclass
class PredictiveAlert:
    """Predictive alert for compliance risk"""
    alert_id: str
    alert_type: str  # 'compliance_risk', 'data_quality', 'trend_anomaly'
    severity: str  # 'low', 'medium', 'high', 'critical'
    sector: str
    predicted_date: datetime
    confidence: float
    description: str
    recommended_actions: List[str]
    current_risk_score: float
    predicted_risk_score: float

@dataclass
class RiskScore:
    """Comprehensive risk scoring"""
    overall_score: float  # 0-100
    compliance_risk: float  # 0-100
    data_quality_risk: float  # 0-100
    trend_risk: float  # 0-100
    regulatory_risk: float  # 0-100
    factors: Dict[str, float]
    recommendations: List[str]

class ClimateTraceAdvancedAnalytics:
    """Advanced analytics service for Climate TRACE integration"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.risk_weights = {
            'compliance_deviation': 0.3,
            'data_quality': 0.25,
            'trend_anomaly': 0.2,
            'regulatory_exposure': 0.15,
            'historical_consistency': 0.1
        }
    
    def analyze_trends(self, sector: Optional[str] = None, 
                      months_back: int = 12) -> List[TrendAnalysis]:
        """
        Analyze emission trends over time
        
        Args:
            sector: Optional sector filter
            months_back: Number of months to analyze
            
        Returns:
            List of trend analysis results
        """
        try:
            # Get historical cross-check data
            end_date = datetime.now()
            start_date = end_date - timedelta(days=months_back * 30)
            
            query = self.db.query(ClimateTraceCrosscheck).filter(
                and_(
                    ClimateTraceCrosscheck.created_at >= start_date,
                    ClimateTraceCrosscheck.created_at <= end_date
                )
            )
            
            if sector:
                query = query.filter(ClimateTraceCrosscheck.ct_sector == sector)
            
            crosschecks = query.order_by(ClimateTraceCrosscheck.created_at).all()
            
            if not crosschecks:
                logger.warning("No cross-check data found for trend analysis")
                return []
            
            # Group by sector and analyze trends
            trends = []
            sector_data = {}
            
            for cc in crosschecks:
                sector_name = cc.ct_sector or 'Unknown'
                if sector_name not in sector_data:
                    sector_data[sector_name] = []
                
                sector_data[sector_name].append({
                    'date': cc.created_at,
                    'delta_percentage': float(cc.delta_percentage or 0),
                    'our_emissions': float(cc.our_emissions_kgco2e or 0),
                    'ct_emissions': float(cc.ct_emissions_kgco2e or 0)
                })
            
            # Analyze trends for each sector
            for sector_name, data in sector_data.items():
                if len(data) < 3:  # Need at least 3 data points
                    continue
                
                trend = self._calculate_trend(sector_name, data)
                if trend:
                    trends.append(trend)
            
            logger.info(f"Analyzed trends for {len(trends)} sectors")
            return trends
            
        except Exception as e:
            logger.error(f"Error in trend analysis: {e}")
            return []
    
    def _calculate_trend(self, sector: str, data: List[Dict]) -> Optional[TrendAnalysis]:
        """Calculate trend for a specific sector"""
        try:
            # Sort by date
            data.sort(key=lambda x: x['date'])
            
            # Extract delta percentages
            deltas = [d['delta_percentage'] for d in data]
            dates = [d['date'] for d in data]
            
            if len(deltas) < 3:
                return None
            
            # Calculate trend using linear regression
            x = np.arange(len(deltas))
            y = np.array(deltas)
            
            # Simple linear regression
            slope, intercept = np.polyfit(x, y, 1)
            
            # Determine trend direction and strength
            if abs(slope) < 0.5:
                trend_direction = 'stable'
                trend_strength = 0.2
            elif slope > 0:
                trend_direction = 'increasing'
                trend_strength = min(abs(slope) / 10, 1.0)
            else:
                trend_direction = 'decreasing'
                trend_strength = min(abs(slope) / 10, 1.0)
            
            # Calculate change rate (percentage per month)
            change_rate = slope
            
            # Calculate confidence based on data consistency
            residuals = y - (slope * x + intercept)
            r_squared = 1 - (np.sum(residuals**2) / np.sum((y - np.mean(y))**2))
            confidence = max(0, min(1, r_squared))
            
            # Calculate last 6 months average
            last_6_months = deltas[-6:] if len(deltas) >= 6 else deltas
            last_6_months_avg = np.mean(last_6_months)
            
            # Predict next month
            next_month_prediction = slope * len(deltas) + intercept
            
            # Determine risk level
            risk_level = self._assess_trend_risk(trend_direction, trend_strength, 
                                               last_6_months_avg, next_month_prediction)
            
            return TrendAnalysis(
                sector=sector,
                trend_direction=trend_direction,
                trend_strength=trend_strength,
                change_rate=change_rate,
                confidence=confidence,
                data_points=len(data),
                last_6_months_avg=last_6_months_avg,
                prediction_next_month=next_month_prediction,
                risk_level=risk_level
            )
            
        except Exception as e:
            logger.error(f"Error calculating trend for {sector}: {e}")
            return None
    
    def _assess_trend_risk(self, direction: str, strength: float, 
                          avg_delta: float, prediction: float) -> str:
        """Assess risk level based on trend analysis"""
        # High risk if:
        # - Strong increasing trend with high deltas
        # - Prediction shows significant deviation
        # - Current average is already high
        
        if direction == 'increasing' and strength > 0.7 and avg_delta > 15:
            return 'critical'
        elif direction == 'increasing' and strength > 0.5 and avg_delta > 10:
            return 'high'
        elif abs(prediction) > 20 or avg_delta > 15:
            return 'high'
        elif abs(prediction) > 10 or avg_delta > 8:
            return 'medium'
        else:
            return 'low'
    
    def generate_predictive_alerts(self, days_ahead: int = 30) -> List[PredictiveAlert]:
        """
        Generate predictive alerts for potential compliance issues
        
        Args:
            days_ahead: How many days ahead to predict
            
        Returns:
            List of predictive alerts
        """
        alerts = []
        
        try:
            # Get recent trends
            trends = self.analyze_trends(months_back=6)
            
            for trend in trends:
                # Check if trend indicates future risk
                if trend.risk_level in ['high', 'critical']:
                    alert = self._create_trend_alert(trend, days_ahead)
                    if alert:
                        alerts.append(alert)
            
            # Check for data quality issues
            quality_alerts = self._check_data_quality_risks()
            alerts.extend(quality_alerts)
            
            # Check for compliance risks
            compliance_alerts = self._check_compliance_risks()
            alerts.extend(compliance_alerts)
            
            logger.info(f"Generated {len(alerts)} predictive alerts")
            return alerts
            
        except Exception as e:
            logger.error(f"Error generating predictive alerts: {e}")
            return []
    
    def _create_trend_alert(self, trend: TrendAnalysis, days_ahead: int) -> Optional[PredictiveAlert]:
        """Create alert based on trend analysis"""
        try:
            # Calculate predicted risk score
            current_risk = self._trend_to_risk_score(trend.last_6_months_avg)
            predicted_risk = self._trend_to_risk_score(trend.prediction_next_month)
            
            # Determine alert severity
            if trend.risk_level == 'critical':
                severity = 'critical'
            elif trend.risk_level == 'high':
                severity = 'high'
            else:
                severity = 'medium'
            
            # Generate recommendations
            recommendations = self._generate_trend_recommendations(trend)
            
            return PredictiveAlert(
                alert_id=f"trend_{trend.sector}_{datetime.now().strftime('%Y%m%d')}",
                alert_type='trend_anomaly',
                severity=severity,
                sector=trend.sector,
                predicted_date=datetime.now() + timedelta(days=days_ahead),
                confidence=trend.confidence,
                description=f"Trend analysis shows {trend.trend_direction} deviation trend in {trend.sector} sector. "
                           f"Current average: {trend.last_6_months_avg:.1f}%, "
                           f"Predicted next month: {trend.prediction_next_month:.1f}%",
                recommended_actions=recommendations,
                current_risk_score=current_risk,
                predicted_risk_score=predicted_risk
            )
            
        except Exception as e:
            logger.error(f"Error creating trend alert: {e}")
            return None
    
    def _trend_to_risk_score(self, delta_percentage: float) -> float:
        """Convert delta percentage to risk score (0-100)"""
        abs_delta = abs(delta_percentage)
        if abs_delta > 20:
            return 90
        elif abs_delta > 15:
            return 75
        elif abs_delta > 10:
            return 60
        elif abs_delta > 5:
            return 40
        else:
            return 20
    
    def _generate_trend_recommendations(self, trend: TrendAnalysis) -> List[str]:
        """Generate recommendations based on trend analysis"""
        recommendations = []
        
        if trend.trend_direction == 'increasing':
            recommendations.extend([
                "Review emission calculation methods for accuracy",
                "Verify activity data and emission factors",
                "Consider implementing additional monitoring",
                "Schedule compliance review meeting"
            ])
        elif trend.trend_direction == 'decreasing':
            recommendations.extend([
                "Verify that emission reductions are real and sustainable",
                "Document improvement measures for reporting",
                "Consider setting more ambitious targets"
            ])
        
        if trend.risk_level in ['high', 'critical']:
            recommendations.extend([
                "Immediate compliance review required",
                "Consider third-party verification",
                "Prepare regulatory response plan"
            ])
        
        return recommendations
    
    def _check_data_quality_risks(self) -> List[PredictiveAlert]:
        """Check for data quality issues that could lead to compliance problems"""
        alerts = []
        
        try:
            # Check for records with missing Climate TRACE mapping
            unmapped_count = self.db.query(EmissionRecord).filter(
                EmissionRecord.ct_sector.is_(None)
            ).count()
            
            if unmapped_count > 10:  # Threshold for alert
                alerts.append(PredictiveAlert(
                    alert_id=f"data_quality_{datetime.now().strftime('%Y%m%d')}",
                    alert_type='data_quality',
                    severity='medium',
                    sector='All',
                    predicted_date=datetime.now() + timedelta(days=7),
                    confidence=0.8,
                    description=f"{unmapped_count} emission records lack Climate TRACE sector mapping. "
                               "This could affect compliance verification accuracy.",
                    recommended_actions=[
                        "Review and update activity type mappings",
                        "Implement automated sector classification",
                        "Schedule data quality audit"
                    ],
                    current_risk_score=60,
                    predicted_risk_score=70
                ))
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error checking data quality risks: {e}")
            return []
    
    def _check_compliance_risks(self) -> List[PredictiveAlert]:
        """Check for immediate compliance risks"""
        alerts = []
        
        try:
            # Check for recent high-risk cross-checks
            recent_high_risk = self.db.query(ClimateTraceCrosscheck).filter(
                and_(
                    ClimateTraceCrosscheck.compliance_status.in_(['at_risk', 'non_compliant']),
                    ClimateTraceCrosscheck.created_at >= datetime.now() - timedelta(days=7),
                    ClimateTraceCrosscheck.is_acknowledged == False
                )
            ).all()
            
            for cc in recent_high_risk:
                alerts.append(PredictiveAlert(
                    alert_id=f"compliance_{cc.id}",
                    alert_type='compliance_risk',
                    severity='high' if cc.compliance_status == 'non_compliant' else 'medium',
                    sector=cc.ct_sector or 'Unknown',
                    predicted_date=datetime.now() + timedelta(days=14),
                    confidence=0.9,
                    description=f"Unacknowledged {cc.compliance_status} status in {cc.ct_sector} sector. "
                               f"Delta: {cc.delta_percentage:.1f}%",
                    recommended_actions=[
                        "Review and acknowledge compliance status",
                        "Investigate root cause of discrepancy",
                        "Implement corrective measures",
                        "Update compliance documentation"
                    ],
                    current_risk_score=80 if cc.compliance_status == 'non_compliant' else 60,
                    predicted_risk_score=90 if cc.compliance_status == 'non_compliant' else 70
                ))
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error checking compliance risks: {e}")
            return []
    
    def calculate_comprehensive_risk_score(self, sector: Optional[str] = None) -> RiskScore:
        """
        Calculate comprehensive risk score for compliance
        
        Args:
            sector: Optional sector filter
            
        Returns:
            Comprehensive risk score
        """
        try:
            factors = {}
            recommendations = []
            
            # 1. Compliance deviation risk
            compliance_risk = self._calculate_compliance_deviation_risk(sector)
            factors['compliance_deviation'] = compliance_risk
            
            # 2. Data quality risk
            data_quality_risk = self._calculate_data_quality_risk(sector)
            factors['data_quality'] = data_quality_risk
            
            # 3. Trend risk
            trend_risk = self._calculate_trend_risk(sector)
            factors['trend_anomaly'] = trend_risk
            
            # 4. Regulatory exposure risk
            regulatory_risk = self._calculate_regulatory_exposure_risk(sector)
            factors['regulatory_exposure'] = regulatory_risk
            
            # 5. Historical consistency risk
            consistency_risk = self._calculate_historical_consistency_risk(sector)
            factors['historical_consistency'] = consistency_risk
            
            # Calculate weighted overall score
            overall_score = sum(
                factors[key] * self.risk_weights[key] 
                for key in factors.keys()
            )
            
            # Generate recommendations
            recommendations = self._generate_risk_recommendations(factors, overall_score)
            
            return RiskScore(
                overall_score=overall_score,
                compliance_risk=compliance_risk,
                data_quality_risk=data_quality_risk,
                trend_risk=trend_risk,
                regulatory_risk=regulatory_risk,
                factors=factors,
                recommendations=recommendations
            )
            
        except Exception as e:
            logger.error(f"Error calculating comprehensive risk score: {e}")
            return RiskScore(
                overall_score=50,
                compliance_risk=50,
                data_quality_risk=50,
                trend_risk=50,
                regulatory_risk=50,
                factors={},
                recommendations=["Error calculating risk score - manual review required"]
            )
    
    def _calculate_compliance_deviation_risk(self, sector: Optional[str] = None) -> float:
        """Calculate risk based on compliance deviations"""
        try:
            query = self.db.query(ClimateTraceCrosscheck)
            if sector:
                query = query.filter(ClimateTraceCrosscheck.ct_sector == sector)
            
            # Get recent cross-checks
            recent_checks = query.filter(
                ClimateTraceCrosscheck.created_at >= datetime.now() - timedelta(days=30)
            ).all()
            
            if not recent_checks:
                return 30  # Low risk if no recent data
            
            # Calculate average deviation
            deviations = [abs(float(cc.delta_percentage or 0)) for cc in recent_checks]
            avg_deviation = np.mean(deviations)
            
            # Convert to risk score
            if avg_deviation > 20:
                return 90
            elif avg_deviation > 15:
                return 75
            elif avg_deviation > 10:
                return 60
            elif avg_deviation > 5:
                return 40
            else:
                return 20
                
        except Exception as e:
            logger.error(f"Error calculating compliance deviation risk: {e}")
            return 50
    
    def _calculate_data_quality_risk(self, sector: Optional[str] = None) -> float:
        """Calculate risk based on data quality issues"""
        try:
            # Check for unmapped records
            query = self.db.query(EmissionRecord)
            if sector:
                query = query.filter(EmissionRecord.ct_sector == sector)
            
            total_records = query.count()
            unmapped_records = query.filter(EmissionRecord.ct_sector.is_(None)).count()
            
            if total_records == 0:
                return 50
            
            unmapped_percentage = (unmapped_records / total_records) * 100
            
            # Convert to risk score
            if unmapped_percentage > 30:
                return 90
            elif unmapped_percentage > 20:
                return 75
            elif unmapped_percentage > 10:
                return 60
            elif unmapped_percentage > 5:
                return 40
            else:
                return 20
                
        except Exception as e:
            logger.error(f"Error calculating data quality risk: {e}")
            return 50
    
    def _calculate_trend_risk(self, sector: Optional[str] = None) -> float:
        """Calculate risk based on trend analysis"""
        try:
            trends = self.analyze_trends(sector=sector, months_back=6)
            
            if not trends:
                return 30
            
            # Find highest risk trend
            max_risk = 0
            for trend in trends:
                risk_score = self._trend_to_risk_score(trend.last_6_months_avg)
                if trend.risk_level == 'critical':
                    risk_score = min(95, risk_score + 20)
                elif trend.risk_level == 'high':
                    risk_score = min(90, risk_score + 10)
                
                max_risk = max(max_risk, risk_score)
            
            return max_risk
            
        except Exception as e:
            logger.error(f"Error calculating trend risk: {e}")
            return 50
    
    def _calculate_regulatory_exposure_risk(self, sector: Optional[str] = None) -> float:
        """Calculate risk based on regulatory exposure"""
        try:
            # This would integrate with regulatory databases
            # For now, use sector-based risk assessment
            
            high_risk_sectors = ['Power', 'Oil and Gas', 'Manufacturing']
            medium_risk_sectors = ['Transportation', 'Waste']
            
            if sector in high_risk_sectors:
                return 70
            elif sector in medium_risk_sectors:
                return 50
            else:
                return 30
                
        except Exception as e:
            logger.error(f"Error calculating regulatory exposure risk: {e}")
            return 50
    
    def _calculate_historical_consistency_risk(self, sector: Optional[str] = None) -> float:
        """Calculate risk based on historical data consistency"""
        try:
            query = self.db.query(ClimateTraceCrosscheck)
            if sector:
                query = query.filter(ClimateTraceCrosscheck.ct_sector == sector)
            
            # Get last 12 months of data
            recent_checks = query.filter(
                ClimateTraceCrosscheck.created_at >= datetime.now() - timedelta(days=365)
            ).all()
            
            if len(recent_checks) < 6:
                return 60  # Higher risk if insufficient historical data
            
            # Calculate coefficient of variation
            deltas = [float(cc.delta_percentage or 0) for cc in recent_checks]
            if len(deltas) == 0:
                return 50
            
            mean_delta = np.mean(deltas)
            std_delta = np.std(deltas)
            
            if mean_delta == 0:
                cv = 0
            else:
                cv = std_delta / abs(mean_delta)
            
            # Convert to risk score
            if cv > 1.0:
                return 80
            elif cv > 0.5:
                return 60
            elif cv > 0.2:
                return 40
            else:
                return 20
                
        except Exception as e:
            logger.error(f"Error calculating historical consistency risk: {e}")
            return 50
    
    def _generate_risk_recommendations(self, factors: Dict[str, float], 
                                     overall_score: float) -> List[str]:
        """Generate recommendations based on risk factors"""
        recommendations = []
        
        if overall_score > 80:
            recommendations.extend([
                "CRITICAL: Immediate compliance review required",
                "Consider third-party verification",
                "Prepare regulatory response plan",
                "Implement emergency monitoring protocols"
            ])
        elif overall_score > 60:
            recommendations.extend([
                "Schedule compliance review within 30 days",
                "Review and update emission calculation methods",
                "Implement additional data quality checks",
                "Consider external audit"
            ])
        elif overall_score > 40:
            recommendations.extend([
                "Monitor trends closely",
                "Review data quality processes",
                "Update compliance documentation"
            ])
        else:
            recommendations.extend([
                "Continue current monitoring practices",
                "Maintain data quality standards"
            ])
        
        # Add specific recommendations based on risk factors
        if factors.get('compliance_deviation', 0) > 70:
            recommendations.append("Investigate and resolve emission calculation discrepancies")
        
        if factors.get('data_quality', 0) > 70:
            recommendations.append("Improve data collection and mapping processes")
        
        if factors.get('trend_anomaly', 0) > 70:
            recommendations.append("Address underlying causes of emission trend anomalies")
        
        return recommendations
