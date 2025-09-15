"""
Analytics dashboard component with charts and insights
"""
import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta

def show_analytics_page(api_base):
    """Show analytics dashboard"""
    st.header("📈 Analytics Dashboard")
    st.markdown("Comprehensive analytics and insights for carbon emission data.")
    
    # Analytics navigation
    analysis_type = st.selectbox(
        "Choose Analysis Type:",
        ["📊 Overview", "🏆 Top Emitters", "📈 Trends & Deltas", "⚠️ Quality Gaps", "🔍 Custom Analysis"]
    )
    
    if analysis_type == "📊 Overview":
        show_overview_analytics(api_base)
    elif analysis_type == "🏆 Top Emitters":
        show_top_emitters_analysis(api_base)
    elif analysis_type == "📈 Trends & Deltas":
        show_trends_analysis(api_base)
    elif analysis_type == "⚠️ Quality Gaps":
        show_quality_analysis(api_base)
    elif analysis_type == "🔍 Custom Analysis":
        show_custom_analysis(api_base)

def show_overview_analytics(api_base):
    """Show overview analytics dashboard"""
    st.subheader("📊 Emission Overview")
    
    try:
        # Date range selector
        col1, col2 = st.columns(2)
        
        with col1:
            from_date = st.date_input(
                "From Date",
                value=date.today() - timedelta(days=90),
                key="analytics_from"
            )
        
        with col2:
            to_date = st.date_input(
                "To Date",
                value=date.today(),
                key="analytics_to"
            )
        
        # Fetch recent events for overview
        params = {
            'from_date': from_date.isoformat(),
            'to_date': to_date.isoformat(),
            'limit': 1000  # Get more data for analytics
        }
        
        with st.spinner("Loading analytics data..."):
            response = requests.get(f"{api_base}/api/events", params=params)
            
            if response.status_code == 200:
                events = response.json()
                
                if events:
                    df = pd.DataFrame(events)
                    show_overview_metrics(df)
                    show_overview_charts(df)
                else:
                    st.info("No data available for the selected date range.")
            else:
                st.error(f"Failed to fetch analytics data: {response.status_code}")
    
    except Exception as e:
        st.error(f"Analytics error: {str(e)}")

def show_overview_metrics(df):
    """Show key metrics overview"""
    # Calculate key metrics
    total_events = len(df)
    total_emissions = df['result_kgco2e'].sum()
    avg_emissions = df['result_kgco2e'].mean()
    avg_uncertainty = df['uncertainty_pct'].mean()
    
    # Quality issues count
    quality_issues = df['quality_flags'].apply(lambda x: len(x) > 0 if x else False).sum()
    
    # Display metrics
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric(
            "Total Events",
            f"{total_events:,}",
            help="Total number of carbon events"
        )
    
    with col2:
        st.metric(
            "Total Emissions",
            f"{total_emissions:,.0f} kg CO₂e",
            help="Sum of all emissions in period"
        )
    
    with col3:
        st.metric(
            "Avg per Event",
            f"{avg_emissions:,.0f} kg CO₂e",
            help="Average emissions per event"
        )
    
    with col4:
        st.metric(
            "Avg Uncertainty",
            f"{avg_uncertainty:.1f}%",
            help="Average uncertainty across events"
        )
    
    with col5:
        st.metric(
            "Quality Issues",
            quality_issues,
            delta=f"{(quality_issues/total_events)*100:.1f}%" if total_events > 0 else "0%",
            help="Events with quality flags"
        )

