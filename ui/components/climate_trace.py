"""
Climate TRACE Integration UI Component

This component provides a business-focused interface for comparing
your emissions data against Climate TRACE methodology benchmarks.
"""
import streamlit as st
import requests
import pandas as pd

# Suppress Plotly deprecation warnings
import warnings
warnings.filterwarnings('ignore', category=DeprecationWarning, module='plotly')
warnings.filterwarnings('ignore', message='.*keyword arguments have been deprecated.*')

import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date
from typing import Dict, List, Optional
import json


def show_climate_trace_page(api_base: str):
    """Main Climate TRACE page"""
    st.title("🌍 Climate TRACE Compliance Analysis")
    st.markdown("Compare your emissions data against Climate TRACE methodology benchmarks for compliance and benchmarking")
    
    # Check if Climate TRACE is enabled
    try:
        response = requests.get(f"{api_base}/api/climate-trace/status", timeout=10)
        if response.status_code == 200:
            status = response.json()
            if not status.get("enabled", False):
                st.warning("⚠️ Climate TRACE integration is disabled. Set COMPLIANCE_CT_ENABLED=true to enable.")
                return
        else:
            st.error("❌ Could not connect to Climate TRACE service")
            return
    except Exception as e:
        st.error(f"❌ Error checking Climate TRACE status: {e}")
        return
    
    # Show methodology-based approach info
    st.info("📊 **Methodology-Based Analysis**: This tool uses Climate TRACE emission factors and sector benchmarks to compare your reported emissions against industry standards.")
    
    # Create tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Cross-Check Analysis", "🗺️ Sector Mapping", "📈 Benchmark Comparison", "⚙️ Settings"])
    
    with tab1:
        show_crosscheck_analysis(api_base)
    
    with tab2:
        show_sector_mapping(api_base)
    
    with tab3:
        show_benchmark_comparison(api_base)
    
    with tab4:
        show_climate_trace_settings(api_base)


