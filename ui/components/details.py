"""
Event details component showing DNA receipt and integrity chain
"""
import streamlit as st
import requests
import json
from datetime import datetime

def show_details_page(api_base):
    """Show detailed event view with DNA receipt"""
    st.header("🧬 Carbon Event DNA Details")
    st.markdown("Detailed view of carbon event with complete audit trail and integrity verification.")
    
    # Event selection
    event_id = get_event_selection(api_base)
    
    if event_id:
        show_event_details(api_base, event_id)
    else:
        st.info("Select an event ID to view details, or browse events in the Event Explorer.")

def get_event_selection(api_base):
    """Get event ID from user input or session state"""
    
    # Check if event was selected from explorer
    selected_id = st.session_state.get('selected_event_id')
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        event_id = st.text_input(
            "Event ID",
            value=selected_id if selected_id else "",
            placeholder="Enter event UUID...",
            help="Paste event ID or select from Event Explorer"
        )
    
    with col2:
        if st.button("🔍 Load Details", type="primary"):
            if event_id:
                return event_id.strip()
            else:
                st.error("Please enter an event ID")
    
    return event_id.strip() if event_id else None

def show_event_details(api_base, event_id):
    """Display complete event details with DNA receipt"""
    try:
        with st.spinner("Loading event details..."):
            response = requests.get(f"{api_base}/api/events/{event_id}")
            
            if response.status_code == 200:
                event = response.json()
                
                # Event header
                show_event_header(event)
                
                # DNA Receipt
                show_dna_receipt(event)
                
                # Provenance panel
                show_provenance_panel(event)
                
                # Integrity chain
                show_integrity_chain(event)
                
                # Action buttons
                show_action_buttons(api_base, event_id)
                
            elif response.status_code == 404:
                st.error("❌ Event not found. Please check the ID and try again.")
            else:
                st.error(f"❌ Failed to load event: {response.status_code}")
    
    except Exception as e:
        st.error(f"Error loading event details: {str(e)}")

def show_event_header(event):
    """Show event summary header"""
    st.subheader(f"Event: {event['activity']} by {event['supplier_name']}")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Emissions",
            f"{event['result_kgco2e']:,.1f} kg CO₂e",
            help="Total calculated emissions for this activity"
        )
    
    with col2:
        st.metric(
            "Uncertainty",
            f"{event['uncertainty_pct']:.1f}%",
            help="Uncertainty percentage in the calculation"
        )
    
    with col3:
        st.metric(
            "Scope",
            event['scope'],
            help="GHG Protocol emission scope"
        )
    
    with col4:
        quality_status = "🟢 Good" if not event['quality_flags'] else "🟡 Issues"
        st.metric(
            "Data Quality",
            quality_status,
            help="Data quality assessment"
        )

def show_dna_receipt(event):
    """Show DNA receipt with all calculation components"""
    st.markdown("---")
    st.subheader("🧬 Carbon DNA Receipt")
    st.markdown("Complete audit trail showing inputs, factors, method, and result.")
    
    # DNA chips layout
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Activity & Inputs**")
        
        # Activity chip
        st.markdown(
            f'<span class="dna-chip">📋 {event["activity"]}</span>',
            unsafe_allow_html=True
        )
        
        # Input chips
        inputs = event.get('inputs', {})
        for key, value in inputs.items():
            if isinstance(value, (int, float)):
                chip_text = f"{key}: {value:,.1f}"
            else:
                chip_text = f"{key}: {value}"
            
            st.markdown(
                f'<span class="dna-chip">🔢 {chip_text}</span>',
                unsafe_allow_html=True
            )
    
    with col2:
        st.markdown("**Calculation & Result**")
        
        # Factor chip
        st.markdown(
            f'<span class="dna-chip">⚖️ {event["factor_ref"]}</span>',
            unsafe_allow_html=True
        )
        
        # Method chip
        st.markdown(
            f'<span class="dna-chip">🔬 {event["method"]}</span>',
            unsafe_allow_html=True
        )
        
        # Result chip
        st.markdown(
            f'<span class="dna-chip">🎯 {event["result_kgco2e"]:,.1f} kg CO₂e</span>',
            unsafe_allow_html=True
        )
        
        # Factor details
        if event.get('factor_value') and event.get('factor_unit'):
            st.markdown(
                f'<span class="dna-chip">📊 {event["factor_value"]} {event["factor_unit"]}</span>',
                unsafe_allow_html=True
            )
    
    # Quality flags
    if event['quality_flags']:
        st.markdown("**⚠️ Quality Flags**")
        for flag in event['quality_flags']:
            st.warning(f"• {flag.replace('_', ' ').title()}")

def show_provenance_panel(event):
    """Show source document provenance"""
    st.markdown("---")
    st.subheader("📄 Provenance Panel")
    
    source_docs = event.get('source_doc', [])
    
    if source_docs:
        for doc in source_docs:
            with st.expander(f"📄 {doc.get('doc_id', 'Unknown Document')}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**Document Information:**")
                    st.write(f"• File: {doc.get('doc_id', 'N/A')}")
                    st.write(f"• Page: {doc.get('page', 'N/A')}")
                    st.write(f"• Field: {doc.get('field', 'N/A')}")
                
                with col2:
                    st.write("**Extracted Data:**")
                    raw_text = doc.get('raw_text', 'No text available')
                    st.code(raw_text[:200] + "..." if len(raw_text) > 200 else raw_text)
    else:
        st.info("No source document information available.")

