"""
Enhanced Audit Snapshots UI Component
Comprehensive audit trail system with immutable history and rich metadata
"""
import streamlit as st
import requests
import json
import pandas as pd

# Suppress Plotly deprecation warnings
import warnings
warnings.filterwarnings('ignore', category=DeprecationWarning, module='plotly')
warnings.filterwarnings('ignore', message='.*keyword arguments have been deprecated.*')

import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional
import uuid

def show_enhanced_audit_snapshots(api_base: str):
    """Show enhanced audit snapshots management interface"""
    
    st.title("🔍 Enhanced Audit Snapshots")
    st.markdown("Comprehensive audit trail system with immutable history and rich metadata")
    
    # Sidebar for navigation
    tab = st.sidebar.selectbox(
        "Navigation",
        [
            "📊 Dashboard",
            "➕ Create Snapshot", 
            "📋 View Snapshots",
            "🔍 Snapshot Details",
            "📈 Analytics",
            "⚙️ Settings"
        ]
    )
    
    if tab == "📊 Dashboard":
        show_audit_dashboard(api_base)
    elif tab == "➕ Create Snapshot":
        show_create_snapshot(api_base)
    elif tab == "📋 View Snapshots":
        show_view_snapshots(api_base)
    elif tab == "🔍 Snapshot Details":
        show_snapshot_details(api_base)
    elif tab == "📈 Analytics":
        show_audit_analytics(api_base)
    elif tab == "⚙️ Settings":
        show_audit_settings(api_base)


