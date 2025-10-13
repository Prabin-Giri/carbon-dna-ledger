"""
Advanced Compliance Dashboard - Industry-Level Compliance Analysis
Provides comprehensive compliance analysis, ROI calculations, and regulatory readiness
"""
import streamlit as st
import requests
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any
import numpy as np

def show_advanced_compliance_dashboard(api_base: str):
    """Main comprehensive compliance dashboard page"""
    st.title("🛡️ Compliance Intelligence Dashboard")
    st.markdown("**Industry-level compliance analysis with ROI insights, regulatory readiness, and audit management**")
    
    # Create tabs for different compliance views
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
        "📊 Executive Summary", 
        "🔍 Gap Analysis", 
        "💰 ROI Calculator",
        "📈 Readiness Assessment",
        "🗺️ Compliance Roadmap",
        "📊 Industry Benchmark",
        "🔍 Audit Snapshots",
        "📋 Compliance Rules"
    ])
    
    with tab1:
        show_executive_summary(api_base)
    
    with tab2:
        show_gap_analysis(api_base)
    
    with tab3:
        show_roi_calculator(api_base)
    
    with tab4:
        show_readiness_assessment(api_base)
    
    with tab5:
        show_compliance_roadmap(api_base)
    
    with tab6:
        show_industry_benchmark(api_base)
    
    with tab7:
        show_audit_snapshots(api_base)
    
    with tab8:
        show_compliance_rules(api_base)

def show_executive_summary(api_base: str):
    """Show executive summary with key compliance metrics"""
    st.subheader("📊 Executive Compliance Summary")
    
    # Framework selection
    frameworks = ["EPA", "EU_ETS", "TCFD", "SEC", "CARB"]
    selected_frameworks = st.multiselect(
        "Select Regulatory Frameworks",
        frameworks,
        default=frameworks[:3],
        help="Select frameworks to analyze"
    )
    
    if not selected_frameworks:
        st.warning("Please select at least one regulatory framework.")
        return
    
    # Get readiness assessments for selected frameworks
    readiness_data = {}
    total_gaps = 0
    total_cost = 0
    avg_readiness = 0
    
    for framework in selected_frameworks:
        try:
            response = requests.get(f"{api_base}/api/advanced-compliance/readiness/{framework}", timeout=10)
            if response.status_code == 200:
                data = response.json()
                readiness_data[framework] = data['readiness_assessment']
                total_gaps += len(data['readiness_assessment']['missing_requirements'])
                total_cost += data['readiness_assessment']['estimated_cost']
                avg_readiness += data['readiness_assessment']['readiness_score']
        except Exception as e:
            st.error(f"Error loading {framework} readiness: {e}")
    
    if readiness_data:
        avg_readiness = avg_readiness / len(readiness_data)
        
        # Key metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="Average Readiness Score",
                value=f"{avg_readiness:.1f}/100",
                delta=f"{'Excellent' if avg_readiness >= 90 else 'Good' if avg_readiness >= 70 else 'Needs Improvement'}"
            )
        
        with col2:
            st.metric(
                label="Total Compliance Gaps",
                value=f"{total_gaps}",
                delta=f"Across {len(selected_frameworks)} frameworks"
            )
        
        with col3:
            st.metric(
                label="Estimated Investment",
                value=f"${total_cost:,.0f}",
                delta="Total compliance cost"
            )
        
        with col4:
            high_risk_frameworks = len([f for f, data in readiness_data.items() if data['risk_level'] in ['high', 'critical']])
            st.metric(
                label="High Risk Frameworks",
                value=f"{high_risk_frameworks}",
                delta=f"Out of {len(selected_frameworks)} frameworks"
            )
        
        # Framework readiness comparison
        st.subheader("📈 Framework Readiness Comparison")
        
        framework_df = pd.DataFrame([
            {
                'Framework': framework,
                'Readiness Score': data['readiness_score'],
                'Compliance Rate': data['compliance_rate'],
                'Risk Level': data['risk_level'],
                'Estimated Cost': data['estimated_cost'],
                'Preparation Time (days)': data['estimated_preparation_time']
            }
            for framework, data in readiness_data.items()
        ])
        
        # Readiness score chart
        fig_readiness = px.bar(
            framework_df,
            x='Framework',
            y='Readiness Score',
            title="Readiness Score by Framework",
            color='Readiness Score',
            color_continuous_scale='RdYlGn',
            range_color=[0, 100]
        )
        fig_readiness.add_hline(y=70, line_dash="dash", line_color="orange", 
                               annotation_text="Minimum Readiness Threshold")
        fig_readiness.add_hline(y=90, line_dash="dash", line_color="green", 
                               annotation_text="Excellent Readiness")
        st.plotly_chart(fig_readiness, width='stretch')
        
        # Risk level distribution
        risk_counts = framework_df['Risk Level'].value_counts()
        fig_risk = px.pie(
            values=risk_counts.values,
            names=risk_counts.index,
            title="Risk Level Distribution",
            color_discrete_map={
                'low': '#2E8B57',
                'medium': '#FFD700',
                'high': '#FF6347',
                'critical': '#8B0000'
            }
        )
        st.plotly_chart(fig_risk, width='stretch')
        
        # Cost vs Readiness scatter
        fig_scatter = px.scatter(
            framework_df,
            x='Readiness Score',
            y='Estimated Cost',
            size='Preparation Time (days)',
            color='Risk Level',
            hover_name='Framework',
            title="Investment vs Readiness Score",
            color_discrete_map={
                'low': '#2E8B57',
                'medium': '#FFD700',
                'high': '#FF6347',
                'critical': '#8B0000'
            }
        )
        st.plotly_chart(fig_scatter, width='stretch')
        
        # Detailed framework table
        st.subheader("📋 Detailed Framework Analysis")
        st.dataframe(
            framework_df,
            width='stretch',
            column_config={
                "Readiness Score": st.column_config.NumberColumn(
                    "Readiness Score",
                    format="%.1f",
                    help="Readiness score out of 100"
                ),
                "Compliance Rate": st.column_config.NumberColumn(
                    "Compliance Rate",
                    format="%.1f%%",
                    help="Percentage of compliant records"
                ),
                "Estimated Cost": st.column_config.NumberColumn(
                    "Estimated Cost",
                    format="$%.0f",
                    help="Estimated cost to achieve compliance"
                ),
                "Preparation Time (days)": st.column_config.NumberColumn(
                    "Prep Time (days)",
                    format="%d",
                    help="Estimated preparation time in days"
                )
            }
        )

