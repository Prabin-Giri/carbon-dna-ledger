"""
Event details component showing DNA receipt and integrity chain
"""
import streamlit as st
import requests
import json
from datetime import datetime

def show_details_page(api_base):
    """Show detailed emission record view"""
    st.header("🧬 Emission Record Details")
    st.markdown("Detailed view of emission record with complete information and data quality assessment.")
    
    # Record selection
    record_id = get_record_selection(api_base)
    
    if record_id:
        show_record_details(api_base, record_id)
    else:
        st.info("Search for a record by external_id, supplier, date, or description.")

def get_record_selection(api_base):
    """User-friendly record search and selection without exposing UUID."""
    # If coming from another page, use internal selection
    preselected = st.session_state.get('selected_record_id')
    if preselected:
        return preselected

    # Check if we have a previously selected record in session state
    if 'details_record_selection' in st.session_state and st.session_state['details_record_selection'] is not None:
        # Get the selected record ID from the search results
        if 'details_search_results' in st.session_state and 'details_record_ids' in st.session_state:
            selected_idx = st.session_state['details_record_selection']
            if selected_idx < len(st.session_state['details_record_ids']):
                return st.session_state['details_record_ids'][selected_idx]

    st.subheader("🔎 Find a Record")

    col1, col2, col3 = st.columns([1.2, 1.2, 1])

    with col1:
        supplier = st.text_input(
            "Supplier",
            placeholder="e.g., City Utilities"
        )

    with col2:
        external_id = st.text_input(
            "External ID",
            placeholder="e.g., BILL-2025-0138"
        )

    with col3:
        description = st.text_input(
            "Description contains",
            placeholder="e.g., electricity, shipping"
        )

    d1, d2, d3, d4 = st.columns([1, 1, 1, 1])
    with d1:
        from_date = st.date_input("From date", value=None, key="details_from_date")
    with d2:
        to_date = st.date_input("To date", value=None, key="details_to_date")
    with d3:
        st.write("")
        st.write("")
        search = st.button("🔎 Search", type="primary")
    with d4:
        st.write("")
        st.write("")
        clear_search = st.button("🔄 Clear", help="Clear search and selection")

    results = []
    if clear_search:
        # Clear session state and rerun to reset the form
        if 'details_record_selection' in st.session_state:
            del st.session_state['details_record_selection']
        if 'details_search_results' in st.session_state:
            del st.session_state['details_search_results']
        if 'details_record_ids' in st.session_state:
            del st.session_state['details_record_ids']
        st.rerun()
    
    # Check if we have existing search results in session state
    if 'details_search_results' in st.session_state and not search:
        results = st.session_state['details_search_results']
    
    if search:
        params = {}
        if supplier.strip():
            params['supplier_name'] = supplier.strip()
        if from_date:
            params['from_date'] = from_date.isoformat()
        if to_date:
            params['to_date'] = to_date.isoformat()

        with st.spinner("Searching records..."):
            try:
                params['limit'] = 10000  # Set high limit to show all records
                r = requests.get(f"{api_base}/api/emission-records", params=params, timeout=30)
                if r.status_code == 200:
                    results = r.json() or []
                else:
                    st.error(f"Search failed: {r.status_code}")
            except Exception as e:
                st.error(f"Search error: {str(e)}")

        # Client-side filters
        if external_id.strip():
            results = [rec for rec in results if str(rec.get('external_id', '')).strip().lower() == external_id.strip().lower()]
        if description.strip():
            needle = description.strip().lower()
            results = [rec for rec in results if needle in str(rec.get('description', '')).lower()]

    if results:
        import pandas as pd
        st.subheader(f"📋 {len(results)} results")
        df = pd.DataFrame(results)
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')

        ids = list(df['id']) if 'id' in df.columns else [None] * len(df)
        display_cols = [
            c for c in [
                'date', 'supplier_name', 'activity_type', 'category', 'subcategory',
                'emissions_kgco2e', 'data_quality_score', 'external_id', 'description'
            ] if c in df.columns
        ]
        preview = df[display_cols].copy()

        # Store search results in session state to prevent regeneration
        st.session_state['details_search_results'] = results
        st.session_state['details_record_ids'] = ids

        # Use selectbox for reliable selection
        if len(preview) > 0:
            # Create display options for selectbox
            display_options = []
            for i, row in preview.iterrows():
                display_text = f"{row.get('date', 'N/A')} | {row.get('supplier_name', 'N/A')} | {row.get('activity_type', 'N/A')} | {row.get('emissions_kgco2e', 'N/A')} kg CO2e"
                display_options.append(display_text)
            
            # Get current selection from session state or default to 0
            current_selection = st.session_state.get('details_record_selection', 0)
            if current_selection >= len(display_options):
                current_selection = 0
            
            selected_idx = st.selectbox(
                "Select a record to view details:",
                range(len(display_options)),
                index=current_selection,
                format_func=lambda x: display_options[x],
                key="details_record_selection_new"
            )
            
            # Update session state when selection changes
            if selected_idx != current_selection:
                st.session_state['details_record_selection'] = selected_idx
                st.rerun()
            
            if selected_idx is not None:
                chosen_id = ids[selected_idx] if selected_idx < len(ids) else None
                if chosen_id:
                    st.success("✅ Record selected. Details are shown below.")
                    return chosen_id

    return None

