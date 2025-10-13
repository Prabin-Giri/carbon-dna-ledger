-- Enhanced Audit Snapshot Migration
-- Comprehensive audit trail system with immutable history and rich metadata

-- Create enum types
CREATE TYPE emission_scope AS ENUM (
    'scope_1', 'scope_2', 'scope_3'
);

CREATE TYPE activity_type AS ENUM (
    'stationary_combustion', 'mobile_combustion', 'process_emissions', 'fugitive_emissions',
    'purchased_electricity', 'purchased_steam', 'purchased_heating', 'purchased_cooling',
    'purchased_goods', 'capital_goods', 'fuel_energy_activities', 'transportation',
    'waste_disposal', 'business_travel', 'employee_commuting', 'leased_assets', 'investments'
);

CREATE TYPE data_source AS ENUM (
    'sensor', 'manual_input', 'api_integration', 'calculated', 'estimated', 'third_party'
);

CREATE TYPE calculation_method AS ENUM (
    'activity_based', 'spend_based', 'hybrid', 'direct_measurement'
);

CREATE TYPE approval_status AS ENUM (
    'draft', 'pending_review', 'under_review', 'approved', 'rejected', 'submitted', 'audited'
);

CREATE TYPE regulatory_framework AS ENUM (
    'epa', 'eu_ets', 'carb', 'tcfd', 'sec', 'cdp', 'gri', 'sasb', 'csrd'
);

