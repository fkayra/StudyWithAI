-- Migration: Add coverage_score column to summary_quality table
-- Date: 2025-11-11
-- Purpose: Track theme coverage ratio in comprehensive quality metrics

-- For PostgreSQL
ALTER TABLE summary_quality ADD COLUMN IF NOT EXISTS coverage_score FLOAT;

-- For SQLite (use this if using SQLite in development)
-- ALTER TABLE summary_quality ADD COLUMN coverage_score REAL;

-- Verify migration
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'summary_quality' 
  AND column_name = 'coverage_score';

-- After running this migration, uncomment coverage_score in:
-- - backend/app/models/telemetry.py (line 35)
-- - backend/app/services/telemetry.py (line 58)