def show_record_details(api_base, record_id):
    """Display complete emission record details"""
    try:
        with st.spinner("Loading record details..."):
            response = requests.get(f"{api_base}/api/emission-records/{record_id}")
            
            if response.status_code == 200:
                record = response.json()
                
                # Record header
                show_record_header(record)
                
                # Record details
                show_record_information(record)
                
                # Calculation breakdown
                show_calculation_breakdown(record)
                
                # Data quality assessment
                show_quality_assessment(record)
                
                # Raw data
                show_raw_data(record)
                
                # Hash / audit
                show_hash_audit(record)
                
                # Action buttons
                show_action_buttons(api_base, record_id)
                
            elif response.status_code == 404:
                st.error("❌ Record not found. Please check the ID and try again.")
            else:
                st.error(f"❌ Failed to load record: {response.status_code}")
    
    except Exception as e:
        st.error(f"Error loading record details: {str(e)}")

def show_record_header(record):
    """Show record summary header"""
    st.subheader(f"Record: {record.get('activity_type', 'N/A')} by {record.get('supplier_name', 'N/A')}")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        emissions = record.get('emissions_kgco2e', 0) or 0
        st.metric(
            "Emissions",
            f"{emissions:,.1f} kg CO₂e",
            help="Total calculated emissions for this activity"
        )
    
    with col2:
        quality_score = record.get('data_quality_score', 0) or 0
        st.metric(
            "Quality Score",
            f"{quality_score:.1f}",
            help="Data quality score (0-100)"
        )
    
    with col3:
        scope = record.get('scope', 'N/A')
        st.metric(
            "Scope",
            scope,
            help="GHG Protocol emission scope"
        )
    
    with col4:
        methodology = record.get('methodology', 'N/A')
        st.metric(
            "Methodology",
            methodology[:20] + "..." if len(str(methodology)) > 20 else methodology,
            help="Calculation methodology used"
        )