def show_overview_charts(df):
    """Show overview visualization charts"""
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Emissions by supplier
        supplier_emissions = df.groupby('supplier_name')['result_kgco2e'].sum().sort_values(ascending=False)
        
        fig = px.bar(
            x=supplier_emissions.index,
            y=supplier_emissions.values,
            title="Total Emissions by Supplier",
            labels={'x': 'Supplier', 'y': 'Emissions (kg CO₂e)'}
        )
        fig.update_layout(xaxis_tickangle=45)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Scope distribution
        scope_dist = df['scope'].value_counts().sort_index()
        scope_labels = [f"Scope {s}" for s in scope_dist.index]
        
        fig = px.pie(
            values=scope_dist.values,
            names=scope_labels,
            title="Emissions by GHG Scope"
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Time series
    st.subheader("📈 Emission Trends")
    
    df['occurred_at'] = pd.to_datetime(df['occurred_at'])
    df['date'] = df['occurred_at'].dt.date
    
    daily_emissions = df.groupby('date')['result_kgco2e'].sum().reset_index()
    
    fig = px.line(
        daily_emissions,
        x='date',
        y='result_kgco2e',
        title="Daily Emission Totals",
        labels={'result_kgco2e': 'Emissions (kg CO₂e)', 'date': 'Date'}
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Activity breakdown
    st.subheader("🏭 Activity Analysis")
    
    activity_stats = df.groupby('activity').agg({
        'result_kgco2e': ['count', 'sum', 'mean'],
        'uncertainty_pct': 'mean'
    }).round(1)
    
    activity_stats.columns = ['Count', 'Total Emissions', 'Avg Emissions', 'Avg Uncertainty']
    
    st.dataframe(activity_stats, use_container_width=True)

def show_top_emitters_analysis(api_base):
    """Show top emitters analysis"""
    st.subheader("🏆 Top Emitters Analysis")
    
    # Period selector
    col1, col2 = st.columns(2)
    
    with col1:
        period = st.selectbox(
            "Analysis Period",
            ["month", "quarter", "year"],
            help="Time period for top emitters analysis"
        )
    
    with col2:
        limit = st.slider(
            "Number of Top Emitters",
            min_value=5,
            max_value=50,
            value=10,
            help="How many top emitters to show"
        )
    
    try:
        with st.spinner("Loading top emitters..."):
            params = {
                'period': period,
                'limit': limit
            }
            
            response = requests.get(f"{api_base}/api/analytics/top_emitters", params=params)
            
            if response.status_code == 200:
                top_emitters = response.json()
                
                if top_emitters:
                    # Convert to DataFrame
                    df = pd.DataFrame(top_emitters)
                    
                    # Display chart
                    fig = px.bar(
                        df,
                        x='supplier_name',
                        y='total_kgco2e',
                        title=f"Top {limit} Emitters - {period.title()}",
                        labels={'total_kgco2e': 'Total Emissions (kg CO₂e)', 'supplier_name': 'Supplier'},
                        color='total_kgco2e',
                        color_continuous_scale='Reds'
                    )
                    
                    fig.update_layout(xaxis_tickangle=45)
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Details table
                    st.subheader("📋 Detailed Rankings")
                    
                    # Add ranking
                    df['rank'] = range(1, len(df) + 1)
                    
                    # Format for display
                    display_df = df[['rank', 'supplier_name', 'total_kgco2e', 'event_count', 'avg_uncertainty']].copy()
                    display_df['total_kgco2e'] = display_df['total_kgco2e'].apply(lambda x: f"{x:,.0f}")
                    display_df['avg_uncertainty'] = display_df['avg_uncertainty'].apply(lambda x: f"{x:.1f}%")
                    
                    display_df.columns = ['Rank', 'Supplier', 'Total Emissions', 'Events', 'Avg Uncertainty']
                    
                    st.dataframe(display_df, use_container_width=True, hide_index=True)
                    
                    # Insights
                    show_top_emitters_insights(df)
                
                else:
                    st.info("No emitters data available.")
            else:
                st.error(f"Failed to fetch top emitters: {response.status_code}")
    
    except Exception as e:
        st.error(f"Top emitters analysis error: {str(e)}")

def show_top_emitters_insights(df):
    """Show insights about top emitters"""
    st.subheader("💡 Key Insights")
    
    total_emissions = df['total_kgco2e'].sum()
    top_emitter = df.iloc[0]
    
    # Top emitter dominance
    dominance_pct = (top_emitter['total_kgco2e'] / total_emissions) * 100
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Top Emitter Dominance",
            f"{dominance_pct:.1f}%",
            help="Percentage of total emissions from top emitter"
        )
    
    with col2:
        # Top 3 concentration
        top3_emissions = df.head(3)['total_kgco2e'].sum()
        top3_pct = (top3_emissions / total_emissions) * 100
        
        st.metric(
            "Top 3 Concentration",
            f"{top3_pct:.1f}%",
            help="Percentage of emissions from top 3 emitters"
        )
    
    with col3:
        # Average uncertainty of top emitters
        avg_uncertainty = df['avg_uncertainty'].mean()
        
        st.metric(
            "Top Emitters Avg Uncertainty",
            f"{avg_uncertainty:.1f}%",
            help="Average uncertainty of top emitters"
        )
    
    # Recommendations
    if dominance_pct > 50:
        st.warning(f"⚠️ **High Concentration**: {top_emitter['supplier_name']} accounts for {dominance_pct:.1f}% of emissions. Focus reduction efforts here for maximum impact.")
    
    if avg_uncertainty > 25:
        st.warning(f"⚠️ **High Uncertainty**: Top emitters have {avg_uncertainty:.1f}% average uncertainty. Improve data quality for better tracking.")

def show_trends_analysis(api_base):
    """Show trends and month-over-month analysis"""
    st.subheader("📈 Emission Trends & Deltas")
    
    try:
        with st.spinner("Loading trend data..."):
            response = requests.get(f"{api_base}/api/analytics/deltas")
            
            if response.status_code == 200:
                deltas = response.json()
                
                if deltas:
                    df = pd.DataFrame(deltas)
                    
                    # Time series chart
                    fig = go.Figure()
                    
                    # Add emissions line
                    fig.add_trace(go.Scatter(
                        x=df['period'],
                        y=df['total_kgco2e'],
                        mode='lines+markers',
                        name='Total Emissions',
                        line=dict(color='blue', width=3),
                        marker=dict(size=8)
                    ))
                    
                    fig.update_layout(
                        title="Monthly Emission Trends",
                        xaxis_title="Period",
                        yaxis_title="Emissions (kg CO₂e)",
                        height=400
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Delta analysis
                    st.subheader("📊 Month-over-Month Changes")
                    
                    # Filter out None values for delta chart
                    delta_df = df[df['pct_change'].notna()].copy()
                    
                    if not delta_df.empty:
                        # Delta chart
                        colors = ['green' if x < 0 else 'red' for x in delta_df['pct_change']]
                        
                        fig2 = go.Figure()
                        
                        fig2.add_trace(go.Bar(
                            x=delta_df['period'],
                            y=delta_df['pct_change'],
                            marker_color=colors,
                            name='% Change',
                            text=[f"{x:+.1f}%" for x in delta_df['pct_change']],
                            textposition='auto'
                        ))
                        
                        fig2.update_layout(
                            title="Month-over-Month Percentage Changes",
                            xaxis_title="Period",
                            yaxis_title="Change (%)",
                            height=400
                        )
                        
                        st.plotly_chart(fig2, use_container_width=True)
                        
                        # Trend insights
                        show_trend_insights(delta_df)
                    
                    # Data table
                    st.subheader("📋 Trend Data")
                    
                    display_df = df.copy()
                    display_df['total_kgco2e'] = display_df['total_kgco2e'].apply(lambda x: f"{x:,.0f}")
                    display_df['pct_change'] = display_df['pct_change'].apply(
                        lambda x: f"{x:+.1f}%" if pd.notna(x) else "N/A"
                    )
                    
                    display_df.columns = ['Period', 'Total Emissions', '% Change']
                    
                    st.dataframe(display_df, use_container_width=True, hide_index=True)
                
                else:
                    st.info("No trend data available.")
            else:
                st.error(f"Failed to fetch trend data: {response.status_code}")
    
    except Exception as e:
        st.error(f"Trends analysis error: {str(e)}")

def show_trend_insights(df):
    """Show insights about emission trends"""
    st.subheader("💡 Trend Insights")
    
    # Calculate trend statistics
    avg_change = df['pct_change'].mean()
    max_increase = df['pct_change'].max()
    max_decrease = df['pct_change'].min()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Average Monthly Change",
            f"{avg_change:+.1f}%",
            help="Average month-over-month percentage change"
        )
    
    with col2:
        st.metric(
            "Largest Increase",
            f"{max_increase:+.1f}%",
            help="Largest month-over-month increase"
        )
    
    with col3:
        st.metric(
            "Largest Decrease",
            f"{max_decrease:+.1f}%",
            help="Largest month-over-month decrease"
        )
    
    # Trend direction
    recent_changes = df.tail(3)['pct_change'].tolist()
    
    if all(x > 0 for x in recent_changes):
        st.error("📈 **Increasing Trend**: Emissions have been consistently increasing. Intervention needed.")
    elif all(x < 0 for x in recent_changes):
        st.success("📉 **Decreasing Trend**: Emissions are consistently decreasing. Good progress!")
    else:
        st.info("📊 **Mixed Trend**: Emissions show mixed patterns. Monitor for stability.")

def show_quality_analysis(api_base):
    """Show data quality analysis"""
    st.subheader("⚠️ Data Quality Analysis")
    
    try:
        with st.spinner("Loading quality data..."):
            response = requests.get(f"{api_base}/api/analytics/quality_gaps")
            
            if response.status_code == 200:
                quality_gaps = response.json()
                
                if quality_gaps:
                    df = pd.DataFrame(quality_gaps)
                    
                    # Quality metrics
                    show_quality_metrics(df)
                    
                    # Quality issues chart
                    show_quality_charts(df)
                    
                    # Detailed quality issues table
                    st.subheader("📋 Quality Issues Details")
                    
                    # Prepare display data
                    display_df = df.copy()
                    display_df['occurred_at'] = pd.to_datetime(display_df['occurred_at']).dt.strftime('%Y-%m-%d')
                    display_df['uncertainty_pct'] = display_df['uncertainty_pct'].apply(lambda x: f"{x:.1f}%")
                    display_df['result_kgco2e'] = display_df['result_kgco2e'].apply(lambda x: f"{x:,.0f}")
                    display_df['quality_flags'] = display_df['quality_flags'].apply(
                        lambda x: ', '.join(x) if x else 'High Uncertainty'
                    )
                    
                    display_df = display_df[['occurred_at', 'supplier_name', 'activity', 'uncertainty_pct', 'quality_flags', 'result_kgco2e']]
                    display_df.columns = ['Date', 'Supplier', 'Activity', 'Uncertainty', 'Issues', 'Emissions']
                    
                    st.dataframe(display_df, use_container_width=True, hide_index=True)
                    
                    # Quality improvement recommendations
                    show_quality_recommendations(df)
                
                else:
                    st.success("✅ No significant quality issues found!")
            else:
                st.error(f"Failed to fetch quality data: {response.status_code}")
    
    except Exception as e:
        st.error(f"Quality analysis error: {str(e)}")

def show_quality_metrics(df):
    """Show quality metrics overview"""
    total_issues = len(df)
    avg_uncertainty = df['uncertainty_pct'].mean()
    high_uncertainty_count = len(df[df['uncertainty_pct'] > 30])
    
    # Count different types of quality flags
    all_flags = []
    for flags in df['quality_flags']:
        if flags:
            all_flags.extend(flags)
    
    flag_counts = pd.Series(all_flags).value_counts() if all_flags else pd.Series()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Quality Issues",
            total_issues,
            help="Total events with quality issues"
        )
    
    with col2:
        st.metric(
            "Avg Uncertainty",
            f"{avg_uncertainty:.1f}%",
            help="Average uncertainty of problematic events"
        )
    
    with col3:
        st.metric(
            "High Uncertainty",
            high_uncertainty_count,
            help="Events with >30% uncertainty"
        )
    
    with col4:
        most_common_issue = flag_counts.index[0] if not flag_counts.empty else "None"
        st.metric(
            "Most Common Issue",
            most_common_issue.replace('_', ' ').title(),
            help="Most frequently occurring quality flag"
        )

