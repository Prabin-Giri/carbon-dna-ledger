"""
Upload component for CSV and PDF ingestion
"""
import streamlit as st
import requests
import json

def show_upload_page(api_base):
    """Show file upload interface"""
    st.header("📤 Upload Carbon Data")
    st.markdown("Upload CSV files or text-based PDF documents containing carbon emission activities.")
    
    # Instructions
    with st.expander("📋 Upload Instructions"):
        st.markdown("""
        **CSV Format Expected:**
        - `occurred_at`: Date in YYYY-MM-DD format
        - `supplier`: Supplier name
        - `activity`: Activity type (e.g., "tanker_voyage", "electricity")
        - `scope`: Emission scope (1, 2, or 3)
        - Optional fields: `distance_km`, `tonnage`, `fuel_type`, `region`, `kwh`
        
        **PDF Format:**
        - Text-based PDFs with structured emission data
        - Must contain recognizable patterns with dates, suppliers, and activities
        
        **Example CSV:**
        ```
        occurred_at,supplier,activity,scope,distance_km,tonnage,fuel_type,region
        2025-06-01,OceanLift,tanker_voyage,3,9600,40000,HFO,US-EU
        2025-06-15,GridCo,electricity,2,,,,,120000
        ```
        """)
    
    # File upload
    uploaded_file = st.file_uploader(
        "Choose a file",
        type=['csv', 'pdf'],
        help="Upload CSV or PDF files containing carbon emission data"
    )
    
    # Additional parameters
    col1, col2 = st.columns(2)
    
    with col1:
        doc_type = st.selectbox(
            "Document Type",
            ["csv", "pdf"],
            help="Select the type of document you're uploading"
        )
    
    with col2:
        supplier_name = st.text_input(
            "Default Supplier Name (optional)",
            help="Use this supplier name if not specified in the file"
        )
    
    # Upload button
    if st.button("🚀 Process Upload", type="primary", disabled=uploaded_file is None):
        if uploaded_file is not None:
            process_upload(api_base, uploaded_file, doc_type, supplier_name)

def process_upload(api_base, uploaded_file, doc_type, supplier_name):
    """Process file upload via API"""
    try:
        with st.spinner("Processing upload..."):
            # Prepare form data
            files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
            data = {"doc_type": doc_type}
            
            if supplier_name.strip():
                data["supplier_name"] = supplier_name.strip()
            
            # Send to API
            response = requests.post(
                f"{api_base}/api/ingest",
                files=files,
                data=data,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Success message
                st.success(f"✅ Successfully processed {uploaded_file.name}")
                
                # Results summary
                col1, col2 = st.columns(2)
                
                with col1:
                    st.metric(
                        "Events Created",
                        result['count_inserted'],
                        help="Number of carbon events created from the upload"
                    )
                
                with col2:
                    if result['sample_ids']:
                        st.metric(
                            "Sample IDs",
                            len(result['sample_ids']),
                            help="Sample event IDs for reference"
                        )
                
                # Show sample IDs
                if result['sample_ids']:
                    st.subheader("📝 Created Events")
                    st.markdown("**Sample Event IDs:**")
                    for event_id in result['sample_ids'][:5]:  # Show first 5
                        st.code(event_id, language=None)
                    
                    if len(result['sample_ids']) > 5:
                        st.caption(f"...and {len(result['sample_ids']) - 5} more events")
                
                # Success actions
                st.markdown("---")
                st.markdown("**Next Steps:**")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if st.button("🔍 View Events"):
                        st.switch_page("pages/explorer.py")
                
                with col2:
                    if st.button("📈 View Analytics"):
                        st.switch_page("pages/analytics.py")
                
                with col3:
                    if st.button("📤 Upload More"):
                        st.rerun()
            
            else:
                # Error handling
                try:
                    error_data = response.json()
                    error_detail = error_data.get('detail', 'Unknown error')
                except:
                    error_detail = response.text or f"HTTP {response.status_code}"
                
                st.error(f"❌ Upload failed: {error_detail}")
                
                # Show debug info
                with st.expander("🔍 Debug Information"):
                    st.write("**Request Details:**")
                    st.write(f"- File: {uploaded_file.name}")
                    st.write(f"- Type: {doc_type}")
                    st.write(f"- Size: {len(uploaded_file.getvalue())} bytes")
                    if supplier_name:
                        st.write(f"- Default Supplier: {supplier_name}")
                    
                    st.write("**Response:**")
                    st.code(response.text, language="json")
    
    except requests.exceptions.Timeout:
        st.error("❌ Upload timed out. Please try with a smaller file.")
    
    except requests.exceptions.ConnectionError:
        st.error("❌ Cannot connect to the API. Please ensure the backend is running.")
    
    except Exception as e:
        st.error(f"❌ Upload error: {str(e)}")
        
        # Show detailed error for debugging
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
        st.dataframe(df, use_container_width=True)
        
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
