"""
Event explorer component for browsing carbon events
"""
import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta

def show_explorer_page(api_base):
    """Show event explorer interface"""
    st.header("🔍 Event Explorer")
    st.markdown("Browse and filter carbon emission events with their DNA receipts.")
    
    # Filters
    show_filters(api_base)
    
    # Events table
    show_events_table(api_base)

def show_filters(api_base):
    """Show filtering controls"""
    st.subheader("🎛️ Filters")
    
    # Fetch available suppliers and activities
    suppliers_response = requests.get(f"{api_base}/api/suppliers")
    activities_response = requests.get(f"{api_base}/api/activities")
    
    suppliers = []
    activities = []
    
    if suppliers_response.status_code == 200:
        suppliers = [s['name'] for s in suppliers_response.json()]
    
    if activities_response.status_code == 200:
        activities = [a['type'] for a in activities_response.json()]
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # Date range
        st.write("**Date Range**")
        from_date = st.date_input(
            "From",
            value=date.today() - timedelta(days=30),
            key="explorer_from_date"
        )
    
    with col2:
        st.write("**&nbsp;**")  # Spacing
        to_date = st.date_input(
            "To",
            value=date.today(),
            key="explorer_to_date"
        )
    
    with col3:
        # Supplier filter
        st.write("**Supplier**")
        supplier_options = ["All"] + suppliers
        supplier_filter = st.selectbox(
            "Supplier name",
            supplier_options,
            key="explorer_supplier"
        )
    
    with col4:
        # Activity filter
        st.write("**Activity**")
        activity_options = ["All"] + activities
        activity_filter = st.selectbox(
            "Activity type",
            activity_options,
            key="explorer_activity"
        )
    
    # Store filters in session state
    st.session_state.explorer_filters = {
        'from_date': from_date,
        'to_date': to_date,
        'supplier': supplier_filter if supplier_filter != "All" else None,
        'activity': activity_filter if activity_filter != "All" else None
    }

