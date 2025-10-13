"""
Enhanced Compliance Roadmap UI Component
"""
import streamlit as st
import requests
import json
import pandas as pd

# Suppress Plotly deprecation warnings
import warnings
warnings.filterwarnings('ignore', category=DeprecationWarning, module='plotly')
warnings.filterwarnings('ignore', message='.*keyword arguments have been deprecated.*')

import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from typing import Dict, List, Any

def show_enhanced_compliance_roadmap(api_base: str):
    """Show enhanced compliance roadmap interface"""
    st.title("🗺️ Enhanced Compliance Roadmap")
    st.markdown("Generate detailed compliance requirements and actionable steps for regulatory frameworks")
    
    # Sidebar configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Framework selection
        available_frameworks = ["EPA", "EU_ETS", "TCFD", "SEC", "CARB", "CDP", "GRI", "SASB", "CSRD"]
        selected_frameworks = st.multiselect(
            "Select Regulatory Frameworks",
            available_frameworks,
            default=["EPA", "EU_ETS", "TCFD"],
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
        
        # Timeline
        timeline_months = st.slider(
            "Timeline (months)",
            min_value=3,
            max_value=24,
            value=12,
            help="Implementation timeline in months"
        )
        
        # Generate button
        generate_roadmap = st.button("🚀 Generate Enhanced Roadmap", type="primary")
    
    if generate_roadmap:
        if not selected_frameworks:
            st.warning("Please select at least one regulatory framework")
            return
        
        with st.spinner("Generating enhanced compliance roadmap..."):
            try:
                # Generate roadmap
                roadmap_data = generate_enhanced_roadmap(
                    api_base, selected_frameworks, budget_constraint, timeline_months
                )
                
                if roadmap_data:
                    display_enhanced_roadmap(roadmap_data)
                else:
                    st.error("Failed to generate roadmap")
                    
            except Exception as e:
                st.error(f"Error generating roadmap: {e}")
    
    # Show example roadmap if no generation requested
    else:
        show_roadmap_example()

def generate_enhanced_roadmap(api_base: str, frameworks: List[str], 
                            budget: float, timeline: int) -> Dict[str, Any]:
    """Generate enhanced compliance roadmap"""
    try:
        request_data = {
            "frameworks": frameworks,
            "budget_constraint": budget,
            "timeline_months": timeline
        }
        
        response = requests.post(
            f"{api_base}/api/compliance/enhanced-roadmap",
            json=request_data,
            timeout=60
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"API Error: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        st.error(f"Error calling API: {e}")
        return None

def display_enhanced_roadmap(roadmap_data: Dict[str, Any]):
    """Display the enhanced compliance roadmap"""
    
    # Overview section
    st.header("📊 Roadmap Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Frameworks", len(roadmap_data['frameworks']))
    
    with col2:
        st.metric("Total Budget", f"${roadmap_data['total_budget']:,.0f}")
    
    with col3:
        st.metric("Requirements", len(roadmap_data['requirements']))
    
    with col4:
        st.metric("Actionable Steps", len(roadmap_data['actionable_steps']))
    
    # Tabs for different views
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📋 Requirements", "🎯 Actionable Steps", "⚠️ Risk Assessment", 
        "👥 Resources", "📈 Success Metrics"
    ])
    
    with tab1:
        display_requirements(roadmap_data['requirements'])
    
    with tab2:
        display_actionable_steps(roadmap_data['actionable_steps'])
    
    with tab3:
        display_risk_assessment(roadmap_data['risk_assessment'])
    
    with tab4:
        display_resource_requirements(roadmap_data['resource_requirements'])
    
    with tab5:
        display_success_metrics(roadmap_data['success_metrics'])

def display_requirements(requirements: List[Dict[str, Any]]):
    """Display compliance requirements"""
    st.subheader("📋 Compliance Requirements")
    
    if not requirements:
        st.info("No requirements generated")
        return
    
    # Create DataFrame for requirements
    req_df = pd.DataFrame(requirements)
    
    # Priority filter
    priority_filter = st.selectbox(
        "Filter by Priority",
        ["All"] + list(req_df['priority'].unique()),
        key="req_priority_filter"
    )
    
    if priority_filter != "All":
        req_df = req_df[req_df['priority'] == priority_filter]
    
    # Category filter
    category_filter = st.selectbox(
        "Filter by Category",
        ["All"] + list(req_df['category'].unique()),
        key="req_category_filter"
    )
    
    if category_filter != "All":
        req_df = req_df[req_df['category'] == category_filter]
    
    # Display requirements
    for idx, req in req_df.iterrows():
        with st.expander(f"🔸 {req['title']} ({req['priority'].upper()})"):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.write(f"**Description:** {req['description']}")
                st.write(f"**Category:** {req['category'].title()}")
                st.write(f"**Regulatory Reference:** {req['regulatory_reference']}")
                
                if req['dependencies']:
                    st.write(f"**Dependencies:** {', '.join(req['dependencies'])}")
                
                st.write("**Deliverables:**")
                for deliverable in req['deliverables']:
                    st.write(f"• {deliverable}")
                
                st.write("**Success Criteria:**")
                for criteria in req['success_criteria']:
                    st.write(f"• {criteria}")
            
            with col2:
                st.metric("Estimated Cost", f"${req['estimated_cost']:,.0f}")
                st.metric("Time (Days)", req['estimated_time_days'])
                
                # Priority indicator
                priority_colors = {
                    'critical': '🔴',
                    'high': '🟠', 
                    'medium': '🟡',
                    'low': '🟢'
                }
                st.write(f"**Priority:** {priority_colors.get(req['priority'], '⚪')} {req['priority'].title()}")

