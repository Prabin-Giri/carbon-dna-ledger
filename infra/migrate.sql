-- Carbon DNA Ledger Database Migration Script
-- Run this in your Supabase SQL Editor to set up the database schema

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create suppliers table
CREATE TABLE IF NOT EXISTS suppliers(
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,
  sector text,
  region text,
  data_quality_score int DEFAULT 50,
  created_at timestamptz DEFAULT now()
);

-- Create emission_factors table
CREATE TABLE IF NOT EXISTS emission_factors(
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source text NOT NULL,
  description text,
  scope smallint CHECK (scope in (1,2,3)),
  activity_category text,
  region text,
  value numeric NOT NULL,
  unit text NOT NULL,
  version text,
  uncertainty_pct numeric DEFAULT 0,
  factor_metadata jsonb DEFAULT '{}'::jsonb
);

-- Create carbon_events table (main hash-chained ledger)
CREATE TABLE IF NOT EXISTS carbon_events(
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  supplier_id uuid REFERENCES suppliers(id),
  occurred_at timestamptz NOT NULL,
  activity text NOT NULL,
  scope smallint CHECK (scope in (1,2,3)) NOT NULL,
  inputs jsonb NOT NULL,
  factor_id uuid REFERENCES emission_factors(id),
  method text NOT NULL,
  result_kgco2e numeric NOT NULL,
  uncertainty_pct numeric DEFAULT 0,
  source_doc jsonb NOT NULL,          -- [{doc_id, page, field, raw_text, bbox?}]
  quality_flags text[],
  fingerprint jsonb NOT NULL,         -- normalized tokens for explain
  row_hash text NOT NULL,
  prev_hash text,
  created_at timestamptz DEFAULT now()
);

-- Create merkle_roots table for daily hash anchoring
CREATE TABLE IF NOT EXISTS merkle_roots(
  id bigserial PRIMARY KEY,
  period_date date NOT NULL,
  root_hash text NOT NULL,
  count_events int NOT NULL,
  created_at timestamptz DEFAULT now()
);

-- Create emission_records table (simplified view for UI)
CREATE TABLE IF NOT EXISTS emission_records(
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  record_id text,
  external_id text,
  contract_id text,
  instrument_type text,
  supplier_name text,
  org_unit text,
  facility_id text,
  country_code text,
  date_start date,
  date_end date,
  date date,
  scope smallint,
  category text,
  subcategory text,
  activity_type text,
  activity_amount numeric,
  activity_unit text,
  distance_km numeric,
  tonnage numeric,
  fuel_type text,
  region text,
  kwh numeric,
  result_kgco2e numeric,
  method text,
  uncertainty_pct numeric,
  data_quality_score numeric,
  description text,
  -- Additional fields for comprehensive emission tracking
  vehicle_type text,
  mass_tonnes numeric,
  energy_kwh numeric,
  grid_region text,
  market_basis text,
  renewable_percent numeric,
  -- Emission factor details
  emission_factor_value numeric,
  emission_factor_unit text,
  ef_source text,
  ef_ref_code text,
  ef_version text,
  gwp_set text,
  -- GHG Protocol results
  co2_kg numeric,
  ch4_kg numeric,
  n2o_kg numeric,
  co2e_kg numeric,
  -- Methodology and quality
  methodology text,
  verification_status text,
  -- Attachments
  attachment_url text,
  notes text,
  -- Simple CSV financial fields
  amount numeric,
  currency text,
  ef_factor_per_currency numeric,
  emissions_kgco2e numeric,
  project_code text,
  -- Calculation provenance
  calculation_method text,
  calculation_metadata jsonb DEFAULT '{}'::jsonb,
  -- Hash chain
  previous_hash text,
  record_hash text,
  salt text,
  -- Raw row storage
  raw_row jsonb DEFAULT '{}'::jsonb,
  -- AI Classification fields
  ai_classified text DEFAULT 'false',
  confidence_score numeric DEFAULT 0.0,
  needs_human_review boolean DEFAULT false,
  ai_model_used text,
  classification_metadata jsonb DEFAULT '{}'::jsonb,
  -- Climate TRACE taxonomy fields
  ct_sector text,
  ct_subsector text,
  ct_asset_type text,
  ct_asset_id text,
  ct_country_code text,
  ct_region text,
  -- Compliance Integrity Engine fields
  compliance_score numeric(5,2) DEFAULT 0.0,
  factor_source_quality numeric(5,2) DEFAULT 0.0,
  metadata_completeness numeric(5,2) DEFAULT 0.0,
  data_entry_method_score numeric(5,2) DEFAULT 0.0,
  fingerprint_integrity numeric(5,2) DEFAULT 0.0,
  llm_confidence numeric(5,2) DEFAULT 0.0,
  compliance_flags jsonb DEFAULT '[]'::jsonb,
  audit_ready boolean DEFAULT FALSE,
  created_at timestamptz DEFAULT now()
);