def show_quality_charts(df):
    """Show quality analysis charts"""
    col1, col2 = st.columns(2)
    
    with col1:
        # Uncertainty distribution
        fig = px.histogram(
            df,
            x='uncertainty_pct',
            title="Uncertainty Distribution",
            nbins=20,
            labels={'uncertainty_pct': 'Uncertainty (%)', 'count': 'Number of Events'}
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Quality flags frequency
        all_flags = []
        for flags in df['quality_flags']:
            if flags:
                all_flags.extend(flags)
        
        if all_flags:
            flag_counts = pd.Series(all_flags).value_counts()
            
            fig = px.bar(
                x=flag_counts.index,
                y=flag_counts.values,
                title="Quality Issues Frequency",
                labels={'x': 'Issue Type', 'y': 'Count'}
            )
            
            fig.update_layout(xaxis_tickangle=45)
            st.plotly_chart(fig, use_container_width=True)

def show_quality_recommendations(df):
    """Show quality improvement recommendations"""
    st.subheader("💡 Quality Improvement Recommendations")
    
    # Analyze quality issues
    all_flags = []
    for flags in df['quality_flags']:
        if flags:
            all_flags.extend(flags)
    
    flag_counts = pd.Series(all_flags).value_counts() if all_flags else pd.Series()
    
    recommendations = []
    
    if 'incomplete' in flag_counts:
        recommendations.append("📝 **Improve Data Completeness**: Many events have incomplete information. Ensure all required fields are captured during data entry.")
    
    if 'missing_tonnage' in flag_counts:
        recommendations.append("⚖️ **Capture Tonnage Data**: Missing cargo weight information increases uncertainty. Implement tonnage tracking for shipping activities.")
    
    if 'missing_distance' in flag_counts:
        recommendations.append("📍 **Track Distance Information**: Missing distance data affects emission calculations. Use GPS or route planning tools to capture accurate distances.")
    
    if df['uncertainty_pct'].mean() > 25:
        recommendations.append("🎯 **Reduce Uncertainty**: High average uncertainty suggests need for better emission factors or more precise input data.")
    
    # Supplier-specific recommendations
    supplier_issues = df.groupby('supplier_name')['uncertainty_pct'].mean().sort_values(ascending=False)
    if not supplier_issues.empty:
        worst_supplier = supplier_issues.index[0]
        worst_uncertainty = supplier_issues.iloc[0]
        
        if worst_uncertainty > 30:
            recommendations.append(f"🏢 **Focus on {worst_supplier}**: This supplier has the highest average uncertainty ({worst_uncertainty:.1f}%). Prioritize data quality improvements here.")
    
    # Display recommendations
    if recommendations:
        for rec in recommendations:
            st.info(rec)
    else:
        st.success("✅ No specific quality recommendations - data quality looks good!")

def show_custom_analysis(api_base):
    """Show custom analysis interface"""
    st.subheader("🔍 Custom Analysis")
    st.markdown("Create custom visualizations and analysis of your emission data.")
    
    # Analysis options
    analysis_option = st.selectbox(
        "Choose Analysis Type:",
        [
            "Activity Comparison",
            "Supplier Deep Dive", 
            "Emission Factor Analysis",
            "Uncertainty Analysis",
            "Time Series Decomposition"
        ]
    )
    
    if analysis_option == "Activity Comparison":
        show_activity_comparison_analysis(api_base)
    elif analysis_option == "Supplier Deep Dive":
        show_supplier_deep_dive(api_base)
    elif analysis_option == "Emission Factor Analysis":
        show_emission_factor_analysis(api_base)
    elif analysis_option == "Uncertainty Analysis":
        show_uncertainty_analysis(api_base)
    elif analysis_option == "Time Series Decomposition":
        show_time_series_analysis(api_base)

def show_activity_comparison_analysis(api_base):
    """Show activity comparison analysis"""
    st.markdown("**Compare emissions across different activities**")
    
    try:
        # Get events data
        response = requests.get(f"{api_base}/api/events", params={"limit": 1000})
        
        if response.status_code == 200:
            events = response.json()
            
            if events:
                df = pd.DataFrame(events)
                
                # Activity statistics
                activity_stats = df.groupby('activity').agg({
                    'result_kgco2e': ['count', 'sum', 'mean', 'std'],
                    'uncertainty_pct': 'mean'
                }).round(2)
                
                activity_stats.columns = ['Event Count', 'Total Emissions', 'Mean Emissions', 'Std Dev', 'Avg Uncertainty']
                
                st.dataframe(activity_stats, use_container_width=True)
                
                # Box plot comparison
                fig = px.box(
                    df,
                    x='activity',
                    y='result_kgco2e',
                    title="Emission Distribution by Activity Type"
                )
                
                fig.update_layout(xaxis_tickangle=45)
                st.plotly_chart(fig, use_container_width=True)
        
        else:
            st.error("Failed to fetch data for activity comparison")
    
    except Exception as e:
        st.error(f"Activity comparison error: {str(e)}")

def show_supplier_deep_dive(api_base):
    """Show detailed supplier analysis"""
    st.markdown("**Deep dive analysis for specific supplier**")
    
    # Supplier selector (would be populated from API in real implementation)
    supplier_name = st.text_input(
        "Supplier Name",
        placeholder="Enter supplier name (e.g., OceanLift, GridCo)",
        help="Enter exact supplier name for analysis"
    )
    
    if supplier_name:
        st.info(f"Deep dive analysis for {supplier_name} would be shown here, including:")
        st.markdown("""
        - Emission trends over time
        - Activity breakdown
        - Quality metrics specific to supplier
        - Comparison with industry benchmarks
        - Improvement recommendations
        """)

def show_emission_factor_analysis(api_base):
    """Show emission factor analysis"""
    st.markdown("**Analysis of emission factors usage and impact**")
    
    st.info("Emission factor analysis would show:")
    st.markdown("""
    - Most frequently used emission factors
    - Factor source reliability comparison
    - Impact of different factors on calculations
    - Recommendations for factor improvements
    """)

def show_uncertainty_analysis(api_base):
    """Show uncertainty analysis"""
    st.markdown("**Detailed uncertainty analysis and contributors**")
    
    st.info("Uncertainty analysis would include:")
    st.markdown("""
    - Uncertainty distribution patterns
    - Main contributors to uncertainty
    - Correlation with data completeness
    - Uncertainty reduction strategies
    """)

def show_time_series_analysis(api_base):
    """Show time series decomposition analysis"""
    st.markdown("**Advanced time series analysis of emission patterns**")
    
    st.info("Time series analysis would provide:")
    st.markdown("""
    - Seasonal decomposition
    - Trend identification
    - Anomaly detection
    - Forecasting models
    """)
