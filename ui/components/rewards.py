"""
Carbon Rewards Engine UI Component
Displays opportunity scanning, value estimation, and application generation
"""
import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
import json

def show_rewards_page(api_base):
    """Show Carbon Rewards Engine interface"""
    st.header("💰 Carbon Rewards Engine")
    st.markdown("Scan your emission data to discover offset opportunities, tax credits, and grant programs that can turn your carbon reductions into money.")
    
    # Main tabs
    tab1, tab2, tab3, tab4 = st.tabs(["🔍 Scan Opportunities", "📊 Opportunity Report", "📅 Deadlines & Reminders", "📝 Application Generator"])
    
    with tab1:
        show_opportunity_scanner(api_base)
    
    with tab2:
        show_opportunity_report(api_base)
    
    with tab3:
        show_deadlines_reminders(api_base)
    
    with tab4:
        show_application_generator(api_base)

def show_opportunity_scanner(api_base):
    """Show opportunity scanning interface"""
    st.subheader("🔍 Scan for Carbon Opportunities")
    st.markdown("Select emission records to scan for potential offset opportunities, tax credits, and grant programs based on your location and qualification criteria.")
    
    # Location and qualification settings
    st.markdown("### 🌍 Location & Qualification Settings")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        country = st.selectbox(
            "Country",
            ["US", "CA", "EU", "Other"],
            help="Select your country for location-specific opportunities"
        )
    
    with col2:
        if country == "US":
            state = st.selectbox(
                "State",
                ["CA", "NY", "TX", "FL", "WA", "Other"],
                help="Select your state for state-specific opportunities"
            )
        else:
            state = st.selectbox(
                "State/Province",
                ["Other"],
                help="Select your state/province for location-specific opportunities"
            )
    
    with col3:
        business_type = st.selectbox(
            "Business Type",
            ["Small Business", "Large Business", "Non-Profit", "Government", "Other"],
            help="Select your business type for qualification criteria"
        )
    
    # Record selection
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("**Select Records to Scan**")
        
        # Date range filter
        date_col1, date_col2 = st.columns(2)
        with date_col1:
            from_date = st.date_input("From Date", value=date(2025, 1, 1))
        with date_col2:
            to_date = st.date_input("To Date", value=date(2025, 3, 31))
        
        # Supplier filter
        supplier_filter = st.text_input("Filter by Supplier (optional)", placeholder="e.g., City Utilities")
        
        # Activity type filter
        activity_filter = st.selectbox(
            "Filter by Activity Type",
            ["All", "electricity", "transportation", "industrial process", "manufacturing", "other"]
        )
    
    with col2:
        st.markdown("**Scan Options**")
        
        # Data source selection
        data_source = st.radio(
            "Data Source",
            ["Real-Time APIs", "Cached Data", "Both"],
            help="Real-Time APIs: Live data from government sources (slower but current). Cached Data: Fast but may be outdated. Both: Comprehensive coverage."
        )
        
        # Opportunity types to scan
        scan_offsets = st.checkbox("Carbon Offsets", value=True)
        scan_tax_credits = st.checkbox("Tax Credits", value=True)
        scan_grants = st.checkbox("Grant Programs", value=True)
        
        # Confidence threshold
        confidence_threshold = st.slider(
            "Confidence Threshold",
            min_value=0.0,
            max_value=1.0,
            value=0.7,
            step=0.1,
            help="Only show opportunities above this confidence level"
        )
        
        # Dataset size warning
        st.info("💡 **Tip**: For large datasets, consider filtering by supplier or activity type to improve performance.")
        
        # Scan buttons
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🚀 Full Scan", type="primary"):
                scan_opportunities(api_base, from_date, to_date, supplier_filter, activity_filter, 
                                 scan_offsets, scan_tax_credits, scan_grants, confidence_threshold,
                                 country, state, business_type, data_source)
        
        with col2:
            if st.button("⚡ Quick Scan (10 records)"):
                # Override to use cached data and limit records for quick scan
                scan_opportunities(api_base, from_date, to_date, supplier_filter, activity_filter, 
                                 scan_offsets, scan_tax_credits, scan_grants, confidence_threshold,
                                 country, state, business_type, "Cached Data", quick_scan=True)

