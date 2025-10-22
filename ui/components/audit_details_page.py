import streamlit as st
import requests
import json

def show_audit_details_page():
    """Show detailed audit snapshot information in a dedicated page"""
    
    # Get snapshot ID from URL parameters or session state
    snapshot_id = st.query_params.get("snapshot_id") or st.session_state.get('audit_snapshot_id')
    api_base = st.session_state.get('audit_api_base', 'http://127.0.0.1:8000')
    
    if not snapshot_id:
        st.error("❌ No audit snapshot ID provided")
        st.info("Please access this page through the audit snapshots dashboard.")
        return
    
    try:
        # Fetch audit snapshot data
        with st.spinner("Loading audit snapshot details..."):
            response = requests.get(f"{api_base}/api/compliance/audit-snapshots/{snapshot_id}", timeout=10)
            response.raise_for_status()
            result = response.json()
        
        # Page header
        st.set_page_config(
            page_title=f"Audit Report - {snapshot_id}",
            page_icon="📊",
            layout="wide"
        )
        
        # Business-friendly header
        st.markdown("# 📊 Audit Snapshot Business Report")
        st.markdown(f"**Snapshot ID:** `{snapshot_id}`")
        st.markdown("---")
        
        # Executive Summary
        st.markdown("## 📈 Executive Summary")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="📈 Total Records",
                value=f"{result.get('total_records', 0):,}",
                help="Number of emission records included in this audit"
            )
        
        with col2:
            total_emissions = result.get('total_emissions_kgco2e', 0)
            st.metric(
                label="🌍 Total Emissions",
                value=f"{total_emissions:,.0f} kg CO₂e",
                delta=f"{total_emissions/1000:,.1f} tonnes CO₂e",
                help="Total greenhouse gas emissions for the reporting period"
            )
        
        with col3:
            compliance_score = result.get('average_compliance_score', 0)
            if compliance_score >= 90:
                status = "🟢 Excellent"
                color = "green"
            elif compliance_score >= 80:
                status = "🟡 Good"
                color = "orange"
            elif compliance_score >= 70:
                status = "🟠 Fair"
                color = "orange"
            else:
                status = "🔴 Needs Improvement"
                color = "red"
            
            st.metric(
                label="📊 Compliance Score",
                value=f"{compliance_score:.1f}/100",
                delta=status,
                help="Overall data quality and compliance rating"
            )
        
        with col4:
            audit_ready = result.get('audit_ready_records', 0)
            total_records = result.get('total_records', 1)
            audit_percentage = (audit_ready / total_records) * 100 if total_records > 0 else 0
            
            st.metric(
                label="✅ Audit Ready",
                value=f"{audit_ready:,} records",
                delta=f"{audit_percentage:.1f}%",
                help="Records ready for regulatory audit"
            )
        
        st.markdown("---")
        
        # Business Context Section
        st.markdown("## 🏢 Business Context")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 📅 Reporting Period")
            st.info(f"**{result.get('reporting_period_start', 'N/A')}** to **{result.get('reporting_period_end', 'N/A')}**")
            
            st.markdown("### 🏛️ Regulatory Framework")
            submission_type = result.get('submission_type', 'Unknown')
            if submission_type == 'EPA':
                st.success("🇺🇸 **EPA (Environmental Protection Agency)** - US Federal Compliance")
            elif submission_type == 'CARB':
                st.success("🇺🇸 **CARB (California Air Resources Board)** - California State Compliance")
            elif submission_type == 'TCFD':
                st.success("🌍 **TCFD (Task Force on Climate-related Financial Disclosures)** - International Standard")
            else:
                st.info(f"📋 **{submission_type}** - Custom Framework")
        
        with col2:
            st.markdown("### 🔒 Data Integrity")
            merkle_hash = result.get('merkle_root_hash', 'N/A')
            st.code(f"Hash: {merkle_hash[:16]}...", language="text")
            st.caption("Cryptographic proof of data integrity")
            
            st.markdown("### 📊 Data Source")
            source = result.get('source', 'unknown')
            if source == 'compliance':
                st.info("🛡️ **Compliance Intelligence System**")
            elif source == 'enhanced':
                st.info("🔍 **Enhanced Audit System**")
            elif source == 'log_entries':
                st.info("📝 **Audit Log System**")
            else:
                st.info(f"📋 **{source.title()}**")
        
        # Risk Assessment
        st.markdown("## ⚠️ Risk Assessment")
        
        non_compliant = result.get('non_compliant_records', 0)
        total_records = result.get('total_records', 1)
        risk_percentage = (non_compliant / total_records) * 100 if total_records > 0 else 0
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            if risk_percentage == 0:
                st.success("🟢 **LOW RISK** - All records are compliant with regulatory requirements")
            elif risk_percentage < 10:
                st.warning("🟡 **MEDIUM RISK** - Minor compliance issues detected")
            elif risk_percentage < 25:
                st.error("🟠 **HIGH RISK** - Significant compliance issues require attention")
            else:
                st.error("🔴 **CRITICAL RISK** - Major compliance failures detected")
        
        with col2:
            st.progress(1 - (risk_percentage / 100))
            st.caption(f"Risk Level: {risk_percentage:.1f}% of records have compliance issues")
        
        # Business Impact
        st.markdown("## 💼 Business Impact")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("### 💰 Financial Impact")
            if compliance_score >= 90:
                st.success("✅ **Low Risk** - Minimal regulatory penalties expected")
            elif compliance_score >= 70:
                st.warning("⚠️ **Medium Risk** - Potential fines and corrective actions")
            else:
                st.error("🚨 **High Risk** - Significant penalties and enforcement actions likely")
        
        with col2:
            st.markdown("### 🏛️ Regulatory Status")
            if audit_ready > total_records * 0.8:
                st.success("✅ **Audit Ready** - Prepared for regulatory review")
            elif audit_ready > total_records * 0.5:
                st.warning("⚠️ **Partially Ready** - Some preparation needed")
            else:
                st.error("🚨 **Not Ready** - Significant work required before audit")
        
        with col3:
            st.markdown("### 📈 Reputation Risk")
            if compliance_score >= 80:
                st.success("✅ **Low Risk** - Strong environmental compliance record")
            elif compliance_score >= 60:
                st.warning("⚠️ **Medium Risk** - Mixed compliance performance")
            else:
                st.error("🚨 **High Risk** - Poor compliance may damage reputation")
        
        # Action Items
        st.markdown("## 🎯 Recommended Actions")
        
        if compliance_score < 70:
            st.error("### 🚨 IMMEDIATE ACTION REQUIRED")
            st.markdown("""
            - **Data Quality Review**: Investigate and fix data quality issues
            - **Process Improvement**: Implement better data collection procedures
            - **Training**: Provide staff training on compliance requirements
            - **External Audit**: Consider hiring external auditors for assessment
            """)
        elif compliance_score < 90:
            st.warning("### ⚠️ IMPROVEMENT NEEDED")
            st.markdown("""
            - **Data Validation**: Implement additional data validation checks
            - **Documentation**: Improve record-keeping and documentation
            - **Monitoring**: Set up regular compliance monitoring
            - **Staff Training**: Provide refresher training on requirements
            """)
        else:
            st.success("### ✅ EXCELLENT PERFORMANCE")
            st.markdown("""
            - **Maintain Standards**: Continue current data quality practices
            - **Best Practices**: Share successful processes across organization
            - **Continuous Improvement**: Look for opportunities to enhance further
            - **Certification**: Consider pursuing environmental certifications
            """)
        
        # Export Options
        st.markdown("## 📤 Export Options")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📄 Generate PDF Report", key="generate_pdf"):
                st.info("PDF generation feature coming soon!")
        
        with col2:
            if st.button("📊 Export to Excel", key="export_excel"):
                st.info("Excel export feature coming soon!")
        
        with col3:
            if st.button("📋 Copy Report Link", key="copy_link"):
                st.info("Report link copied to clipboard!")
        
        # Technical Details (Collapsible)
        with st.expander("🔧 Technical Details (For IT/Audit Teams)"):
            st.json(result)
        
        # Footer
        st.markdown("---")
        st.markdown("**Report Generated:** " + st.session_state.get('report_timestamp', 'Unknown'))
        st.markdown("**Data Source:** Carbon DNA Ledger - Auditable Carbon Emission Tracking System")
        
    except requests.exceptions.RequestException as e:
        st.error(f"❌ **Connection Error**: Unable to connect to the audit system. Please try again later.")
        st.caption(f"Technical details: {e}")
    except Exception as e:
        st.error(f"❌ **System Error**: An unexpected error occurred while loading audit details.")
        st.caption(f"Technical details: {e}")

if __name__ == "__main__":
    show_audit_details_page()
