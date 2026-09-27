# Production observability

Flagtastic uses complementary monitoring layers. Application telemetry goes to
Sentry, external availability checks go to Better Stack, and provider-specific
diagnostics remain available in Vercel and Supabase.

## Data-handling rules

Observability must help diagnose failures without becoming another source of
league-member personal data. Logs and remote events must never contain:

- Passwords or password hashes.
- Session cookies, authorization headers, or API keys.
- CURP, email addresses, or complete request bodies.
- Profile images, team-logo bytes, or imported workbook contents.

`observability.py` enforces an allowlist for structured log fields, disables
Sentry request bodies and local variables, removes sensitive headers, and does
not send Sentry user objects. Operational identifiers such as request id,
route, status code, duration, deployment release, and exception type are safe.

## Application configuration

The integration is optional. Without `SENTRY_DSN`, the application continues
to emit JSON logs to standard output for Vercel while remote telemetry stays
disabled.

| Variable | Production value | Purpose |
| --- | --- | --- |
| `APP_ENV` | `production` | Labels logs and Sentry events. |
| `LOG_LEVEL` | `INFO` | Minimum application log level. |
| `SENTRY_DSN` | Sentry project DSN | Enables remote errors, traces, and logs. |
| `SENTRY_TRACES_SAMPLE_RATE` | `0.1` | Samples 10 percent of request traces. |
| `SENTRY_RELEASE` | Optional | Manual release id outside Vercel. |

Vercel already supplies `VERCEL_ENV` and `VERCEL_GIT_COMMIT_SHA`. The latter is
used as the Sentry release when `SENTRY_RELEASE` is absent, allowing an incident
to be traced to an immutable deployment.

## Health endpoints

- `GET /live` verifies that the FastAPI process can answer a request. It has no
  database dependency.
- `GET /ready` executes `SELECT 1` against PostgreSQL. It returns `503` with the
  generic body `{"status": "unavailable"}` when the database is unreachable.

Both responses disable caching. Every HTTP response also includes
`X-Request-ID`; a safe incoming id from Vercel or another proxy is reused,
otherwise the application generates one. Successful health checks are omitted
from application logs to avoid consuming the free log quota.

## Sentry setup

1. Create a Python project at Sentry and select FastAPI when prompted.
2. Copy the project's DSN. Do not commit it to Git.
3. In Vercel, open the Flagtastic project, then **Settings > Environment
   Variables**.
4. Add `SENTRY_DSN`, `APP_ENV=production`, and
   `SENTRY_TRACES_SAMPLE_RATE=0.1` to Production and Preview. Use
   `APP_ENV=preview` for Preview if separate values are configured.
5. Redeploy so the serverless function receives the variables.
6. Under **Alerts**, enable email notifications for new issues, regressions,
   and an unusual increase in errors.

The Sentry DSN is a write-only ingestion identifier, but it is still managed as
deployment configuration so environments can be separated cleanly.

## Better Stack setup

Create two HTTPS uptime monitors against the production domain:

| Monitor | URL | Expected result | Suggested interval |
| --- | --- | --- | --- |
| Process availability | `/live` | HTTP 200 | 3 minutes |
| Database readiness | `/ready` | HTTP 200 | 3 minutes |

Require two consecutive failures before opening an incident. Add the league
administrator's email as the escalation recipient and enable recovery
notifications. The first monitor distinguishes a complete application outage;
the second reports when the function is alive but Supabase is unavailable.

## Incident workflow

1. Read the Better Stack message to identify `/live` or `/ready` failure.
2. Open Sentry and filter by the incident time, environment, release, route,
   and `request_id`.
3. Use the same request id in Vercel Runtime Logs for the most recent execution.
4. If `/ready` failed, inspect Supabase Logs Explorer and database health.
5. Record the cause, corrective action, and affected release before resolving
   the incident.

Vercel Hobby runtime logs are short-lived, so Sentry is the durable application
record. Supabase logs are for database diagnosis and are not queried
continuously by the application.
