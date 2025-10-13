"""
Upload component for CSV and PDF ingestion
"""
from dotenv import load_dotenv
load_dotenv()
import streamlit as st
import requests
import json
import math
import numpy as np
import os

def show_upload_page(api_base):
    """Show file upload interface"""
    st.header("📤 Upload Carbon Data")
    st.markdown("Upload CSV files, PDF documents, images, or paste text directly for AI-powered classification.")

    # Instructions
    with st.expander("📋 Upload Instructions"):
        st.markdown("""
        **CSV — Simple (Spend-based)**
        Required headers:
        ```
        date,supplier_name,category,amount,currency,scope,methodology
        ```
        Full header set:
        ```
        date,supplier_name,category,subcategory,description,amount,currency,country_code,scope,methodology,ef_source,ef_ref_code,ef_factor_per_currency,emissions_kgco2e,org_unit,project_code,facility_id,data_quality_score,verification_status,previous_hash,record_hash,external_id,notes
        ```
        Example:
        ```
        2025-01-15,Acme Office Supplies,Scope 3: Purchased Goods & Services,420.50,USD,3,GHG Protocol - Spend-based
        ```

        **CSV — Advanced (Activity-based)**
        Required (electricity): `date_start,date_end,activity_amount,activity_unit=kWh,scope=2,methodology` AND (`grid_region` OR emission factor fields).
        Required (freight): `date_start,activity_amount,activity_unit (e.g., tonne.km),scope=3,methodology` AND EF source.
        Full header set:
        ```
        record_id,date_start,date_end,org_unit,facility_id,country_code,scope,category,subcategory,activity_type,activity_amount,activity_unit,fuel_type,vehicle_type,distance_km,mass_tonnes,energy_kwh,grid_region,market_basis,renewable_percent,emission_factor_value,emission_factor_unit,ef_source,ef_ref_code,ef_version,gwp_set,co2_kg,ch4_kg,n2o_kg,co2e_kg,supplier_name,contract_id,instrument_type,methodology,data_quality_score,verification_status,attachment_url,external_id,previous_hash,record_hash,salt
        ```
        Example (electricity):
        ```
        REC-000001,2025-01-01,2025-01-31,HQ,FAC-001,US,2,Scope 2: Electricity,Electricity - Location-based,electricity,32000,kWh,,,,,32000,EPA eGRID SRVC,location-based,0,0.39,kgCO2e/kWh,EPA eGRID 2024,eGRID_SRVC_2024,2024.1,IPCC AR6 100-yr,,,,12482.1,City Utilities,,,GHG Protocol - Activity-based,4,unverified,,BILL-2025-0138,,,
        ```

        **PDF & Images** 📸📄
        - **PDF documents**: Text extraction and AI classification
        - **Images (PNG, JPG, JPEG)**: OCR text extraction + AI classification
        - All processed documents create draft rows for review before import
        - **NEW**: Upload PDFs, photos of invoices, receipts, or documents for automatic processing!

        **AI Text Classification**
        - Paste any invoice or financial document text
        - AI will automatically extract carbon emission data
        - Supports multiple text inputs for batch processing
        - Confidence scoring and human review flags included
        """)

    # File upload
    uploaded_file = st.file_uploader(
        "Choose a file (CSV, PDF, or Images)",
        type=['csv', 'pdf', 'png', 'jpg', 'jpeg'],
        help="Upload CSV, PDF, or image files (PNG, JPG, JPEG) containing carbon emission data. Images will be processed with OCR + AI classification."
    )

    # Additional parameters
    col1, col2 = st.columns(2)

    with col1:
        doc_type = st.selectbox(
            "Document Type",
            ["CSV — Simple (Spend-based)", "CSV — Advanced (Activity-based)", "PDF Document", "Image Document (PNG/JPG/JPEG)"],
            index=0,
            help="Select the type of document you're uploading"
        )

    with col2:
        supplier_name = st.text_input(
            "Default Supplier Name (optional)",
            help="Use this supplier name if not specified in the file"
        )

    # AI Model Selection
    st.subheader("🤖 AI Model Selection")
    try:
        response = requests.get(f"{api_base}/api/ai/models", timeout=10)
        if response.status_code == 200:
            ai_data = response.json()
            if ai_data.get("success"):
                available_models = ai_data.get("available_models", {})
                model_status = ai_data.get("model_status", {})
                
                # Create model selection options with updated labels
                model_options = []
                for model_type, info in available_models.items():
                    status = model_status.get(model_type, {})
                    if status.get("available", False):
                        # Update labels
                        if model_type == "ollama":
                            label = f"{info['name']} (Secure & Private)"
                        elif model_type == "openai":
                            label = f"{info['name']} (High Performance)"
                        else:
                            label = f"{info['name']} ({info['cost']})"
                        model_options.append(label)
                    else:
                        model_options.append(f"{info['name']} - {status.get('error', 'Not available')}")
                
                if model_options:
                    selected_model_idx = st.selectbox(
                        "Choose AI Model:",
                        range(len(model_options)),
                        format_func=lambda x: model_options[x],
                        help="Select the AI model for classification. Local models are secure and private, cloud models offer high performance."
                    )
                    
                    # Map selection back to model type
                    model_types = list(available_models.keys())
                    selected_model_type = model_types[selected_model_idx] if selected_model_idx < len(model_types) else "regex"
                else:
                    selected_model_type = "regex"
                    st.warning("No AI models available. Using pattern matching fallback.")
            else:
                selected_model_type = "regex"
                st.warning("Could not load AI models. Using pattern matching fallback.")
        else:
            selected_model_type = "regex"
            st.warning("Could not connect to AI service. Using pattern matching fallback.")
    except Exception as e:
        selected_model_type = "regex"
        st.warning(f"AI model selection error: {str(e)}. Using pattern matching fallback.")

    # Upload button
    if st.button("🚀 Process Upload", type="primary", disabled=uploaded_file is None):
        if uploaded_file is not None:
            process_upload(api_base, uploaded_file, doc_type, supplier_name, selected_model_type)

    # AI Text Classification Section
    st.markdown("---")
    st.subheader("🤖 AI Text Classification")
    st.markdown("Paste invoice or financial document text for automatic carbon emission data extraction.")
    
    # Smart Suggestions (History + Climate TRACE mapping)
    with st.expander("✨ Smart Suggestions (auto-fill from history and Climate TRACE)"):
        st.markdown("Provide minimal context to get suggested values. You can accept or modify them before submitting.")
        
        # Information about available data
        with st.expander("ℹ️ Available Climate TRACE Data (2024)", expanded=False):
            st.markdown("""
            **Countries with data:** USA, RUS, BOL, CAN, IRN, BRA, CHN, etc.
            
            **Available sectors for USA:**
            - `oil-and-gas-production` (includes Gulf Coast, Delaware, Midland, Williston)
            - `oil-and-gas-transport` (includes Gulf Coast, Appalachian, ArkLaTex)
            - `road-transportation` (Los Angeles, New York, Dallas, Houston, Chicago, Miami, Phoenix, Atlanta)
            
            **Louisiana-relevant regions:**
            - **Gulf Coast** (oil & gas production/transport) - 387M kg CO2e
            - **ArkLaTex** (Arkansas-Louisiana-Texas shale gas) - 244M kg CO2e  
            - **East Gulf Coast** (deepwater oil & gas) - Available
            
            **Individual Plants Available:**
            - **James H Miller Jr** (Power Plant) - 18.6M kg CO2e
            - **U.S. Steel Gary Works** (Steel Plant) - 14.1M kg CO2e  
            - **Georgia Pacific - Brewton, AL** (Paper Plant) - 25.8M kg CO2e
            - **Labadie** (Power Plant) - 14.2M kg CO2e
            
            **Available sectors for other countries:**
            - `forest-land-fires` (BOL, BRA)
            - `electricity-generation` (limited coverage)
            - `iron-and-steel` (limited coverage)
            
            **Note:** Climate TRACE uses `USA` (not `US`) as country code.
            """)
        # Search mode selection
        search_mode = st.radio(
            "Search Mode:",
            ["🌍 Sector/Country Search", "🏭 Specific Facility Search", "🌊 Louisiana Focus", "🏭 Individual Plant Search"],
            horizontal=True
        )
        
        if search_mode == "🌍 Sector/Country Search":
            col_ss1, col_ss2, col_ss3 = st.columns(3)
            with col_ss1:
                ss_supplier = st.text_input("Supplier Name", value=supplier_name or "")
                ss_activity = st.text_input("Activity Type (e.g., electricity, freight, fuel)")
                ss_sector = st.text_input("Sector (CT)")
            with col_ss2:
                ss_subsector = st.text_input("Subsector (CT)")
                ss_year = st.number_input("Year (CT)", min_value=2000, max_value=2100, value=2024, step=1)
                ss_country = st.text_input("Country Code (e.g., USA, RUS, BOL)", value="USA")
            with col_ss3:
                ss_owner = st.text_input("Owner (optional)")
                ss_lat = st.number_input("Latitude (optional)", value=0.0)
                ss_lon = st.number_input("Longitude (optional)", value=0.0)
        elif search_mode == "🏭 Specific Facility Search":
            # Specific facility search
            st.markdown("**🔍 Search for Specific Louisiana Facilities**")
            col_fac1, col_fac2 = st.columns(2)
            
            with col_fac1:
                st.markdown("**Facility Information**")
                facility_name = st.text_input("Facility Name (partial match)", placeholder="e.g., Baton Rouge, Lake Charles")
                company_name = st.selectbox(
                    "Company/Owner",
                    ["", "ExxonMobil", "Shell", "Chevron", "Phillips 66", "Entergy", "Cleco", "SWEPCO", "Dow", "BASF", "Other"]
                )
                if company_name == "Other":
                    company_name = st.text_input("Enter company name")
                
                facility_type = st.selectbox(
                    "Facility Type",
                    ["", "Oil Refinery", "Power Plant", "Chemical Plant", "Manufacturing", "Other"]
                )
            
            with col_fac2:
                st.markdown("**Location (Louisiana)**")
                louisiana_cities = {
                    "Baton Rouge": (30.4515, -91.1871),
                    "New Orleans": (29.9511, -90.0715),
                    "Lake Charles": (30.2266, -93.2174),
                    "Shreveport": (32.5252, -93.7502),
                    "Lafayette": (30.2241, -92.0198),
                    "Custom": (0.0, 0.0)
                }
                
                selected_city = st.selectbox("City/Region", list(louisiana_cities.keys()))
                if selected_city == "Custom":
                    ss_lat = st.number_input("Latitude", value=30.0, format="%.4f")
                    ss_lon = st.number_input("Longitude", value=-91.0, format="%.4f")
                else:
                    ss_lat, ss_lon = louisiana_cities[selected_city]
                    st.info(f"📍 {selected_city}: {ss_lat}, {ss_lon}")
                
                ss_year = st.number_input("Year (CT)", min_value=2000, max_value=2100, value=2024, step=1)
            
            # Map facility type to Climate TRACE parameters
            if facility_type == "Oil Refinery":
                ss_activity = "oil_production"
                ss_sector = "oil-and-gas-production"
                ss_country = "USA"
            elif facility_type == "Power Plant":
                ss_activity = "electricity"
                ss_sector = "electricity-generation"
                ss_country = "USA"
            elif facility_type == "Chemical Plant":
                ss_activity = "manufacturing"
                ss_sector = "iron-and-steel"
                ss_country = "USA"
            else:
                ss_activity = st.text_input("Activity Type", value="")
                ss_sector = st.text_input("Sector (CT)", value="")
                ss_country = "USA"
            
            ss_supplier = facility_name or ""
            ss_owner = company_name or ""
            ss_subsector = ""
        
        elif search_mode == "🌊 Louisiana Focus":
            st.markdown("**🌊 Louisiana-Specific Climate TRACE Data**")
            st.info("Climate TRACE has data for Louisiana's key industrial regions and sectors.")
            
            col_la1, col_la2 = st.columns(2)
            
            with col_la1:
                st.markdown("**Louisiana Regions**")
                la_region = st.selectbox(
                    "Select Louisiana Region",
                    [
                        "Gulf Coast (Oil & Gas Production)",
                        "Gulf Coast (Oil & Gas Transport)", 
                        "ArkLaTex (Shale Gas Transport)",
                        "East Gulf Coast (Deepwater)"
                    ]
                )
                
                # Map region to Climate TRACE parameters
                if "Gulf Coast" in la_region and "Production" in la_region:
                    ss_activity = "oil_production"
                    ss_sector = "oil-and-gas-production"
                    ss_subsector = "Gulf Coast"
                elif "Gulf Coast" in la_region and "Transport" in la_region:
                    ss_activity = "gas_transport"
                    ss_sector = "oil-and-gas-transport"
                    ss_subsector = "Gulf Coast"
                elif "ArkLaTex" in la_region:
                    ss_activity = "gas_transport"
                    ss_sector = "oil-and-gas-transport"
                    ss_subsector = "ArkLaTex"
                elif "East Gulf Coast" in la_region:
                    ss_activity = "oil_production"
                    ss_sector = "oil-and-gas-production"
                    ss_subsector = "Deepwater"
            
            with col_la2:
                st.markdown("**Search Parameters**")
                ss_year = st.number_input("Year (CT)", min_value=2000, max_value=2100, value=2024, step=1)
                ss_country = "USA"
                ss_owner = st.text_input("Company/Owner (optional)", placeholder="e.g., ExxonMobil, Shell, Chevron")
                
                # Louisiana coordinates (approximate center)
                ss_lat = 30.9843
                ss_lon = -91.9623
                st.info(f"📍 Louisiana Center: {ss_lat}, {ss_lon}")
            
            ss_supplier = f"Louisiana - {la_region}"
        
        elif search_mode == "🏭 Individual Plant Search":
            st.markdown("**🏭 Search for Specific Individual Plants**")
            st.info("Climate TRACE has data for specific individual facilities across the USA.")
            
            col_plant1, col_plant2 = st.columns(2)
            
            with col_plant1:
                st.markdown("**Plant Information**")
                plant_name = st.text_input(
                    "Plant/Facility Name", 
                    placeholder="e.g., James H Miller Jr, U.S. Steel Gary Works, Georgia Pacific"
                )
                
                # Show examples of available plants
                with st.expander("📋 Available Individual Plants", expanded=False):
                    st.markdown("""
                    **Power Plants:**
                    - James H Miller Jr (18.6M kg CO2e)
                    - Labadie (14.2M kg CO2e)
                    
                    **Steel Plants:**
                    - U.S. Steel Gary Works (14.1M kg CO2e)
                    
                    **Paper Plants:**
                    - Georgia Pacific - Brewton, AL (25.8M kg CO2e)
                    
                    **Oil & Gas Regions:**
                    - Gulf Coast, Delaware, Midland, Williston, etc.
                    """)
            
            with col_plant2:
                st.markdown("**Search Parameters**")
                ss_year = st.number_input("Year (CT)", min_value=2000, max_value=2100, value=2024, step=1)
                ss_country = "USA"
                
                # Auto-detect sector based on plant name
                if plant_name:
                    if any(word in plant_name.lower() for word in ['miller', 'labadie', 'power', 'electric']):
                        ss_activity = "electricity"
                        ss_sector = "electricity-generation"
                        st.info("🔌 Detected: Power Plant")
                    elif any(word in plant_name.lower() for word in ['steel', 'works']):
                        ss_activity = "steel"
                        ss_sector = "iron-and-steel"
                        st.info("🏭 Detected: Steel Plant")
                    elif any(word in plant_name.lower() for word in ['georgia', 'pacific', 'paper']):
                        ss_activity = "manufacturing"
                        ss_sector = "pulp-and-paper"
                        st.info("📄 Detected: Paper Plant")
                    else:
                        ss_activity = st.text_input("Activity Type", value="")
                        ss_sector = st.text_input("Sector (CT)", value="")
                else:
                    ss_activity = st.text_input("Activity Type", value="")
                    ss_sector = st.text_input("Sector (CT)", value="")
            
            ss_supplier = plant_name or ""
            ss_owner = ""
            ss_subsector = ""
            ss_lat = 0.0
            ss_lon = 0.0
        else:
            # Default values for any other search mode
            ss_supplier = ""
            ss_activity = ""
            ss_sector = ""
            ss_subsector = ""
            ss_year = 2024
            ss_country = "USA"
            ss_owner = ""
            ss_lat = 0.0
            ss_lon = 0.0

        if st.button("🔎 Get Suggestions", key="get_suggestions_btn"):
            try:
                payload = {
                    "supplier_name": ss_supplier,
                    "activity_type": ss_activity,
                    # CT aligned fields
                    "sector": ss_sector,
                    "subsector": ss_subsector,
                    "year": int(ss_year) if ss_year else None,
                    "owner": ss_owner,
                    "latitude": float(ss_lat) if ss_lat is not None else None,
                    "longitude": float(ss_lon) if ss_lon is not None else None,
                    "country_code": ss_country,
                    # kept for our own defaults (not used for CT matching)
                    "grid_region": None,
                    "scope": None,
                    "fuel_type": None,
                }
                resp = requests.post(f"{api_base}/api/intake/suggest", json=payload, timeout=30)
                resp.raise_for_status()
                data = resp.json()
                suggestions = data.get("suggestions", {}) if data.get("success") else {}

                st.success("Suggestions loaded. Review below.")
                
                # Display Climate TRACE data prominently
                ct_data = suggestions.get("climate_trace", {})
                if ct_data.get("emission_data"):
                    st.subheader("🌍 Climate TRACE Emission Data")
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Emissions", f"{ct_data.get('total_emissions_kgco2e', 0):,.0f} kg CO2e")
                    with col2:
                        st.metric("Asset Count", ct_data.get('asset_count', 0))
                    with col3:
                        st.metric("Data Source", ct_data.get('data_source', 'Unknown'))
                    
                    # Show data quality indicators
                    col4, col5, col6 = st.columns(3)
                    with col4:
                        st.info(f"📅 **Freshness**: {ct_data.get('data_freshness', 'Unknown')}")
                    with col5:
                        st.info(f"🎯 **Confidence**: {ct_data.get('confidence_level', 'Unknown')}")
                    with col6:
                        if ct_data.get('import_ready'):
                            st.success("✅ **Ready to Import**")
                        else:
                            st.warning("⚠️ **Not Import Ready**")
                    
                    # Show detailed emission data
                    if ct_data.get('emission_data'):
                        st.markdown("**Detailed Emission Data:**")
                        for emission in ct_data['emission_data']:
                            st.write(f"• **Sector**: {emission.get('sector', 'N/A')}")
                            st.write(f"• **Emissions**: {emission.get('emissions_kgco2e', 0):,.0f} kg CO2e")
                            st.write(f"• **Assets**: {emission.get('asset_count', 0)}")
                            st.write(f"• **Confidence**: {emission.get('confidence', 'Unknown')}")
                            st.write(f"• **Year/Month**: {emission.get('year', 'N/A')}/{emission.get('month', 'N/A')}")
                            st.write("---")
                    
                    # Comparison and Import Section
                    st.subheader("🔄 Compare & Import")
                    st.markdown("Compare Climate TRACE data with your own emissions or import as reference data.")
                    
                    col_comp1, col_comp2 = st.columns(2)
                    
                    with col_comp1:
                        st.markdown("**Your Emissions Data**")
                        user_emissions = st.number_input(
                            "Your Emissions (kg CO2e)", 
                            min_value=0.0, 
                            value=0.0,
                            help="Enter your company's emissions for comparison"
                        )
                        user_notes = st.text_area(
                            "Notes (optional)",
                            placeholder="Add any notes about your data or the comparison..."
                        )
                    
                    with col_comp2:
                        st.markdown("**Import Options**")
                        import_action = st.selectbox(
                            "Import Action",
                            options=[
                                "compare_only",
                                "import_as_reference", 
                                "import_as_primary"
                            ],
                            format_func=lambda x: {
                                "compare_only": "📊 Compare Only (no import)",
                                "import_as_reference": "📋 Import as Reference Data",
                                "import_as_primary": "✅ Import as Primary Data"
                            }[x]
                        )
                        
                        if st.button("🚀 Compare & Import", type="primary"):
                            if ct_data.get('import_ready'):
                                try:
                                    import_payload = {
                                        "ct_data": ct_data,
                                        "user_emissions_kgco2e": user_emissions if user_emissions > 0 else None,
                                        "user_notes": user_notes if user_notes.strip() else None,
                                        "import_action": import_action
                                    }
                                    
                                    with st.spinner("Processing comparison and import..."):
                                        import_response = requests.post(
                                            f"{api_base}/api/intake/import-climate-trace",
                                            json=import_payload,
                                            timeout=30
                                        )
                                        import_response.raise_for_status()
                                        import_result = import_response.json()
                                        
                                        if import_result.get("success"):
                                            st.success("✅ Comparison and import completed!")
                                            
                                            # Show comparison results
                                            comparison = import_result.get("comparison_result", {})
                                            st.subheader("📊 Comparison Results")
                                            
                                            col_res1, col_res2, col_res3 = st.columns(3)
                                            with col_res1:
                                                st.metric(
                                                    "Climate TRACE", 
                                                    f"{comparison.get('climate_trace_emissions', 0):,.0f} kg CO2e"
                                                )
                                            with col_res2:
                                                st.metric(
                                                    "Your Data", 
                                                    f"{comparison.get('user_emissions', 0):,.0f} kg CO2e"
                                                )
                                            with col_res3:
                                                diff = comparison.get('difference_kgco2e', 0)
                                                diff_pct = comparison.get('percentage_difference', 0)
                                                st.metric(
                                                    "Difference", 
                                                    f"{diff:,.0f} kg CO2e",
                                                    f"{diff_pct:+.1f}%"
                                                )
                                            
                                            # Show recommendations
                                            recommendations = import_result.get("recommendations", [])
                                            if recommendations:
                                                st.subheader("💡 Recommendations")
                                                for rec in recommendations:
                                                    st.write(rec)
                                            
                                            # Show import status
                                            if import_result.get("record_id"):
                                                st.success(f"📝 Record created: {import_result.get('record_id')}")
                                                st.info("🔍 This record has been flagged for human review")
                                                
                                        else:
                                            st.error(f"❌ Import failed: {import_result.get('error', 'Unknown error')}")
                                            
                                except requests.exceptions.RequestException as e:
                                    st.error(f"❌ Failed to process import: {e}")
                            else:
                                st.warning("⚠️ Climate TRACE data is not ready for import")
                
                # Display other suggestions
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    st.markdown("**From History**")
                    history_data = suggestions.get("history", {})
                    if history_data:
                        for key, value in history_data.items():
                            st.write(f"• **{key}**: {value}")
                    else:
                        st.write("No historical data found")
                        
                with col_b:
                    st.markdown("**Climate TRACE Mapping**")
                    if ct_data:
                        st.write(f"• **Sector**: {ct_data.get('ct_sector', 'N/A')}")
                        st.write(f"• **Subsector**: {ct_data.get('ct_subsector', 'N/A')}")
                        st.write(f"• **Country**: {ct_data.get('ct_country_code', 'N/A')}")
                        st.write(f"• **Year**: {ct_data.get('ct_year', 'N/A')}")
                        if ct_data.get('ct_owner'):
                            st.write(f"• **Owner**: {ct_data.get('ct_owner')}")
                    else:
                        st.write("No Climate TRACE mapping found")
                        
                with col_c:
                    st.markdown("**Defaults/Hints**")
                    defaults_data = suggestions.get("defaults", {})
                    if defaults_data:
                        for key, value in defaults_data.items():
                            st.write(f"• **{key}**: {value}")
                    else:
                        st.write("No defaults available")

                # Source indicators
                src = suggestions.get("source", {})
                badges = []
                if src.get("history"):
                    badges.append("History")
                if src.get("climate_trace"):
                    badges.append("Climate TRACE")
                st.info("Sources: " + (", ".join(badges) if badges else "None"))
            except requests.exceptions.RequestException as e:
                st.error(f"Failed to load suggestions: {e}")

    # Text input options
    input_method = st.radio(
        "Choose input method:",
        ["Single Text", "Batch Text (Multiple)"],
        horizontal=True
    )
    
    if input_method == "Single Text":
        # Single text input
        text_input = st.text_area(
            "Paste your invoice/financial document text here:",
            height=200,
            placeholder="Invoice #12345\nFrom: Acme Office Supplies\nDate: 2025-01-15\nTotal: $1,250.00\nDescription: Office supplies and equipment..."
        )
        
        col1, col2 = st.columns([3, 1])
        with col1:
            text_supplier = st.text_input(
                "Supplier Name (optional)",
                help="Leave blank to let AI extract from text"
            )
        with col2:
            st.write("")  # Spacing
            st.write("")  # Spacing
        
        if st.button("🧠 Classify & Insert", type="primary", disabled=not text_input.strip()):
            if text_input.strip():
                process_text_classification(api_base, text_input, text_supplier, selected_model_type)
            else:
                st.warning("Please enter some text to classify.")
    
    else:
        # Batch text input
        st.markdown("**Enter multiple texts (one per line):**")
        batch_texts = st.text_area(
            "Paste multiple invoice/financial document texts:",
            height=300,
            placeholder="Invoice #12345\nFrom: Acme Office Supplies\nDate: 2025-01-15\nTotal: $1,250.00\n\nInvoice #12346\nFrom: City Utilities\nDate: 2025-01-16\nTotal: $850.00\n\n..."
        )
        
        batch_suppliers = st.text_input(
            "Supplier Names (optional, comma-separated)",
            help="Leave blank to let AI extract from each text. If provided, must match number of texts."
        )
        
        if st.button("🧠 Classify Batch with AI", type="primary", disabled=not batch_texts.strip()):
            if batch_texts.strip():
                texts = [t.strip() for t in batch_texts.split('\n\n') if t.strip()]
                suppliers = [s.strip() for s in batch_suppliers.split(',')] if batch_suppliers.strip() else None
                process_batch_classification(api_base, texts, suppliers, selected_model_type)
            else:
                st.warning("Please enter some text to classify.")

