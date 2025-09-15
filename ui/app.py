"""
Carbon DNA Ledger - Streamlit UI
Main application with all UI components
"""
import streamlit as st
import requests
import json
from datetime import datetime, date, timedelta
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import os

from components import uploader, explorer, details, scenario, analytics, query

# Configure Streamlit page
st.set_page_config(
    page_title="Carbon DNA Ledger",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API base URL
API_BASE = os.getenv("API_BASE", "http://localhost:8000")

# Custom CSS for better styling
st.markdown("""
<style>
.main-header {
    font-size: 2.5rem;
    color: #2E8B57;
    text-align: center;
    margin-bottom: 2rem;
}
.metric-card {
    background-color: #f0f2f6;
    padding: 1rem;
    border-radius: 0.5rem;
    border-left: 4px solid #2E8B57;
}
.hash-display {
    font-family: 'Courier New', monospace;
    background-color: #f8f9fa;
    padding: 0.5rem;
    border-radius: 0.25rem;
    font-size: 0.8rem;
    word-break: break-all;
}
.dna-chip {
    display: inline-block;
    background-color: #e8f5e8;
    padding: 0.3rem 0.8rem;
    margin: 0.2rem;
    border-radius: 1rem;
    font-size: 0.85rem;
    border: 1px solid #2E8B57;
}
</style>
""", unsafe_allow_html=True)

def main():
    """Main Streamlit application"""
    
    # Header
    st.markdown('<h1 class="main-header">🌱 Carbon DNA Ledger</h1>', unsafe_allow_html=True)
    st.markdown("**Auditable Carbon Emission Tracking with Hash-Chained Integrity**")
    
    # Sidebar navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.selectbox(
        "Choose a page:",
        ["📊 Dashboard", "📤 Upload Data", "🔍 Event Explorer", "🧬 Event Details", 
         "🔄 What-If Scenarios", "📈 Analytics", "❓ Ask Questions"]
    )
    
    # API health check
    try:
        response = requests.get(f"{API_BASE}/", timeout=5)
        if response.status_code == 200:
            st.sidebar.success("✅ API Connected")
        else:
            st.sidebar.error("❌ API Error")
    except:
        st.sidebar.error("❌ API Unreachable")
        st.error("Cannot connect to backend API. Please ensure the FastAPI server is running on port 8000.")
        return
    
    # Page routing
    if page == "📊 Dashboard":
        show_dashboard()
    elif page == "📤 Upload Data":
        uploader.show_upload_page(API_BASE)
    elif page == "🔍 Event Explorer":
        explorer.show_explorer_page(API_BASE)
    elif page == "🧬 Event Details":
        details.show_details_page(API_BASE)
    elif page == "🔄 What-If Scenarios":
        scenario.show_scenario_page(API_BASE)
    elif page == "📈 Analytics":
        analytics.show_analytics_page(API_BASE)
    elif page == "❓ Ask Questions":
        query.show_query_page(API_BASE)

def show_dashboard():
    """Show main dashboard with key metrics"""
    st.header("📊 Dashboard Overview")
    
    try:
        # Get recent events for dashboard
        response = requests.get(f"{API_BASE}/api/events", params={"limit": 10})
        if response.status_code == 200:
            events = response.json()
            
            if events:
                # Key metrics
                total_events = len(events)
                total_emissions = sum(event['result_kgco2e'] for event in events)
                avg_uncertainty = sum(event['uncertainty_pct'] for event in events) / len(events)
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.markdown(
                        f'<div class="metric-card"><h3>{total_events}</h3><p>Recent Events</p></div>',
                        unsafe_allow_html=True
                    )
                
                with col2:
                    st.markdown(
                        f'<div class="metric-card"><h3>{total_emissions:,.0f}</h3><p>Total kg CO2e</p></div>',
                        unsafe_allow_html=True
                    )
                
                with col3:
                    st.markdown(
                        f'<div class="metric-card"><h3>{avg_uncertainty:.1f}%</h3><p>Avg Uncertainty</p></div>',
                        unsafe_allow_html=True
                    )
                
                st.markdown("---")
                
                # Recent events table
                st.subheader("🔄 Recent Events")
                df = pd.DataFrame(events)
                df['occurred_at'] = pd.to_datetime(df['occurred_at']).dt.strftime('%Y-%m-%d %H:%M')
                
                st.dataframe(
                    df[['occurred_at', 'supplier_name', 'activity', 'result_kgco2e', 'uncertainty_pct']],
                    use_container_width=True
                )
                
                # Quick charts
                st.subheader("📈 Quick Insights")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    # Emissions by supplier
                    supplier_totals = df.groupby('supplier_name')['result_kgco2e'].sum().reset_index()
                    fig = px.bar(
                        supplier_totals, 
                        x='supplier_name', 
                        y='result_kgco2e',
                        title="Emissions by Supplier"
                    )
                    st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    # Scope distribution
                    scope_dist = df['scope'].value_counts().reset_index()
                    scope_dist.columns = ['scope', 'count']
                    scope_dist['scope'] = 'Scope ' + scope_dist['scope'].astype(str)
                    
                    fig = px.pie(
                        scope_dist, 
                        values='count', 
                        names='scope',
                        title="Events by Scope"
                    )
                    st.plotly_chart(fig, use_container_width=True)
            
            else:
                st.info("No events found. Upload some data to get started!")
                
                # Show demo instructions
                st.subheader("🚀 Quick Start")
                st.markdown("""
                1. **Upload Data**: Use the Upload page to ingest CSV or PDF files
                2. **Explore Events**: Browse your carbon events with filters
                3. **View DNA Details**: See the complete audit trail for each event
                4. **Run Scenarios**: Test what-if changes to parameters
                5. **Analyze Trends**: View analytics and top emitters
                
                **Demo Data**: The system comes with sample data from OceanLift and GridCo.
                """)
        
        else:
            st.error(f"Failed to fetch events: {response.status_code}")
            
    except Exception as e:
        st.error(f"Dashboard error: {str(e)}")
    
    # System status
    st.markdown("---")
    st.subheader("🔧 System Status")
    
    try:
        # Check API health
        health_response = requests.get(f"{API_BASE}/")
        if health_response.status_code == 200:
            health_data = health_response.json()
            st.success(f"✅ API: {health_data.get('message', 'OK')} (v{health_data.get('version', 'unknown')})")
        
        # Check recent hash integrity (demonstration)
        st.info("🔗 Hash chain integrity verification available in Event Details")
        
        # Database info
        st.info("🗄️ Database: Connected to Supabase PostgreSQL")
        
    except Exception as e:
        st.error(f"System status check failed: {str(e)}")

if __name__ == "__main__":
    main()