def show_record_information(record):
    """Show detailed record information"""
    st.markdown("---")
    st.subheader("📋 Record Information")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Basic Information**")
        # Display date information - show date range if available
        if record.get('date_start') and record.get('date_end') and record.get('date_start') != record.get('date_end'):
            st.write(f"**Date Range:** {record.get('date_start')} to {record.get('date_end')}")
        else:
            st.write(f"**Date:** {record.get('date', 'N/A')}")
        st.write(f"**Supplier:** {record.get('supplier_name', 'N/A')}")
        st.write(f"**Activity Type:** {record.get('activity_type', 'N/A')}")
        st.write(f"**Category:** {record.get('category', 'N/A')}")
        st.write(f"**Subcategory:** {record.get('subcategory', 'N/A')}")
        st.write(f"**Scope:** {record.get('scope', 'N/A')}")
    
    with col2:
        st.markdown("**Activity Details**")
        if record.get('activity_amount'):
            amount = record.get('activity_amount')
            unit = record.get('activity_unit', '')
            st.write(f"**Amount:** {amount:,.1f} {unit}")
        if record.get('fuel_type'):
            st.write(f"**Fuel Type:** {record.get('fuel_type')}")
        if record.get('vehicle_type'):
            st.write(f"**Vehicle Type:** {record.get('vehicle_type')}")
        if record.get('distance_km'):
            distance = record.get('distance_km')
            st.write(f"**Distance:** {distance:,.1f} km")
        if record.get('mass_tonnes'):
            mass = record.get('mass_tonnes')
            st.write(f"**Mass:** {mass:,.1f} tonnes")
        if record.get('energy_kwh'):
            energy = record.get('energy_kwh')
            st.write(f"**Energy:** {energy:,.1f} kWh")

def show_quality_assessment(record):
    """Show data quality assessment"""
    st.markdown("---")
    st.subheader("🔍 Data Quality Assessment")
    
    quality_score = record.get('data_quality_score', 0) or 0
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Quality score visualization
        if quality_score >= 80:
            st.success(f"🟢 **High Quality** - Score: {quality_score:.1f}")
        elif quality_score >= 60:
            st.warning(f"🟡 **Medium Quality** - Score: {quality_score:.1f}")
        else:
            st.error(f"🔴 **Low Quality** - Score: {quality_score:.1f}")
        
        # Verification status
        verification = record.get('verification_status', 'Not specified')
        st.write(f"**Verification Status:** {verification}")
    
    with col2:
        # Emission factor information
        st.markdown("**Emission Factor Details**")
        if record.get('ef_source'):
            st.write(f"**Source:** {record.get('ef_source')}")
        if record.get('ef_ref_code'):
            st.write(f"**Reference:** {record.get('ef_ref_code')}")
        if record.get('ef_version'):
            st.write(f"**Version:** {record.get('ef_version')}")
        if record.get('emission_factor_value'):
            st.write(f"**Factor:** {record.get('emission_factor_value')} {record.get('emission_factor_unit', '')}")

