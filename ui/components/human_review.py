"""
Human Review Component for Carbon DNA Ledger
Displays records that need human review based on confidence threshold
"""
import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import json

def show_human_review_page():
    """Display the human review page"""
    st.title("🔍 Human Review Queue")
    st.markdown("Review AI-classified records that need manual verification")
    
    # Configuration
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Review Settings")
        confidence_threshold = st.slider(
            "Confidence Threshold", 
            min_value=0.0, 
            max_value=1.0, 
            value=0.7, 
            step=0.1,
            help="Records with confidence below this threshold will be flagged for review"
        )
    
    with col2:
        st.metric("Current Threshold", f"{confidence_threshold:.1%}")
    
    # Fetch and display summary statistics
    show_review_summary()
    
    # Fetch human review records
    if st.button("🔄 Refresh Review Queue", type="primary"):
        st.rerun()
    
    # Display records
    show_human_review_records()

def show_review_summary():
    """Display summary statistics for human review"""
    try:
        # Fetch human review records
        response = requests.get("http://127.0.0.1:8000/api/human-review")
        
        if response.status_code == 200:
            data = response.json()
            
            if data["success"]:
                records = data["records"]
                
                # Calculate statistics
                total_pending = len(records)
                avg_confidence = sum(r['confidence_score'] for r in records) / len(records) if records else 0
                low_confidence = sum(1 for r in records if r['confidence_score'] < 0.5)
                medium_confidence = sum(1 for r in records if 0.5 <= r['confidence_score'] < 0.7)
                high_confidence = sum(1 for r in records if r['confidence_score'] >= 0.7)
                
                # Display metrics
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Pending Review", total_pending)
                
                with col2:
                    st.metric("Avg Confidence", f"{avg_confidence:.1%}")
                
                with col3:
                    st.metric("Low Confidence", low_confidence)
                
                with col4:
                    st.metric("High Confidence", high_confidence)
                
                # Confidence distribution
                if records:
                    st.subheader("📊 Confidence Distribution")
                    confidence_data = pd.DataFrame({
                        'Confidence Range': ['Low (0-50%)', 'Medium (50-70%)', 'High (70%+)'],
                        'Count': [low_confidence, medium_confidence, high_confidence]
                    })
                    st.bar_chart(confidence_data.set_index('Confidence Range'))
                
            else:
                st.error(f"Failed to fetch summary: {data.get('error', 'Unknown error')}")
        else:
            st.error(f"API Error: {response.status_code}")
            
    except Exception as e:
        st.error(f"Error fetching summary: {str(e)}")

def show_human_review_records():
    """Display records that need human review"""
    try:
        # Fetch records from API
        response = requests.get("http://127.0.0.1:8000/api/human-review")
        
        if response.status_code == 200:
            data = response.json()
            
            if data["success"]:
                records = data["records"]
                
                if not records:
                    st.success("🎉 No records need human review!")
                    st.info("All AI-classified records have high confidence scores.")
                    return
                
                st.subheader(f"📋 Records Needing Review ({len(records)} total)")
                
                # Display each record
                for i, record in enumerate(records):
                    show_review_record(record, i)
                    
            else:
                st.error(f"Failed to fetch records: {data.get('error', 'Unknown error')}")
        else:
            st.error(f"API Error: {response.status_code}")
            
    except Exception as e:
        st.error(f"Error fetching human review records: {str(e)}")

