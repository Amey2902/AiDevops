# Post-Mortem: Incident-20260312 - Database Connection Starvation during Flash Sale

## Executive Summary
On 2026-03-12 at 14:22 UTC, the primary payment and checkout service `order-service` experienced an outage lasting 18 minutes. Users received HTTP 500 errors during checkout. The AI investigation revealed that a newly deployed analytics logging function did not release database connections upon exceptions, leading to database connection pool exhaustion within 7 minutes of elevated traffic.

## Impact
- **Severity**: P1 Critical
- **Duration**: 18 minutes (14:22 UTC - 14:40 UTC)
- **Affected Services**: `order-service`, `payment-gateway-proxy`
- **Error Rate**: 84% HTTP 500 failure rate on `/api/v1/checkout`

## Timeline of Events
- **14:20 UTC**: Traffic spike to 1,200 req/sec following promotion push.
- **14:22 UTC**: Prometheus fired alert `HighErrorRate5xx` on `order-service`.
- **14:24 UTC**: Logs showed `psycopg2.OperationalError: remaining connection slots are reserved for non-replication superuser connections`.
- **14:28 UTC**: SRE team identified connection count reached `max_connections: 200` with 185 connections stuck in `idle in transaction`.
- **14:35 UTC**: Terminated idle transactions and restarted `order-service` pods.
- **14:40 UTC**: Error rate returned to 0.01%.

## Root Cause
An unhandled exception in `record_audit_event()` caused the database session to remain open without invoking `.commit()` or `.rollback()`, leaving active sockets held indefinitely in the PostgreSQL connection table until `max_connections` was saturated.

## Key Learnings & Preventative Actions
1. Enforce automated database connection teardown using context managers.
2. Introduce PgBouncer connection pooler in front of PostgreSQL.
3. Add alert for `pg_stat_activity` when connection utilization exceeds 80%.