-- Enhanced audit snapshots table
CREATE TABLE IF NOT EXISTS audit_snapshots_enhanced (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Submission details
    submission_id text NOT NULL UNIQUE,
    submission_type regulatory_framework NOT NULL,
    reporting_period_start date NOT NULL,
    reporting_period_end date NOT NULL,
    submission_date timestamptz NOT NULL,
    
    -- Hierarchical organization
    organization_id text,
    business_unit text,
    reporting_entity text,
    
    -- Cryptographic integrity
    merkle_root_hash text NOT NULL,
    total_records int NOT NULL,
    total_emissions_kgco2e numeric(20,6) NOT NULL,
    
    -- Scope breakdown
    scope_1_emissions numeric(20,6) DEFAULT 0,
    scope_2_emissions numeric(20,6) DEFAULT 0,
    scope_3_emissions numeric(20,6) DEFAULT 0,
    
    -- Compliance metrics
    average_compliance_score numeric(5,2) DEFAULT 0.0,
    audit_ready_records int DEFAULT 0,
    non_compliant_records int DEFAULT 0,
    compliance_flags jsonb DEFAULT '[]'::jsonb,
    
    -- Quality metrics
    average_uncertainty numeric(5,2),
    data_quality_score numeric(5,2),
    
    -- Approval workflow
    approval_status approval_status DEFAULT 'draft',
    workflow_stage text DEFAULT 'data_collection',
    
    -- Multi-level sign-offs
    data_collector text,
    data_collector_timestamp timestamptz,
    reviewer text,
    reviewer_timestamp timestamptz,
    approver text,
    approver_timestamp timestamptz,
    auditor text,
    auditor_timestamp timestamptz,
    
    -- Regulatory submission
    regulatory_submission_id text,
    submission_status text DEFAULT 'draft',
    submission_confirmation text,
    regulatory_deadline date,
    
    -- Generated reports and exports
    pdf_report_path text,
    pdf_report_hash text,
    json_data_path text,
    json_data_hash text,
    excel_export_path text,
    excel_export_hash text,
    
    -- Regulatory framework specific data
    framework_specific_data jsonb DEFAULT '{}'::jsonb,
    
    -- Metadata
    description text,
    tags jsonb DEFAULT '[]'::jsonb,
    custom_attributes jsonb DEFAULT '{}'::jsonb,
    
    -- Immutable audit trail
    created_by text NOT NULL,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

-- Audit snapshot entries table
CREATE TABLE IF NOT EXISTS audit_snapshot_entries (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Parent snapshot reference
    snapshot_id uuid NOT NULL REFERENCES audit_snapshots_enhanced(id) ON DELETE CASCADE,
    
    -- Timestamped record
    measurement_timestamp timestamptz NOT NULL,
    created_timestamp timestamptz DEFAULT now(),
    
    -- Scope and source categorization
    emission_scope emission_scope NOT NULL,
    activity_type activity_type NOT NULL,
    business_unit text,
    facility_id text,
    location text,
    
    -- Emission data
    activity_data numeric(20,6) NOT NULL,
    activity_unit text NOT NULL,
    emissions_kgco2e numeric(20,6) NOT NULL,
    
    -- Data provenance
    data_source data_source NOT NULL,
    source_system text,
    source_user text,
    source_document text,
    
    -- Emission factors and methodologies
    emission_factor numeric(20,6) NOT NULL,
    emission_factor_source text NOT NULL,
    emission_factor_version text,
    calculation_method calculation_method NOT NULL,
    calculation_formula text,
    
    -- Quality and uncertainty
    uncertainty_percentage numeric(5,2),
    quality_score numeric(5,2),
    data_quality_flags jsonb DEFAULT '[]'::jsonb,
    
    -- Approval workflow
    approval_status approval_status DEFAULT 'draft',
    reviewed_by text,
    review_timestamp timestamptz,
    review_notes text,
    approved_by text,
    approval_timestamp timestamptz,
    
    -- Evidence and attachments
    evidence_files jsonb DEFAULT '[]'::jsonb,
    iot_device_ids jsonb DEFAULT '[]'::jsonb,
    external_system_refs jsonb DEFAULT '[]'::jsonb,
    
    -- Metadata
    tags jsonb DEFAULT '[]'::jsonb,
    custom_attributes jsonb DEFAULT '{}'::jsonb,
    notes text,
    
    -- Immutable audit trail
    created_by text NOT NULL,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

-- Audit log entries table (immutable event log)
CREATE TABLE IF NOT EXISTS audit_log_entries (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- References
    snapshot_id uuid REFERENCES audit_snapshots_enhanced(id) ON DELETE CASCADE,
    snapshot_entry_id uuid REFERENCES audit_snapshot_entries(id) ON DELETE CASCADE,
    
    -- Event details
    event_type text NOT NULL,
    event_timestamp timestamptz DEFAULT now(),
    event_description text NOT NULL,
    
    -- Actor information
    actor_id text NOT NULL,
    actor_type text NOT NULL,
    actor_role text,
    
    -- Change details
    old_values jsonb,
    new_values jsonb,
    changed_fields jsonb,
    
    -- Context
    ip_address text,
    user_agent text,
    session_id text,
    
    -- Additional metadata
    notes text,
    tags jsonb DEFAULT '[]'::jsonb
);

-- Emission factor registry table
CREATE TABLE IF NOT EXISTS emission_factor_registry (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Factor identification
    factor_name text NOT NULL,
    factor_code text NOT NULL,
    version text NOT NULL,
    
    -- Factor details
    emission_factor numeric(20,6) NOT NULL,
    unit text NOT NULL,
    co2_factor numeric(20,6) NOT NULL,
    ch4_factor numeric(20,6) DEFAULT 0,
    n2o_factor numeric(20,6) DEFAULT 0,
    
    -- Source information
    source_organization text NOT NULL,
    source_document text,
    source_url text,
    publication_date date,
    
    -- Applicability
    emission_scope emission_scope NOT NULL,
    activity_type activity_type NOT NULL,
    applicable_regions jsonb DEFAULT '[]'::jsonb,
    applicable_industries jsonb DEFAULT '[]'::jsonb,
    
    -- Quality and uncertainty
    uncertainty_percentage numeric(5,2),
    quality_rating text,
    
    -- Status
    is_active boolean DEFAULT true,
    is_default boolean DEFAULT false,
    
    -- Metadata
    description text,
    notes text,
    
    -- Audit trail
    created_by text NOT NULL,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now(),
    
    -- Unique constraint
    UNIQUE(factor_code, version)
);

-- Evidence files table
CREATE TABLE IF NOT EXISTS evidence_files (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- File details
    filename text NOT NULL,
    original_filename text NOT NULL,
    file_path text NOT NULL,
    file_size int NOT NULL,
    mime_type text NOT NULL,
    file_hash text NOT NULL,
    
    -- References
    snapshot_id uuid REFERENCES audit_snapshots_enhanced(id) ON DELETE CASCADE,
    snapshot_entry_id uuid REFERENCES audit_snapshot_entries(id) ON DELETE CASCADE,
    
    -- File metadata
    upload_timestamp timestamptz DEFAULT now(),
    uploaded_by text NOT NULL,
    file_description text,
    file_category text,
    
    -- Processing status
    is_processed boolean DEFAULT false,
    processing_notes text,
    
    -- Access control
    is_public boolean DEFAULT false,
    access_level text DEFAULT 'restricted',
    
    -- Audit trail
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_audit_snapshots_enhanced_submission_id ON audit_snapshots_enhanced (submission_id);
CREATE INDEX IF NOT EXISTS idx_audit_snapshots_enhanced_type ON audit_snapshots_enhanced (submission_type);
CREATE INDEX IF NOT EXISTS idx_audit_snapshots_enhanced_period ON audit_snapshots_enhanced (reporting_period_start, reporting_period_end);
CREATE INDEX IF NOT EXISTS idx_audit_snapshots_enhanced_status ON audit_snapshots_enhanced (approval_status);
CREATE INDEX IF NOT EXISTS idx_audit_snapshots_enhanced_created_at ON audit_snapshots_enhanced (created_at);
CREATE INDEX IF NOT EXISTS idx_audit_snapshots_enhanced_organization ON audit_snapshots_enhanced (organization_id);

CREATE INDEX IF NOT EXISTS idx_audit_entries_snapshot_id ON audit_snapshot_entries (snapshot_id);
CREATE INDEX IF NOT EXISTS idx_audit_entries_scope ON audit_snapshot_entries (emission_scope);
CREATE INDEX IF NOT EXISTS idx_audit_entries_timestamp ON audit_snapshot_entries (measurement_timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_entries_status ON audit_snapshot_entries (approval_status);
CREATE INDEX IF NOT EXISTS idx_audit_entries_business_unit ON audit_snapshot_entries (business_unit);

CREATE INDEX IF NOT EXISTS idx_audit_logs_snapshot_id ON audit_log_entries (snapshot_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_entry_id ON audit_log_entries (snapshot_entry_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_event_type ON audit_log_entries (event_type);
CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_log_entries (event_timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_logs_actor ON audit_log_entries (actor_id);

CREATE INDEX IF NOT EXISTS idx_emission_factors_code ON emission_factor_registry (factor_code);
CREATE INDEX IF NOT EXISTS idx_emission_factors_scope ON emission_factor_registry (emission_scope);
CREATE INDEX IF NOT EXISTS idx_emission_factors_activity ON emission_factor_registry (activity_type);
CREATE INDEX IF NOT EXISTS idx_emission_factors_source ON emission_factor_registry (source_organization);

CREATE INDEX IF NOT EXISTS idx_evidence_files_snapshot_id ON evidence_files (snapshot_id);
CREATE INDEX IF NOT EXISTS idx_evidence_files_entry_id ON evidence_files (snapshot_entry_id);
CREATE INDEX IF NOT EXISTS idx_evidence_files_hash ON evidence_files (file_hash);
CREATE INDEX IF NOT EXISTS idx_evidence_files_uploaded_by ON evidence_files (uploaded_by);

-- Add comments for documentation
COMMENT ON TABLE audit_snapshots_enhanced IS 'Enhanced audit snapshots with comprehensive metadata and immutable history';
COMMENT ON TABLE audit_snapshot_entries IS 'Individual audit snapshot entries with full provenance tracking';
COMMENT ON TABLE audit_log_entries IS 'Immutable audit log for all changes and actions (event-sourced)';
COMMENT ON TABLE emission_factor_registry IS 'Registry of emission factors with versioning and source tracking';
COMMENT ON TABLE evidence_files IS 'Evidence files and attachments for audit snapshots';

-- Insert sample emission factors
INSERT INTO emission_factor_registry (
    factor_name, factor_code, version, emission_factor, unit, co2_factor,
    source_organization, emission_scope, activity_type, is_default, created_by
) VALUES 
    ('Natural Gas Combustion', 'NG_COMB', '2023.1', 0.20244, 'kg CO2e/m3', 0.20244,
     'EPA', 'scope_1', 'stationary_combustion', true, 'system'),
    ('Electricity Grid Average', 'ELEC_GRID', '2023.1', 0.000408, 'kg CO2e/kWh', 0.000408,
     'EPA', 'scope_2', 'purchased_electricity', true, 'system'),
    ('Gasoline Combustion', 'GASOLINE', '2023.1', 2.31, 'kg CO2e/liter', 2.31,
     'EPA', 'scope_1', 'mobile_combustion', true, 'system'),
    ('Diesel Combustion', 'DIESEL', '2023.1', 2.68, 'kg CO2e/liter', 2.68,
     'EPA', 'scope_1', 'mobile_combustion', true, 'system'),
    ('Business Travel - Air', 'AIR_TRAVEL', '2023.1', 0.255, 'kg CO2e/km', 0.255,
     'GHG Protocol', 'scope_3', 'business_travel', true, 'system')
ON CONFLICT (factor_code, version) DO NOTHING;

-- Create views for common queries
CREATE OR REPLACE VIEW audit_snapshot_summary AS
SELECT 
    s.id,
    s.submission_id,
    s.submission_type,
    s.reporting_period_start,
    s.reporting_period_end,
    s.total_records,
    s.total_emissions_kgco2e,
    s.scope_1_emissions,
    s.scope_2_emissions,
    s.scope_3_emissions,
    s.approval_status,
    s.workflow_stage,
    s.created_at,
    s.created_by,
    COUNT(e.id) as entry_count,
    AVG(e.quality_score) as avg_quality_score
FROM audit_snapshots_enhanced s
LEFT JOIN audit_snapshot_entries e ON s.id = e.snapshot_id
GROUP BY s.id, s.submission_id, s.submission_type, s.reporting_period_start, 
         s.reporting_period_end, s.total_records, s.total_emissions_kgco2e,
         s.scope_1_emissions, s.scope_2_emissions, s.scope_3_emissions,
         s.approval_status, s.workflow_stage, s.created_at, s.created_by;

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_audit_snapshots_enhanced_updated_at 
    BEFORE UPDATE ON audit_snapshots_enhanced 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_audit_snapshot_entries_updated_at 
    BEFORE UPDATE ON audit_snapshot_entries 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_emission_factor_registry_updated_at 
    BEFORE UPDATE ON emission_factor_registry 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_evidence_files_updated_at 
    BEFORE UPDATE ON evidence_files 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Grant permissions (adjust as needed for your setup)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO your_app_user;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO your_app_user;

RAISE NOTICE 'Enhanced audit snapshot tables created successfully';