def show_review_record(record, index):
    """Display a single record for review with editing capabilities"""
    with st.expander(f"Record #{index + 1}: {record['supplier_name']} - Confidence: {record['confidence_score']:.1%}", expanded=True):
        
        # Create a form for editing the record
        with st.form(key=f"review_form_{record['id']}"):
            st.markdown("### 📝 Review & Edit Record")
            
            # Confidence and AI info at the top
            col1, col2, col3 = st.columns(3)
            with col1:
                confidence = record['confidence_score']
                if confidence >= 0.8:
                    confidence_color = "🟢"
                elif confidence >= 0.6:
                    confidence_color = "🟡"
                else:
                    confidence_color = "🔴"
                st.metric("AI Confidence", f"{confidence_color} {confidence:.1%}")
            
            with col2:
                st.metric("AI Model", record['ai_model_used'].split(':')[-1] if record['ai_model_used'] else "Unknown")
            
            with col3:
                st.metric("Created", record['created_at'][:10] if record['created_at'] else "Unknown")
            
            st.divider()
            
            # Editable fields in two columns
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Basic Information**")
                
                # Supplier name
                supplier_name = st.text_input(
                    "Supplier Name *",
                    value=record['supplier_name'] or "",
                    key=f"supplier_{record['id']}",
                    help="Name of the supplier or company"
                )
                
                # Activity type
                activity_type = st.selectbox(
                    "Activity Type *",
                    options=["transportation", "energy", "waste", "materials", "other"],
                    index=["transportation", "energy", "waste", "materials", "other"].index(record['activity_type']) if record['activity_type'] in ["transportation", "energy", "waste", "materials", "other"] else 4,
                    key=f"activity_{record['id']}",
                    help="Type of carbon emission activity"
                )
                
                # Amount and currency
                amount_col, currency_col = st.columns([2, 1])
                with amount_col:
                    amount = st.number_input(
                        "Amount",
                        value=float(record['amount']) if record['amount'] else 0.0,
                        min_value=0.0,
                        step=0.01,
                        key=f"amount_{record['id']}",
                        help="Monetary amount"
                    )
                with currency_col:
                    currency = st.selectbox(
                        "Currency",
                        options=["USD", "EUR", "GBP", "CAD", "AUD", "JPY", "CHF"],
                        index=["USD", "EUR", "GBP", "CAD", "AUD", "JPY", "CHF"].index(record['currency']) if record['currency'] in ["USD", "EUR", "GBP", "CAD", "AUD", "JPY", "CHF"] else 0,
                        key=f"currency_{record['id']}"
                    )
                
                # Date
                date_str = st.text_input(
                    "Date (YYYY-MM-DD)",
                    value=record['date'] or "",
                    key=f"date_{record['id']}",
                    help="Date of the emission activity"
                )
                
                # Scope
                scope = st.selectbox(
                    "Scope",
                    options=[1, 2, 3],
                    index=[1, 2, 3].index(record['scope']) if record['scope'] in [1, 2, 3] else 2,
                    key=f"scope_{record['id']}",
                    help="Carbon emission scope (1=Direct, 2=Indirect, 3=Other)"
                )
            
            with col2:
                st.markdown("**Activity Details**")
                
                # Description
                description = st.text_area(
                    "Description",
                    value=record['description'] or "",
                    height=100,
                    key=f"description_{record['id']}",
                    help="Detailed description of the activity"
                )
                
                # Category and subcategory
                category = st.text_input(
                    "Category",
                    value=record['category'] or "",
                    key=f"category_{record['id']}",
                    help="Emission category"
                )
                
                subcategory = st.text_input(
                    "Subcategory",
                    value=record['subcategory'] or "",
                    key=f"subcategory_{record['id']}",
                    help="Emission subcategory"
                )
                
                # Activity amount and unit
                activity_amount = st.number_input(
                    "Activity Amount",
                    value=float(record['activity_amount']) if record['activity_amount'] else 0.0,
                    min_value=0.0,
                    step=0.01,
                    key=f"activity_amount_{record['id']}",
                    help="Amount of the activity (e.g., distance, weight)"
                )
                
                activity_unit = st.text_input(
                    "Activity Unit",
                    value=record['activity_unit'] or "",
                    key=f"activity_unit_{record['id']}",
                    help="Unit of measurement (e.g., km, tonnes, kWh)"
                )
            
            # Additional fields in a collapsible section
            with st.expander("🔧 Advanced Fields"):
                col1, col2 = st.columns(2)
                
                with col1:
                    fuel_type = st.text_input(
                        "Fuel Type",
                        value=record['fuel_type'] or "",
                        key=f"fuel_type_{record['id']}",
                        help="Type of fuel used"
                    )
                    
                    vehicle_type = st.text_input(
                        "Vehicle Type",
                        value=record['vehicle_type'] or "",
                        key=f"vehicle_type_{record['id']}",
                        help="Type of vehicle used"
                    )
                    
                    distance_km = st.number_input(
                        "Distance (km)",
                        value=float(record['distance_km']) if record['distance_km'] else 0.0,
                        min_value=0.0,
                        step=0.1,
                        key=f"distance_{record['id']}",
                        help="Distance traveled in kilometers"
                    )
                
                with col2:
                    mass_tonnes = st.number_input(
                        "Mass (tonnes)",
                        value=float(record['mass_tonnes']) if record['mass_tonnes'] else 0.0,
                        min_value=0.0,
                        step=0.01,
                        key=f"mass_{record['id']}",
                        help="Mass in tonnes"
                    )
                    
                    energy_kwh = st.number_input(
                        "Energy (kWh)",
                        value=float(record['energy_kwh']) if record['energy_kwh'] else 0.0,
                        min_value=0.0,
                        step=0.1,
                        key=f"energy_{record['id']}",
                        help="Energy consumption in kWh"
                    )
            
            # AI reasoning section
            if record.get('classification_metadata'):
                with st.expander("🤖 AI Reasoning & Raw Response"):
                    metadata = record['classification_metadata']
                    if isinstance(metadata, dict) and 'raw_response' in metadata:
                        st.text_area(
                            "AI Raw Response",
                            value=metadata['raw_response'],
                            height=150,
                            key=f"raw_response_{record['id']}",
                            help="The original response from the AI model"
                        )
            
            st.divider()
            
            # Action buttons
            col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
            
            with col1:
                approve_btn = st.form_submit_button("✅ Approve", type="primary", help="Approve this record as-is")
            
            with col2:
                approve_edited_btn = st.form_submit_button("✅ Approve Edited", help="Approve with your changes")
            
            with col3:
                reject_btn = st.form_submit_button("❌ Reject", help="Reject this record")
            
            with col4:
                save_draft_btn = st.form_submit_button("💾 Save Draft", help="Save changes for later review")
            
            # Add a main submit button for the form
            if st.form_submit_button("🔄 Process Action", type="secondary"):
                st.info("Please select one of the action buttons above to process this record.")
            
            # Handle form submissions
            if approve_btn:
                approve_record(record['id'])
            elif approve_edited_btn:
                # Collect all the form data
                updated_data = {
                    "supplier_name": supplier_name,
                    "activity_type": activity_type,
                    "amount": amount if amount > 0 else None,
                    "currency": currency,
                    "date": date_str if date_str else None,
                    "description": description,
                    "scope": scope,
                    "category": category,
                    "subcategory": subcategory,
                    "activity_amount": activity_amount if activity_amount > 0 else None,
                    "activity_unit": activity_unit,
                    "fuel_type": fuel_type,
                    "vehicle_type": vehicle_type,
                    "distance_km": distance_km if distance_km > 0 else None,
                    "mass_tonnes": mass_tonnes if mass_tonnes > 0 else None,
                    "energy_kwh": energy_kwh if energy_kwh > 0 else None,
                }
                approve_record_with_changes(record['id'], updated_data)
            elif reject_btn:
                reject_record(record['id'])
            elif save_draft_btn:
                st.info("💾 Draft saved! (This feature will be implemented in the next version)")

