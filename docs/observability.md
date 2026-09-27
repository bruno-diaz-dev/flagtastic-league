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

### Current deployment

The Sentry organization is `flagtastic-league` and the FastAPI project is
`python-fastapi`. Error monitoring, logs, and tracing are enabled. The project
has a high-priority issue alert delivered by email.

`SENTRY_DSN` is stored as a Vercel secret for both Production and Preview. No
manual `APP_ENV` value is required on Vercel because `VERCEL_ENV` labels events
as `production` or `preview`. The application defaults to a trace sample rate
of `0.1`, so `SENTRY_TRACES_SAMPLE_RATE` only needs to be added when the rate
must be changed without a code deployment.

The production deployment was verified after configuration:

- Vercel reported the deployment as ready.
- `GET /live` returned `{"status": "alive"}`.
- `GET /ready` returned `{"status": "ready"}`.
- Vercel Runtime Logs recorded `application.observability.configured` with
  `sentry_enabled: true` and `environment: "production"`.
- A synthetic Sentry sample issue confirmed the project and email alert flow.

The synthetic sample issue is not a production application failure.

### Reconfiguration or recovery

1. Open the FastAPI project in Sentry and copy its DSN. Do not commit it.
2. In Vercel, open **Settings > Environment Variables**.
3. Store `SENTRY_DSN` as a Secret for Production and Preview.
4. Redeploy the affected environment so its serverless functions receive the
   latest value.
5. Check Vercel Runtime Logs for `sentry_enabled: true`.
6. Confirm that the project alert named **Send a notification for high priority
   issues** still uses email.

The Sentry DSN is a write-only ingestion identifier, but it is still managed as
deployment configuration so environments can be separated cleanly.

## Better Stack setup

Better Stack is the active external availability layer. The league workspace
contains the following HTTPS monitors against the production domain:

| Monitor | URL | Expected result | Interval | Verified state |
| --- | --- | --- | --- | --- |
| Flagtastic process availability | `https://flagtastic-league.vercel.app/live` | HTTP 200 | 3 minutes | Up |
| Flagtastic database readiness | `https://flagtastic-league.vercel.app/ready` | HTTP 200 | 3 minutes | Up |

Both monitors use a three-minute confirmation period, equivalent to a second
failed check at the current interval, before opening an incident. Recovery also
requires three healthy minutes. The primary responder receives email alerts.
The first monitor distinguishes a complete application outage; the second
reports when the function is alive but Supabase is unavailable.

After creating or changing a monitor, run its manual check and confirm the last
response is HTTP 200. Do not mark Better Stack setup complete merely because
the endpoints work from a local machine; the authoritative signal is a
successful check in the Better Stack dashboard.

Creating or editing monitors requires membership in the league's Better Stack
workspace. Monitor identifiers are provider metadata, not application
configuration. No Better Stack credential, session, or magic link belongs in
the repository.

## Incident workflow

1. Read the Better Stack message to identify `/live` or `/ready` failure.
2. Open Sentry and filter by the incident time, environment, release, route,
   and `request_id`.
3. Use the same request id in Vercel Runtime Logs for the most recent execution.
4. If `/ready` failed, inspect Supabase Logs Explorer and database health.
5. Record the cause, corrective action, and affected release before resolving
   the incident.

For Sentry notifications, inspect the issue before resolving it. A resolution
does not replace a code fix or rollback. For Better Stack incidents, verify
both `/live` and `/ready` before closing the incident so application and
database recovery are confirmed independently.

Vercel Hobby runtime logs are short-lived, so Sentry is the durable application
record. Supabase logs are for database diagnosis and are not queried
continuously by the application.