def show_integrity_chain(event):
    """Show hash chain integrity with tamper simulation"""
    st.markdown("---")
    st.subheader("🔗 Integrity Chain")
    st.markdown("Cryptographic hash chain ensuring data immutability.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Hash Chain:**")
        
        # Previous hash
        prev_hash = event.get('prev_hash', 'Genesis')
        if prev_hash:
            st.markdown(f"**Previous Hash:**")
            st.markdown(f'<div class="hash-display">{prev_hash}</div>', unsafe_allow_html=True)
        else:
            st.markdown("**Previous Hash:** `Genesis Block`")
        
        st.markdown("⬇️")
        
        # Current hash
        row_hash = event.get('row_hash', '')
        st.markdown(f"**Event Hash:**")
        st.markdown(f'<div class="hash-display">{row_hash}</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown("**Tamper Detection Simulation:**")
        
        # Tamper simulation controls
        if st.button("⚠️ Simulate Tamper", help="Demonstrate integrity verification"):
            simulate_tamper(event)

def simulate_tamper(event):
    """Simulate tampering to demonstrate integrity verification"""
    st.markdown("**🚨 Tamper Simulation Active**")
    
    # Show original
    st.markdown("**Original Event:**")
    st.success(f"✅ Emissions: {event['result_kgco2e']} kg CO₂e")
    st.success(f"✅ Hash: {event['row_hash'][:16]}...")
    
    # Show tampered version
    st.markdown("**Tampered Version:**")
    tampered_emissions = event['result_kgco2e'] * 0.5  # Reduce by 50%
    st.error(f"❌ Emissions: {tampered_emissions} kg CO₂e")
    st.error(f"❌ Hash: {event['row_hash'][:8]}TAMPERED{event['row_hash'][-8:]}")
    
    # Verification result
    st.markdown("**Verification Result:**")
    st.error("🔒 **INTEGRITY VIOLATION DETECTED**")
    st.error("Hash mismatch indicates the data has been modified!")
    
    # Explanation
    with st.expander("🔍 How This Works"):
        st.markdown("""
        **Hash Chain Integrity:**
        1. Each event's hash is calculated from its content + previous event's hash
        2. Any change to the data changes the hash completely
        3. This creates an immutable chain where tampering is immediately detectable
        4. In a production system, this would trigger alerts and investigation
        
        **What Changed:**
        • Original: 40,000 kg CO₂e → Tampered: 20,000 kg CO₂e
        • Hash verification immediately detects this unauthorized modification
        """)

def show_action_buttons(api_base, event_id):
    """Show action buttons for the event"""
    st.markdown("---")
    st.subheader("⚡ Actions")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("🔄 Run What-If", type="primary"):
            st.session_state.selected_event_id = event_id
            st.switch_page("pages/scenario.py")
    
    with col2:
        if st.button("📋 Copy Event ID"):
            st.code(event_id)
            st.success("Event ID displayed above for copying")
    
    with col3:
        if st.button("🔍 Find Similar"):
            show_similar_events(api_base, event_id)
    
    with col4:
        if st.button("📊 Event Analytics"):
            show_event_analytics(api_base, event_id)

def show_similar_events(api_base, event_id):
    """Show events similar to current one"""
    st.subheader("🔍 Similar Events")
    
    try:
        # This would typically use the fingerprint to find similar events
        # For now, show a placeholder
        response = requests.get(f"{api_base}/api/events", params={"limit": 5})
        
        if response.status_code == 200:
            events = response.json()
            
            st.markdown("**Recently Created Events:**")
            for event in events[:3]:
                st.write(f"• {event['supplier_name']} - {event['activity']} ({event['result_kgco2e']:.0f} kg CO₂e)")
        
    except Exception as e:
        st.error(f"Error finding similar events: {str(e)}")

def show_event_analytics(api_base, event_id):
    """Show analytics context for this event"""
    import plotly.express as px
    
    st.subheader("📊 Event Analytics")
    
    try:
        # Get recent events for context
        response = requests.get(f"{api_base}/api/events", params={"limit": 20})
        
        if response.status_code == 200:
            events = response.json()
            
            # Convert to DataFrame for analysis
            import pandas as pd
            df = pd.DataFrame(events)
            
            # Emission distribution
            fig = px.histogram(
                df,
                x='result_kgco2e',
                title="Emission Distribution (Recent Events)",
                nbins=10
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Uncertainty vs Emissions
            fig2 = px.scatter(
                df,
                x='result_kgco2e',
                y='uncertainty_pct',
                color='supplier_name',
                title="Uncertainty vs Emissions"
            )
            
            st.plotly_chart(fig2, use_container_width=True)
    
    except Exception as e:
        st.error(f"Error loading analytics: {str(e)}")