def show_raw_data(record):
    """Show raw data and metadata"""
    st.markdown("---")
    st.subheader("📄 Raw Data & Metadata")
    
    # Raw row data
    if record.get('raw_row'):
        with st.expander("🔍 Raw Row Data"):
            st.json(record['raw_row'])
    
    # Additional information
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Timestamps**")
        st.write(f"**Created:** {record.get('created_at', 'N/A')}")
        if record.get('date_start') and record.get('date_end'):
            st.write(f"**Date Range:** {record.get('date_start')} to {record.get('date_end')}")
        else:
            st.write(f"**Record Date:** {record.get('date', 'N/A')}")
    
    with col2:
        st.markdown("**Identifiers**")
        # Hide internal UUID from UI; show only external-facing identifiers
        if record.get('external_id'):
            st.write(f"**External ID:** {record.get('external_id')}")
        if record.get('project_code'):
            st.write(f"**Project Code:** {record.get('project_code')}")
    
    # Notes
    if record.get('notes'):
        st.markdown("**Notes**")
        st.write(record['notes'])

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
            if isinstance(value, (int, float)) and value is not None:
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
        result_kgco2e = event.get("emissions_kgco2e", 0) or 0
        st.markdown(
            f'<span class="dna-chip">🎯 {result_kgco2e:,.1f} kg CO₂e</span>',
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
    st.success(f"✅ Emissions: {event['emissions_kgco2e']} kg CO₂e")
    record_hash = event.get('record_hash', 'N/A')
    if record_hash and record_hash != 'N/A':
        st.success(f"✅ Hash: {record_hash[:16]}...")
    else:
        st.success(f"✅ Hash: Not available")
    
    # Show tampered version
    st.markdown("**Tampered Version:**")
    tampered_emissions = event['emissions_kgco2e'] * 0.5  # Reduce by 50%
    st.error(f"❌ Emissions: {tampered_emissions} kg CO₂e")
    if record_hash and record_hash != 'N/A':
        st.error(f"❌ Hash: {record_hash[:8]}TAMPERED{record_hash[-8:]}")
    else:
        st.error(f"❌ Hash: TAMPERED")
    
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

def show_action_buttons(api_base, record_id):
    """Show action buttons for the record"""
    st.markdown("---")
    st.subheader("⚡ Actions")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        if st.button("🔄 Run What-If", type="primary"):
            st.session_state.selected_record_id = record_id
            st.info("Scenario analysis would be shown here")
    
    with col2:
        if st.button("🔄 Reset View", help="Clear current record and start fresh"):
            # Clear session state to start fresh
            if 'details_record_selection' in st.session_state:
                del st.session_state['details_record_selection']
            st.rerun()
    
    with col3:
        if st.button("🔍 Find Similar"):
            show_similar_records(api_base, record_id)
    
    with col4:
        if st.button("📊 Record Analytics"):
            show_record_analytics(api_base, record_id)
    
    with col5:
        if st.button("🏠 Back to Search", help="Return to record search"):
            # Clear all session state related to record selection
            if 'details_record_selection' in st.session_state:
                del st.session_state['details_record_selection']
            if 'selected_record_id' in st.session_state:
                del st.session_state['selected_record_id']
            if 'details_search_results' in st.session_state:
                del st.session_state['details_search_results']
            if 'details_record_ids' in st.session_state:
                del st.session_state['details_record_ids']
            # Also clear Event Explorer session state
            if 'explorer_selected_record_id' in st.session_state:
                del st.session_state['explorer_selected_record_id']
            if 'explorer_selected_record_data' in st.session_state:
                del st.session_state['explorer_selected_record_data']
            st.rerun()

def show_similar_records(api_base, record_id):
    """Show records similar to current one"""
    st.subheader("🔍 Similar Records")
    
    try:
        # Get recent records for context
        response = requests.get(f"{api_base}/api/emission-records", params={"limit": 5})
        
        if response.status_code == 200:
            records = response.json()
            
            st.markdown("**Recently Created Records:**")
            for record in records[:3]:
                st.write(f"• {record.get('supplier_name', 'N/A')} - {record.get('activity_type', 'N/A')} ({record.get('emissions_kgco2e', 0):.0f} kg CO₂e)")
        
    except Exception as e:
        st.error(f"Error finding similar records: {str(e)}")

def show_record_analytics(api_base, record_id):
    """Show analytics context for this record"""
    import plotly.express as px
    
    st.subheader("📊 Record Analytics")
    
    try:
        # Get recent records for context
        response = requests.get(f"{api_base}/api/emission-records", params={"limit": 20})
        
        if response.status_code == 200:
            records = response.json()
            
            # Convert to DataFrame for analysis
            import pandas as pd
            df = pd.DataFrame(records)
            
            # Emission distribution
            if 'emissions_kgco2e' in df.columns:
                fig = px.histogram(
                    df,
                    x='emissions_kgco2e',
                    title="Emission Distribution (Recent Records)",
                    nbins=10
                )
                
                st.plotly_chart(fig, width='stretch')
            
            # Quality vs Emissions
            if 'emissions_kgco2e' in df.columns and 'data_quality_score' in df.columns:
                fig2 = px.scatter(
                    df,
                    x='emissions_kgco2e',
                    y='data_quality_score',
                    color='supplier_name',
                    title="Quality Score vs Emissions"
                )
                
                st.plotly_chart(fig2, width='stretch')
    
    except Exception as e:
        st.error(f"Error loading analytics: {str(e)}")

# --- Helpers to satisfy calls used in details flow ---
def show_calculation_breakdown(record):
    """Display calculation breakdown (placeholder)."""
    st.markdown("---")
    st.subheader("🧮 Calculation Breakdown")
    st.info("Calculation breakdown will appear here in a future update.")

def show_hash_audit(record):
    """Wrapper to show integrity chain without exposing internals."""
    show_integrity_chain(record)