def display_actionable_steps(steps: List[Dict[str, Any]]):
    """Display actionable steps"""
    st.subheader("🎯 Actionable Steps")
    
    if not steps:
        st.info("No actionable steps generated")
        return
    
    # Group steps by requirement
    steps_by_requirement = {}
    for step in steps:
        req_id = step['requirement_id']
        if req_id not in steps_by_requirement:
            steps_by_requirement[req_id] = []
        steps_by_requirement[req_id].append(step)
    
    # Display steps grouped by requirement
    for req_id, req_steps in steps_by_requirement.items():
        st.write(f"**Requirement:** {req_id}")
        
        for step in req_steps:
            with st.expander(f"📌 {step['title']}"):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.write(f"**Description:** {step['description']}")
                    st.write(f"**Framework:** {step['framework']}")
                    
                    if step['prerequisites']:
                        st.write("**Prerequisites:**")
                        for prereq in step['prerequisites']:
                            st.write(f"• {prereq}")
                    
                    st.write("**Resources Needed:**")
                    for resource in step['resources_needed']:
                        st.write(f"• {resource}")
                    
                    st.write("**Deliverables:**")
                    for deliverable in step['deliverables']:
                        st.write(f"• {deliverable}")
                    
                    st.write("**Validation Criteria:**")
                    for criteria in step['validation_criteria']:
                        st.write(f"• {criteria}")
                
                with col2:
                    st.metric("Estimated Hours", step['estimated_hours'])
                    
                    # Progress tracking
                    progress = st.slider(
                        "Progress (%)",
                        min_value=0,
                        max_value=100,
                        value=0,
                        key=f"progress_{step['step_id']}"
                    )
                    
                    if progress > 0:
                        st.progress(progress / 100)

def display_risk_assessment(risk_data: Dict[str, Any]):
    """Display risk assessment"""
    st.subheader("⚠️ Risk Assessment")
    
    # Regulatory risks
    if risk_data.get('regulatory_risks'):
        st.write("**🔴 Regulatory Risks**")
        for risk in risk_data['regulatory_risks']:
            with st.expander(f"{risk['framework']}: {risk['risk']}"):
                st.write(f"**Probability:** {risk['probability'].title()}")
                st.write(f"**Impact:** {risk['impact'].title()}")
                st.write(f"**Description:** {risk['description']}")
    
    # Operational risks
    if risk_data.get('operational_risks'):
        st.write("**🟠 Operational Risks**")
        for risk in risk_data['operational_risks']:
            with st.expander(f"{risk['framework']}: {risk['risk']}"):
                st.write(f"**Probability:** {risk['probability'].title()}")
                st.write(f"**Impact:** {risk['impact'].title()}")
                st.write(f"**Description:** {risk['description']}")
    
    # Financial risks
    if risk_data.get('financial_risks'):
        st.write("**💰 Financial Risks**")
        for risk in risk_data['financial_risks']:
            with st.expander(f"{risk['framework']}: {risk['risk']}"):
                st.write(f"**Probability:** {risk['probability'].title()}")
                st.write(f"**Impact:** {risk['impact'].title()}")
                st.write(f"**Description:** {risk['description']}")
    
    # Mitigation strategies
    if risk_data.get('mitigation_strategies'):
        st.write("**🛡️ Mitigation Strategies**")
        for strategy in risk_data['mitigation_strategies']:
            st.write(f"• {strategy}")

def display_resource_requirements(resource_data: Dict[str, Any]):
    """Display resource requirements"""
    st.subheader("👥 Resource Requirements")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Total Hours", f"{resource_data.get('total_hours', 0):,.0f}")
        st.metric("FTE Months", f"{resource_data.get('estimated_fte_months', 0):.1f}")
    
    with col2:
        if resource_data.get('critical_resources'):
            st.write("**Critical Resources:**")
            for resource in resource_data['critical_resources']:
                st.write(f"• {resource}")
    
    # Resource breakdown chart
    if resource_data.get('resource_breakdown'):
        st.write("**Resource Breakdown:**")
        
        resources = list(resource_data['resource_breakdown'].keys())
        hours = list(resource_data['resource_breakdown'].values())
        
        fig = px.bar(
            x=resources,
            y=hours,
            title="Hours Required by Resource Type",
            labels={'x': 'Resource Type', 'y': 'Hours'}
        )
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, width='stretch')