def approve_record(record_id):
    """Approve a record for human review"""
    try:
        response = requests.post(f"http://127.0.0.1:8000/api/human-review/{record_id}/approve")
        
        if response.status_code == 200:
            data = response.json()
            if data["success"]:
                st.success("✅ Record approved successfully!")
                st.rerun()
            else:
                st.error(f"Failed to approve record: {data.get('error', 'Unknown error')}")
        else:
            st.error(f"API Error: {response.status_code}")
            
    except Exception as e:
        st.error(f"Error approving record: {str(e)}")

def approve_record_with_changes(record_id, updated_data):
    """Approve a record with human-made changes"""
    try:
        response = requests.post(
            f"http://127.0.0.1:8000/api/human-review/{record_id}/approve-with-changes",
            json=updated_data
        )
        
        if response.status_code == 200:
            data = response.json()
            if data["success"]:
                st.success("✅ Record approved with your changes!")
                st.rerun()
            else:
                st.error(f"Failed to approve record: {data.get('error', 'Unknown error')}")
        else:
            st.error(f"API Error: {response.status_code}")
            
    except Exception as e:
        st.error(f"Error approving record with changes: {str(e)}")

def reject_record(record_id):
    """Reject a record for human review"""
    try:
        response = requests.post(f"http://127.0.0.1:8000/api/human-review/{record_id}/reject")
        
        if response.status_code == 200:
            data = response.json()
            if data["success"]:
                st.success("❌ Record rejected successfully!")
                st.rerun()
            else:
                st.error(f"Failed to reject record: {data.get('error', 'Unknown error')}")
        else:
            st.error(f"API Error: {response.status_code}")
            
    except Exception as e:
        st.error(f"Error rejecting record: {str(e)}")

def show_confidence_analytics():
    """Show analytics about confidence scores"""
    try:
        response = requests.get("http://127.0.0.1:8000/api/emission-records")
        
        if response.status_code == 200:
            data = response.json()
            
            if data["success"]:
                records = data["records"]
                
                if records:
                    # Create DataFrame for analysis
                    df = pd.DataFrame(records)
                    
                    # Filter AI-classified records
                    ai_records = df[df['ai_classified'] == 'true']
                    
                    if not ai_records.empty:
                        st.subheader("📊 Confidence Score Analytics")
                        
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            avg_confidence = ai_records['confidence_score'].mean()
                            st.metric("Average Confidence", f"{avg_confidence:.1%}")
                            
                        with col2:
                            low_confidence = (ai_records['confidence_score'] < 0.7).sum()
                            st.metric("Low Confidence Records", low_confidence)
                            
                        with col3:
                            high_confidence = (ai_records['confidence_score'] >= 0.7).sum()
                            st.metric("High Confidence Records", high_confidence)
                        
                        # Confidence distribution chart
                        st.bar_chart(ai_records['confidence_score'].value_counts().sort_index())
                        
                        # Records by confidence level
                        st.subheader("Confidence Distribution")
                        confidence_ranges = pd.cut(ai_records['confidence_score'], 
                                                 bins=[0, 0.3, 0.5, 0.7, 0.9, 1.0], 
                                                 labels=['Very Low (0-30%)', 'Low (30-50%)', 'Medium (50-70%)', 'High (70-90%)', 'Very High (90-100%)'])
                        
                        distribution = confidence_ranges.value_counts()
                        st.bar_chart(distribution)
                        
                    else:
                        st.info("No AI-classified records found.")
                else:
                    st.info("No records found.")
            else:
                st.error(f"Failed to fetch records: {data.get('error', 'Unknown error')}")
        else:
            st.error(f"API Error: {response.status_code}")
            
    except Exception as e:
        st.error(f"Error fetching analytics: {str(e)}")