def show_crosscheck_analysis(api_base: str):
    """Show cross-check analysis between business data and Climate TRACE benchmarks"""
    st.header("📊 Cross-Check Analysis")
    st.markdown("Compare your reported emissions against Climate TRACE methodology benchmarks")
    
    # Date selection
    col1, col2 = st.columns(2)
    with col1:
        year = st.selectbox("Year", options=list(range(2020, 2030)), index=5)  # Default to 2025
    with col2:
        month = st.selectbox("Month", options=list(range(1, 13)), index=9)  # Default to October
    
    # Threshold setting
    threshold = st.slider("Compliance Threshold (%)", min_value=5, max_value=50, value=10, 
                         help="Percentage difference threshold for flagging compliance issues")
    
    # Run analysis button
    if st.button("🔄 Run Cross-Check Analysis", type="primary"):
        with st.spinner("Running cross-check analysis..."):
            try:
                # Run cross-check analysis
                response = requests.post(
                    f"{api_base}/api/climate-trace/crosscheck",
                    params={"year": year, "month": month, "threshold_percentage": threshold},
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("success"):
                        st.success(f"✅ Analysis completed! Created {result.get('crosschecks_created', 0)} cross-check results")
                        
                        # Show results
                        if result.get("results"):
                            show_crosscheck_results(result["results"])
                        else:
                            st.info("No cross-check results found for the selected period")
                    else:
                        st.error(f"❌ Analysis failed: {result.get('error', 'Unknown error')}")
                else:
                    st.error(f"❌ API request failed: {response.status_code}")
                    
            except Exception as e:
                st.error(f"❌ Error running analysis: {e}")
    
    # Show existing results
    st.subheader("📋 Recent Cross-Check Results")
    show_recent_crosscheck_results(api_base)


def show_crosscheck_results(results: List[Dict]):
    """Display cross-check results in a table and charts"""
    if not results:
        st.info("No cross-check results to display")
        return
    
    # Create DataFrame
    df = pd.DataFrame(results)
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Sectors", len(df))
    with col2:
        compliant = len(df[df['compliance_status'] == 'compliant'])
        st.metric("Compliant Sectors", compliant)
    with col3:
        over_emitting = len(df[df['compliance_status'] == 'over_emitting'])
        st.metric("Over-Emitting", over_emitting)
    with col4:
        under_emitting = len(df[df['compliance_status'] == 'under_emitting'])
        st.metric("Under-Emitting", under_emitting)
    
    # Results table
    st.subheader("📊 Detailed Results")
    
    # Format the data for display
    display_df = df.copy()
    
    # Handle different field name formats (API vs database)
    if 'our_emissions_kgco2e' in display_df.columns:
        our_emissions_col = 'our_emissions_kgco2e'
        ct_emissions_col = 'ct_emissions_kgco2e'
    else:
        our_emissions_col = 'our_emissions'
        ct_emissions_col = 'ct_emissions'
    
    display_df['our_emissions_kgco2e'] = display_df[our_emissions_col].apply(lambda x: f"{x:,.0f}")
    display_df['ct_emissions'] = display_df[ct_emissions_col].apply(lambda x: f"{x:,.0f}")
    display_df['delta_percentage'] = display_df['delta_percentage'].apply(lambda x: f"{x:.1f}%")
    
    # Color code compliance status
    def color_status(val):
        if val == 'compliant':
            return 'background-color: #d4edda'
        elif val == 'over_emitting':
            return 'background-color: #f8d7da'
        elif val == 'under_emitting':
            return 'background-color: #fff3cd'
        return ''
    
    styled_df = display_df[['sector', 'our_emissions_kgco2e', 'ct_emissions', 'delta_percentage', 'compliance_status']].style.applymap(color_status, subset=['compliance_status'])
    st.dataframe(styled_df, use_container_width=True)
    
    # Charts
    col1, col2 = st.columns(2)
    
    with col1:
        # Emissions comparison chart
        fig = go.Figure()
        # Handle different field name formats for charts
        if 'our_emissions_kgco2e' in df.columns:
            our_emissions_col = 'our_emissions_kgco2e'
            ct_emissions_col = 'ct_emissions_kgco2e'
        else:
            our_emissions_col = 'our_emissions'
            ct_emissions_col = 'ct_emissions'
        
        fig.add_trace(go.Bar(
            name='Your Emissions',
            x=df['sector'],
            y=df[our_emissions_col],
            marker_color='#1f77b4'
        ))
        fig.add_trace(go.Bar(
            name='Climate TRACE Benchmark',
            x=df['sector'],
            y=df[ct_emissions_col],
            marker_color='#ff7f0e'
        ))
        
        fig.update_layout(
            title="Emissions Comparison by Sector",
            xaxis_title="Sector",
            yaxis_title="Emissions (kg CO2e)",
            barmode='group',
            height=400
        )
        st.plotly_chart(fig, width='stretch')
    
    with col2:
        # Compliance status pie chart
        status_counts = df['compliance_status'].value_counts()
        fig = px.pie(
            values=status_counts.values,
            names=status_counts.index,
            title="Compliance Status Distribution",
            color_discrete_map={
                'compliant': '#28a745',
                'over_emitting': '#dc3545',
                'under_emitting': '#ffc107'
            }
        )
        st.plotly_chart(fig, width='stretch')


def show_recent_crosscheck_results(api_base: str):
    """Show recent cross-check results from the database"""
    try:
        response = requests.get(f"{api_base}/api/climate-trace/crosschecks?limit=10", timeout=10)
        if response.status_code == 200:
            results = response.json()
            if results:
                # Create DataFrame
                df = pd.DataFrame(results)
                
                # Show only results with Climate TRACE benchmarks
                ct_results = df[df['ct_emissions_kgco2e'] > 0]
                
                if not ct_results.empty:
                    st.dataframe(
                        ct_results[['sector', 'our_emissions_kgco2e', 'ct_emissions_kgco2e', 'compliance_status']].head(5),
                        use_container_width=True
                    )
                else:
                    st.info("No recent cross-check results with Climate TRACE benchmarks found")
            else:
                st.info("No cross-check results found")
        else:
            st.error("❌ Could not fetch recent results")
    except Exception as e:
        st.error(f"❌ Error fetching recent results: {e}")


def show_sector_mapping(api_base: str):
    """Show sector mapping interface"""
    st.header("🗺️ Sector Mapping")
    st.markdown("Map your activity types to Climate TRACE sectors for accurate comparison")
    
    # Map records button
    if st.button("🔄 Map All Records to Climate TRACE Sectors", type="primary"):
        with st.spinner("Mapping records to Climate TRACE sectors..."):
            try:
                response = requests.post(
                    f"{api_base}/api/climate-trace/map-records",
                    json={},
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("success"):
                        st.success(f"✅ Successfully mapped {result.get('mapped_count', 0)}/{result.get('total_count', 0)} records")
                    else:
                        st.error(f"❌ Mapping failed: {result.get('error', 'Unknown error')}")
                else:
                    st.error(f"❌ API request failed: {response.status_code}")
                    
            except Exception as e:
                st.error(f"❌ Error mapping records: {e}")
    
    # Show available sectors
    st.subheader("📋 Available Climate TRACE Sectors")
    try:
        response = requests.get(f"{api_base}/api/climate-trace/sectors", timeout=10)
        if response.status_code == 200:
            result = response.json()
            if result.get("success") and result.get("sectors"):
                sectors_df = pd.DataFrame(result["sectors"], columns=["Sector"])
                st.dataframe(sectors_df, use_container_width=True)
            else:
                st.info("No sectors available")
        else:
            st.error("❌ Could not fetch sectors")
    except Exception as e:
        st.error(f"❌ Error fetching sectors: {e}")


def show_benchmark_comparison(api_base: str):
    """Show benchmark comparison interface"""
    st.header("📈 Benchmark Comparison")
    st.markdown("Compare your emissions against Climate TRACE methodology benchmarks by sector")
    
    # Get available sectors
    try:
        response = requests.get(f"{api_base}/api/climate-trace/sectors", timeout=10)
        if response.status_code == 200:
            result = response.json()
            if result.get("success") and result.get("sectors"):
                sectors = result["sectors"]
                
                # Sector selection
                selected_sector = st.selectbox("Select Sector", options=sectors)
                
                if st.button("📊 Get Benchmark Data", type="primary"):
                    with st.spinner("Fetching benchmark data..."):
                        # This would need a new API endpoint for benchmark data
                        st.info("Benchmark comparison feature coming soon!")
                        
                        # For now, show some example data
                        show_example_benchmark(selected_sector)
            else:
                st.info("No sectors available")
        else:
            st.error("❌ Could not fetch sectors")
    except Exception as e:
        st.error(f"❌ Error fetching sectors: {e}")


def show_example_benchmark(sector: str):
    """Show example benchmark data"""
    # Example benchmark data based on Climate TRACE methodology
    benchmarks = {
        'electricity-generation': {
            'emission_factor': '0.5 kg CO2e/kWh',
            'typical_activity': '100,000 kWh/month',
            'benchmark_emissions': '50,000 kg CO2e/month',
            'confidence': 'Medium'
        },
        'road-transportation': {
            'emission_factor': '0.18 kg CO2e/km',
            'typical_activity': '50,000 km/month',
            'benchmark_emissions': '9,000 kg CO2e/month',
            'confidence': 'Medium'
        },
        'iron-and-steel': {
            'emission_factor': '1.8 kg CO2e/kg steel',
            'typical_activity': '10,000 kg/month',
            'benchmark_emissions': '18,000 kg CO2e/month',
            'confidence': 'High'
        }
    }
    
    if sector in benchmarks:
        benchmark = benchmarks[sector]
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Emission Factor", benchmark['emission_factor'])
            st.metric("Typical Activity Level", benchmark['typical_activity'])
        with col2:
            st.metric("Benchmark Emissions", benchmark['benchmark_emissions'])
            st.metric("Confidence Level", benchmark['confidence'])
        
        st.info("💡 **Note**: These benchmarks are based on Climate TRACE methodology and typical industry activity levels. Your actual emissions may vary based on your specific operations and efficiency measures.")


def show_climate_trace_settings(api_base: str):
    """Show Climate TRACE settings and configuration"""
    st.header("⚙️ Climate TRACE Settings")
    
    # Service status
    st.subheader("🔧 Service Configuration")
    try:
        response = requests.get(f"{api_base}/api/climate-trace/status", timeout=10)
        if response.status_code == 200:
            status = response.json()
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Service Status", "✅ Enabled" if status.get("enabled") else "❌ Disabled")
            with col2:
                st.metric("API Available", "✅ Available" if status.get("api_available") else "❌ Unavailable")
            
            # Show configuration details
            st.subheader("📋 Configuration Details")
            st.json(status)
        else:
            st.error("❌ Could not fetch service status")
    except Exception as e:
        st.error(f"❌ Error fetching service status: {e}")
    
    # Methodology information
    st.subheader("📚 Methodology Information")
    st.markdown("""
    **Climate TRACE Integration Approach:**
    
    This platform uses Climate TRACE methodology-based emission factors and sector benchmarks to provide:
    
    - **Emission Factors**: Industry-standard emission factors from Climate TRACE methodology documents
    - **Sector Benchmarks**: Typical activity levels and corresponding emissions for each sector
    - **Compliance Analysis**: Comparison of your reported emissions against methodology-based benchmarks
    - **Business Intelligence**: Insights into your emissions performance relative to industry standards
    
    **Benefits:**
    - ✅ No external API dependencies
    - ✅ Fast and reliable analysis
    - ✅ Business-focused comparisons
    - ✅ Compliance-ready reporting
    - ✅ Cost-effective solution
    """)
    
    # Help and support
    st.subheader("🆘 Help & Support")
    st.markdown("""
    **Need Help?**
    
    - 📖 **Documentation**: Check the Climate TRACE methodology documents for detailed emission factors
    - 🔧 **Configuration**: Ensure `COMPLIANCE_CT_ENABLED=true` is set in your environment
    - 📊 **Data Quality**: Make sure your emission records have proper activity types for accurate sector mapping
    - 🎯 **Compliance**: Use the cross-check analysis to identify areas for improvement
    """)


if __name__ == "__main__":
    # For testing
    show_climate_trace_page("http://127.0.0.1:8000")