def show_audit_dashboard(api_base: str):
    """Show audit snapshots dashboard"""
    st.subheader("📊 Audit Snapshots Dashboard")
    
    try:
        # Get recent snapshots
        response = requests.get(f"{api_base}/api/audit/snapshots?limit=10")
        response.raise_for_status()
        snapshots = response.json()
        
        if not snapshots:
            st.info("No audit snapshots found. Create your first snapshot to get started.")
            return
        
        # Key metrics
        col1, col2, col3, col4 = st.columns(4)
        
        total_snapshots = len(snapshots)
        total_emissions = sum(float(s.get('total_emissions_kgco2e', 0) or 0) for s in snapshots)
        approved_snapshots = len([s for s in snapshots if s.get('approval_status') == 'approved'])
        pending_snapshots = len([s for s in snapshots if s.get('approval_status') in ['draft', 'pending_review']])
        
        with col1:
            st.metric("Total Snapshots", total_snapshots)
        with col2:
            st.metric("Total Emissions (tCO2e)", f"{total_emissions/1000:.1f}")
        with col3:
            st.metric("Approved", approved_snapshots)
        with col4:
            st.metric("Pending", pending_snapshots)
        
        # Recent snapshots table
        st.subheader("Recent Audit Snapshots")
        
        df = pd.DataFrame(snapshots)
        if not df.empty:
            # Format the dataframe for display
            df['reporting_period'] = df.apply(
                lambda row: f"{row['reporting_period_start']} to {row['reporting_period_end']}", 
                axis=1
            )
            df['emissions_tco2e'] = pd.to_numeric(df['total_emissions_kgco2e'], errors='coerce') / 1000
            
            display_df = df[['submission_id', 'submission_type', 'reporting_period', 
                           'total_records', 'emissions_tco2e', 'approval_status', 'created_at']].copy()
            display_df.columns = ['Submission ID', 'Framework', 'Period', 'Records', 'Emissions (tCO2e)', 'Status', 'Created']
            
            st.dataframe(display_df, use_container_width=True)
        
        # Status distribution chart
        if len(snapshots) > 0:
            st.subheader("Approval Status Distribution")
            
            status_counts = pd.Series([s.get('approval_status', 'unknown') for s in snapshots]).value_counts()
            
            fig = px.pie(
                values=status_counts.values,
                names=status_counts.index,
                title="Audit Snapshot Status Distribution",
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            st.plotly_chart(fig, width='stretch')
        
        # Emissions by framework
        if len(snapshots) > 0:
            st.subheader("Emissions by Regulatory Framework")
            
            framework_emissions = {}
            for snapshot in snapshots:
                framework = snapshot.get('submission_type', 'unknown')
                emissions = float(snapshot.get('total_emissions_kgco2e', 0)) / 1000
                framework_emissions[framework] = framework_emissions.get(framework, 0) + emissions
            
            if framework_emissions:
                fig = px.bar(
                    x=list(framework_emissions.keys()),
                    y=list(framework_emissions.values()),
                    title="Total Emissions by Regulatory Framework (tCO2e)",
                    labels={'x': 'Framework', 'y': 'Emissions (tCO2e)'}
                )
                st.plotly_chart(fig, width='stretch')
        
    except requests.exceptions.RequestException as e:
        st.error(f"Error loading dashboard data: {e}")
    except Exception as e:
        st.error(f"Error displaying dashboard: {e}")


def show_create_snapshot(api_base: str):
    """Show create audit snapshot interface"""
    st.subheader("➕ Create New Audit Snapshot")
    
    # Data availability info
    st.info("💡 **Data Availability**: Your emission data spans January-March 2025. Use Q1 2025 dates for the best results with 250+ records!")
    
    with st.form("create_audit_snapshot"):
        col1, col2 = st.columns(2)
        
        with col1:
            # Get supported frameworks
            try:
                frameworks_response = requests.get(f"{api_base}/api/audit/frameworks")
                frameworks_response.raise_for_status()
                frameworks = frameworks_response.json()
                framework_options = {f["label"]: f["value"] for f in frameworks}
                
                selected_framework = st.selectbox(
                    "Regulatory Framework",
                    options=list(framework_options.keys()),
                    help="Select the regulatory framework for this audit snapshot"
                )
                submission_type = framework_options[selected_framework]
                
            except:
                st.error("Could not load regulatory frameworks")
                return
            
            start_date = st.date_input(
                "Reporting Period Start",
                value=date(2025, 1, 1),  # Default to Q1 2025 where data exists
                help="Start date of the reporting period"
            )
            
            end_date = st.date_input(
                "Reporting Period End", 
                value=date(2025, 3, 31),  # Default to Q1 2025 where data exists
                help="End date of the reporting period"
            )
            
            organization_id = st.text_input(
                "Organization ID",
                help="Organization identifier (optional)"
            )
            
            business_unit = st.text_input(
                "Business Unit",
                help="Business unit identifier (optional)"
            )
        
        with col2:
            reporting_entity = st.text_input(
                "Reporting Entity",
                help="Name of the reporting entity"
            )
            
            description = st.text_area(
                "Description",
                help="Description of the audit snapshot",
                height=100
            )
            
            st.markdown("**Scope Selection**")
            include_scope_1 = st.checkbox("Include Scope 1", value=True, help="Direct emissions")
            include_scope_2 = st.checkbox("Include Scope 2", value=True, help="Indirect emissions from purchased energy")
            include_scope_3 = st.checkbox("Include Scope 3", value=True, help="Other indirect emissions")
            
            created_by = st.text_input(
                "Created By",
                value="user@example.com",
                help="User creating the snapshot"
            )
        
        # Advanced options
        with st.expander("Advanced Options"):
            record_ids_input = st.text_area(
                "Specific Record IDs (optional)",
                help="Enter specific record IDs to include, one per line",
                height=100
            )
            
            record_ids = [rid.strip() for rid in record_ids_input.split('\n') if rid.strip()] if record_ids_input else None
        
        submitted = st.form_submit_button("Create Audit Snapshot", type="primary")
        
        if submitted:
            if start_date >= end_date:
                st.error("Start date must be before end date")
                return
            
            # Create the snapshot
            with st.spinner("Creating audit snapshot..."):
                try:
                    request_data = {
                        "submission_type": submission_type,
                        "reporting_period_start": start_date.isoformat(),
                        "reporting_period_end": end_date.isoformat(),
                        "organization_id": organization_id if organization_id else None,
                        "business_unit": business_unit if business_unit else None,
                        "reporting_entity": reporting_entity if reporting_entity else None,
                        "description": description if description else None,
                        "record_ids": record_ids,
                        "include_scope_1": include_scope_1,
                        "include_scope_2": include_scope_2,
                        "include_scope_3": include_scope_3,
                        "created_by": created_by
                    }
                    
                    response = requests.post(
                        f"{api_base}/api/audit/snapshots",
                        json=request_data,
                        timeout=60
                    )
                    response.raise_for_status()
                    result = response.json()
                    
                    if result.get('success'):
                        st.success("✅ Audit snapshot created successfully!")
                        
                        # Display results
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("Total Records", result.get('total_records', 0))
                            st.metric("Total Emissions (tCO2e)", f"{result.get('total_emissions_kgco2e', 0)/1000:.2f}")
                        
                        with col2:
                            st.metric("Submission ID", result.get('submission_id', 'N/A'))
                            st.metric("Status", result.get('approval_status', 'N/A'))
                        
                        # Scope breakdown
                        scope_breakdown = result.get('scope_breakdown', {})
                        if scope_breakdown:
                            st.subheader("Scope Breakdown")
                            scope_df = pd.DataFrame([
                                {"Scope": "Scope 1", "Emissions (tCO2e)": scope_breakdown.get('scope_1', 0)/1000},
                                {"Scope": "Scope 2", "Emissions (tCO2e)": scope_breakdown.get('scope_2', 0)/1000},
                                {"Scope": "Scope 3", "Emissions (tCO2e)": scope_breakdown.get('scope_3', 0)/1000}
                            ])
                            st.dataframe(scope_df, use_container_width=True)
                        
                        # Compliance metrics
                        compliance_metrics = result.get('compliance_metrics', {})
                        if compliance_metrics:
                            st.subheader("Compliance Metrics")
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Avg Compliance Score", f"{compliance_metrics.get('average_compliance_score', 0):.1f}%")
                            with col2:
                                st.metric("Audit Ready Records", compliance_metrics.get('audit_ready_records', 0))
                            with col3:
                                st.metric("Compliance Rate", f"{compliance_metrics.get('compliance_rate', 0):.1f}%")
                        
                        # Store snapshot ID for navigation
                        st.session_state['last_created_snapshot_id'] = result.get('submission_id')
                        
                    else:
                        st.error(f"Error creating audit snapshot: {result.get('message', 'Unknown error')}")
                        
                except requests.exceptions.RequestException as e:
                    st.error(f"Error connecting to API: {e}")
                except Exception as e:
                    st.error(f"Error creating audit snapshot: {e}")


def show_view_snapshots(api_base: str):
    """Show view audit snapshots interface"""
    st.subheader("📋 View Audit Snapshots")
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Get frameworks for filter
        try:
            frameworks_response = requests.get(f"{api_base}/api/audit/frameworks")
            frameworks_response.raise_for_status()
            frameworks = frameworks_response.json()
            framework_options = {f["label"]: f["value"] for f in frameworks}
            framework_options["All"] = None
            
            selected_framework = st.selectbox(
                "Filter by Framework",
                options=list(framework_options.keys()),
                index=0
            )
            framework_filter = framework_options[selected_framework]
            
        except:
            framework_filter = None
    
    with col2:
        # Get approval statuses for filter
        try:
            statuses_response = requests.get(f"{api_base}/api/audit/approval-statuses")
            statuses_response.raise_for_status()
            statuses = statuses_response.json()
            status_options = {s["label"]: s["value"] for s in statuses}
            status_options["All"] = None
            
            selected_status = st.selectbox(
                "Filter by Status",
                options=list(status_options.keys()),
                index=0
            )
            status_filter = status_options[selected_status]
            
        except:
            status_filter = None
    
    with col3:
        organization_filter = st.text_input(
            "Filter by Organization ID",
            help="Enter organization ID to filter (optional)"
        )
        organization_filter = organization_filter if organization_filter else None
    
    # Load snapshots
    try:
        params = {
            "limit": 50,
            "offset": 0
        }
        if framework_filter:
            params["submission_type"] = framework_filter
        if status_filter:
            params["approval_status"] = status_filter
        if organization_filter:
            params["organization_id"] = organization_filter
        
        response = requests.get(f"{api_base}/api/audit/snapshots", params=params)
        response.raise_for_status()
        snapshots = response.json()
        
        if not snapshots:
            st.info("No audit snapshots found matching the criteria.")
            return
        
        # Display snapshots
        st.subheader(f"Found {len(snapshots)} Audit Snapshots")
        
        for snapshot in snapshots:
            with st.expander(f"📄 {snapshot.get('submission_id', 'Unknown')} - {snapshot.get('submission_type', 'Unknown').upper()}"):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.write(f"**Period:** {snapshot.get('reporting_period_start', 'N/A')} to {snapshot.get('reporting_period_end', 'N/A')}")
                    st.write(f"**Records:** {snapshot.get('total_records', 0)}")
                    st.write(f"**Emissions:** {snapshot.get('total_emissions_kgco2e', 0)/1000:.2f} tCO2e")
                
                with col2:
                    st.write(f"**Status:** {snapshot.get('approval_status', 'N/A')}")
                    st.write(f"**Workflow Stage:** {snapshot.get('workflow_stage', 'N/A')}")
                    st.write(f"**Created:** {snapshot.get('created_at', 'N/A')}")
                
                with col3:
                    st.write(f"**Created By:** {snapshot.get('created_by', 'N/A')}")
                    if snapshot.get('organization_id'):
                        st.write(f"**Organization:** {snapshot.get('organization_id')}")
                    if snapshot.get('business_unit'):
                        st.write(f"**Business Unit:** {snapshot.get('business_unit')}")
                
                # Action buttons
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    if st.button("View Details", key=f"view_{snapshot.get('submission_id')}"):
                        st.session_state['selected_snapshot_id'] = snapshot.get('submission_id')
                        st.rerun()
                
                with col2:
                    if st.button("Export JSON", key=f"export_json_{snapshot.get('submission_id')}"):
                        export_snapshot_json(api_base, snapshot.get('submission_id'))
                
                with col3:
                    if st.button("Export PDF", key=f"export_pdf_{snapshot.get('submission_id')}"):
                        export_snapshot_pdf(api_base, snapshot.get('submission_id'))
                
                with col4:
                    if st.button("Compliance Check", key=f"compliance_{snapshot.get('submission_id')}"):
                        run_compliance_check(api_base, snapshot.get('submission_id'))
        
    except requests.exceptions.RequestException as e:
        st.error(f"Error loading audit snapshots: {e}")
    except Exception as e:
        st.error(f"Error displaying audit snapshots: {e}")


def show_snapshot_details(api_base: str):
    """Show detailed audit snapshot information"""
    st.subheader("🔍 Audit Snapshot Details")
    
    # Get snapshot ID
    snapshot_id = st.text_input(
        "Enter Snapshot ID",
        value=st.session_state.get('selected_snapshot_id', ''),
        help="Enter the submission ID of the audit snapshot to view"
    )
    
    if not snapshot_id:
        st.info("Please enter a snapshot ID to view details.")
        return
    
    try:
        response = requests.get(f"{api_base}/api/audit/snapshots/{snapshot_id}")
        response.raise_for_status()
        details = response.json()
        
        if not details:
            st.error("Audit snapshot not found.")
            return
        
        snapshot = details.get('snapshot', {})
        entries = details.get('entries', [])
        audit_logs = details.get('audit_logs', [])
        
        # Snapshot overview
        st.subheader("📊 Snapshot Overview")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Submission ID", snapshot.get('submission_id', 'N/A'))
            st.metric("Framework", snapshot.get('submission_type', 'N/A'))
            st.metric("Total Records", snapshot.get('total_records', 0))
        
        with col2:
            st.metric("Total Emissions", f"{snapshot.get('total_emissions_kgco2e', 0)/1000:.2f} tCO2e")
            st.metric("Approval Status", snapshot.get('approval_status', 'N/A'))
            st.metric("Workflow Stage", snapshot.get('workflow_stage', 'N/A'))
        
        with col3:
            st.metric("Created", snapshot.get('created_at', 'N/A')[:10])
            st.metric("Created By", snapshot.get('created_by', 'N/A'))
            if snapshot.get('organization_id'):
                st.metric("Organization", snapshot.get('organization_id'))
        
        # Scope breakdown
        scope_breakdown = snapshot.get('scope_breakdown', {})
        if scope_breakdown:
            st.subheader("📈 Scope Breakdown")
            
            scope_data = [
                {"Scope": "Scope 1", "Emissions (tCO2e)": scope_breakdown.get('scope_1', 0)/1000},
                {"Scope": "Scope 2", "Emissions (tCO2e)": scope_breakdown.get('scope_2', 0)/1000},
                {"Scope": "Scope 3", "Emissions (tCO2e)": scope_breakdown.get('scope_3', 0)/1000}
            ]
            
            scope_df = pd.DataFrame(scope_data)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.dataframe(scope_df, use_container_width=True)
            
            with col2:
                fig = px.pie(
                    scope_df, 
                    values='Emissions (tCO2e)', 
                    names='Scope',
                    title="Emissions by Scope"
                )
                st.plotly_chart(fig, width='stretch')
        
        # Entries details
        if entries:
            st.subheader("📋 Snapshot Entries")
            
            # Filters for entries
            col1, col2, col3 = st.columns(3)
            
            with col1:
                scope_filter = st.selectbox(
                    "Filter by Scope",
                    options=["All"] + list(set([e.get('emission_scope', '') for e in entries])),
                    key="scope_filter"
                )
            
            with col2:
                activity_filter = st.selectbox(
                    "Filter by Activity Type",
                    options=["All"] + list(set([e.get('activity_type', '') for e in entries])),
                    key="activity_filter"
                )
            
            with col3:
                status_filter = st.selectbox(
                    "Filter by Status",
                    options=["All"] + list(set([e.get('approval_status', '') for e in entries])),
                    key="status_filter"
                )
            
            # Apply filters
            filtered_entries = entries
            if scope_filter != "All":
                filtered_entries = [e for e in filtered_entries if e.get('emission_scope') == scope_filter]
            if activity_filter != "All":
                filtered_entries = [e for e in filtered_entries if e.get('activity_type') == activity_filter]
            if status_filter != "All":
                filtered_entries = [e for e in filtered_entries if e.get('approval_status') == status_filter]
            
            st.write(f"Showing {len(filtered_entries)} of {len(entries)} entries")
            
            # Display entries
            if filtered_entries:
                entries_df = pd.DataFrame(filtered_entries)
                
                # Select columns to display
                display_columns = [
                    'measurement_timestamp', 'emission_scope', 'activity_type',
                    'activity_data', 'activity_unit', 'emissions_kgco2e',
                    'data_source', 'emission_factor_source', 'approval_status'
                ]
                
                available_columns = [col for col in display_columns if col in entries_df.columns]
                display_df = entries_df[available_columns].copy()
                
                # Format columns
                if 'measurement_timestamp' in display_df.columns:
                    display_df['measurement_timestamp'] = pd.to_datetime(display_df['measurement_timestamp']).dt.strftime('%Y-%m-%d')
                if 'emissions_kgco2e' in display_df.columns:
                    display_df['emissions_kgco2e'] = display_df['emissions_kgco2e'] / 1000
                    display_df.rename(columns={'emissions_kgco2e': 'emissions_tco2e'}, inplace=True)
                
                st.dataframe(display_df, use_container_width=True)
        
        # Audit logs
        if audit_logs:
            st.subheader("📝 Audit Logs")
            
            logs_df = pd.DataFrame(audit_logs)
            logs_df['event_timestamp'] = pd.to_datetime(logs_df['event_timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
            
            st.dataframe(logs_df, use_container_width=True)
        
        # Action buttons
        st.subheader("🔧 Actions")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("Update Status", type="primary"):
                show_status_update_form(api_base, snapshot_id)
        
        with col2:
            if st.button("Export JSON"):
                export_snapshot_json(api_base, snapshot_id)
        
        with col3:
            if st.button("Export PDF"):
                export_snapshot_pdf(api_base, snapshot_id)
        
        with col4:
            if st.button("Compliance Check"):
                run_compliance_check(api_base, snapshot_id)
        
    except requests.exceptions.RequestException as e:
        st.error(f"Error loading snapshot details: {e}")
    except Exception as e:
        st.error(f"Error displaying snapshot details: {e}")


def show_status_update_form(api_base: str, snapshot_id: str):
    """Show form for updating approval status"""
    st.subheader("🔄 Update Approval Status")
    
    with st.form("update_status"):
        # Get approval statuses
        try:
            statuses_response = requests.get(f"{api_base}/api/audit/approval-statuses")
            statuses_response.raise_for_status()
            statuses = statuses_response.json()
            status_options = {s["label"]: s["value"] for s in statuses}
            
            new_status = st.selectbox(
                "New Status",
                options=list(status_options.keys()),
                help="Select the new approval status"
            )
            
            actor_role = st.selectbox(
                "Your Role",
                options=["REVIEWER", "APPROVER", "AUDITOR"],
                help="Select your role in the approval process"
            )
            
            notes = st.text_area(
                "Notes",
                help="Add notes about the status change",
                height=100
            )
            
            actor_id = st.text_input(
                "Actor ID",
                value="user@example.com",
                help="Your user ID"
            )
            
            submitted = st.form_submit_button("Update Status", type="primary")
            
            if submitted:
                try:
                    request_data = {
                        "new_status": status_options[new_status],
                        "actor_role": actor_role,
                        "notes": notes if notes else None
                    }
                    
                    response = requests.put(
                        f"{api_base}/api/audit/snapshots/{snapshot_id}/approval-status",
                        json=request_data,
                        params={"actor_id": actor_id}
                    )
                    response.raise_for_status()
                    result = response.json()
                    
                    if result.get('success'):
                        st.success("✅ Status updated successfully!")
                        st.rerun()
                    else:
                        st.error(f"Error updating status: {result.get('message', 'Unknown error')}")
                        
                except requests.exceptions.RequestException as e:
                    st.error(f"Error updating status: {e}")
                except Exception as e:
                    st.error(f"Error updating status: {e}")
                    
        except requests.exceptions.RequestException as e:
            st.error(f"Error loading approval statuses: {e}")


def export_snapshot_json(api_base: str, snapshot_id: str):
    """Export snapshot as JSON"""
    try:
        response = requests.get(f"{api_base}/api/audit/snapshots/{snapshot_id}/export/json")
        response.raise_for_status()
        result = response.json()
        
        if result.get('success'):
            st.success("✅ JSON export completed!")
            st.download_button(
                label="Download JSON",
                data=json.dumps(result.get('data', {}), indent=2),
                file_name=f"audit_snapshot_{snapshot_id}.json",
                mime="application/json"
            )
        else:
            st.error("Error exporting JSON")
            
    except requests.exceptions.RequestException as e:
        st.error(f"Error exporting JSON: {e}")
    except Exception as e:
        st.error(f"Error exporting JSON: {e}")


def export_snapshot_pdf(api_base: str, snapshot_id: str):
    """Export snapshot as PDF"""
    try:
        response = requests.get(f"{api_base}/api/audit/snapshots/{snapshot_id}/export/pdf")
        response.raise_for_status()
        result = response.json()
        
        if result.get('success'):
            st.success("✅ PDF export initiated!")
            st.info(f"Download URL: {result.get('download_url', 'N/A')}")
        else:
            st.error("Error exporting PDF")
            
    except requests.exceptions.RequestException as e:
        st.error(f"Error exporting PDF: {e}")
    except Exception as e:
        st.error(f"Error exporting PDF: {e}")


def run_compliance_check(api_base: str, snapshot_id: str):
    """Run compliance check for snapshot"""
    try:
        response = requests.get(f"{api_base}/api/audit/snapshots/{snapshot_id}/compliance-check")
        response.raise_for_status()
        result = response.json()
        
        st.subheader("🔍 Compliance Check Results")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Compliance Score", f"{result.get('compliance_score', 0):.1f}%")
        with col2:
            st.metric("Audit Ready", result.get('audit_ready', 0))
        with col3:
            st.metric("Compliance Rate", f"{result.get('compliance_rate', 0):.1f}%")
        
        # Issues
        issues = result.get('issues', [])
        if issues:
            st.subheader("⚠️ Issues Found")
            for issue in issues:
                st.error(f"• {issue}")
        
        # Recommendations
        recommendations = result.get('recommendations', [])
        if recommendations:
            st.subheader("💡 Recommendations")
            for rec in recommendations:
                st.info(f"• {rec}")
        
        if not issues and not recommendations:
            st.success("✅ No compliance issues found!")
            
    except requests.exceptions.RequestException as e:
        st.error(f"Error running compliance check: {e}")
    except Exception as e:
        st.error(f"Error running compliance check: {e}")


def show_audit_analytics(api_base: str):
    """Show audit analytics and insights"""
    st.subheader("📈 Audit Analytics")
    
    try:
        # Get snapshots for analytics
        response = requests.get(f"{api_base}/api/audit/snapshots?limit=100")
        response.raise_for_status()
        snapshots = response.json()
        
        if not snapshots:
            st.info("No audit snapshots available for analytics.")
            return
        
        df = pd.DataFrame(snapshots)
        
        # Time series of snapshots
        st.subheader("📅 Snapshot Creation Timeline")
        
        df['created_date'] = pd.to_datetime(df['created_at']).dt.date
        daily_counts = df.groupby('created_date').size().reset_index(name='count')
        
        fig = px.line(
            daily_counts, 
            x='created_date', 
            y='count',
            title="Audit Snapshots Created Over Time"
        )
        st.plotly_chart(fig, width='stretch')
        
        # Emissions trends
        st.subheader("📊 Emissions Trends")
        
        df['emissions_tco2e'] = df['total_emissions_kgco2e'] / 1000
        df['created_date'] = pd.to_datetime(df['created_at']).dt.date
        
        emissions_trend = df.groupby('created_date')['emissions_tco2e'].sum().reset_index()
        
        fig = px.line(
            emissions_trend,
            x='created_date',
            y='emissions_tco2e',
            title="Total Emissions Over Time (tCO2e)"
        )
        st.plotly_chart(fig, width='stretch')
        
        # Framework distribution
        st.subheader("🏛️ Regulatory Framework Distribution")
        
        framework_counts = df['submission_type'].value_counts()
        
        fig = px.pie(
            values=framework_counts.values,
            names=framework_counts.index,
            title="Snapshots by Regulatory Framework"
        )
        st.plotly_chart(fig, width='stretch')
        
        # Compliance metrics
        st.subheader("✅ Compliance Metrics")
        
        compliance_data = []
        for snapshot in snapshots:
            compliance_metrics = snapshot.get('compliance_metrics', {})
            compliance_data.append({
                'submission_id': snapshot.get('submission_id'),
                'compliance_score': compliance_metrics.get('average_compliance_score', 0),
                'audit_ready': compliance_metrics.get('audit_ready_records', 0),
                'total_records': snapshot.get('total_records', 0),
                'compliance_rate': compliance_metrics.get('compliance_rate', 0)
            })
        
        if compliance_data:
            compliance_df = pd.DataFrame(compliance_data)
            
            col1, col2 = st.columns(2)
            
            with col1:
                fig = px.histogram(
                    compliance_df,
                    x='compliance_score',
                    title="Distribution of Compliance Scores",
                    nbins=20
                )
                st.plotly_chart(fig, width='stretch')
            
            with col2:
                fig = px.scatter(
                    compliance_df,
                    x='total_records',
                    y='compliance_rate',
                    title="Compliance Rate vs Total Records",
                    hover_data=['submission_id']
                )
                st.plotly_chart(fig, width='stretch')
        
    except requests.exceptions.RequestException as e:
        st.error(f"Error loading analytics data: {e}")
    except Exception as e:
        st.error(f"Error displaying analytics: {e}")


def show_audit_settings(api_base: str):
    """Show audit settings and configuration"""
    st.subheader("⚙️ Audit Settings")
    
    st.info("Audit settings and configuration options will be available here.")
    
    # Placeholder for future settings
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Notification Settings")
        st.checkbox("Email notifications for status changes", value=True)
        st.checkbox("Slack notifications for approvals", value=False)
        st.checkbox("Weekly compliance reports", value=True)
    
    with col2:
        st.markdown("### Workflow Settings")
        st.selectbox("Default approval workflow", ["Standard", "Fast-track", "Extended"])
        st.number_input("Auto-approval threshold (%)", min_value=0, max_value=100, value=95)
        st.number_input("Review timeout (days)", min_value=1, max_value=30, value=7)
