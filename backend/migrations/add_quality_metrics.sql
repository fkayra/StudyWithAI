-- Migration: Add comprehensive quality metrics columns to summary_quality table
-- Date: 2025-11-11
-- Purpose: Track detailed quality metrics for evrensel quality system

-- For PostgreSQL (Railway/Supabase)
ALTER TABLE summary_quality ADD COLUMN IF NOT EXISTS coverage_score FLOAT;
ALTER TABLE summary_quality ADD COLUMN IF NOT EXISTS numeric_density FLOAT;
ALTER TABLE summary_quality ADD COLUMN IF NOT EXISTS formula_completeness FLOAT;
ALTER TABLE summary_quality ADD COLUMN IF NOT EXISTS citation_depth FLOAT;
ALTER TABLE summary_quality ADD COLUMN IF NOT EXISTS readability_score FLOAT;
ALTER TABLE summary_quality ADD COLUMN IF NOT EXISTS is_final_ready INTEGER DEFAULT 0;

-- For SQLite (development)
-- ALTER TABLE summary_quality ADD COLUMN coverage_score REAL;
-- ALTER TABLE summary_quality ADD COLUMN numeric_density REAL;
-- ALTER TABLE summary_quality ADD COLUMN formula_completeness REAL;
-- ALTER TABLE summary_quality ADD COLUMN citation_depth REAL;
-- ALTER TABLE summary_quality ADD COLUMN readability_score REAL;
-- ALTER TABLE summary_quality ADD COLUMN is_final_ready INTEGER DEFAULT 0;

-- Verify migration
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'summary_quality' 
  AND column_name IN ('coverage_score', 'numeric_density', 'formula_completeness', 
                       'citation_depth', 'readability_score', 'is_final_ready');

-- After running this migration, uncomment all quality metrics in:
-- - backend/app/models/telemetry.py (lines 35-40)
-- - backend/app/services/telemetry.py (lines 58-63)
