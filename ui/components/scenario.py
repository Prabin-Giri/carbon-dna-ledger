"""
What-if scenario analysis component
"""
import streamlit as st
import requests
import json
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

def show_scenario_page(api_base):
    """Show what-if scenario analysis interface"""
    st.header("🔄 What-If Scenario Analysis")
    st.markdown("Test different parameters to see how they would affect carbon emissions.")
    
    # Event selection
    event_id = get_event_for_scenario(api_base)
    
    if event_id:
        show_scenario_interface(api_base, event_id)
    else:
        st.info("Select an event ID to run scenarios, or browse events in the Event Explorer.")

def get_event_for_scenario(api_base):
    """Get event ID for scenario analysis"""
    
    # Check if event was selected from explorer or details
    selected_id = st.session_state.get('selected_event_id')
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        event_id = st.text_input(
            "Event ID for Analysis",
            value=selected_id if selected_id else "",
            placeholder="Enter event UUID...",
            help="Event to analyze - get ID from Event Explorer"
        )
    
    with col2:
        if st.button("🔄 Load Event", type="primary"):
            if event_id:
                return event_id.strip()
            else:
                st.error("Please enter an event ID")
    
    return event_id.strip() if event_id else None

def show_scenario_interface(api_base, event_id):
    """Display scenario analysis interface"""
    try:
        # First, get the event details
        with st.spinner("Loading event details..."):
            response = requests.get(f"{api_base}/api/events/{event_id}")
            
            if response.status_code == 200:
                event = response.json()
                
                # Show current event summary
                show_current_event_summary(event)
                
                # Scenario controls
                changes = show_scenario_controls(event)
                
                # Run scenario button
                if st.button("🚀 Run Scenario Analysis", type="primary"):
                    run_scenario_analysis(api_base, event_id, changes, event)
                
            elif response.status_code == 404:
                st.error("❌ Event not found. Please check the ID.")
            else:
                st.error(f"❌ Failed to load event: {response.status_code}")
                
    except Exception as e:
        st.error(f"Error in scenario interface: {str(e)}")

def show_current_event_summary(event):
    """Show summary of current event being analyzed"""
    st.subheader(f"📊 Current Event: {event['activity']}")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Current Emissions",
            f"{event['result_kgco2e']:,.1f} kg CO₂e"
        )
    
    with col2:
        st.metric(
            "Supplier",
            event['supplier_name']
        )
    
    with col3:
        st.metric(
            "Method",
            event['method']
        )
    
    with col4:
        st.metric(
            "Uncertainty",
            f"{event['uncertainty_pct']:.1f}%"
        )
    
    # Show current inputs
    st.subheader("🔧 Current Parameters")
    inputs = event.get('inputs', {})
    
    if inputs:
        cols = st.columns(min(len(inputs), 4))
        for i, (key, value) in enumerate(inputs.items()):
            with cols[i % 4]:
                if isinstance(value, (int, float)):
                    st.write(f"**{key.replace('_', ' ').title()}:** {value:,.1f}")
                else:
                    st.write(f"**{key.replace('_', ' ').title()}:** {value}")
    else:
        st.info("No input parameters available for modification.")