def scan_opportunities(api_base, from_date, to_date, supplier_filter, activity_filter, 
                      scan_offsets, scan_tax_credits, scan_grants, confidence_threshold,
                      country, state, business_type, data_source, quick_scan=False):
    """Execute opportunity scan"""
    try:
        # Show appropriate spinner message based on data source
        if data_source == "Real-Time APIs":
            spinner_msg = "🌐 Fetching real-time opportunities from government APIs..."
        elif data_source == "Cached Data":
            spinner_msg = "💾 Scanning cached opportunity data..."
        else:
            spinner_msg = "🔄 Scanning both real-time and cached opportunities..."
        
        with st.spinner(spinner_msg):
            # Build query parameters
            params = {
                'from_date': from_date.isoformat(),
                'to_date': to_date.isoformat()
            }
            
            if supplier_filter:
                params['supplier_name'] = supplier_filter
            if activity_filter != "All":
                params['activity_type'] = activity_filter
            
            # Fetch emission records with size management
            params['limit'] = 10000  # Set high limit to show all records
            response = requests.get(f"{api_base}/api/emission-records", params=params, timeout=30)
            
            if response.status_code == 200:
                records = response.json()
                
                if not records:
                    st.warning("No emission records found for the selected criteria.")
                    return
                
                # Check dataset size and warn user
                record_count = len(records)
                
                # Handle quick scan
                if quick_scan:
                    records = records[:10]  # Limit to 10 records for quick scan
                    st.info(f"⚡ **Quick Scan Mode**: Limited to {len(records)} records for fast results.")
                else:
                    st.success(f"Found {record_count} emission records to scan.")
                
                # Warn about large datasets (only for full scan)
                if not quick_scan and record_count > 100:
                    st.warning(f"⚠️ **Large Dataset**: You have {record_count} records. This may take longer to process. Consider filtering by supplier or activity type for faster results.")
                    
                    # Offer to limit the dataset
                    if st.button("🔧 Limit to 50 Most Recent Records", key="limit_records"):
                        records = records[:50]
                        st.info(f"Limited to {len(records)} most recent records for faster processing.")
                
                # Show progress for large datasets (or quick scan)
                if record_count > 50 or quick_scan:
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                
                # Add location information to records
                for record in records:
                    record['country_code'] = country
                    record['state_code'] = state
                    record['business_type'] = business_type
                
                # Call rewards engine API
                scan_params = {
                    'scan_offsets': scan_offsets,
                    'scan_tax_credits': scan_tax_credits,
                    'scan_grants': scan_grants,
                    'confidence_threshold': confidence_threshold,
                    'data_source': data_source,
                    'location': {
                        'country': country,
                        'state': state,
                        'business_type': business_type
                    }
                }
                
                # Adjust timeout based on dataset size and data source
                base_timeout = 60 if data_source == "Cached Data" else 120
                timeout = base_timeout + (len(records) // 10)  # Add 1 second per 10 records
                
                # Update progress for large datasets or quick scan
                if record_count > 50 or quick_scan:
                    if quick_scan:
                        status_text.text("⚡ Quick scanning opportunities...")
                    else:
                        status_text.text("🔄 Scanning opportunities... This may take a moment for large datasets.")
                    progress_bar.progress(0.3)
                
                try:
                    scan_response = requests.post(
                        f"{api_base}/api/scan-opportunities",
                        json={'records': records, 'options': scan_params},
                        timeout=timeout
                    )
                except requests.exceptions.Timeout:
                    st.error(f"⏰ **Request Timeout**: The scan took longer than {timeout} seconds. Try filtering your data or using cached data for faster results.")
                    return
                except requests.exceptions.ConnectionError:
                    st.error("🔌 **Connection Error**: Unable to connect to the server. Please check your connection and try again.")
                    return
                except Exception as e:
                    st.error(f"❌ **Unexpected Error**: {str(e)}")
                    return
                
                if scan_response.status_code == 200:
                    response_data = scan_response.json()
                    if response_data.get('success'):
                        opportunities = response_data.get('opportunities', {})
                        
                        # Complete progress for large datasets or quick scan
                        if record_count > 50 or quick_scan:
                            progress_bar.progress(1.0)
                            status_text.text("✅ Scan completed successfully!")
                        
                        st.success(f"✅ Scan completed! Found opportunities for {response_data.get('records_scanned', 0)} records.")
                        display_scan_results(opportunities)
                    else:
                        st.error(f"Scan failed: {response_data.get('error', 'Unknown error')}")
                else:
                    st.error(f"Scan failed: {scan_response.status_code}")
                    if scan_response.status_code == 500:
                        st.error("🔧 **Server Error**: The server encountered an error processing your request. This might be due to the dataset size. Try filtering your data or contact support.")
                    else:
                        st.error(f"Response: {scan_response.text}")
            
            else:
                st.error(f"Failed to fetch records: {response.status_code}")
    
    except Exception as e:
        st.error(f"Scan error: {str(e)}")
        
        # Offer fallback options for large datasets
        if "timeout" in str(e).lower() or "connection" in str(e).lower():
            st.markdown("### 🔧 **Troubleshooting Options**")
            st.markdown("If you're experiencing issues with large datasets, try these solutions:")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Option 1: Filter Your Data**")
                st.markdown("- Use the supplier filter to focus on specific suppliers")
                st.markdown("- Select a specific activity type")
                st.markdown("- Reduce the date range")
            
            with col2:
                st.markdown("**Option 2: Use Cached Data**")
                st.markdown("- Select 'Cached Data' for faster processing")
                st.markdown("- Data may be slightly outdated but processes faster")
                st.markdown("- Reduces external API calls")

def display_scan_results(opportunities):
    """Display scan results"""
    st.subheader("🎯 Scan Results")
    
    # Show data source
    data_source = opportunities.get('data_source', 'unknown')
    if data_source == 'real_time':
        st.info("🌐 **Data Source:** Real-time government APIs (most current)")
    elif data_source == 'fallback':
        st.warning("💾 **Data Source:** Cached data (may be outdated)")
    else:
        st.info("🔄 **Data Source:** Mixed real-time and cached data")
    
    summary = opportunities.get('summary', {})
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Opportunities", summary.get('total_opportunities', 0))
    
    with col2:
        st.metric("High Confidence", summary.get('high_confidence_opportunities', 0))
    
    with col3:
        st.metric("Total Potential Value", f"${summary.get('total_potential_value', 0):,.0f}")
    
    with col4:
        st.metric("Upcoming Deadlines", summary.get('upcoming_deadlines', 0))
    
    # Opportunity breakdown
    st.subheader("📊 Opportunity Breakdown")
    
    opp_data = {
        'Type': ['Carbon Offsets', 'Tax Credits', 'Grant Programs'],
        'Count': [
            summary.get('offset_opportunities', 0),
            summary.get('tax_credits', 0),
            summary.get('grant_programs', 0)
        ]
    }
    
    fig = px.bar(opp_data, x='Type', y='Count', title="Opportunities by Type")
    st.plotly_chart(fig, width='stretch')
    
    # Detailed opportunities
    show_detailed_opportunities(opportunities)

def show_detailed_opportunities(opportunities):
    """Show detailed opportunity listings"""
    st.subheader("💎 Detailed Opportunities")
    
    # Carbon Offsets
    if opportunities.get('offset_opportunities'):
        st.markdown("### 🌱 Carbon Offset Opportunities")
        for i, opp in enumerate(opportunities['offset_opportunities']):
            with st.expander(f"Offset #{i+1}: {opp.get('protocol', 'Unknown')} - ${opp.get('potential_value', 0):,.0f}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Protocol:** {opp.get('protocol', 'N/A')}")
                    st.write(f"**Platform:** {opp.get('platform', 'N/A')}")
                    st.write(f"**Emissions Reduced:** {opp.get('emissions_reduced', 0):,.1f} kg CO₂e")
                    st.write(f"**Confidence:** {opp.get('confidence', 0):.1%}")
                    
                    # Qualification status
                    qualification = opp.get('qualification_status', 'unknown')
                    if qualification == 'qualified':
                        st.success("✅ Qualified")
                    elif qualification == 'not_qualified':
                        st.error("❌ Not Qualified")
                    else:
                        st.warning("⚠️ Qualification Unknown")
                
                with col2:
                    st.write(f"**Potential Value:** ${opp.get('potential_value', 0):,.0f}")
                    st.write(f"**Deadline:** {opp.get('deadline', 'N/A')}")
                    st.write(f"**Description:** {opp.get('description', 'N/A')}")
                    
                    if opp.get('application_link'):
                        st.link_button("Apply Now", opp['application_link'])
                
                # Show specific requirements and next steps if available
                if opp.get('specific_requirements'):
                    st.write(f"**Requirements:** {opp['specific_requirements']}")
                
                if opp.get('next_steps'):
                    st.write(f"**Next Steps:** {opp['next_steps']}")
    
    # Tax Credits
    if opportunities.get('tax_credits'):
        st.markdown("### 💰 Tax Credit Opportunities")
        for i, opp in enumerate(opportunities['tax_credits']):
            with st.expander(f"Tax Credit #{i+1}: {opp.get('program', 'Unknown')} - ${opp.get('potential_value', 0):,.0f}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Program:** {opp.get('program', 'N/A')}")
                    st.write(f"**Credit Rate:** {opp.get('credit_rate', 'N/A')}")
                    st.write(f"**Emissions Reduced:** {opp.get('emissions_reduced', 0):,.1f} kg CO₂e")
                    st.write(f"**Confidence:** {opp.get('confidence', 0):.1%}")
                    
                    # Qualification status
                    qualification = opp.get('qualification_status', 'unknown')
                    if qualification == 'qualified':
                        st.success("✅ Qualified")
                    elif qualification == 'not_qualified':
                        st.error("❌ Not Qualified")
                    else:
                        st.warning("⚠️ Qualification Unknown")
                
                with col2:
                    st.write(f"**Potential Value:** ${opp.get('potential_value', 0):,.0f}")
                    st.write(f"**Deadline:** {opp.get('deadline', 'N/A')}")
                    st.write(f"**Description:** {opp.get('description', 'N/A')}")
                    
                    if opp.get('application_link'):
                        st.link_button("Apply Now", opp['application_link'])
                
                # Show specific requirements and next steps if available
                if opp.get('specific_requirements'):
                    st.write(f"**Requirements:** {opp['specific_requirements']}")
                
                if opp.get('next_steps'):
                    st.write(f"**Next Steps:** {opp['next_steps']}")
    
    # Grant Programs
    if opportunities.get('grant_programs'):
        st.markdown("### 🏛️ Grant Program Opportunities")
        for i, opp in enumerate(opportunities['grant_programs']):
            with st.expander(f"Grant #{i+1}: {opp.get('program', 'Unknown')} - ${opp.get('potential_value', 0):,.0f}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Program:** {opp.get('program', 'N/A')}")
                    st.write(f"**Grant Amount:** {opp.get('grant_amount', 'N/A')}")
                    st.write(f"**Emissions Reduced:** {opp.get('emissions_reduced', 0):,.1f} kg CO₂e")
                    st.write(f"**Confidence:** {opp.get('confidence', 0):.1%}")
                    
                    # Qualification status
                    qualification = opp.get('qualification_status', 'unknown')
                    if qualification == 'qualified':
                        st.success("✅ Qualified")
                    elif qualification == 'not_qualified':
                        st.error("❌ Not Qualified")
                    else:
                        st.warning("⚠️ Qualification Unknown")
                
                with col2:
                    st.write(f"**Potential Value:** ${opp.get('potential_value', 0):,.0f}")
                    st.write(f"**Deadline:** {opp.get('deadline', 'N/A')}")
                    st.write(f"**Description:** {opp.get('description', 'N/A')}")
                    
                    if opp.get('application_link'):
                        st.link_button("Apply Now", opp['application_link'])
                
                # Show specific requirements and next steps if available
                if opp.get('specific_requirements'):
                    st.write(f"**Requirements:** {opp['specific_requirements']}")
                
                if opp.get('next_steps'):
                    st.write(f"**Next Steps:** {opp['next_steps']}")

def show_opportunity_report(api_base):
    """Show comprehensive opportunity report"""
    st.subheader("📊 Carbon Opportunity Report")
    st.markdown("Comprehensive analysis of all detected opportunities and their potential value.")
    
    # Fetch all opportunities
    try:
        response = requests.get(f"{api_base}/api/opportunities", timeout=30)
        
        if response.status_code == 200:
            opportunities = response.json()
            display_opportunity_report(opportunities)
        else:
            st.error(f"Failed to fetch opportunities: {response.status_code}")
    
    except Exception as e:
        st.error(f"Error loading opportunities: {str(e)}")

def display_opportunity_report(opportunities):
    """Display comprehensive opportunity report"""
    if not opportunities:
        st.info("No opportunities found. Run a scan to discover potential carbon rewards.")
        return
    
    # Convert to DataFrame for analysis
    df = pd.DataFrame(opportunities)
    
    # Summary statistics
    st.subheader("📈 Summary Statistics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_value = df['potential_value'].sum()
        st.metric("Total Potential Value", f"${total_value:,.0f}")
    
    with col2:
        avg_value = df['potential_value'].mean()
        st.metric("Average Value per Opportunity", f"${avg_value:,.0f}")
    
    with col3:
        high_confidence = len(df[df['confidence_score'] >= 0.8])
        st.metric("High Confidence Opportunities", high_confidence)
    
    with col4:
        pending_deadlines = len(df[df['deadline'] != 'Ongoing'])
        st.metric("Upcoming Deadlines", pending_deadlines)
    
    # Value distribution chart
    st.subheader("💰 Value Distribution")
    
    fig = px.histogram(df, x='potential_value', nbins=20, title="Distribution of Opportunity Values")
    st.plotly_chart(fig, width='stretch')
    
    # Opportunities by type
    st.subheader("📊 Opportunities by Type")
    
    type_counts = df['opportunity_type'].value_counts()
    fig = px.pie(values=type_counts.values, names=type_counts.index, title="Opportunities by Type")
    st.plotly_chart(fig, width='stretch')
    
    # Confidence vs Value scatter
    st.subheader("🎯 Confidence vs Value Analysis")
    
    fig = px.scatter(df, x='confidence_score', y='potential_value', 
                     color='opportunity_type', size='emissions_reduced',
                     title="Confidence Score vs Potential Value")
    st.plotly_chart(fig, width='stretch')
    
    # Top opportunities table
    st.subheader("🏆 Top Opportunities by Value")
    
    top_opportunities = df.nlargest(10, 'potential_value')
    
    display_columns = ['program_name', 'opportunity_type', 'potential_value', 'confidence_score', 'deadline']
    st.dataframe(
        top_opportunities[display_columns],
        width='stretch',
        hide_index=True
    )

def show_deadlines_reminders(api_base):
    """Show deadlines and reminder management"""
    st.subheader("📅 Deadlines & Reminders")
    st.markdown("Track application deadlines and set up automated reminders.")
    
    # Fetch deadlines
    try:
        response = requests.get(f"{api_base}/api/deadlines", timeout=30)
        
        if response.status_code == 200:
            deadlines = response.json()
            display_deadlines(deadlines)
        else:
            st.error(f"Failed to fetch deadlines: {response.status_code}")
    
    except Exception as e:
        st.error(f"Error loading deadlines: {str(e)}")

def display_deadlines(deadlines):
    """Display deadline management interface"""
    if not deadlines:
        st.info("No deadlines found. Opportunities will appear here once detected.")
        return
    
    # Convert to DataFrame
    df = pd.DataFrame(deadlines)
    df['deadline_date'] = pd.to_datetime(df['deadline_date'])
    
    # Filter options
    col1, col2 = st.columns(2)
    
    with col1:
        show_completed = st.checkbox("Show Completed Deadlines", value=False)
    
    with col2:
        days_ahead = st.selectbox("Show Deadlines Within", [7, 14, 30, 90, 365], index=2)
    
    # Filter data
    if not show_completed:
        df = df[df['is_completed'] == False]
    
    # Filter by days ahead
    cutoff_date = date.today() + timedelta(days=days_ahead)
    df = df[df['deadline_date'].dt.date <= cutoff_date]
    
    # Sort by deadline
    df = df.sort_values('deadline_date')
    
    # Display deadlines
    st.subheader(f"📋 Upcoming Deadlines ({len(df)} found)")
    
    for _, deadline in df.iterrows():
        days_until = (deadline['deadline_date'].date() - date.today()).days
        
        if days_until < 0:
            status = "❌ Overdue"
            color = "red"
        elif days_until == 0:
            status = "⚠️ Due Today"
            color = "orange"
        elif days_until <= 7:
            status = f"🔴 Due in {days_until} days"
            color = "red"
        elif days_until <= 30:
            status = f"🟡 Due in {days_until} days"
            color = "orange"
        else:
            status = f"🟢 Due in {days_until} days"
            color = "green"
        
        with st.expander(f"{deadline['program_name']} - {status}"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**Program:** {deadline['program_name']}")
                st.write(f"**Type:** {deadline['deadline_type']}")
                st.write(f"**Deadline:** {deadline['deadline_date'].strftime('%Y-%m-%d')}")
                st.write(f"**Timezone:** {deadline.get('timezone', 'UTC')}")
            
            with col2:
                st.write(f"**Status:** {status}")
                st.write(f"**Active:** {'Yes' if deadline['is_active'] else 'No'}")
                st.write(f"**Completed:** {'Yes' if deadline['is_completed'] else 'No'}")
                
                if not deadline['is_completed']:
                    if st.button(f"Mark Complete", key=f"complete_{deadline['id']}"):
                        mark_deadline_complete(api_base, deadline['id'])

def mark_deadline_complete(api_base, deadline_id):
    """Mark a deadline as complete"""
    try:
        response = requests.post(f"{api_base}/api/deadlines/{deadline_id}/complete")
        if response.status_code == 200:
            st.success("Deadline marked as complete!")
            st.rerun()
        else:
            st.error("Failed to mark deadline as complete")
    except Exception as e:
        st.error(f"Error: {str(e)}")

def show_application_generator(api_base):
    """Show application generation interface"""
    st.subheader("📝 Application Generator")
    st.markdown("Generate pre-filled applications for detected opportunities.")
    
    # Select opportunity
    try:
        response = requests.get(f"{api_base}/api/opportunities", timeout=30)
        
        if response.status_code == 200:
            opportunities = response.json()
            
            if not opportunities:
                st.info("No opportunities found. Run a scan to discover potential applications.")
                return
            
            # Opportunity selector
            opportunity_options = {
                f"{opp['program_name']} - ${opp['potential_value']:,.0f}": opp['id'] 
                for opp in opportunities
            }
            
            selected_opp_name = st.selectbox("Select Opportunity", list(opportunity_options.keys()))
            selected_opp_id = opportunity_options[selected_opp_name]
            
            # Get opportunity details
            opp_details = next(opp for opp in opportunities if opp['id'] == selected_opp_id)
            
            # Generate application
            if st.button("📝 Generate Application", type="primary"):
                generate_application(api_base, selected_opp_id, opp_details)
        
        else:
            st.error(f"Failed to fetch opportunities: {response.status_code}")
    
    except Exception as e:
        st.error(f"Error loading opportunities: {str(e)}")

def generate_application(api_base, opportunity_id, opportunity_details):
    """Generate pre-filled application"""
    try:
        with st.spinner("Generating application..."):
            response = requests.post(
                f"{api_base}/api/generate-application",
                json={'opportunity_id': opportunity_id},
                timeout=60
            )
            
            if response.status_code == 200:
                application = response.json()
                display_generated_application(application, opportunity_details)
            else:
                st.error(f"Application generation failed: {response.status_code}")
    
    except Exception as e:
        st.error(f"Error generating application: {str(e)}")

def display_generated_application(application, opportunity_details):
    """Display generated application"""
    st.subheader("📄 Generated Application")
    
    # Application summary
    col1, col2 = st.columns(2)
    
    with col1:
        st.write(f"**Program:** {opportunity_details['program_name']}")
        st.write(f"**Opportunity Type:** {opportunity_details['opportunity_type']}")
        st.write(f"**Potential Value:** ${opportunity_details['potential_value']:,.0f}")
    
    with col2:
        st.write(f"**Application URL:** {opportunity_details.get('application_link', 'N/A')}")
        st.write(f"**Deadline:** {opportunity_details.get('deadline', 'N/A')}")
        st.write(f"**Confidence:** {opportunity_details.get('confidence_score', 0):.1%}")
    
    # Pre-filled form data
    st.subheader("📋 Pre-filled Form Data")
    
    if application.get('form_fields'):
        form_data = application['form_fields']
        
        for field, value in form_data.items():
            st.write(f"**{field.replace('_', ' ').title()}:** {value}")
    
    # Required documents
    if application.get('required_documents'):
        st.subheader("📎 Required Documents")
        
        for doc in application['required_documents']:
            st.write(f"• {doc}")
    
    # Download options
    st.subheader("💾 Download Application")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📄 Download PDF"):
            st.info("PDF download would be generated here")
    
    with col2:
        if st.button("📊 Download Excel"):
            st.info("Excel download would be generated here")
    
    with col3:
        if st.button("📧 Email Application"):
            st.info("Email application would be sent here")
    
    # Application tracking
    st.subheader("📈 Application Tracking")
    
    if st.button("📝 Submit Application"):
        submit_application(api_base, opportunity_details['id'])

def submit_application(api_base, opportunity_id):
    """Submit application and update status"""
    try:
        response = requests.post(
            f"{api_base}/api/submit-application",
            json={'opportunity_id': opportunity_id},
            timeout=30
        )
        
        if response.status_code == 200:
            st.success("Application submitted successfully!")
            st.info("You will receive updates on the application status.")
        else:
            st.error("Failed to submit application")
    
    except Exception as e:
        st.error(f"Error submitting application: {str(e)}")