def process_upload(api_base, uploaded_file, doc_type, supplier_name, model_preference=None):
    """Process file upload via API"""
    try:
        with st.spinner("Processing upload..."):
            # Handle image files
            if uploaded_file.type and uploaded_file.type.startswith('image/') or doc_type == "Image Document (PNG/JPG/JPEG)":
                return process_image_upload(api_base, uploaded_file, supplier_name, model_preference)
            
            # Handle PDF files
            if uploaded_file.type == 'application/pdf' or doc_type == "PDF Document":
                return process_pdf_upload(api_base, uploaded_file, supplier_name, model_preference)

            # Map document type
            if doc_type.startswith("CSV — Simple"):
                document_type = "simple"
                required_headers = [
                    'date','supplier_name','category','amount','currency','scope','methodology'
                ]
            else:
                document_type = "advanced"
                required_headers = [
                    'record_id','date_start','date_end','org_unit','facility_id','country_code','scope',
                    'category','subcategory','activity_type','activity_amount','activity_unit','methodology'
                ]

            # Read CSV
            import pandas as pd
            import io
            csv_bytes = uploaded_file.getvalue()
            df = pd.read_csv(io.BytesIO(csv_bytes))
            # Replace NaN/NaT/Inf with None so JSON is valid (null)
            df = df.replace([np.inf, -np.inf], None)
            df = df.where(pd.notnull(df), None)

            headers = list(df.columns)

            # Validation: required headers
            missing = [h for h in required_headers if h not in headers]
            if missing:
                st.error("Missing required headers: " + ", ".join(missing))
                return

            # Additional conditional checks for advanced
            if document_type == "advanced":
                # Electricity-style checks: if activity_type suggests electricity
                if 'activity_type' in headers and any(
                    df['activity_type'].astype(str).str.contains('electric', case=False, na=False)
                ):
                    cond_missing = []
                    for h in ['date_start','date_end','activity_amount','activity_unit','scope','methodology']:
                        if h not in headers:
                            cond_missing.append(h)
                    if cond_missing:
                        st.error("Missing required electricity fields: " + ", ".join(cond_missing))
                        return

            # Convert rows
            rows = df.to_dict(orient='records')

            # Final sanitize pass to remove any lingering NaN/Inf from numpy/pandas types
            def _sanitize(value):
                if value is None:
                    return None
                if isinstance(value, float):
                    if math.isnan(value) or math.isinf(value):
                        return None
                    return value
                if isinstance(value, np.floating):
                    fv = float(value)
                    return None if (math.isnan(fv) or math.isinf(fv)) else fv
                if isinstance(value, dict):
                    return {k: _sanitize(v) for k, v in value.items()}
                if isinstance(value, list):
                    return [_sanitize(v) for v in value]
                return value

            rows = [_sanitize(r) for r in rows]

            # Build payload
            payload = {
                'documentType': document_type,
                'headers': headers,
                'rows': rows
            }

            # Send JSON to backend - force correct API base
            response = requests.post(
                f"{api_base}/api/ingest-records",
                json=payload,
                timeout=120
            )

            if response.status_code == 200:
                result = response.json()
                st.success(f"✅ Imported {result.get('count_inserted', 0)} records from {uploaded_file.name}")
            else:
                try:
                    error_detail = response.json().get('detail', response.text)
                except:
                    error_detail = response.text
                st.error(f"❌ Upload failed: {error_detail}")
    except requests.exceptions.Timeout:
        st.error("❌ Upload timed out. Please try with a smaller file.")
    except requests.exceptions.ConnectionError:
        st.error("❌ Cannot connect to the API. Please ensure the backend is running.")
    except Exception as e:
        st.error(f"❌ Upload error: {str(e)}")
        with st.expander("🔍 Error Details"):
            st.exception(e)

