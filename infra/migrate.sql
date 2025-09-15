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

-- Add comments for documentation
COMMENT ON TABLE suppliers IS 'Master table of carbon emission suppliers/organizations';
COMMENT ON TABLE emission_factors IS 'Catalog of emission factors from various sources (IPCC, regional grids, etc.)';
COMMENT ON TABLE carbon_events IS 'Main hash-chained ledger of carbon emission events with DNA receipts';
COMMENT ON TABLE merkle_roots IS 'Daily Merkle root anchoring for blockchain-style integrity';

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

-- Insert success message
DO $$
BEGIN
    RAISE NOTICE 'Carbon DNA Ledger database schema created successfully!';
    RAISE NOTICE 'Tables created: suppliers, emission_factors, carbon_events, merkle_roots';
    RAISE NOTICE 'Indexes and view created for optimal performance';
    RAISE NOTICE 'Ready for seed data insertion';
END $$;