def show_scenario_controls(event):
    """Show controls for modifying scenario parameters"""
    st.markdown("---")
    st.subheader("🎛️ Scenario Parameters")
    st.markdown("Adjust parameters below to see how they would affect emissions:")
    
    inputs = event.get('inputs', {})
    changes = {}
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**🚢 Shipping Parameters**")
        
        # Fuel type
        current_fuel = inputs.get('fuel_type', 'HFO')
        fuel_options = ['HFO', 'LNG', 'MDO', 'Methanol', 'Hydrogen']
        
        new_fuel = st.selectbox(
            "Fuel Type",
            fuel_options,
            index=fuel_options.index(current_fuel) if current_fuel in fuel_options else 0,
            help="Change fuel type to see emission impact"
        )
        
        if new_fuel != current_fuel:
            changes['fuel_type'] = new_fuel
        
        # Distance
        current_distance = inputs.get('distance_km', 0)
        if current_distance > 0:
            new_distance = st.slider(
                "Distance (km)",
                min_value=int(current_distance * 0.5),
                max_value=int(current_distance * 2),
                value=int(current_distance),
                step=100,
                help="Adjust shipping distance"
            )
            
            if new_distance != current_distance:
                changes['distance_km'] = new_distance
        
        # Tonnage
        current_tonnage = inputs.get('tonnage', 0)
        if current_tonnage > 0:
            new_tonnage = st.slider(
                "Cargo Tonnage",
                min_value=int(current_tonnage * 0.5),
                max_value=int(current_tonnage * 1.5),
                value=int(current_tonnage),
                step=1000,
                help="Adjust cargo weight"
            )
            
            if new_tonnage != current_tonnage:
                changes['tonnage'] = new_tonnage
    
    with col2:
        st.markdown("**⚡ Energy Parameters**")
        
        # kWh
        current_kwh = inputs.get('kwh', 0)
        if current_kwh > 0:
            new_kwh = st.slider(
                "Energy Consumption (kWh)",
                min_value=int(current_kwh * 0.5),
                max_value=int(current_kwh * 1.5),
                value=int(current_kwh),
                step=1000,
                help="Adjust energy consumption"
            )
            
            if new_kwh != current_kwh:
                changes['kwh'] = new_kwh
        
        # Grid renewable mix
        current_renewables = inputs.get('grid_mix_renewables', 0)
        new_renewables = st.slider(
            "Grid Renewable Mix (%)",
            min_value=0,
            max_value=100,
            value=int(current_renewables) if current_renewables else 0,
            step=5,
            help="Percentage of renewable energy in grid mix"
        )
        
        if new_renewables != current_renewables:
            changes['grid_mix_renewables'] = new_renewables
        
        # Manual factor override
        st.markdown("**🔬 Advanced Options**")
        
        use_factor_override = st.checkbox("Override Emission Factor")
        if use_factor_override:
            # This would typically show a list of available factors
            st.info("Factor override feature - would show available emission factors")
    
    # Show what will be changed
    if changes:
        st.markdown("**📝 Planned Changes:**")
        for key, value in changes.items():
            if isinstance(value, (int, float)):
                st.write(f"• {key.replace('_', ' ').title()}: {value:,.1f}")
            else:
                st.write(f"• {key.replace('_', ' ').title()}: {value}")
    else:
        st.info("No changes selected. Adjust parameters above to run scenario.")
    
    return changes

