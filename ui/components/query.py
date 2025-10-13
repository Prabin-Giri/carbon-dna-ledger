"""
Template-based NL-to-SQL query component
"""
import streamlit as st
import requests
import pandas as pd
import json

def show_query_page(api_base):
    """Show template-based query interface"""
    st.header("❓ Ask Questions")
    st.markdown("Query your carbon data using pre-defined question templates with full SQL transparency.")
    
    # Available query templates
    show_available_templates()
    
    # Query interface
    show_query_interface(api_base)

def show_available_templates():
    """Show information about available query templates"""
    with st.expander("📋 Available Query Templates"):
        st.markdown("""
        **🏆 Top Suppliers in Period**
        - Find the highest emitting suppliers in a specified time period
        - Parameters: period (month/quarter/year), limit (number of results)
        - Note: Uses record date or creation date if record date is missing
        
        **📈 Largest Month-over-Month Increase**  
        - Identify suppliers with the biggest emission increases
        - Parameters: None (automatically uses recent data)
        
        **⚠️ Events with Highest Uncertainty**
        - Find events with the most uncertainty or quality issues (data_quality_score < 90)
        - Parameters: limit (number of results)
        - Note: Uncertainty = 100 - data_quality_score, so higher uncertainty means lower quality
        
        **📊 Total Emissions by Activity Type**
        - Analyze emissions breakdown by activity category
        - Parameters: limit (number of activity types)
        
        **📈 Recent Emission Trends**
        - View daily emission trends over time
        - Parameters: days (time period to analyze)
        
        **📋 All Suppliers Summary**
        - View all suppliers with emissions (excludes zero-emission suppliers)
        - Parameters: limit (number of suppliers)
        
        **📋 All Suppliers Including Zeros**
        - View all suppliers including those with zero emissions
        - Parameters: limit (number of suppliers)
        
        These templates ensure safe, pre-validated queries while providing full SQL transparency.
        """)

def show_query_interface(api_base):
    """Show the query interface"""
    st.subheader("🔍 Query Builder")
    
    # Template selection
    template_options = {
        "Top suppliers in period": "Find the highest emitting suppliers in a specific time period",
        "Largest month-over-month increase": "Find suppliers with biggest emission increases", 
        "Events with highest uncertainty": "Find events with most uncertainty or quality issues",
        "Total emissions by activity type": "Analyze emissions by activity category",
        "Recent emission trends": "View daily emission trends over time",
        "All suppliers summary": "View all suppliers with emissions (excludes zero-emission suppliers)",
        "All suppliers including zeros": "View all suppliers including those with zero emissions"
    }
    
    selected_template = st.selectbox(
        "Choose a question template:",
        list(template_options.keys()),
        help="Select from available pre-defined query templates"
    )
    
    st.info(f"**Selected**: {template_options[selected_template]}")
    
    # Parameter input based on selected template
    params = collect_template_parameters(selected_template)
    
    # Execute query button
    if st.button("🚀 Execute Query", type="primary"):
        execute_template_query(api_base, selected_template, params)