def display_success_metrics(metrics_data: Dict[str, Any]):
    """Display success metrics"""
    st.subheader("📈 Success Metrics")
    
    # Compliance scores
    if metrics_data.get('compliance_scores'):
        st.write("**Compliance Scores**")
        compliance_df = pd.DataFrame([
            {
                'Framework': framework,
                'Current': data['current'],
                'Target': data['target']
            }
            for framework, data in metrics_data['compliance_scores'].items()
        ])
        
        fig = go.Figure()
        fig.add_trace(go.Bar(name='Current', x=compliance_df['Framework'], y=compliance_df['Current']))
        fig.add_trace(go.Bar(name='Target', x=compliance_df['Framework'], y=compliance_df['Target']))
        fig.update_layout(title="Compliance Score Progress", barmode='group')
        st.plotly_chart(fig, width='stretch')
    
    # Timeline metrics
    if metrics_data.get('timeline_metrics'):
        st.write("**Timeline Metrics**")
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("On-Time Delivery Target", f"{metrics_data['timeline_metrics'].get('on_time_delivery', 0)*100:.0f}%")
        
        with col2:
            st.metric("Budget Adherence Target", f"{metrics_data['timeline_metrics'].get('budget_adherence', 0)*100:.0f}%")
    
    # Quality metrics
    if metrics_data.get('quality_metrics'):
        st.write("**Quality Metrics**")
        quality_df = pd.DataFrame([
            {'Metric': 'Data Accuracy', 'Target': metrics_data['quality_metrics'].get('data_accuracy', 0)*100},
            {'Metric': 'Process Efficiency', 'Target': metrics_data['quality_metrics'].get('process_efficiency', 0)*100},
            {'Metric': 'Documentation Completeness', 'Target': metrics_data['quality_metrics'].get('documentation_completeness', 0)*100}
        ])
        
        fig = px.bar(quality_df, x='Metric', y='Target', title="Quality Metrics Targets")
        fig.update_layout(yaxis_title="Target (%)")
        st.plotly_chart(fig, width='stretch')
    
    # Business metrics
    if metrics_data.get('business_metrics'):
        st.write("**Business Metrics**")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Penalty Avoidance", f"${metrics_data['business_metrics'].get('regulatory_penalty_avoidance', 0):,.0f}")
        
        with col2:
            st.metric("Efficiency Gain", f"{metrics_data['business_metrics'].get('operational_efficiency_gain', 0)*100:.0f}%")
        
        with col3:
            st.metric("Stakeholder Satisfaction", f"{metrics_data['business_metrics'].get('stakeholder_satisfaction', 0)*100:.0f}%")

def show_roadmap_example():
    """Show example roadmap"""
    st.info("👆 Configure your compliance roadmap in the sidebar and click 'Generate Enhanced Roadmap' to get started")
    
    st.subheader("🎯 What You'll Get")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**📋 Detailed Requirements**")
        st.write("• Specific compliance requirements for each framework")
        st.write("• Priority levels and cost estimates")
        st.write("• Dependencies and success criteria")
        st.write("• Regulatory references")
    
    with col2:
        st.write("**🎯 Actionable Steps**")
        st.write("• Step-by-step implementation guide")
        st.write("• Resource requirements and timelines")
        st.write("• Progress tracking capabilities")
        st.write("• Validation criteria")
    
    st.subheader("🔍 Key Features")
    
    features = [
        "AI-powered requirement analysis using your OpenAI key",
        "Multi-framework compliance planning",
        "Budget optimization and resource allocation",
        "Risk assessment and mitigation strategies",
        "Success metrics and progress tracking",
        "Integration with your existing audit data"
    ]
    
    for feature in features:
        st.write(f"✅ {feature}")
    
    st.subheader("📊 Supported Frameworks")
    
    frameworks = [
        ("EPA", "Environmental Protection Agency (US)"),
        ("EU_ETS", "European Union Emissions Trading System"),
        ("TCFD", "Task Force on Climate-related Financial Disclosures"),
        ("SEC", "Securities and Exchange Commission"),
        ("CARB", "California Air Resources Board"),
        ("CDP", "Carbon Disclosure Project"),
        ("GRI", "Global Reporting Initiative"),
        ("SASB", "Sustainability Accounting Standards Board"),
        ("CSRD", "Corporate Sustainability Reporting Directive")
    ]
    
    for framework, description in frameworks:
        st.write(f"**{framework}:** {description}")