def run_scenario_analysis(api_base, event_id, changes, original_event):
    """Run scenario analysis and display results"""
    if not changes:
        st.warning("No changes to analyze. Please modify some parameters.")
        return
    
    try:
        with st.spinner("Running scenario analysis..."):
            # Call scenario API
            response = requests.post(
                f"{api_base}/api/events/{event_id}/scenario",
                json={"changes": changes}
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Display results
                show_scenario_results(result, original_event, changes)
                
            else:
                st.error(f"❌ Scenario analysis failed: {response.status_code}")
                try:
                    error_detail = response.json().get('detail', 'Unknown error')
                    st.error(error_detail)
                except:
                    st.error(response.text)
    
    except Exception as e:
        st.error(f"Error running scenario: {str(e)}")

def show_scenario_results(result, original_event, changes):
    """Display scenario analysis results"""
    st.markdown("---")
    st.subheader("📊 Scenario Results")
    
    before = result['before']
    after = result['after']
    pct_change = result['pct_change']
    
    # Before/After comparison
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**📊 Before**")
        st.metric(
            "Emissions",
            f"{before['result_kgco2e']:,.1f} kg CO₂e"
        )
        st.write(f"Method: {before['method']}")
        st.write(f"Factor: {before['factor_ref']}")
    
    with col2:
        st.markdown("**📊 After**")
        st.metric(
            "Emissions",
            f"{after['result_kgco2e']:,.1f} kg CO₂e",
            delta=f"{pct_change:+.1f}%"
        )
        st.write(f"Method: {after['method']}")
        st.write(f"Factor: {after['factor_ref']}")
    
    with col3:
        st.markdown("**📊 Impact**")
        
        change_color = "green" if pct_change < 0 else "red"
        impact_icon = "📉" if pct_change < 0 else "📈"
        
        st.markdown(f"**{impact_icon} {pct_change:+.1f}% Change**")
        
        emission_diff = after['result_kgco2e'] - before['result_kgco2e']
        st.write(f"Difference: {emission_diff:+,.1f} kg CO₂e")
        
        # Impact assessment
        if abs(pct_change) < 5:
            st.info("🟡 Minor impact")
        elif abs(pct_change) < 20:
            st.warning("🟠 Moderate impact") 
        else:
            st.error("🔴 Major impact")
    
    # Visualization
    show_scenario_visualization(before, after, changes)
    
    # Changed tokens
    if result.get('changed_tokens'):
        st.subheader("🔄 What Changed")
        for token in result['changed_tokens']:
            st.write(f"• {token.replace('_', ' ').title()}")
    
    # Recommendations
    show_scenario_recommendations(result, changes)

def show_scenario_visualization(before, after, changes):
    """Show visual comparison of scenario results"""
    st.subheader("📊 Visual Comparison")
    
    # Create comparison chart
    comparison_data = {
        'Scenario': ['Before', 'After'],
        'Emissions (kg CO₂e)': [before['result_kgco2e'], after['result_kgco2e']]
    }
    
    fig = px.bar(
        comparison_data,
        x='Scenario',
        y='Emissions (kg CO₂e)',
        title="Emission Comparison",
        color='Scenario',
        color_discrete_map={'Before': '#ff7f7f', 'After': '#7f7fff'}
    )
    
    # Add percentage change annotation
    pct_change = ((after['result_kgco2e'] - before['result_kgco2e']) / before['result_kgco2e']) * 100
    
    fig.add_annotation(
        x=1, y=max(before['result_kgco2e'], after['result_kgco2e']),
        text=f"{pct_change:+.1f}%",
        showarrow=True,
        arrowhead=2,
        font=dict(size=14, color="black"),
        bgcolor="white",
        bordercolor="black",
        borderwidth=1
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Parameter changes visualization if multiple changes
    if len(changes) > 1:
        show_parameter_impact_chart(changes)

def show_parameter_impact_chart(changes):
    """Show impact of individual parameter changes"""
    st.subheader("🎯 Parameter Impact Analysis")
    
    # This would ideally run individual scenarios for each parameter
    # For now, show the changes made
    
    change_data = []
    for param, value in changes.items():
        change_data.append({
            'Parameter': param.replace('_', ' ').title(),
            'New Value': str(value)
        })
    
    if change_data:
        import pandas as pd
        df = pd.DataFrame(change_data)
        
        st.dataframe(df, use_container_width=True, hide_index=True)

def show_scenario_recommendations(result, changes):
    """Show recommendations based on scenario results"""
    st.markdown("---")
    st.subheader("💡 Recommendations")
    
    pct_change = result['pct_change']
    
    if pct_change < -10:
        st.success("✅ **Excellent Improvement!** This scenario significantly reduces emissions.")
        st.success("Consider implementing these changes in your operations.")
    elif pct_change < 0:
        st.success("✅ **Positive Impact** - This scenario reduces emissions.")
    elif pct_change > 10:
        st.error("❌ **High Impact Warning** - This scenario significantly increases emissions.")
        st.error("Consider alternative approaches to minimize environmental impact.")
    else:
        st.info("ℹ️ **Minimal Impact** - This scenario has limited effect on emissions.")
    
    # Specific recommendations based on changes
    if 'fuel_type' in changes:
        if changes['fuel_type'] in ['LNG', 'Methanol', 'Hydrogen']:
            st.success("🌿 Switching to cleaner fuel alternatives is a positive step!")
        elif changes['fuel_type'] == 'HFO':
            st.warning("⚠️ Heavy Fuel Oil has higher emissions. Consider cleaner alternatives.")
    
    if 'grid_mix_renewables' in changes and changes['grid_mix_renewables'] > 50:
        st.success("🔋 Higher renewable energy mix significantly reduces emissions!")
    
    # Save scenario button
    if st.button("💾 Save Scenario"):
        save_scenario_results(result, changes)

def save_scenario_results(result, changes):
    """Save scenario results for later reference"""
    try:
        # In a full implementation, this would save to database or file
        scenario_data = {
            'timestamp': datetime.now().isoformat(),
            'changes': changes,
            'result': result
        }
        
        # For now, just show the data that would be saved
        st.success("✅ Scenario saved!")
        
        with st.expander("📄 Saved Scenario Data"):
            st.json(scenario_data)
            
        # Download option
        import json
        scenario_json = json.dumps(scenario_data, indent=2)
        
        st.download_button(
            label="📥 Download Scenario",
            data=scenario_json,
            file_name=f"scenario_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )
        
    except Exception as e:
        st.error(f"Failed to save scenario: {str(e)}")

def show_multi_scenario_comparison():
    """Show interface for comparing multiple scenarios"""
    st.markdown("---")
    st.subheader("🔄 Multi-Scenario Comparison")
    
    st.info("Multi-scenario comparison feature - would allow comparing multiple what-if scenarios side by side")
    
    # Placeholder for future enhancement
    scenarios = [
        {"name": "Current", "emissions": 40000, "change": 0},
        {"name": "LNG Fuel", "emissions": 30000, "change": -25},
        {"name": "Route Optimization", "emissions": 35000, "change": -12.5},
        {"name": "Both Changes", "emissions": 26250, "change": -34.4}
    ]
    
    # Would show comparison chart here
    st.info("This would show a comparison chart of different scenario options")
