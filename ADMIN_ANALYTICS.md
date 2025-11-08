# Admin Analytics & Tracking Features

## Overview

The admin panel now includes comprehensive tracking and analytics for:
- **Transaction History**: All Stripe payments and subscriptions
- **Token Usage**: OpenAI API token consumption tracking
- **Revenue Analytics**: Revenue, costs, and profitability metrics
- **User Analytics**: Detailed user information with payment and usage history

## Features

### 1. Transaction Tracking

**Database Table: `transactions`**
- Stores all Stripe payment events
- Tracks: amount, status, tier, customer ID, subscription ID
- Events tracked:
  - `checkout.session.completed` - Initial subscription
  - `invoice.paid` - Recurring payments
  - `invoice.payment_failed` - Failed payments

**Admin Endpoints:**
- `GET /admin/transactions` - List all transactions
- `GET /admin/users/{user_id}/details` - Get user transactions

**Frontend:**
- Transactions tab in admin panel
- Shows: amount, status, user, date, event type
- Filterable by user

### 2. Token Usage Tracking

**Database Table: `token_usage`**
- Tracks every OpenAI API call
- Records: input tokens, output tokens, total tokens, estimated cost
- Links to: user_id, endpoint, model
- Cost calculation based on model pricing:
  - `gpt-4o-mini`: $0.15/1M input, $0.60/1M output
  - `gpt-4o`: $2.50/1M input, $10.00/1M output
  - `gpt-4`: $30/1M input, $60/1M output

**Tracked Endpoints:**
- `summarize` - Summary generation
- `flashcards` - Flashcard creation
- `exam` - Exam generation
- `chat` - Chat conversations
- `explain` - Question explanations
- `truefalse` - True/False statements

**Admin Endpoints:**
- `GET /admin/token-usage` - List token usage records
- `GET /admin/users/{user_id}/details` - Get user token usage
- `GET /admin/revenue` - Get token cost analytics

**Frontend:**
- Token Usage tab in admin panel
- Shows: user, endpoint, tokens used, cost per request
- Filterable by user and endpoint

### 3. Revenue Analytics

**Metrics Tracked:**
- Total revenue (completed transactions)
- Total token costs
- Net revenue (revenue - costs)
- Revenue by tier (free, premium, pro)
- Revenue by time period (daily)
- Token usage by endpoint
- Top users by token cost
- Transaction statistics

**Admin Endpoint:**
- `GET /admin/revenue?days=30` - Get revenue statistics

**Frontend:**
- Revenue tab in admin panel
- Dashboard with key metrics
- Revenue by tier breakdown
- Token usage by endpoint
- Top users by cost
- Daily revenue chart (data available)

### 4. User Details

**Enhanced User Information:**
- Basic user info (email, name, tier, admin status)
- Transaction history
- Total amount paid
- Token usage statistics
- Token usage by endpoint
- Total token cost for user
- Usage statistics (daily quotas)
- History and upload counts

**Admin Endpoint:**
- `GET /admin/users/{user_id}/details` - Get comprehensive user details

**Frontend:**
- "Details" button on each user in Users tab
- Modal showing all user information
- Transaction list
- Token usage breakdown

## Database Schema

### Transactions Table
```sql
CREATE TABLE transactions (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    stripe_session_id TEXT UNIQUE,
    stripe_customer_id TEXT,
    stripe_subscription_id TEXT,
    stripe_payment_intent_id TEXT,
    amount REAL,
    currency TEXT DEFAULT 'usd',
    status TEXT,  -- 'completed', 'pending', 'failed', 'refunded'
    tier TEXT,    -- 'premium', 'pro', etc.
    event_type TEXT,  -- 'checkout.session.completed', 'invoice.paid', etc.
    metadata TEXT,    -- JSON string
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

### Token Usage Table
```sql
CREATE TABLE token_usage (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,  -- NULL for anonymous users
    endpoint TEXT,    -- 'summarize', 'flashcards', 'exam', etc.
    model TEXT DEFAULT 'gpt-4o-mini',
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    estimated_cost REAL,  -- USD
    created_at TIMESTAMP
);
```

## API Endpoints

### Transactions
- `GET /admin/transactions?skip=0&limit=100&user_id=123`
  - List all transactions
  - Optional filters: user_id

### Token Usage
- `GET /admin/token-usage?skip=0&limit=100&user_id=123&endpoint=exam`
  - List token usage records
  - Optional filters: user_id, endpoint

### Revenue Statistics
- `GET /admin/revenue?days=30`
  - Get revenue analytics for last N days
  - Returns: total revenue, costs, net revenue, breakdowns

### User Details
- `GET /admin/users/{user_id}/details`
  - Get comprehensive user information
  - Includes: transactions, token usage, statistics

## Cost Calculation

Token costs are calculated based on OpenAI pricing:

### GPT-4o-mini (default)
- Input: $0.15 per 1M tokens
- Output: $0.60 per 1M tokens

### GPT-4o
- Input: $2.50 per 1M tokens
- Output: $10.00 per 1M tokens

### GPT-4
- Input: $30.00 per 1M tokens
- Output: $60.00 per 1M tokens

Costs are calculated automatically for each API call and stored in the database.

## Usage

### View Transactions
1. Go to Admin Panel
2. Click "💳 Transactions" tab
3. View all payment transactions
4. See: amount, status, user, date

### View Token Usage
1. Go to Admin Panel
2. Click "🔑 Token Usage" tab
3. View all API calls and token consumption
4. See: user, endpoint, tokens, cost

### View Revenue Analytics
1. Go to Admin Panel
2. Click "💰 Revenue" tab
3. View:
   - Total revenue
   - Token costs
   - Net revenue
   - Revenue by tier
   - Token usage by endpoint
   - Top users by cost

### View User Details
1. Go to Admin Panel
2. Click "👥 Users" tab
3. Click "Details" on any user
4. View:
   - Transaction history
   - Token usage
   - Total paid
   - Usage statistics

## Migration

Run the migration endpoint to create the new tables:

```bash
curl -X POST http://localhost:8000/admin/migrate-database
```

Or manually:

```sql
-- SQLite
CREATE TABLE IF NOT EXISTS transactions (...);
CREATE TABLE IF NOT EXISTS token_usage (...);
```

## Future Enhancements

Potential additions:
- Export transactions to CSV
- Revenue charts and graphs
- Token usage trends over time
- Cost alerts and notifications
- User lifetime value calculations
- Cohort analysis
- Revenue forecasting

## Notes

- Token tracking starts after migration (historical data won't be available)
- Transaction tracking starts after webhook is updated (past transactions won't be available)
- Costs are estimates based on OpenAI pricing (actual costs may vary)
- Anonymous users (not logged in) have `user_id = NULL` in token_usage table

