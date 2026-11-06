# Runbook: PostgreSQL Connection Pool Exhaustion & Database Timeouts

## Overview
Application microservices rely on relational databases (such as PostgreSQL) for persistent storage. When the number of active, idle-in-transaction, or leaked database connections reaches the database's `max_connections` threshold, incoming queries queue up, time out, or throw fatal connection refused errors, triggering widespread HTTP 500/503 errors across client-facing applications.

## Symptoms & Indicators
1. **Application Error Logs**:
   - `FATAL: remaining connection slots are reserved for non-replication superuser connections`
   - `psycopg2.OperationalError: could not connect to server: Connection refused`
   - `django.db.utils.OperationalError: server closed the connection unexpectedly`
   - `Timeout: connection pool exhausted (timeout after 30s)`
2. **Prometheus Metrics**:
   - Application HTTP error rate: `rate(http_requests_total{status=~"5.."}[5m])` surges.
   - P99 HTTP Request Latency jumps from milliseconds to tens of seconds (matching connection timeouts).
   - PostgreSQL connections metric: `pg_stat_database_numbackends` reaches near `pg_settings_max_connections`.
3. **Database Health State**:
   - High count of connections in `idle in transaction` state.
   - Elevated lock wait counts or long-running queries blocking transactions.

## Diagnostic Workflow
1. **Verify Database Connection Count**:
   - Query Prometheus or `pg_stat_activity` for active vs idle connection breakdown.
   - Look for sudden surges in connection counts across microservice instances.
2. **Inspect Slow Queries and Blocked Locks**:
   - Check `pg_stat_activity` for transactions with duration `> 30s`.
   - Identify unindexed queries table-scanning large tables and holding locks open.
3. **Check Application Connection Pool Configurations**:
   - Calculate total potential connections: $\text{Replicas} \times \text{Workers per Replica} \times \text{Pool Size per Worker}$.
   - Ensure total does not exceed PostgreSQL `max_connections` (minus superuser reserved slots).

## Recommended Remediation Steps
### Immediate Mitigation (Short-term)
- Terminate stuck `idle in transaction` connections:
  `SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle in transaction' AND state_change < current_timestamp - INTERVAL '5 minutes';`
- Increase `max_connections` temporarily in `postgresql.conf` if memory allows, or restart stalled client worker processes that leaked connections.
- Restart severely impacted application instances to drop stale dead sockets.

### Root Cause Resolution (Long-term)
- Deploy **PgBouncer** or an intermediate connection pooler in transaction pooling mode.
- Ensure all application database operations use context managers (`with db.transaction():`) to prevent orphan uncommitted transactions.
- Set aggressive timeouts: `idle_in_transaction_session_timeout = '30s'` and `statement_timeout = '15s'`.
- Review connection pooling configurations in application settings (e.g. `CONN_MAX_AGE`, `pool_size`).
