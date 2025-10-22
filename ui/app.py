"""
Carbon DNA Ledger - Streamlit UI
Main application with all UI components
"""
# Load environment variables (optional for local dev, not needed on Streamlit Cloud)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # Running on Streamlit Cloud or dotenv not available
    pass

# Suppress Plotly deprecation warnings
import warnings
warnings.filterwarnings('ignore', category=DeprecationWarning, module='plotly')
warnings.filterwarnings('ignore', message='.*keyword arguments have been deprecated.*')

import streamlit as st
import requests
import json
from datetime import datetime, date, timedelta
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import os

from components import uploader, explorer, details, scenario, analytics, query, human_review, rewards, climate_trace, advanced_compliance_dashboard, enhanced_audit_snapshots, enhanced_compliance_roadmap, audit_details_page

# Configure Streamlit page
st.set_page_config(
    page_title="Carbon DNA Ledger",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API base URL - Use Streamlit secrets on cloud, env variable locally
# For Streamlit Cloud deployment, this will be set in the secrets
try:
    # Try Streamlit secrets first (for Streamlit Cloud)
    API_BASE = st.secrets.get("API_BASE", "http://127.0.0.1:8000")
except:
    # Fall back to environment variable (for local dev)
    API_BASE = os.getenv("API_BASE", "http://127.0.0.1:8000")

# For Streamlit Cloud: You MUST deploy backend separately and set API_BASE in secrets
# Options:
# 1. Deploy backend to Render and set API_BASE to your Render URL
# 2. Deploy backend to Railway and set API_BASE to your Railway URL
# 3. For local development, use http://127.0.0.1:8000

# Debug: Show API base URL
if st.sidebar.checkbox("🔧 Debug Mode"):
    st.sidebar.write(f"API Base URL: {API_BASE}")
    
    # Test API connectivity
    try:
        import socket
        host, port = API_BASE.replace("http://", "").split(":")
        port = int(port)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((host, port))
        sock.close()
        if result == 0:
            st.sidebar.success(f"Port {port} is open")
        else:
            st.sidebar.error(f"Port {port} is closed")
    except Exception as e:
        st.sidebar.error(f"Debug error: {e}")

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
    color: #111111; /* ensure text is visible on light background */
}
.metric-card h3, .metric-card p { color: #111111; }
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
         "🔄 What-If Scenarios", "📈 Analytics", "🔍 Human Review", "💰 Carbon Rewards",
         "🔍 Data Integrity Center", "🛡️ Compliance Intelligence", "🔍 Enhanced Audit Snapshots", "🗺️ Enhanced Compliance Roadmap", "❓ Ask Questions"]
    )
    
    # API health check
    try:
        response = requests.get(f"{API_BASE}/", timeout=10)
        if response.status_code == 200:
            st.sidebar.success("✅ API Connected")
        else:
            st.sidebar.error(f"❌ API Error: {response.status_code}")
            st.error(f"API returned status code {response.status_code}. Please check the server logs.")
            return
    except requests.exceptions.ConnectionError as e:
        st.sidebar.error("❌ API Unreachable")
        st.error(f"Cannot connect to backend API at {API_BASE}. Please ensure the FastAPI server is running on port 8000.")
        st.error(f"Connection error: {str(e)}")
        return
    except requests.exceptions.Timeout as e:
        st.sidebar.error("❌ API Timeout")
        st.error(f"API request timed out. Please check if the server is running.")
        return
    except Exception as e:
        st.sidebar.error("❌ API Error")
        st.error(f"Unexpected error connecting to API: {str(e)}")
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
    elif page == "🔍 Human Review":
        human_review.show_human_review_page()
    elif page == "💰 Carbon Rewards":
        rewards.show_rewards_page(API_BASE)
    elif page == "🔍 Data Integrity Center":
        climate_trace.show_climate_trace_page(API_BASE)
    elif page == "🛡️ Compliance Intelligence":
        advanced_compliance_dashboard.show_advanced_compliance_dashboard(API_BASE)
    elif page == "🔍 Enhanced Audit Snapshots":
        enhanced_audit_snapshots.show_enhanced_audit_snapshots(API_BASE)
    elif page == "🗺️ Enhanced Compliance Roadmap":
        enhanced_compliance_roadmap.show_enhanced_compliance_roadmap(API_BASE)
    elif page == "❓ Ask Questions":
        query.show_query_page(API_BASE)
    elif page == "audit_details":
        audit_details_page.show_audit_details_page()

def show_dashboard():
    """Show main dashboard with key metrics"""
    st.header("📊 Dashboard Overview")
    
    try:
        # Get recent emission records for dashboard
        response = requests.get(f"{API_BASE}/api/emission-records", params={"limit": 10000})
        if response.status_code == 200:
            records = response.json()
            
            if records:
                # Key metrics
                total_records = len(records)
                total_emissions = sum(record['emissions_kgco2e'] for record in records)
                avg_quality = sum(record['data_quality_score'] for record in records) / len(records)
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.markdown(
                        f'<div class="metric-card"><h3>{total_records}</h3><p>Emission Records</p></div>',
                        unsafe_allow_html=True
                    )
                
                with col2:
                    st.markdown(
                        f'<div class="metric-card"><h3>{total_emissions:,.0f}</h3><p>Total kg CO2e</p></div>',
                        unsafe_allow_html=True
                    )
                
                with col3:
                    st.markdown(
                        f'<div class="metric-card"><h3>{avg_quality:.1f}</h3><p>Avg Quality Score</p></div>',
                        unsafe_allow_html=True
                    )
                
                st.markdown("---")
                
                # Recent records table
                st.subheader("🔄 Recent Emission Records")
                df = pd.DataFrame(records)
                df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
                
                # Display relevant columns
                display_columns = ['date', 'supplier_name', 'activity_type', 'emissions_kgco2e', 'data_quality_score']
                available_columns = [col for col in display_columns if col in df.columns]
                
                st.dataframe(
                    df[available_columns],
                    width='stretch'
                )
                
                # Quick charts
                st.subheader("📈 Quick Insights")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    # Emissions by supplier
                    if 'supplier_name' in df.columns and 'emissions_kgco2e' in df.columns:
                        supplier_totals = df.groupby('supplier_name')['emissions_kgco2e'].sum().reset_index()
                        fig = px.bar(
                            supplier_totals, 
                            x='supplier_name', 
                            y='emissions_kgco2e',
                            title="Emissions by Supplier"
                        )
                        st.plotly_chart(fig, width='stretch')
                
                with col2:
                    # Scope distribution
                    if 'scope' in df.columns:
                        scope_dist = df['scope'].value_counts().reset_index()
                        scope_dist.columns = ['scope', 'count']
                        scope_dist['scope'] = 'Scope ' + scope_dist['scope'].astype(str)
                        
                        fig = px.pie(
                            scope_dist, 
                            values='count', 
                            names='scope',
                            title="Records by Scope"
                        )
                        st.plotly_chart(fig, width='stretch')
            
            else:
                st.info("No emission records found. Upload some data to get started!")
                
                # Show demo instructions
                st.subheader("🚀 Quick Start")
                st.markdown("""
                1. **Upload Data**: Use the Upload page to ingest CSV or PDF files
                2. **Explore Records**: Browse your emission records with filters
                3. **View Details**: See detailed information for each record
                4. **Run Scenarios**: Test what-if changes to parameters
                5. **Analyze Trends**: View analytics and insights
                
                **Demo Data**: The system comes with sample data from various suppliers.
                """)
        
        else:
            st.error(f"Failed to fetch emission records: {response.status_code}")
            
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