def show_events_table(api_base):
    """Display events table with filtering"""
    try:
        # Get filters
        filters = st.session_state.get('explorer_filters', {})
        
        # Build query parameters
        params = {}
        if filters.get('from_date'):
            params['from_date'] = filters['from_date'].isoformat()
        if filters.get('to_date'):
            params['to_date'] = filters['to_date'].isoformat()
        if filters.get('supplier'):
            params['supplier_name'] = filters['supplier']
        if filters.get('activity'):
            params['activity_type'] = filters['activity']
        
        # Fetch emission records
        with st.spinner("Loading emission records..."):
            # Set a high limit to show all records
            params['limit'] = 10000
            response = requests.get(f"{api_base}/api/emission-records", params=params)
            
            if response.status_code == 200:
                records = response.json()
                
                if records:
                    # Convert to DataFrame
                    df = pd.DataFrame(records)
                    
                    if df.empty:
                        st.info("No records match the current filters.")
                        return
                    
                    # Format date
                    if 'date' in df.columns:
                        df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
                    
                    # Display summary
                    st.subheader(f"📊 Found {len(df)} Emission Records")
                    
                    # Summary metrics
                    total_emissions = df['emissions_kgco2e'].sum() if 'emissions_kgco2e' in df.columns else 0
                    avg_quality = df['data_quality_score'].mean() if 'data_quality_score' in df.columns else 0
                    unique_suppliers = df['supplier_name'].nunique() if 'supplier_name' in df.columns else 0
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("Total Emissions", f"{total_emissions:,.0f} kg CO₂e")
                    
                    with col2:
                        st.metric("Avg Quality Score", f"{avg_quality:.1f}")
                    
                    with col3:
                        st.metric("Unique Suppliers", unique_suppliers)
                    
                    # Records table
                    st.subheader("📋 Emission Records Table")
                    
                    # Prepare display data - use available columns
                    display_columns = ['date', 'supplier_name', 'activity_type', 'scope', 'emissions_kgco2e', 'data_quality_score']
                    available_columns = [col for col in display_columns if col in df.columns]
                    
                    display_df = df[available_columns].copy()
                    
                    # Format columns
                    if 'emissions_kgco2e' in display_df.columns:
                        display_df['emissions_kgco2e'] = display_df['emissions_kgco2e'].apply(lambda x: f"{x:,.1f}")
                    if 'data_quality_score' in display_df.columns:
                        display_df['data_quality_score'] = display_df['data_quality_score'].apply(lambda x: f"{x:.1f}")
                    
                    # Column configuration
                    column_config = {}
                    if 'date' in display_df.columns:
                        column_config['date'] = st.column_config.TextColumn('Date', width="medium")
                    if 'supplier_name' in display_df.columns:
                        column_config['supplier_name'] = st.column_config.TextColumn('Supplier', width="medium")
                    if 'activity_type' in display_df.columns:
                        column_config['activity_type'] = st.column_config.TextColumn('Activity', width="medium")
                    if 'scope' in display_df.columns:
                        column_config['scope'] = st.column_config.NumberColumn('Scope', width="small")
                    if 'emissions_kgco2e' in display_df.columns:
                        column_config['emissions_kgco2e'] = st.column_config.TextColumn('Emissions (kg CO₂e)', width="medium")
                    if 'data_quality_score' in display_df.columns:
                        column_config['data_quality_score'] = st.column_config.TextColumn('Quality Score', width="small")
                    
                    # Display the table with selection
                    st.markdown("---")
                    st.subheader("📋 Records Table")
                    
                    if len(df) > 0:
                        # Create a selectable dataframe
                        selected_df = st.dataframe(
                            display_df,
                            column_config=column_config,
                            width='stretch',
                            hide_index=True,
                            on_select="rerun",
                            selection_mode="single-row",
                            key="explorer_dataframe"
                        )
                        
                        # Handle selection
                        if selected_df.selection.rows:
                            selected_idx = selected_df.selection.rows[0]
                            selected_record = df.iloc[selected_idx]
                            selected_record_id = selected_record['id']
                            
                            # Store selected record in session state
                            st.session_state.explorer_selected_record_id = selected_record_id
                            st.session_state.explorer_selected_record_data = selected_record.to_dict()
                            
                            # Show selected record info
                            st.markdown("---")
                            st.subheader("🎯 Selected Record Details")
                            
                            # Display record information in a nice format
                            col1, col2 = st.columns([1, 1])
                            
                            with col1:
                                st.markdown("**📊 Record Information**")
                                st.metric("Supplier", selected_record.get('supplier_name', 'N/A'))
                                st.metric("Activity Type", selected_record.get('activity_type', 'N/A'))
                                st.metric("Scope", selected_record.get('scope', 'N/A'))
                                st.metric("Date", selected_record.get('date', 'N/A'))
                            
                            with col2:
                                st.markdown("**📈 Emissions & Quality**")
                                st.metric("Emissions", f"{selected_record.get('emissions_kgco2e', 0):,.1f} kg CO₂e")
                                st.metric("Quality Score", f"{selected_record.get('data_quality_score', 0):.1f}")
                                st.metric("Compliance Score", f"{selected_record.get('compliance_score', 0):.1f}")
                                st.metric("Uncertainty", f"{selected_record.get('uncertainty_pct', 0):.1f}%")
                            
                            # Action buttons
                            st.markdown("---")
                            st.subheader("🚀 Actions")
                            col1, col2, col3, col4 = st.columns(4)
                            
                            with col1:
                                if st.button("🧬 View Full Details", type="primary", key="view_details_btn"):
                                    st.session_state.selected_record_id = selected_record_id
                                    st.success("✅ Record selected! Navigate to '🧬 Event Details' page to view full details.")
                            
                            with col2:
                                if st.button("🔄 Run Scenario", key="run_scenario_btn"):
                                    st.session_state.selected_record_id = selected_record_id
                                    st.info("Scenario analysis would be shown here")
                            
                            with col3:
                                if st.button("📊 Record Chart", key="record_chart_btn"):
                                    show_record_chart(df, selected_idx)
                            
                            with col4:
                                if st.button("📋 Export Data", key="export_data_btn"):
                                    export_records_data(df)
                        
                        # Clear selection button
                        if st.button("Clear Selection", key="clear_selection_btn"):
                            if hasattr(st.session_state, 'explorer_selected_record_id'):
                                del st.session_state.explorer_selected_record_id
                            if hasattr(st.session_state, 'explorer_selected_record_data'):
                                del st.session_state.explorer_selected_record_data
                            st.rerun()
                
                else:
                    st.info("No emission records found. Try uploading some data first.")
            
            else:
                st.error(f"Failed to fetch emission records: {response.status_code}")
    
    except Exception as e:
        st.error(f"Error loading emission records: {str(e)}")

