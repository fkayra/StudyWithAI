# Database Migration Instructions

## Coverage Score Migration (2025-11-11)

### Issue
The `coverage_score` column was added to the `SummaryQuality` model but the database was not migrated. This causes an error:
```
psycopg2.errors.UndefinedColumn: column "coverage_score" of relation "summary_quality" does not exist
```

### Solution

#### Option 1: Run SQL Migration (Recommended for Production)

**For PostgreSQL (Railway/Supabase):**
```bash
# Connect to your database
psql $DATABASE_URL

# Run the migration
\i backend/migrations/add_coverage_score.sql
```

**Or use Railway CLI:**
```bash
railway run psql $DATABASE_URL < backend/migrations/add_coverage_score.sql
```

**Or manually:**
```sql
ALTER TABLE summary_quality ADD COLUMN IF NOT EXISTS coverage_score FLOAT;
```

#### Option 2: Temporary Fix (Current Status)

The `coverage_score` field is temporarily commented out in:
- `backend/app/models/telemetry.py` (line 35)
- `backend/app/services/telemetry.py` (line 58)

This allows the application to run without errors, but coverage scores won't be tracked.

#### After Migration

Once the database migration is complete:

1. Uncomment `coverage_score` in `backend/app/models/telemetry.py`:
   ```python
   coverage_score = Column(Float, nullable=True)  # Theme coverage ratio
   ```

2. Uncomment `coverage_score` in `backend/app/services/telemetry.py`:
   ```python
   coverage_score=coverage_score,
   ```

3. Redeploy the application

### Verification

To verify the migration was successful:

**PostgreSQL:**
```sql
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'summary_quality' 
  AND column_name = 'coverage_score';
```

**SQLite:**
```sql
PRAGMA table_info(summary_quality);
```

You should see `coverage_score` with type `FLOAT` (PostgreSQL) or `REAL` (SQLite).

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