-- Create carbon_opportunities table for Carbon Rewards Engine
CREATE TABLE IF NOT EXISTS carbon_opportunities(
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  emission_record_id uuid REFERENCES emission_records(id),
  opportunity_type text NOT NULL,
  program_name text NOT NULL,
  program_agency text,
  description text,
  emissions_reduced numeric,
  potential_value numeric,
  confidence_score numeric,
  deadline_date date,
  application_link text,
  specific_requirements text,
  next_steps text,
  is_active boolean DEFAULT true,
  created_at timestamptz DEFAULT now()
);

-- Create compliance_deadlines table for Carbon Rewards Engine
CREATE TABLE IF NOT EXISTS compliance_deadlines(
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  opportunity_id uuid REFERENCES carbon_opportunities(id),
  program_name text NOT NULL,
  deadline_type text NOT NULL,
  deadline_date date NOT NULL,
  timezone text DEFAULT 'UTC',
  reminder_days int DEFAULT 30,
  last_reminder_sent timestamptz,
  is_active boolean DEFAULT true,
  is_completed boolean DEFAULT false,
  completion_date timestamptz,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- Create application_templates table for Carbon Rewards Engine
CREATE TABLE IF NOT EXISTS application_templates(
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  opportunity_id uuid REFERENCES carbon_opportunities(id),
  template_name text NOT NULL,
  template_type text NOT NULL,
  form_data jsonb,
  required_documents text[],
  submission_instructions text,
  is_active boolean DEFAULT true,
  created_at timestamptz DEFAULT now()
);

-- Create ct_crosschecks table for Climate TRACE integration
CREATE TABLE IF NOT EXISTS ct_crosschecks(
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  -- Time period
  year int NOT NULL,
  month int NOT NULL CHECK (month >= 1 AND month <= 12),
  -- Climate TRACE data
  ct_sector text NOT NULL,
  ct_subsector text,
  ct_country_code text,
  ct_region text,
  -- Emissions comparison
  ct_emissions_kgco2e numeric(20,6),
  our_emissions_kgco2e numeric(20,6),
  delta_kgco2e numeric(20,6),
  delta_percentage numeric(8,4),
  -- Compliance status
  compliance_status text DEFAULT 'compliant' CHECK (compliance_status IN ('compliant', 'at_risk', 'non_compliant')),
  threshold_exceeded boolean DEFAULT false,
  threshold_percentage numeric(8,4) DEFAULT 10.0,
  -- Analysis metadata
  record_count int DEFAULT 0,
  confidence_score numeric(3,2) DEFAULT 0.0,
  data_quality_flags jsonb DEFAULT '[]'::jsonb,
  -- Remediation suggestions
  remediation_suggestions jsonb DEFAULT '[]'::jsonb,
  suggested_actions text,
  -- Status tracking
  is_acknowledged boolean DEFAULT false,
  acknowledged_by text,
  acknowledged_at timestamptz,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_events_fingerprint_activity ON carbon_events ((fingerprint->>'activity'));
CREATE INDEX IF NOT EXISTS idx_events_occurred_at ON carbon_events (occurred_at);
CREATE INDEX IF NOT EXISTS idx_events_inputs ON carbon_events USING gin (inputs);
CREATE INDEX IF NOT EXISTS idx_events_source_doc ON carbon_events USING gin (source_doc);
CREATE INDEX IF NOT EXISTS idx_events_supplier_id ON carbon_events (supplier_id);
CREATE INDEX IF NOT EXISTS idx_events_factor_id ON carbon_events (factor_id);
CREATE INDEX IF NOT EXISTS idx_events_scope ON carbon_events (scope);
CREATE INDEX IF NOT EXISTS idx_events_created_at ON carbon_events (created_at);

-- Create indexes for suppliers
CREATE INDEX IF NOT EXISTS idx_suppliers_name ON suppliers (name);
CREATE INDEX IF NOT EXISTS idx_suppliers_sector ON suppliers (sector);
CREATE INDEX IF NOT EXISTS idx_suppliers_region ON suppliers (region);

-- Create indexes for emission_factors
CREATE INDEX IF NOT EXISTS idx_factors_category ON emission_factors (activity_category);
CREATE INDEX IF NOT EXISTS idx_factors_scope ON emission_factors (scope);
CREATE INDEX IF NOT EXISTS idx_factors_region ON emission_factors (region);
CREATE INDEX IF NOT EXISTS idx_factors_source ON emission_factors (source);

-- Create indexes for merkle_roots
CREATE INDEX IF NOT EXISTS idx_merkle_period_date ON merkle_roots (period_date);
CREATE INDEX IF NOT EXISTS idx_merkle_created_at ON merkle_roots (created_at);

-- Create indexes for emission_records
CREATE INDEX IF NOT EXISTS idx_emission_records_supplier_name ON emission_records (supplier_name);
CREATE INDEX IF NOT EXISTS idx_emission_records_activity_type ON emission_records (activity_type);
CREATE INDEX IF NOT EXISTS idx_emission_records_scope ON emission_records (scope);
CREATE INDEX IF NOT EXISTS idx_emission_records_date ON emission_records (date);
CREATE INDEX IF NOT EXISTS idx_emission_records_external_id ON emission_records (external_id);

-- Create indexes for carbon_opportunities
CREATE INDEX IF NOT EXISTS idx_carbon_opportunities_type ON carbon_opportunities (opportunity_type);
CREATE INDEX IF NOT EXISTS idx_carbon_opportunities_program ON carbon_opportunities (program_name);
CREATE INDEX IF NOT EXISTS idx_carbon_opportunities_emission_record ON carbon_opportunities (emission_record_id);
CREATE INDEX IF NOT EXISTS idx_carbon_opportunities_active ON carbon_opportunities (is_active);

-- Create indexes for compliance_deadlines
CREATE INDEX IF NOT EXISTS idx_compliance_deadlines_opportunity ON compliance_deadlines (opportunity_id);
CREATE INDEX IF NOT EXISTS idx_compliance_deadlines_date ON compliance_deadlines (deadline_date);
CREATE INDEX IF NOT EXISTS idx_compliance_deadlines_active ON compliance_deadlines (is_active);
CREATE INDEX IF NOT EXISTS idx_compliance_deadlines_completed ON compliance_deadlines (is_completed);

-- Create indexes for application_templates
CREATE INDEX IF NOT EXISTS idx_application_templates_opportunity ON application_templates (opportunity_id);
CREATE INDEX IF NOT EXISTS idx_application_templates_type ON application_templates (template_type);
CREATE INDEX IF NOT EXISTS idx_application_templates_active ON application_templates (is_active);

-- Create indexes for ct_crosschecks
CREATE INDEX IF NOT EXISTS idx_ct_crosschecks_year_month ON ct_crosschecks (year, month);
CREATE INDEX IF NOT EXISTS idx_ct_crosschecks_sector ON ct_crosschecks (ct_sector);
CREATE INDEX IF NOT EXISTS idx_ct_crosschecks_subsector ON ct_crosschecks (ct_subsector);
CREATE INDEX IF NOT EXISTS idx_ct_crosschecks_compliance_status ON ct_crosschecks (compliance_status);
CREATE INDEX IF NOT EXISTS idx_ct_crosschecks_threshold_exceeded ON ct_crosschecks (threshold_exceeded);
CREATE INDEX IF NOT EXISTS idx_ct_crosschecks_acknowledged ON ct_crosschecks (is_acknowledged);
CREATE INDEX IF NOT EXISTS idx_ct_crosschecks_created_at ON ct_crosschecks (created_at);

-- Create indexes for emission_records new fields
CREATE INDEX IF NOT EXISTS idx_emission_records_ct_sector ON emission_records (ct_sector);
CREATE INDEX IF NOT EXISTS idx_emission_records_ct_subsector ON emission_records (ct_subsector);
CREATE INDEX IF NOT EXISTS idx_emission_records_ct_country ON emission_records (ct_country_code);
CREATE INDEX IF NOT EXISTS idx_emission_records_ai_classified ON emission_records (ai_classified);
CREATE INDEX IF NOT EXISTS idx_emission_records_needs_review ON emission_records (needs_human_review);
CREATE INDEX IF NOT EXISTS idx_emission_records_calculation_method ON emission_records (calculation_method);

-- Add comments for documentation
COMMENT ON TABLE suppliers IS 'Master table of carbon emission suppliers/organizations';
COMMENT ON TABLE emission_factors IS 'Catalog of emission factors from various sources (IPCC, regional grids, etc.)';
COMMENT ON TABLE carbon_events IS 'Main hash-chained ledger of carbon emission events with DNA receipts';
COMMENT ON TABLE merkle_roots IS 'Daily Merkle root anchoring for blockchain-style integrity';
COMMENT ON TABLE emission_records IS 'Comprehensive emission data table with AI classification and Climate TRACE mapping';
COMMENT ON TABLE carbon_opportunities IS 'Carbon offset and credit opportunities detected from emission data';
COMMENT ON TABLE compliance_deadlines IS 'Deadline tracking for carbon opportunity applications';
COMMENT ON TABLE application_templates IS 'Pre-filled application templates for carbon opportunities';
COMMENT ON TABLE ct_crosschecks IS 'Climate TRACE cross-check results for compliance verification';

COMMENT ON COLUMN carbon_events.fingerprint IS 'Normalized tokens for duplicate detection and explain queries';
COMMENT ON COLUMN carbon_events.row_hash IS 'SHA-256 hash of canonical event data for integrity chain';
COMMENT ON COLUMN carbon_events.prev_hash IS 'Previous event row_hash for blockchain-style chaining';
COMMENT ON COLUMN carbon_events.source_doc IS 'Provenance information linking back to source documents';

-- Optional: Create a view for easier querying of events with supplier/factor details
CREATE OR REPLACE VIEW carbon_events_detailed AS
SELECT 
    ce.id,
    ce.occurred_at,
    ce.activity,
    ce.scope,
    s.name as supplier_name,
    s.sector as supplier_sector,
    s.region as supplier_region,
    ce.inputs,
    ce.method,
    ce.result_kgco2e,
    ce.uncertainty_pct,
    ef.source as factor_source,
    ef.description as factor_description,
    ef.value as factor_value,
    ef.unit as factor_unit,
    ef.version as factor_version,
    ce.quality_flags,
    ce.fingerprint,
    ce.row_hash,
    ce.prev_hash,
    ce.created_at
FROM carbon_events ce
LEFT JOIN suppliers s ON ce.supplier_id = s.id
LEFT JOIN emission_factors ef ON ce.factor_id = ef.id;

COMMENT ON VIEW carbon_events_detailed IS 'Detailed view of carbon events with joined supplier and emission factor information';

-- Create audit_snapshots table for Compliance Integrity Engine
CREATE TABLE IF NOT EXISTS audit_snapshots(
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  -- Submission details
  submission_id text NOT NULL UNIQUE,
  submission_type text NOT NULL,  -- 'EPA', 'EU_ETS', 'CARB', 'TCFD', 'SEC'
  reporting_period_start date NOT NULL,
  reporting_period_end date NOT NULL,
  submission_date timestamptz NOT NULL,
  -- Cryptographic integrity
  merkle_root_hash text NOT NULL,  -- Root hash of all included records
  total_records int NOT NULL,  -- Number of records in snapshot
  total_emissions_kgco2e numeric(20,6) NOT NULL,  -- Total emissions
  -- Compliance metrics
  average_compliance_score numeric(5,2) DEFAULT 0.0,
  audit_ready_records int DEFAULT 0,
  non_compliant_records int DEFAULT 0,
  compliance_flags jsonb DEFAULT '[]'::jsonb,
  -- Generated reports
  pdf_report_path text,  -- Path to generated PDF report
  pdf_report_hash text,  -- Hash of PDF for integrity verification
  json_data_path text,  -- Path to JSON data export
  json_data_hash text,  -- Hash of JSON data
  -- Regulatory submission
  regulatory_submission_id text,  -- External regulatory submission ID
  submission_status text DEFAULT 'draft',  -- 'draft', 'submitted', 'approved', 'rejected'
  submission_confirmation text,  -- Regulatory confirmation number
  -- Verification
  verified_by text,  -- Who verified the submission
  verification_date timestamptz,
  verification_notes text,
  -- Metadata
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- Create compliance_rules table for Compliance Integrity Engine
CREATE TABLE IF NOT EXISTS compliance_rules(
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  -- Rule identification
  rule_id text NOT NULL UNIQUE,
  framework text NOT NULL,  -- 'EPA', 'EU_ETS', 'CARB', 'TCFD', 'SEC'
  rule_name text NOT NULL,
  rule_description text,
  -- Rule conditions
  conditions jsonb NOT NULL,  -- JSON conditions for rule matching
  severity text DEFAULT 'medium',  -- 'low', 'medium', 'high', 'critical'
  auto_apply boolean DEFAULT TRUE,  -- Whether to auto-apply this rule
  -- Compliance requirements
  required_fields jsonb DEFAULT '[]'::jsonb,  -- Required fields for compliance
  validation_rules jsonb DEFAULT '[]'::jsonb,  -- Validation rules
  threshold_values jsonb DEFAULT '{}'::jsonb,  -- Threshold values for compliance
  -- Status
  is_active boolean DEFAULT TRUE,
  effective_date date,
  expiry_date date,
  -- Metadata
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- Create indexes for audit_snapshots
CREATE INDEX IF NOT EXISTS idx_audit_snapshots_submission_id ON audit_snapshots (submission_id);
CREATE INDEX IF NOT EXISTS idx_audit_snapshots_submission_type ON audit_snapshots (submission_type);
CREATE INDEX IF NOT EXISTS idx_audit_snapshots_period ON audit_snapshots (reporting_period_start, reporting_period_end);
CREATE INDEX IF NOT EXISTS idx_audit_snapshots_submission_date ON audit_snapshots (submission_date);
CREATE INDEX IF NOT EXISTS idx_audit_snapshots_status ON audit_snapshots (submission_status);
CREATE INDEX IF NOT EXISTS idx_audit_snapshots_created_at ON audit_snapshots (created_at);

-- Create indexes for compliance_rules
CREATE INDEX IF NOT EXISTS idx_compliance_rules_rule_id ON compliance_rules (rule_id);
CREATE INDEX IF NOT EXISTS idx_compliance_rules_framework ON compliance_rules (framework);
CREATE INDEX IF NOT EXISTS idx_compliance_rules_active ON compliance_rules (is_active);
CREATE INDEX IF NOT EXISTS idx_compliance_rules_severity ON compliance_rules (severity);
CREATE INDEX IF NOT EXISTS idx_compliance_rules_effective_date ON compliance_rules (effective_date);

-- Create indexes for compliance integrity fields in emission_records
CREATE INDEX IF NOT EXISTS idx_emission_records_compliance_score ON emission_records (compliance_score);
CREATE INDEX IF NOT EXISTS idx_emission_records_audit_ready ON emission_records (audit_ready);
CREATE INDEX IF NOT EXISTS idx_emission_records_factor_source_quality ON emission_records (factor_source_quality);
CREATE INDEX IF NOT EXISTS idx_emission_records_metadata_completeness ON emission_records (metadata_completeness);

-- Add table comments
COMMENT ON TABLE audit_snapshots IS 'Audit snapshots for regulatory submissions and compliance verification';
COMMENT ON TABLE compliance_rules IS 'Compliance rules for different regulatory frameworks';

-- Insert success message
DO $$
BEGIN
    RAISE NOTICE 'Carbon DNA Ledger database schema created successfully!';
    RAISE NOTICE 'Tables created: suppliers, emission_factors, carbon_events, merkle_roots, emission_records, carbon_opportunities, compliance_deadlines, application_templates, ct_crosschecks, audit_snapshots, compliance_rules';
    RAISE NOTICE 'Indexes and view created for optimal performance';
    RAISE NOTICE 'Carbon Rewards Engine tables included';
    RAISE NOTICE 'Climate TRACE integration tables included';
    RAISE NOTICE 'Compliance Integrity Engine tables included';
    RAISE NOTICE 'AI Classification and Climate TRACE mapping fields added to emission_records';
    RAISE NOTICE 'Compliance scoring and audit readiness fields added to emission_records';
    RAISE NOTICE 'Ready for seed data insertion';
END $$;