def collect_template_parameters(template_name):
    """Collect parameters for the selected template"""
    params = {}
    
    if template_name == "Top suppliers in period":
        col1, col2 = st.columns(2)
        
        with col1:
            params['period'] = st.selectbox(
                "Time Period",
                ["month", "quarter", "year"],
                help="Period for supplier ranking analysis"
            )
        
        with col2:
            params['limit'] = st.slider(
                "Number of Results",
                min_value=5,
                max_value=50,
                value=10,
                help="How many top suppliers to return"
            )
    
    elif template_name == "Largest month-over-month increase":
        st.info("This template uses recent data automatically - no parameters needed.")
    
    elif template_name == "Events with highest uncertainty":
        params['limit'] = st.slider(
            "Number of Results",
            min_value=5,
            max_value=100,
            value=20,
            help="How many high-uncertainty events to return"
        )
    
    elif template_name == "Total emissions by activity type":
        params['limit'] = st.slider(
            "Number of Activity Types",
            min_value=5,
            max_value=20,
            value=10,
            help="How many activity types to show"
        )
    
    elif template_name == "Recent emission trends":
        params['days'] = st.slider(
            "Time Period (Days)",
            min_value=7,
            max_value=90,
            value=30,
            help="How many days back to analyze"
        )
    
    elif template_name == "All suppliers summary":
        params['limit'] = st.slider(
            "Number of Suppliers",
            min_value=5,
            max_value=50,
            value=20,
            help="How many suppliers to show (excludes zero-emission suppliers)"
        )
    
    elif template_name == "All suppliers including zeros":
        params['limit'] = st.slider(
            "Number of Suppliers",
            min_value=5,
            max_value=50,
            value=20,
            help="How many suppliers to show (includes zero-emission suppliers)"
        )
    
    return params