def show_gap_analysis(api_base: str):
    """Show detailed compliance gap analysis"""
    st.subheader("🔍 Compliance Gap Analysis")
    
    # Framework selection
    framework = st.selectbox(
        "Select Regulatory Framework",
        ["EPA", "EU_ETS", "TCFD", "SEC", "CARB"],
        help="Select framework for gap analysis"
    )
    
    if st.button("Analyze Compliance Gaps", type="primary"):
        try:
            response = requests.get(f"{api_base}/api/advanced-compliance/gaps/{framework}", timeout=15)
            response.raise_for_status()
            data = response.json()
            
            if data['total_gaps'] == 0:
                st.success(f"✅ No compliance gaps found for {framework}!")
                return
            
            # Summary metrics
            summary = data['summary']
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    label="Critical Gaps",
                    value=summary['critical_gaps'],
                    delta="Immediate action required"
                )
            
            with col2:
                st.metric(
                    label="High Priority Gaps",
                    value=summary['high_gaps'],
                    delta="Address within 30 days"
                )
            
            with col3:
                st.metric(
                    label="Total Affected Records",
                    value=f"{summary['total_affected_records']:,}",
                    delta="Records needing attention"
                )
            
            with col4:
                st.metric(
                    label="Total Investment Required",
                    value=f"${summary['total_estimated_cost']:,.0f}",
                    delta=f"{summary['total_estimated_time']} days"
                )
            
            # Gap severity distribution
            severity_counts = {
                'Critical': summary['critical_gaps'],
                'High': summary['high_gaps'],
                'Medium': summary['medium_gaps'],
                'Low': summary['low_gaps']
            }
            
            fig_severity = px.bar(
                x=list(severity_counts.keys()),
                y=list(severity_counts.values()),
                title="Gap Distribution by Severity",
                color=list(severity_counts.keys()),
                color_discrete_map={
                    'Critical': '#8B0000',
                    'High': '#FF6347',
                    'Medium': '#FFD700',
                    'Low': '#2E8B57'
                }
            )
            st.plotly_chart(fig_severity, width='stretch')
            
            # Detailed gap analysis
            st.subheader("📋 Detailed Gap Analysis")
            
            gaps_df = pd.DataFrame(data['gaps'])
            
            # Sort by priority score
            gaps_df = gaps_df.sort_values('priority_score', ascending=False)
            
            # Display gaps with expandable details
            for idx, gap in gaps_df.iterrows():
                with st.expander(f"**{gap['requirement'].replace('_', ' ').title()}** - {gap['severity'].upper()} (Priority: {gap['priority_score']:.1f})"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**Description:** {gap['gap_description']}")
                        st.write(f"**Affected Records:** {gap['affected_records']:,}")
                        st.write(f"**Estimated Cost:** ${gap['estimated_cost']:,.0f}")
                        st.write(f"**Estimated Time:** {gap['estimated_time']} days")
                        st.write(f"**ROI Impact:** {gap['roi_impact']:.1f}%")
                    
                    with col2:
                        st.write("**Remediation Actions:**")
                        for action in gap['remediation_actions']:
                            st.write(f"• {action}")
                        
                        # Priority indicator
                        if gap['severity'] == 'critical':
                            st.error("🚨 CRITICAL: Address immediately")
                        elif gap['severity'] == 'high':
                            st.warning("⚠️ HIGH: Address within 30 days")
                        elif gap['severity'] == 'medium':
                            st.info("ℹ️ MEDIUM: Address within 90 days")
                        else:
                            st.success("✅ LOW: Address when resources available")
            
            # Gap prioritization matrix
            st.subheader("📊 Gap Prioritization Matrix")
            
            fig_matrix = px.scatter(
                gaps_df,
                x='estimated_cost',
                y='priority_score',
                size='affected_records',
                color='severity',
                hover_name='requirement',
                title="Gap Prioritization Matrix (Cost vs Priority)",
                color_discrete_map={
                    'critical': '#8B0000',
                    'high': '#FF6347',
                    'medium': '#FFD700',
                    'low': '#2E8B57'
                }
            )
            fig_matrix.update_layout(
                xaxis_title="Estimated Cost ($)",
                yaxis_title="Priority Score"
            )
            st.plotly_chart(fig_matrix, width='stretch')
            
        except requests.exceptions.RequestException as e:
            st.error(f"Error connecting to API: {e}")
        except Exception as e:
            st.error(f"Error analyzing compliance gaps: {e}")

def show_roi_calculator(api_base: str):
    """Show ROI calculator for compliance investments"""
    st.subheader("💰 Compliance ROI Calculator")
    
    col1, col2 = st.columns(2)
    
    with col1:
        framework = st.selectbox(
            "Select Regulatory Framework",
            ["EPA", "EU_ETS", "TCFD", "SEC", "CARB"],
            help="Select framework for ROI calculation"
        )
    
    with col2:
        investment_amount = st.number_input(
            "Investment Amount ($)",
            min_value=1000,
            max_value=10000000,
            value=100000,
            step=10000,
            help="Total investment amount for compliance"
        )
    
    time_horizon = st.slider(
        "Time Horizon (months)",
        min_value=6,
        max_value=36,
        value=12,
        help="Time horizon for ROI calculation"
    )
    
    if st.button("Calculate ROI", type="primary"):
        try:
            response = requests.get(
                f"{api_base}/api/advanced-compliance/roi/{framework}",
                params={
                    'investment_amount': investment_amount,
                    'time_horizon_months': time_horizon
                },
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            roi_analysis = data['roi_analysis']
            breakdown = data['breakdown']
            
            # Key ROI metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    label="Total ROI",
                    value=f"{roi_analysis['total_roi']:.1f}%",
                    delta=f"Over {time_horizon} months"
                )
            
            with col2:
                st.metric(
                    label="Payback Period",
                    value=f"{roi_analysis['payback_period']} months",
                    delta="Time to recover investment"
                )
            
            with col3:
                st.metric(
                    label="Net Benefit",
                    value=f"${breakdown['net_benefit']:,.0f}",
                    delta="Total benefits minus investment"
                )
            
            with col4:
                st.metric(
                    label="Risk Reduction",
                    value=f"{roi_analysis['risk_reduction']:.1f}%",
                    delta="Compliance risk reduction"
                )
            
            # ROI breakdown
            st.subheader("📊 ROI Breakdown")
            
            benefits_data = {
                'Compliance Cost Savings': roi_analysis['compliance_cost_savings'],
                'Penalty Avoidance': roi_analysis['penalty_avoidance'],
                'Operational Efficiency': roi_analysis['operational_efficiency'],
                'Reputation Value': roi_analysis['reputation_value']
            }
            
            # Benefits pie chart
            fig_benefits = px.pie(
                values=list(benefits_data.values()),
                names=list(benefits_data.keys()),
                title="ROI Benefits Breakdown",
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            st.plotly_chart(fig_benefits, width='stretch')
            
            # Benefits bar chart
            fig_benefits_bar = px.bar(
                x=list(benefits_data.keys()),
                y=list(benefits_data.values()),
                title="ROI Benefits by Category",
                color=list(benefits_data.keys()),
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            fig_benefits_bar.update_layout(
                xaxis_title="Benefit Category",
                yaxis_title="Value ($)",
                showlegend=False
            )
            st.plotly_chart(fig_benefits_bar, width='stretch')
            
            # Investment vs Benefits comparison
            st.subheader("💡 Investment vs Benefits Analysis")
            
            comparison_data = {
                'Investment': investment_amount,
                'Total Benefits': breakdown['total_benefits'],
                'Net Benefit': breakdown['net_benefit']
            }
            
            fig_comparison = px.bar(
                x=list(comparison_data.keys()),
                y=list(comparison_data.values()),
                title="Investment vs Benefits Comparison",
                color=list(comparison_data.keys()),
                color_discrete_map={
                    'Investment': '#FF6347',
                    'Total Benefits': '#2E8B57',
                    'Net Benefit': '#32CD32'
                }
            )
            fig_comparison.update_layout(
                xaxis_title="Category",
                yaxis_title="Amount ($)",
                showlegend=False
            )
            st.plotly_chart(fig_comparison, width='stretch')
            
            # ROI timeline projection
            st.subheader("📈 ROI Timeline Projection")
            
            months = list(range(1, time_horizon + 1))
            cumulative_benefits = []
            cumulative_roi = []
            
            monthly_benefits = breakdown['total_benefits'] / time_horizon
            
            for month in months:
                cumulative_benefit = monthly_benefits * month
                cumulative_benefits.append(cumulative_benefit)
                roi = ((cumulative_benefit - investment_amount) / investment_amount) * 100
                cumulative_roi.append(roi)
            
            timeline_df = pd.DataFrame({
                'Month': months,
                'Cumulative Benefits': cumulative_benefits,
                'Cumulative ROI': cumulative_roi
            })
            
            fig_timeline = go.Figure()
            fig_timeline.add_trace(go.Scatter(
                x=timeline_df['Month'],
                y=timeline_df['Cumulative ROI'],
                mode='lines+markers',
                name='Cumulative ROI (%)',
                line=dict(color='#2E8B57', width=3)
            ))
            fig_timeline.add_hline(y=0, line_dash="dash", line_color="red", 
                                 annotation_text="Break-even Point")
            fig_timeline.update_layout(
                title="ROI Timeline Projection",
                xaxis_title="Month",
                yaxis_title="Cumulative ROI (%)",
                height=400
            )
            st.plotly_chart(fig_timeline, width='stretch')
            
            # Recommendations
            st.subheader("🎯 Investment Recommendations")
            
            if roi_analysis['total_roi'] > 200:
                st.success("🚀 **EXCELLENT ROI**: This investment shows exceptional returns. Strongly recommended.")
            elif roi_analysis['total_roi'] > 100:
                st.success("✅ **GOOD ROI**: This investment shows good returns. Recommended.")
            elif roi_analysis['total_roi'] > 50:
                st.warning("⚠️ **MODERATE ROI**: This investment shows moderate returns. Consider carefully.")
            else:
                st.error("❌ **LOW ROI**: This investment shows low returns. Consider alternatives.")
            
            if roi_analysis['payback_period'] <= 12:
                st.info("💰 **Quick Payback**: Investment will be recovered within 12 months.")
            elif roi_analysis['payback_period'] <= 24:
                st.info("⏰ **Medium Payback**: Investment will be recovered within 24 months.")
            else:
                st.warning("🐌 **Long Payback**: Investment will take more than 24 months to recover.")
            
        except requests.exceptions.RequestException as e:
            st.error(f"Error connecting to API: {e}")
        except Exception as e:
            st.error(f"Error calculating ROI: {e}")

def show_readiness_assessment(api_base: str):
    """Show regulatory readiness assessment"""
    st.subheader("📈 Regulatory Readiness Assessment")
    
    framework = st.selectbox(
        "Select Regulatory Framework",
        ["EPA", "EU_ETS", "TCFD", "SEC", "CARB"],
        help="Select framework for readiness assessment"
    )
    
    if st.button("Assess Readiness", type="primary"):
        try:
            response = requests.get(f"{api_base}/api/advanced-compliance/readiness/{framework}", timeout=10)
            response.raise_for_status()
            data = response.json()
            
            assessment = data['readiness_assessment']
            recommendations = data['recommendations']
            
            # Readiness score with visual indicator
            st.subheader("🎯 Readiness Score")
            
            readiness_score = assessment['readiness_score']
            
            # Create a gauge chart
            fig_gauge = go.Figure(go.Indicator(
                mode = "gauge+number+delta",
                value = readiness_score,
                domain = {'x': [0, 1], 'y': [0, 1]},
                title = {'text': f"{framework} Readiness Score"},
                delta = {'reference': 70},
                gauge = {
                    'axis': {'range': [None, 100]},
                    'bar': {'color': "darkblue"},
                    'steps': [
                        {'range': [0, 50], 'color': "lightgray"},
                        {'range': [50, 70], 'color': "yellow"},
                        {'range': [70, 90], 'color': "lightgreen"},
                        {'range': [90, 100], 'color': "green"}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 70
                    }
                }
            ))
            
            fig_gauge.update_layout(height=400)
            st.plotly_chart(fig_gauge, width='stretch')
            
            # Key metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    label="Compliance Rate",
                    value=f"{assessment['compliance_rate']:.1f}%",
                    delta="Records compliant"
                )
            
            with col2:
                st.metric(
                    label="Missing Requirements",
                    value=len(assessment['missing_requirements']),
                    delta="Requirements to address"
                )
            
            with col3:
                st.metric(
                    label="Critical Gaps",
                    value=len(assessment['critical_gaps']),
                    delta="Immediate attention needed"
                )
            
            with col4:
                st.metric(
                    label="Risk Level",
                    value=assessment['risk_level'].upper(),
                    delta=f"{assessment['estimated_cost']:,.0f} investment"
                )
            
            # Risk level indicator
            risk_colors = {
                'low': '🟢',
                'medium': '🟡',
                'high': '🟠',
                'critical': '🔴'
            }
            
            st.markdown(f"### {risk_colors.get(assessment['risk_level'], '⚪')} Risk Level: {assessment['risk_level'].upper()}")
            
            # Preparation timeline
            st.subheader("⏰ Preparation Timeline")
            
            prep_time = assessment['estimated_preparation_time']
            prep_cost = assessment['estimated_cost']
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric(
                    label="Estimated Preparation Time",
                    value=f"{prep_time} days",
                    delta=f"{prep_time/30:.1f} months"
                )
            
            with col2:
                st.metric(
                    label="Estimated Investment",
                    value=f"${prep_cost:,.0f}",
                    delta=f"${prep_cost/prep_time:.0f}/day"
                )
            
            # Timeline visualization
            if prep_time > 0:
                timeline_data = {
                    'Phase': ['Planning', 'Implementation', 'Testing', 'Submission'],
                    'Duration (days)': [
                        prep_time * 0.2,
                        prep_time * 0.5,
                        prep_time * 0.2,
                        prep_time * 0.1
                    ]
                }
                
                fig_timeline = px.bar(
                    timeline_data,
                    x='Phase',
                    y='Duration (days)',
                    title="Preparation Timeline Breakdown",
                    color='Phase',
                    color_discrete_sequence=px.colors.qualitative.Set2
                )
                st.plotly_chart(fig_timeline, width='stretch')
            
            # Missing requirements
            if assessment['missing_requirements']:
                st.subheader("📋 Missing Requirements")
                
                requirements_df = pd.DataFrame({
                    'Requirement': assessment['missing_requirements']
                })
                
                st.dataframe(
                    requirements_df,
                    width='stretch',
                    hide_index=True
                )
            
            # Critical gaps
            if assessment['critical_gaps']:
                st.subheader("🚨 Critical Gaps")
                
                for gap in assessment['critical_gaps']:
                    st.error(f"• {gap}")
            
            # Recommendations
            st.subheader("💡 Recommendations")
            
            for recommendation in recommendations:
                if "EXCELLENT" in recommendation:
                    st.success(recommendation)
                elif "CRITICAL" in recommendation or "POOR" in recommendation:
                    st.error(recommendation)
                elif "HIGH" in recommendation or "GOOD" in recommendation:
                    st.warning(recommendation)
                else:
                    st.info(recommendation)
            
            # Action plan
            st.subheader("📝 Recommended Action Plan")
            
            if readiness_score >= 90:
                st.success("🎉 **Ready for Submission**: Your organization is well-prepared for regulatory submission.")
                st.info("**Next Steps:**\n- Final review of documentation\n- Submit to regulatory authority\n- Monitor for any follow-up requirements")
            elif readiness_score >= 70:
                st.warning("⚠️ **Almost Ready**: Minor improvements needed before submission.")
                st.info("**Next Steps:**\n- Address remaining gaps\n- Complete missing documentation\n- Conduct final review")
            elif readiness_score >= 50:
                st.error("🔧 **Significant Work Required**: Substantial improvements needed.")
                st.info("**Next Steps:**\n- Prioritize critical gaps\n- Allocate resources for compliance\n- Develop detailed action plan")
            else:
                st.error("🚨 **Major Compliance Issues**: Immediate action required.")
                st.info("**Next Steps:**\n- Emergency compliance review\n- Allocate maximum resources\n- Consider external consultants")
            
        except requests.exceptions.RequestException as e:
            st.error(f"Error connecting to API: {e}")
        except Exception as e:
            st.error(f"Error assessing readiness: {e}")

def show_compliance_roadmap(api_base: str):
    """Show compliance roadmap generator"""
    st.subheader("🗺️ Compliance Roadmap Generator")
    
    # Framework selection
    available_frameworks = ["EPA", "EU_ETS", "TCFD", "SEC", "CARB"]
    selected_frameworks = st.multiselect(
        "Select Frameworks for Roadmap",
        available_frameworks,
        default=available_frameworks[:3],
        help="Select multiple frameworks to create a comprehensive roadmap"
    )
    
    # Budget constraint
    budget_constraint = st.number_input(
        "Budget Constraint ($)",
        min_value=10000,
        max_value=5000000,
        value=100000,
        step=10000,
        help="Total budget available for compliance investments"
    )
    
    if st.button("Generate Roadmap", type="primary"):
        if not selected_frameworks:
            st.warning("Please select at least one framework.")
            return
        
        try:
            response = requests.post(
                f"{api_base}/api/advanced-compliance/roadmap",
                json={
                    'frameworks': selected_frameworks,
                    'budget_constraint': budget_constraint
                },
                timeout=15
            )
            response.raise_for_status()
            data = response.json()
            
            roadmap = data['roadmap']
            
            # Budget allocation summary
            st.subheader("💰 Budget Allocation Summary")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric(
                    label="Total Budget",
                    value=f"${roadmap['total_budget']:,.0f}",
                    delta="Available budget"
                )
            
            with col2:
                st.metric(
                    label="Allocated Budget",
                    value=f"${roadmap['allocated_budget']:,.0f}",
                    delta=f"{roadmap['allocated_budget']/roadmap['total_budget']*100:.1f}% of budget"
                )
            
            with col3:
                st.metric(
                    label="Remaining Budget",
                    value=f"${roadmap['remaining_budget']:,.0f}",
                    delta="Unallocated funds"
                )
            
            # Framework analysis
            st.subheader("📊 Framework Analysis")
            
            if roadmap['frameworks']:
                framework_df = pd.DataFrame([
                    {
                        'Framework': framework,
                        'Readiness Score': data['readiness_score'],
                        'Compliance Rate': data['compliance_rate'],
                        'Estimated Cost': data['estimated_cost'],
                        'Estimated Time': data['estimated_time'],
                        'Risk Level': data['risk_level']
                    }
                    for framework, data in roadmap['frameworks'].items()
                ])
                
                st.dataframe(
                    framework_df,
                    width='stretch',
                    column_config={
                        "Readiness Score": st.column_config.NumberColumn(
                            "Readiness Score",
                            format="%.1f"
                        ),
                        "Compliance Rate": st.column_config.NumberColumn(
                            "Compliance Rate",
                            format="%.1f%%"
                        ),
                        "Estimated Cost": st.column_config.NumberColumn(
                            "Estimated Cost",
                            format="$%.0f"
                        ),
                        "Estimated Time": st.column_config.NumberColumn(
                            "Estimated Time",
                            format="%d days"
                        )
                    }
                )
            
            # Priority actions
            st.subheader("🎯 Priority Actions")
            
            if roadmap['priority_actions']:
                for i, action in enumerate(roadmap['priority_actions'], 1):
                    with st.expander(f"**{i}. {action['framework']}** - {action['action']}"):
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.metric("Cost", f"${action['cost']:,.0f}")
                        
                        with col2:
                            st.metric("Time", f"{action['time']} days")
                        
                        with col3:
                            st.metric("Priority Score", f"{action['priority_score']:.1f}")
            
            # Timeline
            st.subheader("📅 Implementation Timeline")
            
            if roadmap['timeline']:
                timeline_df = pd.DataFrame(roadmap['timeline'])
                timeline_df['start_date'] = pd.to_datetime(timeline_df['start_date'])
                timeline_df['end_date'] = pd.to_datetime(timeline_df['end_date'])
                
                # Gantt chart
                fig_gantt = px.timeline(
                    timeline_df,
                    x_start='start_date',
                    x_end='end_date',
                    y='framework',
                    color='framework',
                    title="Compliance Implementation Timeline",
                    hover_data=['action', 'duration_days']
                )
                fig_gantt.update_layout(
                    height=400,
                    xaxis_title="Timeline",
                    yaxis_title="Framework"
                )
                st.plotly_chart(fig_gantt, width='stretch')
                
                # Timeline table
                st.dataframe(
                    timeline_df,
                    width='stretch',
                    column_config={
                        "start_date": st.column_config.DatetimeColumn(
                            "Start Date",
                            format="YYYY-MM-DD"
                        ),
                        "end_date": st.column_config.DatetimeColumn(
                            "End Date",
                            format="YYYY-MM-DD"
                        ),
                        "duration_days": st.column_config.NumberColumn(
                            "Duration (days)",
                            format="%d"
                        )
                    }
                )
            
            # Expected ROI
            st.subheader("💰 Expected ROI")
            
            expected_roi = roadmap['expected_roi']
            
            if expected_roi > 200:
                st.success(f"🚀 **Expected ROI: {expected_roi:.1f}%** - Exceptional returns expected!")
            elif expected_roi > 100:
                st.success(f"✅ **Expected ROI: {expected_roi:.1f}%** - Good returns expected!")
            elif expected_roi > 50:
                st.warning(f"⚠️ **Expected ROI: {expected_roi:.1f}%** - Moderate returns expected.")
            else:
                st.error(f"❌ **Expected ROI: {expected_roi:.1f}%** - Low returns expected.")
            
            # Recommendations
            st.subheader("💡 Roadmap Recommendations")
            
            if roadmap['allocated_budget'] < roadmap['total_budget'] * 0.8:
                st.info("💡 **Budget Optimization**: Consider allocating more budget to maximize compliance benefits.")
            
            if len(roadmap['priority_actions']) < len(selected_frameworks):
                st.warning("⚠️ **Limited Scope**: Not all frameworks could be addressed within budget constraints.")
            
            if expected_roi > 150:
                st.success("🎯 **High ROI Opportunity**: This roadmap shows excellent return potential.")
            
            # Export roadmap
            if st.button("Export Roadmap"):
                roadmap_json = json.dumps(roadmap, indent=2, default=str)
                st.download_button(
                    label="Download Roadmap JSON",
                    data=roadmap_json,
                    file_name=f"compliance_roadmap_{datetime.now().strftime('%Y%m%d')}.json",
                    mime="application/json"
                )
            
        except requests.exceptions.RequestException as e:
            st.error(f"Error connecting to API: {e}")
        except Exception as e:
            st.error(f"Error generating roadmap: {e}")

def show_industry_benchmark(api_base: str):
    """Show industry benchmarking"""
    st.subheader("📊 Industry Benchmarking")
    
    # Industry selection
    industry = st.selectbox(
        "Select Industry",
        ["manufacturing", "energy", "transportation", "technology"],
        help="Select your industry for benchmarking"
    )
    
    if st.button("Get Benchmark", type="primary"):
        try:
            response = requests.get(
                f"{api_base}/api/advanced-compliance/benchmark",
                params={'industry': industry},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            if 'error' in data:
                st.error(f"Error: {data['error']}")
                return
            
            benchmark_data = data['benchmark_data']
            company_performance = data['company_performance']
            recommendations = data['recommendations']
            
            # Industry overview
            st.subheader(f"🏭 {industry.title()} Industry Overview")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    label="Industry Avg Compliance Score",
                    value=f"{benchmark_data['average_compliance_score']:.1f}/100",
                    delta="Industry benchmark"
                )
            
            with col2:
                st.metric(
                    label="Industry Avg Cost/Record",
                    value=f"${benchmark_data['average_compliance_cost_per_record']:.0f}",
                    delta="Per record cost"
                )
            
            with col3:
                st.metric(
                    label="Industry Avg Verification Rate",
                    value=f"{benchmark_data['average_verification_rate']:.1f}%",
                    delta="Verification benchmark"
                )
            
            with col4:
                st.metric(
                    label="Industry Avg ROI",
                    value=f"{benchmark_data['average_roi']:.1f}%",
                    delta="Return on investment"
                )
            
            # Company vs Industry comparison
            st.subheader("📈 Company vs Industry Performance")
            
            # Compliance score comparison
            compliance_comparison = company_performance['compliance_score']
            
            fig_compliance = go.Figure()
            fig_compliance.add_trace(go.Bar(
                name='Your Company',
                x=['Compliance Score'],
                y=[compliance_comparison['company']],
                marker_color='#2E8B57' if compliance_comparison['performance'] == 'above' else '#FF6347'
            ))
            fig_compliance.add_trace(go.Bar(
                name='Industry Average',
                x=['Compliance Score'],
                y=[compliance_comparison['industry_average']],
                marker_color='lightgray'
            ))
            fig_compliance.update_layout(
                title="Compliance Score Comparison",
                yaxis_title="Score",
                barmode='group'
            )
            st.plotly_chart(fig_compliance, width='stretch')
            
            # Verification rate comparison
            verification_comparison = company_performance['verification_rate']
            
            fig_verification = go.Figure()
            fig_verification.add_trace(go.Bar(
                name='Your Company',
                x=['Verification Rate'],
                y=[verification_comparison['company']],
                marker_color='#2E8B57' if verification_comparison['performance'] == 'above' else '#FF6347'
            ))
            fig_verification.add_trace(go.Bar(
                name='Industry Average',
                x=['Verification Rate'],
                y=[verification_comparison['industry_average']],
                marker_color='lightgray'
            ))
            fig_verification.update_layout(
                title="Verification Rate Comparison",
                yaxis_title="Rate (%)",
                barmode='group'
            )
            st.plotly_chart(fig_verification, width='stretch')
            
            # Performance summary
            st.subheader("📊 Performance Summary")
            
            performance_df = pd.DataFrame([
                {
                    'Metric': 'Compliance Score',
                    'Your Company': compliance_comparison['company'],
                    'Industry Average': compliance_comparison['industry_average'],
                    'Gap': compliance_comparison['gap'],
                    'Performance': compliance_comparison['performance'].title()
                },
                {
                    'Metric': 'Verification Rate',
                    'Your Company': verification_comparison['company'],
                    'Industry Average': verification_comparison['industry_average'],
                    'Gap': verification_comparison['gap'],
                    'Performance': verification_comparison['performance'].title()
                }
            ])
            
            st.dataframe(
                performance_df,
                width='stretch',
                column_config={
                    "Your Company": st.column_config.NumberColumn(
                        "Your Company",
                        format="%.1f"
                    ),
                    "Industry Average": st.column_config.NumberColumn(
                        "Industry Average",
                        format="%.1f"
                    ),
                    "Gap": st.column_config.NumberColumn(
                        "Gap",
                        format="%.1f"
                    )
                }
            )
            
            # Industry insights
            st.subheader("💡 Industry Insights")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric(
                    label="Penalty Frequency",
                    value=f"{benchmark_data['average_penalty_frequency']*100:.1f}%",
                    delta="Companies facing penalties"
                )
            
            with col2:
                st.metric(
                    label="Industry ROI",
                    value=f"{benchmark_data['average_roi']:.1f}%",
                    delta="Average return on investment"
                )
            
            # Recommendations
            st.subheader("🎯 Benchmarking Recommendations")
            
            for recommendation in recommendations:
                if "EXCELLENT" in recommendation:
                    st.success(recommendation)
                elif "CRITICAL" in recommendation or "HIGH PRIORITY" in recommendation:
                    st.error(recommendation)
                elif "MEDIUM PRIORITY" in recommendation:
                    st.warning(recommendation)
                else:
                    st.info(recommendation)
            
            # Competitive positioning
            st.subheader("🏆 Competitive Positioning")
            
            # Calculate overall performance score
            compliance_performance = 1 if compliance_comparison['performance'] == 'above' else 0
            verification_performance = 1 if verification_comparison['performance'] == 'above' else 0
            overall_score = (compliance_performance + verification_performance) / 2 * 100
            
            if overall_score >= 75:
                st.success(f"🎉 **Competitive Advantage**: Your company performs above industry average in {overall_score:.0f}% of key metrics!")
            elif overall_score >= 50:
                st.warning(f"⚖️ **Industry Parity**: Your company performs at industry average in {overall_score:.0f}% of key metrics.")
            else:
                st.error(f"📉 **Below Industry Average**: Your company performs below industry average in {overall_score:.0f}% of key metrics.")
            
            # Action items
            st.subheader("📝 Action Items")
            
            if compliance_comparison['performance'] == 'below':
                gap = abs(compliance_comparison['gap'])
                st.info(f"🔧 **Improve Compliance Score**: Focus on closing the {gap:.1f} point gap with industry average.")
            
            if verification_comparison['performance'] == 'below':
                gap = abs(verification_comparison['gap'])
                st.info(f"✅ **Increase Verification Rate**: Work on improving verification rate by {gap:.1f} percentage points.")
            
            if benchmark_data['average_roi'] > 200:
                st.info(f"💰 **ROI Opportunity**: Industry shows {benchmark_data['average_roi']:.1f}% average ROI. Consider compliance investments.")
            
        except requests.exceptions.RequestException as e:
            st.error(f"Error connecting to API: {e}")
        except Exception as e:
            st.error(f"Error getting benchmark: {e}")

def show_audit_snapshots(api_base: str):
    """Show audit snapshots management"""
    st.subheader("🔍 Audit Snapshots Management")
    
    # Create new snapshot section
    st.markdown("### Create New Audit Snapshot")
    
    # Data availability info
    st.info("💡 **Data Availability**: Your emission data spans January-March 2025. Click '📅 Q1 2025' for the best results with 250+ records!")
    
    col1, col2 = st.columns(2)
    
    with col1:
        submission_type = st.selectbox(
            "Submission Type",
            ["EPA", "EU_ETS", "CARB", "TCFD", "SEC"],
            help="Select the regulatory framework for this submission"
        )
    
    with col2:
        reporting_period = st.selectbox(
            "Reporting Period",
            ["2025", "2024", "2023", "2022", "2021"],
            help="Select the reporting year"
        )
    
    col3, col4 = st.columns(2)
    
    with col3:
        # Set default dates based on reporting period
        if reporting_period == "2025":
            default_start = date(2025, 1, 1)
            default_end = date(2025, 3, 31)  # Q1 2025 where your data is
        else:
            default_start = date(int(reporting_period), 1, 1)
            default_end = date(int(reporting_period), 12, 31)
            
        start_date = st.date_input(
            "Reporting Period Start",
            value=default_start,
            help="Start date of the reporting period"
        )
    
    with col4:
        end_date = st.date_input(
            "Reporting Period End",
            value=default_end,
            help="End date of the reporting period"
        )
    
    # Quick preset buttons
    st.markdown("**Quick Date Presets:**")
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        if st.button("📅 Q1 2025", help="January-March 2025 (has data)", type="primary"):
            st.session_state.audit_start_date = date(2025, 1, 1)
            st.session_state.audit_end_date = date(2025, 3, 31)
            st.rerun()
    
    with col2:
        if st.button("📅 Jan 2025", help="January 2025 only"):
            st.session_state.audit_start_date = date(2025, 1, 1)
            st.session_state.audit_end_date = date(2025, 1, 31)
            st.rerun()
    
    with col3:
        if st.button("📅 Feb 2025", help="February 2025 only"):
            st.session_state.audit_start_date = date(2025, 2, 1)
            st.session_state.audit_end_date = date(2025, 2, 28)
            st.rerun()
    
    with col4:
        if st.button("📅 Mar 2025", help="March 2025 only"):
            st.session_state.audit_start_date = date(2025, 3, 1)
            st.session_state.audit_end_date = date(2025, 3, 31)
            st.rerun()
    
    with col5:
        if st.button("📅 Full 2025", help="January-December 2025"):
            st.session_state.audit_start_date = date(2025, 1, 1)
            st.session_state.audit_end_date = date(2025, 12, 31)
            st.rerun()
    
    # Use session state values if set
    if 'audit_start_date' in st.session_state:
        start_date = st.session_state.audit_start_date
    if 'audit_end_date' in st.session_state:
        end_date = st.session_state.audit_end_date
    
    if st.button("Create Audit Snapshot", type="primary"):
        # Validate date range
        if start_date >= end_date:
            st.error("❌ Start date must be before end date.")
            return
        
        # Check if date range is reasonable
        date_diff = (end_date - start_date).days
        if date_diff > 365:
            st.warning(f"⚠️ Date range is {date_diff} days long. This may take longer to process.")
        
        try:
            with st.spinner("Creating audit snapshot..."):
                response = requests.post(
                    f"{api_base}/api/compliance/audit-snapshot",
                    json={
                        "submission_type": submission_type,
                        "reporting_period_start": start_date.isoformat(),
                        "reporting_period_end": end_date.isoformat()
                    },
                    timeout=30
                )
                response.raise_for_status()
                result = response.json()
                
                if result.get('success'):
                    snapshot_data = result.get('snapshot_data', {})
                    total_records = snapshot_data.get('total_records', 0)
                    
                    if total_records == 0:
                        st.warning(f"⚠️ Audit snapshot created but contains no emission records for the selected date range ({start_date} to {end_date}).")
                        st.info("💡 **Tip**: Try adjusting the date range to include periods with emission data (e.g., 2025-01-01 to 2025-03-31).")
                    else:
                        st.success(f"✅ Audit snapshot created successfully with {total_records} records!")
                    
                    # Show snapshot summary
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Total Records", total_records)
                    with col2:
                        st.metric("Total Emissions", f"{snapshot_data.get('total_emissions_kgco2e', 0):,.1f} kg CO₂e")
                    with col3:
                        st.metric("Compliance Score", f"{snapshot_data.get('average_compliance_score', 0):.1f}")
                    with col4:
                        st.metric("Audit Ready", f"{snapshot_data.get('audit_ready_records', 0)}")
                    
                    # Show detailed data
                    with st.expander("📋 View Snapshot Details"):
                        st.json(snapshot_data)
                    
                    # Generate PDF report button (only if there's data)
                    if total_records > 0:
                        if st.button("📄 Generate PDF Report", key="generate_pdf_after_create"):
                            generate_pdf_report(api_base, snapshot_data.get('submission_id'))
                    else:
                        st.button("📄 Generate PDF Report", key="generate_pdf_after_create", disabled=True, 
                                help="No data available to generate PDF report")
                else:
                    st.error(f"Error creating audit snapshot: {result.get('error', 'Unknown error')}")
                    
        except requests.exceptions.RequestException as e:
            st.error(f"Error connecting to API: {e}")
        except Exception as e:
            st.error(f"Error creating audit snapshot: {e}")
    
    # Existing snapshots
    st.markdown("### Existing Audit Snapshots")
    
    try:
        response = requests.get(f"{api_base}/api/compliance/submission-history", timeout=10)
        response.raise_for_status()
        snapshots = response.json()
        
        if snapshots:
            df = pd.DataFrame(snapshots)
            
            # Filter out empty snapshots by default
            show_empty = st.checkbox("Show empty snapshots (0 records)", value=False)
            if not show_empty:
                df = df[df['total_records'] > 0]
            
            if len(df) > 0:
                st.info(f"Showing {len(df)} audit snapshot(s). Use the checkbox above to include empty snapshots.")
                
                # Add action buttons
                for idx, row in df.iterrows():
                    # Determine status color and icon
                    if row['total_records'] == 0:
                        status_icon = "⚠️"
                        status_color = "red"
                        status_text = "Empty"
                    elif row['average_compliance_score'] >= 90:
                        status_icon = "✅"
                        status_color = "green"
                        status_text = "Excellent"
                    elif row['average_compliance_score'] >= 70:
                        status_icon = "🟡"
                        status_color = "orange"
                        status_text = "Good"
                    else:
                        status_icon = "🔴"
                        status_color = "red"
                        status_text = "Needs Work"
                    
                    col1, col2, col3, col4, col5 = st.columns([4, 1, 1, 1, 1])
                    
                    with col1:
                        st.write(f"**{row['submission_id']}**")
                        st.write(f"Type: {row['submission_type']} | "
                               f"Period: {row['reporting_period_start']} to {row['reporting_period_end']} | "
                               f"Records: {row['total_records']} | "
                               f"Score: {row['average_compliance_score']:.1f} | "
                               f"{status_icon} {status_text}")
                    
                    with col2:
                        if st.button("View", key=f"view_{idx}"):
                            view_snapshot_details(api_base, row['submission_id'])
                    
                    with col3:
                        if row['total_records'] > 0:
                            if st.button("PDF", key=f"pdf_{idx}"):
                                generate_pdf_report(api_base, row['submission_id'])
                        else:
                            st.button("PDF", key=f"pdf_{idx}", disabled=True, help="No data to generate PDF")
                    
                    with col4:
                        if row['total_records'] > 0 and row['average_compliance_score'] >= 70:
                            if st.button("Submit", key=f"submit_{idx}"):
                                submit_to_regulatory(api_base, row['submission_id'], row['submission_type'])
                        else:
                            st.button("Submit", key=f"submit_{idx}", disabled=True, 
                                    help="Submit disabled: insufficient data or low compliance score")
                    
                    with col5:
                        if st.button("🗑️", key=f"delete_{idx}", help="Delete snapshot"):
                            delete_audit_snapshot(api_base, row['submission_id'])
                    
                    st.divider()
            else:
                if show_empty:
                    st.info("No audit snapshots found. Create one to get started.")
                else:
                    st.info("No audit snapshots with data found. Create one to get started.")
        else:
            st.info("No audit snapshots found. Create one to get started.")
            
    except requests.exceptions.RequestException as e:
        st.error(f"Error connecting to API: {e}")
    except Exception as e:
        st.error(f"Error loading audit snapshots: {e}")

def show_compliance_rules(api_base: str):
    """Show compliance rules management"""
    st.subheader("📋 Compliance Rules Management")
    
    # Get compliance rules
    try:
        response = requests.get(f"{api_base}/api/compliance/rules", timeout=10)
        response.raise_for_status()
        rules = response.json()
        
        if rules:
            st.markdown("### Active Compliance Rules")
            
            for rule in rules:
                with st.expander(f"**{rule['rule_name']}** ({rule['framework']})"):
                    st.write(f"**Description:** {rule['rule_description']}")
                    st.write(f"**Severity:** {rule['severity']}")
                    st.write(f"**Auto Apply:** {'Yes' if rule['auto_apply'] else 'No'}")
                    
                    if rule['required_fields']:
                        st.write("**Required Fields:**")
                        for field in rule['required_fields']:
                            st.write(f"• {field}")
                    
                    if rule['validation_rules']:
                        st.write("**Validation Rules:**")
                        for validation in rule['validation_rules']:
                            st.write(f"• {validation}")
        else:
            st.info("No compliance rules found.")
            
    except requests.exceptions.RequestException as e:
        st.error(f"Error connecting to API: {e}")
    except Exception as e:
        st.error(f"Error loading compliance rules: {e}")
    
    # Add new rule section
    st.markdown("### Add New Compliance Rule")
    
    with st.form("new_rule_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            rule_name = st.text_input("Rule Name")
            framework = st.selectbox("Framework", ["EPA", "EU_ETS", "CARB", "TCFD", "SEC"])
            severity = st.selectbox("Severity", ["low", "medium", "high", "critical"])
        
        with col2:
            rule_description = st.text_area("Description")
            auto_apply = st.checkbox("Auto Apply", value=True)
        
        required_fields = st.multiselect(
            "Required Fields",
            ["supplier_name", "date", "activity_type", "scope", "activity_amount", 
             "activity_unit", "emission_factor_value", "result_kgco2e"]
        )
        
        if st.form_submit_button("Add Rule"):
            if rule_name and framework:
                try:
                    response = requests.post(
                        f"{api_base}/api/compliance/rules",
                        json={
                            "rule_name": rule_name,
                            "framework": framework,
                            "rule_description": rule_description,
                            "severity": severity,
                            "auto_apply": auto_apply,
                            "required_fields": required_fields
                        },
                        timeout=10
                    )
                    response.raise_for_status()
                    result = response.json()
                    
                    if result.get('success'):
                        st.success("✅ Compliance rule added successfully!")
                        st.rerun()
                    else:
                        st.error(f"Error adding rule: {result.get('error', 'Unknown error')}")
                        
                except requests.exceptions.RequestException as e:
                    st.error(f"Error connecting to API: {e}")
                except Exception as e:
                    st.error(f"Error adding compliance rule: {e}")
            else:
                st.error("Please fill in all required fields.")

def generate_pdf_report(api_base: str, snapshot_id: str):
    """Generate PDF report for audit snapshot"""
    try:
        response = requests.post(
            f"{api_base}/api/compliance/generate-report",
            json={"snapshot_id": snapshot_id},
            timeout=30
        )
        response.raise_for_status()
        result = response.json()
        
        if result.get('success'):
            st.success("✅ PDF report generated successfully!")
            st.json(result.get('report_data', {}))
        else:
            st.error(f"Error generating PDF report: {result.get('error', 'Unknown error')}")
            
    except requests.exceptions.RequestException as e:
        st.error(f"Error connecting to API: {e}")
    except Exception as e:
        st.error(f"Error generating PDF report: {e}")

def view_snapshot_details(api_base: str, snapshot_id: str):
    """View detailed audit snapshot information"""
    try:
        response = requests.get(
            f"{api_base}/api/compliance/snapshot-details/{snapshot_id}",
            timeout=10
        )
        response.raise_for_status()
        details = response.json()
        
        st.json(details)
        
    except requests.exceptions.RequestException as e:
        st.error(f"Error connecting to API: {e}")
    except Exception as e:
        st.error(f"Error loading snapshot details: {e}")

def submit_to_regulatory(api_base: str, snapshot_id: str, submission_type: str):
    """Submit audit snapshot to regulatory framework"""
    try:
        response = requests.post(
            f"{api_base}/api/compliance/regulatory-submission",
            json={
                "snapshot_id": snapshot_id,
                "regulatory_framework": submission_type
            },
            timeout=30
        )
        response.raise_for_status()
        result = response.json()
        
        if result.get('success'):
            st.success(f"✅ Submission package generated for {submission_type}!")
            st.json(result.get('submission_data', {}))
        else:
            st.error(f"Error generating submission: {result.get('error', 'Unknown error')}")
            
    except requests.exceptions.RequestException as e:
        st.error(f"Error connecting to API: {e}")
    except Exception as e:
        st.error(f"Error generating regulatory submission: {e}")

def delete_audit_snapshot(api_base: str, snapshot_id: str):
    """Delete an audit snapshot with confirmation"""
    try:
        # Show confirmation dialog
        if st.session_state.get(f"confirm_delete_{snapshot_id}", False):
            response = requests.delete(
                f"{api_base}/api/compliance/audit-snapshots/{snapshot_id}",
                timeout=10
            )
            response.raise_for_status()
            result = response.json()
            
            if result.get('success'):
                st.success(f"✅ {result.get('message', 'Audit snapshot deleted successfully')}")
                # Clear the confirmation state
                if f"confirm_delete_{snapshot_id}" in st.session_state:
                    del st.session_state[f"confirm_delete_{snapshot_id}"]
                st.rerun()
            else:
                st.error(f"Error deleting snapshot: {result.get('error', 'Unknown error')}")
        else:
            # Set confirmation state
            st.session_state[f"confirm_delete_{snapshot_id}"] = True
            st.warning(f"⚠️ Are you sure you want to delete snapshot '{snapshot_id}'? Click the delete button again to confirm.")
            
    except requests.exceptions.RequestException as e:
        st.error(f"Error connecting to API: {e}")
    except Exception as e:
        st.error(f"Error deleting audit snapshot: {e}")
