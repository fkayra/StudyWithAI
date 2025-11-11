# Database Migration Instructions

## Comprehensive Quality Metrics Migration (2025-11-11)

### Issue
Multiple quality metric columns were added to the `SummaryQuality` model but the database was not migrated. This causes errors:
```
psycopg2.errors.UndefinedColumn: column "coverage_score" of relation "summary_quality" does not exist
psycopg2.errors.UndefinedColumn: column "numeric_density" of relation "summary_quality" does not exist
```

**Missing columns:**
- `coverage_score` - Theme coverage ratio
- `numeric_density` - % examples with numbers
- `formula_completeness` - % formulas with variables + examples
- `citation_depth` - % citations with page/section details
- `readability_score` - Sentence density score
- `is_final_ready` - Binary flag for quality threshold

### Solution

#### Option 1: Run SQL Migration (Recommended for Production)

**For PostgreSQL (Railway/Supabase):**
```bash
# Connect to your database
psql $DATABASE_URL

# Run the migration
\i backend/migrations/add_quality_metrics.sql
```

**Or use Railway CLI:**
```bash
railway run psql $DATABASE_URL < backend/migrations/add_quality_metrics.sql
```

**Or manually:**
```sql
ALTER TABLE summary_quality ADD COLUMN IF NOT EXISTS coverage_score FLOAT;
ALTER TABLE summary_quality ADD COLUMN IF NOT EXISTS numeric_density FLOAT;
ALTER TABLE summary_quality ADD COLUMN IF NOT EXISTS formula_completeness FLOAT;
ALTER TABLE summary_quality ADD COLUMN IF NOT EXISTS citation_depth FLOAT;
ALTER TABLE summary_quality ADD COLUMN IF NOT EXISTS readability_score FLOAT;
ALTER TABLE summary_quality ADD COLUMN IF NOT EXISTS is_final_ready INTEGER DEFAULT 0;
```

#### Option 2: Temporary Fix (Current Status)

All quality metric fields are temporarily commented out in:
- `backend/app/models/telemetry.py` (lines 35-40)
- `backend/app/services/telemetry.py` (lines 58-64)

This allows the application to run without errors, but detailed quality metrics won't be tracked.

#### After Migration

Once the database migration is complete:

1. Uncomment all quality metrics in `backend/app/models/telemetry.py`:
   ```python
   coverage_score = Column(Float, nullable=True)
   numeric_density = Column(Float, nullable=True)
   formula_completeness = Column(Float, nullable=True)
   citation_depth = Column(Float, nullable=True)
   readability_score = Column(Float, nullable=True)
   is_final_ready = Column(Integer, nullable=True)
   ```

2. Uncomment all fields in `backend/app/services/telemetry.py`:
   ```python
   coverage_score=coverage_score,
   numeric_density=numeric_density,
   formula_completeness=formula_completeness,
   citation_depth=citation_depth,
   readability_score=readability_score,
   is_final_ready=1 if is_final_ready else 0
   ```

3. Redeploy the application

### Verification

To verify the migration was successful:

**PostgreSQL:**
```sql
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'summary_quality' 
  AND column_name IN ('coverage_score', 'numeric_density', 'formula_completeness', 
                       'citation_depth', 'readability_score', 'is_final_ready');
```

**SQLite:**
```sql
PRAGMA table_info(summary_quality);
```

You should see all 6 columns with appropriate types:
- `coverage_score`: FLOAT/REAL
- `numeric_density`: FLOAT/REAL
- `formula_completeness`: FLOAT/REAL
- `citation_depth`: FLOAT/REAL
- `readability_score`: FLOAT/REAL
- `is_final_ready`: INTEGER

### Future Migrations

To avoid this issue in the future:
1. Always create migration scripts when modifying models
2. Test migrations in development before deploying to production
3. Consider using Alembic for automated migrations:
   ```bash
   pip install alembic
   alembic init migrations
   alembic revision --autogenerate -m "Add coverage_score"
   alembic upgrade head
   ```