def execute_template_query(api_base, question, params):
    """Execute the template query and display results"""
    try:
        with st.spinner("Executing query..."):
            # Prepare request
            query_request = {
                "question": question,
                "params": params
            }
            
            # Call API
            response = requests.post(
                f"{api_base}/api/query",
                json=query_request
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Display query results
                show_query_results(result)
                
            else:
                st.error(f"Query failed: {response.status_code}")
                try:
                    error_detail = response.json().get('detail', 'Unknown error')
                    st.error(f"Error details: {error_detail}")
                except:
                    st.error(f"Response: {response.text}")
    
    except Exception as e:
        st.error(f"Query execution error: {str(e)}")

def show_query_results(result):
    """Display query execution results"""
    st.markdown("---")
    st.subheader("📊 Query Results")
    
    # Show template information
    st.success(f"✅ Executed template: **{result['template_name']}**")
    
    # Show SQL transparency
    show_sql_transparency(result['sql'])
    
    # Show results data
    show_results_data(result['rows'], result['template_name'])

def show_sql_transparency(sql_query):
    """Show the SQL query for transparency"""
    with st.expander("🔍 SQL Query (Transparency)"):
        st.markdown("**Generated SQL:**")
        st.code(sql_query, language="sql")
        
        st.markdown("**Why SQL Transparency Matters:**")
        st.info("""
        - **Auditability**: You can see exactly what data is being queried
        - **Trust**: No hidden logic or black-box operations  
        - **Learning**: Understand how questions translate to database queries
        - **Verification**: Technical users can validate the query logic
        """)

def show_results_data(rows, template_name):
    """Display query results with appropriate formatting"""
    st.subheader("📋 Results")
    
    if not rows:
        st.info("No results found for this query.")
        return
    
    # Convert to DataFrame for better display
    df = pd.DataFrame(rows)
    
    if template_name == "Top suppliers in period":
        show_top_suppliers_results(df)
    elif template_name == "Largest month-over-month increase":
        show_delta_results(df)
    elif template_name == "Events with highest uncertainty":
        show_uncertainty_results(df)
    elif template_name == "Total emissions by activity type":
        show_activity_results(df)
    elif template_name == "Recent emission trends":
        show_trends_results(df)
    elif template_name == "All suppliers summary":
        show_all_suppliers_results(df)
    elif template_name == "All suppliers including zeros":
        show_all_suppliers_results(df)
    else:
        # Generic table display
        st.dataframe(df, width='stretch')
    
    # Export options
    show_export_options(df, template_name)

def show_top_suppliers_results(df):
    """Display top suppliers results with visualization"""
    # Format numeric columns
    if 'total_kgco2e' in df.columns:
        df['total_kgco2e'] = df['total_kgco2e'].round(1)
    
    if 'avg_uncertainty' in df.columns:
        df['avg_uncertainty'] = df['avg_uncertainty'].round(1)
    
    # Display table
    st.dataframe(
        df,
        column_config={
            "supplier_name": st.column_config.TextColumn("Supplier"),
            "total_kgco2e": st.column_config.NumberColumn("Total Emissions (kg CO₂e)", format="%.1f"),
            "event_count": st.column_config.NumberColumn("Events"),
            "avg_uncertainty": st.column_config.NumberColumn("Avg Uncertainty (%)", format="%.1f")
        },
        width='stretch',
        hide_index=True
    )
    
    # Visualization
    if len(df) > 1:
        import plotly.express as px
        
        fig = px.bar(
            df.head(10),  # Show top 10 in chart
            x='supplier_name',
            y='total_kgco2e',
            title="Top Emitters Visualization",
            labels={'total_kgco2e': 'Total Emissions (kg CO₂e)', 'supplier_name': 'Supplier'}
        )
        
        fig.update_layout(xaxis_tickangle=45)
        st.plotly_chart(fig, width='stretch')

def show_delta_results(df):
    """Display delta/increase results"""
    # Format numeric columns
    if 'delta_kgco2e' in df.columns:
        df['delta_kgco2e'] = df['delta_kgco2e'].round(1)
    
    if 'pct_change' in df.columns:
        df['pct_change'] = df['pct_change'].round(1)
    
    # Display table with color coding
    st.dataframe(
        df,
        column_config={
            "supplier_name": st.column_config.TextColumn("Supplier"),
            "delta_kgco2e": st.column_config.NumberColumn("Change (kg CO₂e)", format="%.1f"),
            "pct_change": st.column_config.NumberColumn("Change (%)", format="%.1f")
        },
        width='stretch',
        hide_index=True
    )
    
    # Insights
    if not df.empty:
        largest_increase = df.iloc[0] if len(df) > 0 else None
        
        if largest_increase is not None:
            st.warning(f"⚠️ **Largest Increase**: {largest_increase['supplier_name']} had the biggest increase with {largest_increase.get('pct_change', 0):.1f}% change")

def show_uncertainty_results(df):
    """Display uncertainty results with quality indicators"""
    # Format columns
    if 'uncertainty_pct' in df.columns:
        df['uncertainty_pct'] = df['uncertainty_pct'].round(1)
    
    if 'result_kgco2e' in df.columns:
        df['result_kgco2e'] = df['result_kgco2e'].round(1)
    
    # Format occurred_at if present
    if 'occurred_at' in df.columns:
        df['occurred_at'] = pd.to_datetime(df['occurred_at']).dt.strftime('%Y-%m-%d')
    
    # Display with quality indicators
    display_df = df.copy()
    
    # Add quality indicator
    if 'uncertainty_pct' in display_df.columns:
        display_df['quality_indicator'] = display_df['uncertainty_pct'].apply(
            lambda x: "🔴 High" if x > 30 else "🟡 Medium" if x > 15 else "🟢 Good"
        )
    
    st.dataframe(
        display_df,
        column_config={
            "occurred_at": st.column_config.TextColumn("Date"),
            "supplier_name": st.column_config.TextColumn("Supplier"), 
            "activity": st.column_config.TextColumn("Activity"),
            "uncertainty_pct": st.column_config.NumberColumn("Uncertainty (%)", format="%.1f"),
            "result_kgco2e": st.column_config.NumberColumn("Emissions (kg CO₂e)", format="%.1f"),
            "quality_indicator": st.column_config.TextColumn("Quality")
        },
        width='stretch',
        hide_index=True
    )
    
    # Quality summary
    if 'uncertainty_pct' in df.columns:
        avg_uncertainty = df['uncertainty_pct'].mean()
        high_uncertainty_count = len(df[df['uncertainty_pct'] > 30])
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Average Uncertainty", f"{avg_uncertainty:.1f}%")
        
        with col2:
            st.metric("High Uncertainty Events", high_uncertainty_count)

def show_activity_results(df):
    """Display activity type results with visualization"""
    # Format numeric columns
    if 'total_emissions' in df.columns:
        df['total_emissions'] = df['total_emissions'].round(1)
    
    if 'avg_emissions' in df.columns:
        df['avg_emissions'] = df['avg_emissions'].round(1)
    
    if 'avg_quality' in df.columns:
        df['avg_quality'] = df['avg_quality'].round(1)
    
    # Display table
    st.dataframe(
        df,
        column_config={
            "activity_type": st.column_config.TextColumn("Activity Type"),
            "record_count": st.column_config.NumberColumn("Records"),
            "total_emissions": st.column_config.NumberColumn("Total Emissions (kg CO₂e)", format="%.1f"),
            "avg_emissions": st.column_config.NumberColumn("Avg Emissions (kg CO₂e)", format="%.1f"),
            "avg_quality": st.column_config.NumberColumn("Avg Quality Score", format="%.1f")
        },
        width='stretch',
        hide_index=True
    )
    
    # Visualization
    if len(df) > 1:
        import plotly.express as px
        
        fig = px.pie(
            df,
            values='total_emissions',
            names='activity_type',
            title="Emissions Distribution by Activity Type"
        )
        st.plotly_chart(fig, width='stretch')

def show_trends_results(df):
    """Display trends results with time series visualization"""
    # Format numeric columns
    if 'daily_emissions' in df.columns:
        df['daily_emissions'] = df['daily_emissions'].round(1)
    
    if 'avg_quality' in df.columns:
        df['avg_quality'] = df['avg_quality'].round(1)
    
    # Convert date column
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
    
    # Display table
    st.dataframe(
        df,
        column_config={
            "date": st.column_config.DateColumn("Date"),
            "daily_records": st.column_config.NumberColumn("Daily Records"),
            "daily_emissions": st.column_config.NumberColumn("Daily Emissions (kg CO₂e)", format="%.1f"),
            "avg_quality": st.column_config.NumberColumn("Avg Quality Score", format="%.1f")
        },
        width='stretch',
        hide_index=True
    )
    
    # Time series visualization
    if len(df) > 1 and 'date' in df.columns:
        import plotly.express as px
        
        fig = px.line(
            df,
            x='date',
            y='daily_emissions',
            title="Daily Emission Trends",
            labels={'daily_emissions': 'Daily Emissions (kg CO₂e)', 'date': 'Date'}
        )
        fig.update_layout(xaxis_title="Date", yaxis_title="Daily Emissions (kg CO₂e)")
        st.plotly_chart(fig, width='stretch')
        
        # Quality trends
        fig2 = px.line(
            df,
            x='date',
            y='avg_quality',
            title="Daily Data Quality Trends",
            labels={'avg_quality': 'Average Quality Score', 'date': 'Date'}
        )
        fig2.update_layout(xaxis_title="Date", yaxis_title="Average Quality Score")
        st.plotly_chart(fig2, width='stretch')

def show_all_suppliers_results(df):
    """Display all suppliers results with date ranges"""
    # Format numeric columns
    if 'total_kgco2e' in df.columns:
        df['total_kgco2e'] = df['total_kgco2e'].round(1)
    
    if 'avg_uncertainty' in df.columns:
        df['avg_uncertainty'] = df['avg_uncertainty'].round(1)
    
    # Format date columns
    if 'earliest_date' in df.columns:
        df['earliest_date'] = pd.to_datetime(df['earliest_date']).dt.strftime('%Y-%m-%d')
    if 'latest_date' in df.columns:
        df['latest_date'] = pd.to_datetime(df['latest_date']).dt.strftime('%Y-%m-%d')
    
    # Display table
    st.dataframe(
        df,
        column_config={
            "supplier_name": st.column_config.TextColumn("Supplier"),
            "total_kgco2e": st.column_config.NumberColumn("Total Emissions (kg CO₂e)", format="%.1f"),
            "event_count": st.column_config.NumberColumn("Records"),
            "avg_uncertainty": st.column_config.NumberColumn("Avg Uncertainty (%)", format="%.1f"),
            "earliest_date": st.column_config.TextColumn("First Record"),
            "latest_date": st.column_config.TextColumn("Latest Record")
        },
        width='stretch',
        hide_index=True
    )
    
    # Summary statistics
    if not df.empty:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            total_emissions = df['total_kgco2e'].sum()
            st.metric("Total Emissions", f"{total_emissions:,.1f} kg CO₂e")
        
        with col2:
            total_records = df['event_count'].sum()
            st.metric("Total Records", f"{total_records:,}")
        
        with col3:
            avg_uncertainty = df['avg_uncertainty'].mean()
            st.metric("Average Uncertainty", f"{avg_uncertainty:.1f}%")
    
    # Visualization
    if len(df) > 1:
        import plotly.express as px
        
        fig = px.bar(
            df.head(10),  # Show top 10 in chart
            x='supplier_name',
            y='total_kgco2e',
            title="All Suppliers - Total Emissions",
            labels={'total_kgco2e': 'Total Emissions (kg CO₂e)', 'supplier_name': 'Supplier'}
        )
        
        fig.update_layout(xaxis_tickangle=45)
        st.plotly_chart(fig, width='stretch')

def show_export_options(df, template_name):
    """Show export options for query results"""
    st.markdown("---")
    st.subheader("📤 Export Results")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # CSV export
        csv = df.to_csv(index=False)
        st.download_button(
            label="📊 Download as CSV",
            data=csv,
            file_name=f"query_results_{template_name.replace(' ', '_').lower()}.csv",
            mime="text/csv"
        )
    
    with col2:
        # JSON export
        json_data = df.to_json(orient='records', indent=2)
        st.download_button(
            label="📋 Download as JSON", 
            data=json_data,
            file_name=f"query_results_{template_name.replace(' ', '_').lower()}.json",
            mime="application/json"
        )
    
    with col3:
        # Copy to clipboard (show data for copying)
        if st.button("📋 Show Raw Data"):
            st.code(df.to_string(index=False), language=None)

def show_query_examples():
    """Show examples of how to use the query system"""
    st.markdown("---")
    st.subheader("💡 Query Examples")
    
    examples = [
        {
            "title": "Find Monthly Top Emitters",
            "template": "Top suppliers in period",
            "params": {"period": "month", "limit": 5},
            "description": "Get the top 5 emitting suppliers from the current month"
        },
        {
            "title": "Identify Growing Emissions",
            "template": "Largest month-over-month increase", 
            "params": {},
            "description": "Find which suppliers had the biggest emission increases recently"
        },
        {
            "title": "Quality Control Check",
            "template": "Events with highest uncertainty",
            "params": {"limit": 20},
            "description": "Find the 20 events with highest uncertainty for quality review"
        }
    ]
    
    for example in examples:
        with st.expander(f"📝 {example['title']}"):
            st.write(f"**Template**: {example['template']}")
            st.write(f"**Parameters**: {example['params'] if example['params'] else 'None required'}")  
            st.write(f"**Purpose**: {example['description']}")

def show_query_limitations():
    """Show information about query limitations and security"""
    with st.expander("🔒 Security & Limitations"):
        st.markdown("""
        **Security Features:**
        - ✅ Only pre-approved query templates allowed
        - ✅ No arbitrary SQL injection possible  
        - ✅ Parameters are validated and sanitized
        - ✅ Full SQL transparency for auditability
        
        **Current Limitations:**
        - 🚫 No freeform SQL queries (by design for security)
        - 📊 Limited to 3 pre-defined query patterns
        - ⏱️ Query timeout after 30 seconds
        - 📄 Results limited to 1000 rows maximum
        
        **Why These Limitations:**
        - **Security**: Prevents SQL injection and unauthorized data access
        - **Performance**: Ensures queries don't overwhelm the database  
        - **Compliance**: Maintains audit trail and access control
        - **Usability**: Provides guided experience for non-technical users
        """)