def show_record_chart(df, selected_idx):
    """Show visualization for selected record context"""
    import plotly.express as px
    import plotly.graph_objects as go
    
    selected_record = df.iloc[selected_idx]
    
    st.subheader(f"📊 Context for {selected_record['supplier_name']} - {selected_record.get('activity_type', 'N/A')}")
    
    # Time series for this supplier
    if 'supplier_name' in df.columns and 'date' in df.columns and 'emissions_kgco2e' in df.columns:
        supplier_records = df[df['supplier_name'] == selected_record['supplier_name']].copy()
        supplier_records['date'] = pd.to_datetime(supplier_records['date'])
        supplier_records = supplier_records.sort_values('date')
        
        if len(supplier_records) > 1:
            fig = px.line(
                supplier_records,
                x='date',
                y='emissions_kgco2e',
                title=f"Emission Trend - {selected_record['supplier_name']}",
                markers=True
            )
            
            # Highlight selected record
            fig.add_scatter(
                x=[pd.to_datetime(selected_record['date'])],
                y=[selected_record['emissions_kgco2e']],
                mode='markers',
                marker=dict(size=15, color='red', symbol='star'),
                name='Selected Record'
            )
            
            st.plotly_chart(fig, width='stretch')
    
    # Quality score comparison
    if 'data_quality_score' in df.columns and 'supplier_name' in df.columns:
        fig2 = px.box(
            df,
            x='supplier_name',
            y='data_quality_score',
            title="Quality Score Distribution by Supplier"
        )
        
        st.plotly_chart(fig2, width='stretch')

def export_records_data(df):
    """Export emission records data as CSV"""
    try:
        # Prepare export data
        export_df = df.copy()
        
        # Generate CSV
        csv = export_df.to_csv(index=False)
        
        # Download button
        st.download_button(
            label="📥 Download CSV",
            data=csv,
            file_name=f"emission_records_{date.today().isoformat()}.csv",
            mime="text/csv"
        )
        
        st.success("✅ Export ready for download!")
    
    except Exception as e:
        st.error(f"Export failed: {str(e)}")

def show_quick_stats(df):
    """Show quick statistics for current view"""
    st.markdown("---")
    st.subheader("📈 Quick Statistics")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Top suppliers
        top_suppliers = df.groupby('supplier_name')['result_kgco2e'].sum().sort_values(ascending=False).head(5)
        
        st.write("**Top Emitters:**")
        for supplier, emissions in top_suppliers.items():
            st.write(f"• {supplier}: {emissions:,.0f} kg CO₂e")
    
    with col2:
        # Scope distribution
        scope_dist = df['scope'].value_counts().sort_index()
        
        st.write("**Scope Distribution:**")
        for scope, count in scope_dist.items():
            percentage = (count / len(df)) * 100
            st.write(f"• Scope {scope}: {count} events ({percentage:.1f}%)")


