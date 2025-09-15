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
        supplier_filter = st.text_input(
            "Supplier name",
            placeholder="Enter supplier name...",
            key="explorer_supplier"
        )
    
    with col4:
        # Activity filter
        st.write("**Activity**")
        activity_filter = st.selectbox(
            "Activity type",
            ["All", "tanker_voyage", "electricity", "refinery", "other"],
            key="explorer_activity"
        )
    
    # Store filters in session state
    st.session_state.explorer_filters = {
        'from_date': from_date,
        'to_date': to_date,
        'supplier': supplier_filter if supplier_filter.strip() else None,
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
        
        # Fetch events
        with st.spinner("Loading events..."):
            response = requests.get(f"{api_base}/api/events", params=params)
            
            if response.status_code == 200:
                events = response.json()
                
                if events:
                    # Convert to DataFrame
                    df = pd.DataFrame(events)
                    
                    # Apply client-side filters
                    if filters.get('supplier'):
                        df = df[df['supplier_name'].str.contains(filters['supplier'], case=False, na=False)]
                    
                    if filters.get('activity'):
                        df = df[df['activity'].str.contains(filters['activity'], case=False, na=False)]
                    
                    if df.empty:
                        st.info("No events match the current filters.")
                        return
                    
                    # Format datetime
                    df['occurred_at'] = pd.to_datetime(df['occurred_at']).dt.strftime('%Y-%m-%d %H:%M')
                    
                    # Display summary
                    st.subheader(f"📊 Found {len(df)} Events")
                    
                    # Summary metrics
                    total_emissions = df['result_kgco2e'].sum()
                    avg_uncertainty = df['uncertainty_pct'].mean()
                    quality_issues = df['quality_flags'].apply(lambda x: len(x) > 0 if x else False).sum()
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("Total Emissions", f"{total_emissions:,.0f} kg CO₂e")
                    
                    with col2:
                        st.metric("Avg Uncertainty", f"{avg_uncertainty:.1f}%")
                    
                    with col3:
                        st.metric("Quality Issues", quality_issues)
                    
                    # Events table
                    st.subheader("📋 Events Table")
                    
                    # Prepare display data
                    display_df = df[[
                        'occurred_at', 'supplier_name', 'activity', 'scope',
                        'result_kgco2e', 'uncertainty_pct', 'quality_flags'
                    ]].copy()
                    
                    # Format columns
                    display_df['result_kgco2e'] = display_df['result_kgco2e'].apply(lambda x: f"{x:,.1f}")
                    display_df['uncertainty_pct'] = display_df['uncertainty_pct'].apply(lambda x: f"{x:.1f}%")
                    display_df['quality_flags'] = display_df['quality_flags'].apply(
                        lambda x: ', '.join(x) if x else '✅'
                    )
                    
                    # Column configuration
                    column_config = {
                        'occurred_at': st.column_config.TextColumn('Date', width="medium"),
                        'supplier_name': st.column_config.TextColumn('Supplier', width="medium"),
                        'activity': st.column_config.TextColumn('Activity', width="medium"),
                        'scope': st.column_config.NumberColumn('Scope', width="small"),
                        'result_kgco2e': st.column_config.TextColumn('Emissions (kg CO₂e)', width="medium"),
                        'uncertainty_pct': st.column_config.TextColumn('Uncertainty', width="small"),
                        'quality_flags': st.column_config.TextColumn('Quality', width="medium")
                    }
                    
                    # Display table with selection
                    selected_df = st.dataframe(
                        display_df,
                        column_config=column_config,
                        use_container_width=True,
                        hide_index=True,
                        on_select="rerun",
                        selection_mode="single-row"
                    )
                    
                    # Handle row selection
                    if selected_df and len(selected_df['selection']['rows']) > 0:
                        selected_idx = selected_df['selection']['rows'][0]
                        selected_event_id = df.iloc[selected_idx]['id']
                        
                        # Action buttons
                        st.markdown("---")
                        col1, col2, col3, col4 = st.columns(4)
                        
                        with col1:
                            if st.button("🧬 View DNA Details", type="primary"):
                                st.session_state.selected_event_id = selected_event_id
                                st.switch_page("pages/details.py")
                        
                        with col2:
                            if st.button("🔄 Run Scenario"):
                                st.session_state.selected_event_id = selected_event_id
                                st.switch_page("pages/scenario.py")
                        
                        with col3:
                            if st.button("📊 Event Chart"):
                                show_event_chart(df, selected_idx)
                        
                        with col4:
                            if st.button("📋 Export Data"):
                                export_events_data(df)
                
                else:
                    st.info("No events found. Try uploading some data first.")
            
            else:
                st.error(f"Failed to fetch events: {response.status_code}")
    
    except Exception as e:
        st.error(f"Error loading events: {str(e)}")

def show_event_chart(df, selected_idx):
    """Show visualization for selected event context"""
    import plotly.express as px
    import plotly.graph_objects as go
    
    selected_event = df.iloc[selected_idx]
    
    st.subheader(f"📊 Context for {selected_event['supplier_name']} - {selected_event['activity']}")
    
    # Time series for this supplier
    supplier_events = df[df['supplier_name'] == selected_event['supplier_name']].copy()
    supplier_events['occurred_at'] = pd.to_datetime(supplier_events['occurred_at'])
    supplier_events = supplier_events.sort_values('occurred_at')
    
    if len(supplier_events) > 1:
        fig = px.line(
            supplier_events,
            x='occurred_at',
            y='result_kgco2e',
            title=f"Emission Trend - {selected_event['supplier_name']}",
            markers=True
        )
        
        # Highlight selected event
        fig.add_scatter(
            x=[pd.to_datetime(selected_event['occurred_at'])],
            y=[selected_event['result_kgco2e']],
            mode='markers',
            marker=dict(size=15, color='red', symbol='star'),
            name='Selected Event'
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Uncertainty comparison
    fig2 = px.box(
        df,
        x='supplier_name',
        y='uncertainty_pct',
        title="Uncertainty Distribution by Supplier"
    )
    
    st.plotly_chart(fig2, use_container_width=True)

def export_events_data(df):
    """Export events data as CSV"""
    try:
        # Prepare export data
        export_df = df.copy()
        
        # Convert lists to strings
        export_df['quality_flags'] = export_df['quality_flags'].apply(
            lambda x: '; '.join(x) if x else ''
        )
        
        # Generate CSV
        csv = export_df.to_csv(index=False)
        
        # Download button
        st.download_button(
            label="📥 Download CSV",
            data=csv,
            file_name=f"carbon_events_{date.today().isoformat()}.csv",
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