def process_text_classification(api_base, text, supplier_name, model_preference=None):
    """Process single text classification via AI"""
    try:
        with st.spinner("🤖 AI is analyzing the text..."):
            # Prepare payload
            payload = {
                "text": text,
                "supplier_name": supplier_name if supplier_name.strip() else None,
                "model_preference": model_preference
            }
            
            # Call AI classification API
            response = requests.post(
                f"{api_base}/api/classify-text",
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get("success"):
                    st.success("✅ Text classified successfully!")
                    
                    # Display results
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader("📊 Classification Results")
                        data = result.get("classified_data", {})
                        
                        st.write(f"**Supplier:** {data.get('supplier_name', 'N/A')}")
                        st.write(f"**Activity Type:** {data.get('activity_type', 'N/A')}")
                        st.write(f"**Category:** {data.get('category', 'N/A')}")
                        st.write(f"**Amount:** {data.get('amount', 'N/A')} {data.get('currency', '')}")
                        st.write(f"**Date:** {data.get('date', 'N/A')}")
                        st.write(f"**Scope:** {data.get('scope', 'N/A')}")
                        
                        if data.get('description'):
                            st.write(f"**Description:** {data.get('description')}")
                    
                    with col2:
                        st.subheader("🎯 AI Confidence")
                        confidence = result.get("confidence_score", 0)
                        needs_review = result.get("needs_human_review", False)
                        model_used = result.get("ai_model_used", "Unknown")
                        
                        # Confidence gauge
                        if confidence >= 0.8:
                            st.success(f"High Confidence: {confidence:.1%}")
                        elif confidence >= 0.6:
                            st.warning(f"Medium Confidence: {confidence:.1%}")
                        else:
                            st.error(f"Low Confidence: {confidence:.1%}")
                        
                        if needs_review:
                            st.warning("⚠️ Needs Human Review")
                        else:
                            st.success("✅ Auto-approved")
                        
                        st.write(f"**Model:** {model_used}")
                        st.write(f"**Record ID:** {result.get('record_id', 'N/A')}")
                    
                    # Show raw data if available
                    if data.get('reasoning'):
                        with st.expander("🧠 AI Reasoning"):
                            st.write(data['reasoning'])
                
                else:
                    st.error(f"❌ Classification failed: {result.get('error', 'Unknown error')}")
                    if result.get('needs_human_review'):
                        st.warning("This text may need manual review.")
            
            else:
                try:
                    error_detail = response.json().get('error', response.text)
                except:
                    error_detail = response.text
                st.error(f"❌ Classification failed: {error_detail}")
    except requests.exceptions.Timeout:
        st.error("❌ Classification timed out. Please try with shorter text.")
    except requests.exceptions.ConnectionError:
        st.error("❌ Cannot connect to the API. Please ensure the backend is running.")
    except Exception as e:
        st.error(f"❌ Classification error: {str(e)}")
        with st.expander("🔍 Error Details"):
            st.exception(e)

def process_batch_classification(api_base, texts, supplier_names, model_preference=None):
    """Process batch text classification via AI"""
    try:
        with st.spinner(f"🤖 AI is analyzing {len(texts)} texts..."):
            # Prepare payload
            payload = {
                "texts": texts,
                "supplier_names": supplier_names,
                "model_preference": model_preference
            }
            
            # Call AI batch classification API
            response = requests.post(
                f"{api_base}/api/classify-batch",
                json=payload,
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get("success"):
                    total_processed = result.get("total_processed", 0)
                    created_records = result.get("created_records", 0)
                    errors = result.get("errors", 0)
                    
                    st.success(f"✅ Batch processing complete!")
                    st.write(f"**Processed:** {total_processed} texts")
                    st.write(f"**Created:** {created_records} records")
                    st.write(f"**Errors:** {errors} texts")
                    
                    # Show created records
                    if result.get("records"):
                        st.subheader("📊 Created Records")
                        records = result["records"]
                        
                        for record in records:
                            col1, col2, col3 = st.columns(3)
                            
                            with col1:
                                st.write(f"**Text {record['index'] + 1}:**")
                                st.write(f"Supplier: {record['supplier_name']}")
                                st.write(f"Activity: {record['activity_type']}")
                            
                            with col2:
                                confidence = record['confidence_score']
                                if confidence >= 0.8:
                                    st.success(f"Confidence: {confidence:.1%}")
                                elif confidence >= 0.6:
                                    st.warning(f"Confidence: {confidence:.1%}")
                                else:
                                    st.error(f"Confidence: {confidence:.1%}")
                                
                                if record['needs_human_review']:
                                    st.warning("Needs Review")
                                else:
                                    st.success("Auto-approved")
                            
                            with col3:
                                st.write(f"Record ID: {record['record_id']}")
                    
                    # Show errors if any
                    if result.get("error_details"):
                        st.subheader("❌ Errors")
                        for error in result["error_details"]:
                            st.error(f"Text {error['index'] + 1}: {error['error']}")
                            with st.expander(f"Text {error['index'] + 1} Preview"):
                                st.text(error['text_preview'])
                
                else:
                    st.error(f"❌ Batch classification failed: {result.get('error', 'Unknown error')}")
            
            else:
                try:
                    error_detail = response.json().get('error', response.text)
                except:
                    error_detail = response.text
                st.error(f"❌ Batch classification failed: {error_detail}")
    
    except requests.exceptions.Timeout:
        st.error("❌ Batch classification timed out. Please try with fewer texts.")
    except requests.exceptions.ConnectionError:
        st.error("❌ Cannot connect to the API. Please ensure the backend is running.")
    except Exception as e:
        st.error(f"❌ Batch classification error: {str(e)}")
        with st.expander("🔍 Error Details"):
            st.exception(e)

def show_upload_history():
    """Show recent upload history (if available)"""
    st.subheader("📚 Recent Uploads")
    
    # This would typically query the API for recent ingestion logs
    # For now, show placeholder
    st.info("Upload history tracking not implemented. Check Event Explorer for recently created events.")

def validate_csv_preview(uploaded_file):
    """Show preview of CSV content for validation"""
    try:
        import pandas as pd
        
        # Read first few rows
        df = pd.read_csv(uploaded_file, nrows=5)
        
        st.subheader("📋 File Preview")
        st.dataframe(df, width='stretch')
        
        # Column analysis
        st.subheader("📊 Column Analysis")
        
        required_cols = ['occurred_at', 'supplier', 'activity', 'scope']
        optional_cols = ['distance_km', 'tonnage', 'fuel_type', 'region', 'kwh']
        
        found_required = [col for col in required_cols if col in df.columns]
        found_optional = [col for col in optional_cols if col in df.columns]
        missing_required = [col for col in required_cols if col not in df.columns]
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.write("**✅ Found Required:**")
            for col in found_required:
                st.write(f"- {col}")
        
        with col2:
            st.write("**➕ Found Optional:**")
            for col in found_optional:
                st.write(f"- {col}")
        
        with col3:
            st.write("**❌ Missing Required:**")
            for col in missing_required:
                st.write(f"- {col}")
        
        # Validation summary
        if missing_required:
            st.warning(f"⚠️ Missing required columns: {', '.join(missing_required)}")
            return False
        else:
            st.success("✅ All required columns found!")
            return True
            
    except Exception as e:
        st.error(f"Cannot preview file: {str(e)}")
        return False

def process_image_upload(api_base, uploaded_file, supplier_name, model_preference):
    """Process image upload using OCR and AI classification"""
    try:
        # Prepare form data
        files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
        data = {}
        
        if supplier_name:
            data["supplier_name"] = supplier_name
        if model_preference:
            data["model_preference"] = model_preference
        
        # Make API request
        response = requests.post(
            f"{api_base}/api/classify-image",
            files=files,
            data=data,
            timeout=60  # Longer timeout for image processing
        )
        
        if response.status_code == 200:
            result = response.json()
            
            if result.get("success"):
                st.success("✅ Image processed successfully!")
                
                # Show extracted text
                if result.get("extracted_text"):
                    with st.expander("📄 Extracted Text from Image"):
                        st.text(result["extracted_text"])
                
                # Show classification results
                st.subheader("🎯 Classification Results")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Confidence Score", f"{result.get('confidence_score', 0):.1%}")
                with col2:
                    st.metric("AI Model Used", result.get('ai_model_used', 'Unknown'))
                with col3:
                    needs_review = result.get('needs_human_review', False)
                    st.metric("Needs Review", "⚠️ Yes" if needs_review else "✅ No")
                
                # Show extracted data
                if result.get("data"):
                    data = result["data"]
                    st.subheader("📊 Extracted Emission Data")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Supplier:** {data.get('supplier_name', 'Unknown')}")
                        st.write(f"**Activity Type:** {data.get('activity_type', 'Unknown')}")
                        st.write(f"**Scope:** {data.get('scope', 'Unknown')}")
                        st.write(f"**Category:** {data.get('category', 'Unknown')}")
                    
                    with col2:
                        st.write(f"**Amount:** {data.get('amount', 'N/A')} {data.get('currency', '')}")
                        st.write(f"**Date:** {data.get('date', 'N/A')}")
                        st.write(f"**Description:** {data.get('description', 'N/A')}")
                        if data.get('emissions_kgco2e'):
                            st.write(f"**Emissions:** {data.get('emissions_kgco2e')} kg CO2e")
                
                # Show record ID if created
                if result.get("record_id"):
                    st.success(f"📝 Emission record created with ID: {result['record_id']}")
                
                # Warning if needs review
                if needs_review:
                    st.warning("⚠️ This record has been flagged for human review due to low confidence or missing data.")
                
            else:
                st.error(f"❌ Image processing failed: {result.get('error', 'Unknown error')}")
                
                # Show extracted text even if classification failed
                if result.get("extracted_text"):
                    with st.expander("📄 Extracted Text (Classification Failed)"):
                        st.text(result["extracted_text"])
        else:
            st.error(f"❌ API request failed with status {response.status_code}")
            try:
                error_data = response.json()
                st.error(f"Error: {error_data.get('error', 'Unknown error')}")
            except:
                st.error(f"Response: {response.text}")
                
    except Exception as e:
        st.error(f"❌ Error processing image: {str(e)}")

def process_pdf_upload(api_base, uploaded_file, supplier_name, model_preference):
    """Process PDF upload using text extraction and AI classification"""
    try:
        # First extract text from PDF
        with st.spinner("📄 Extracting text from PDF..."):
            import pdfplumber
            
            # Read PDF content
            pdf_content = uploaded_file.getvalue()
            
            # Extract text from PDF
            extracted_text = ""
            with pdfplumber.open(io.BytesIO(pdf_content)) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        extracted_text += page_text + "\n"
            
            if not extracted_text.strip():
                st.error("❌ No text could be extracted from the PDF. Please ensure the PDF contains readable text.")
                return
        
        # Show extracted text
        with st.expander("📄 Extracted Text from PDF"):
            st.text(extracted_text[:2000] + "..." if len(extracted_text) > 2000 else extracted_text)
        
        # Now classify the extracted text using AI
        with st.spinner("🤖 Classifying extracted text with AI..."):
            # Prepare payload for text classification
            payload = {
                "text": extracted_text,
                "supplier_name": supplier_name if supplier_name and supplier_name.strip() else None,
                "model_preference": model_preference
            }
            
            # Call AI classification API
            response = requests.post(
                f"{api_base}/api/classify-text",
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get("success"):
                    st.success("✅ PDF processed successfully!")
                    
                    # Show classification results
                    st.subheader("🎯 Classification Results")
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Confidence Score", f"{result.get('confidence_score', 0):.1%}")
                    with col2:
                        st.metric("AI Model Used", result.get('ai_model_used', 'Unknown'))
                    with col3:
                        needs_review = result.get('needs_human_review', False)
                        st.metric("Needs Review", "⚠️ Yes" if needs_review else "✅ No")
                    
                    # Show extracted data
                    if result.get("classified_data"):
                        data = result["classified_data"]
                        st.subheader("📊 Extracted Emission Data")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write(f"**Supplier:** {data.get('supplier_name', 'Unknown')}")
                            st.write(f"**Activity Type:** {data.get('activity_type', 'Unknown')}")
                            st.write(f"**Scope:** {data.get('scope', 'Unknown')}")
                            st.write(f"**Category:** {data.get('category', 'Unknown')}")
                        
                        with col2:
                            st.write(f"**Amount:** {data.get('amount', 'N/A')} {data.get('currency', '')}")
                            st.write(f"**Date:** {data.get('date', 'N/A')}")
                            st.write(f"**Description:** {data.get('description', 'N/A')}")
                            if data.get('emissions_kgco2e'):
                                st.write(f"**Emissions:** {data.get('emissions_kgco2e')} kg CO2e")
                    
                    # Show record ID if created
                    if result.get("record_id"):
                        st.success(f"📝 Emission record created with ID: {result['record_id']}")
                    
                    # Warning if needs review
                    if needs_review:
                        st.warning("⚠️ This record has been flagged for human review due to low confidence or missing data.")
                
                else:
                    st.error(f"❌ PDF classification failed: {result.get('error', 'Unknown error')}")
            else:
                st.error(f"❌ API request failed with status {response.status_code}")
                try:
                    error_data = response.json()
                    st.error(f"Error: {error_data.get('error', 'Unknown error')}")
                except:
                    st.error(f"Response: {response.text}")
                    
    except Exception as e:
        st.error(f"❌ Error processing PDF: {str(e)}")
        with st.expander("🔍 Error Details"):
            st.exception(e)
