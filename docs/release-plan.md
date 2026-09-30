# Flagtastic Release Plan

## Purpose

This document tracks the production baseline and the work required to evolve
Flagtastic safely. It replaces the original pre-launch plan: the public MVP was
deployed by September 27, 2026, and the project is now in stabilization and
operational improvement.

The working team is Bruno and Codex. Work is intentionally divided into small,
reviewable pull requests. Every change must preserve least-privilege access,
database migration safety, responsive behavior, and the existing public flows.

## Delivery Workflow

All changes follow this path:

```text
Issue or verified requirement
        |
Feature/fix branch
        |
Automated tests + local verification
        |
Pull request in English
        |
GitHub CI + CodeQL + Vercel Preview
        |
Production merge and smoke check
```

Rules:

1. Do not commit directly to `main`.
2. Keep one coherent concern per pull request whenever practical.
3. Add or update tests for behavior changes.
4. Use Alembic for every schema change and verify upgrade and downgrade.
5. Test affected pages at desktop and mobile widths before merge.
6. Update README or focused documentation when operations, architecture, or
   user-visible behavior changes.
7. Do not seed mock data into production unless an explicit migration plan
   requires it.

## Release 1 Production Baseline

Release 1 is deployed at <https://flagtastic-league.vercel.app>.

### Public experience

- Multipage server-rendered interface with responsive navigation.
- Team directory with branch/category filters and deterministic ordering.
- Dedicated roster and public player-profile pages.
- Canonical roster links from team names across all public and role dashboards.
- Chronological game agenda with team-name, jornada, branch, category, and
  field filters, plus scores and game details.
- Division standings with team logos.
- Top-five individual leaderboards by branch and category.
- Integral privacy notice.

### Team and roster operations

- Authenticated team creation with automatic creator assignment.
- Team lifecycle: `pending`, `active`, and `inactive`.
- Case-insensitive team identity within each branch/category division.
- Administrator team rename, representative assignment/removal, and deletion.
- Representative access limited to explicitly assigned teams.
- Team logos and Head Coach, Coach, and Manager fields.
- Roster player create, edit, deactivate, and photo update workflows.
- CSV/XLSX roster imports plus a downloadable CSV template.
- Search and assignment of existing active player accounts by legal name or AKA,
  with division eligibility rechecked at write time.
- CURP-derived age validation based on age reached during the calendar year.

### Accounts and authorization

- Database-backed sessions with secure production cookies.
- Player self-registration linked to roster identity.
- Required profile photo and optional AKA.
- Cumulative `league_admin`, `team_representative`, `player`, and `referee`
  roles.
- Forced initial-password replacement for administrator-created staff.
- Administrator user and role management.
- Public, player, representative, referee, and administrator data scopes
  enforced by FastAPI dependencies rather than UI visibility alone.

### Games, officials, and statistics

- Game scheduling, fields 1-8, scores, jornada filtering, postponement, and
  administrator-only deletion of one game or a complete jornada.
- Manual scheduling with shared division filters and independent local and
  visitor team-name searches.
- Reviewed role import from the league XLSX calendar, normalized CSV, or image;
  unresolved teams are blocked, recognized times remain editable, and repeated
  schedule slots are handled safely.
- Browser OCR of the operational six-field grid, including complete hourly-row
  detection and separate `Pitbulls Jr`/`Pitbulls Sr` matching.
- Game-level player statistics for both participating teams.
- Complete-jornada workbook imports linked to game, player, team, and division.
- Aggregated player profiles and named leaderboards.
- Passing-percentage qualification: no minimum through jornada 3, then at least
  30 attempted passes.
- Referee, Down Judge, Field Judge, Side Judge, and Statistician assignments.
- Referee and Down Judge as the required core positions when confirming an
  official role; optional positions support U6, regular games, and finals.
- OCR-assisted official schedule review with explicit administrator
  confirmation before data changes.
- Private referee assignments and administrator replacement of officials.
- Authenticated referee roster with self-service photos for referee-only
  accounts and shared player photos for multi-role accounts.

### Delivery and operations

- PostgreSQL schema managed by Alembic.
- Production database on Supabase with Row Level Security as defense in depth.
- Application deployment and Preview environments on Vercel.
- GitHub Actions tests migrations from scratch and runs pytest.
- Docker image build and GHCR publication on non-PR builds.
- CodeQL analysis and branch-based pull-request workflow.
- Privacy-scrubbed Sentry telemetry.
- Vercel and Supabase diagnostic logs.
- Better Stack external monitoring of `/live` and `/ready` with email alerts.

## Release Gates

Every production release must satisfy all applicable gates.

### Automated gates

- Dependency installation and `pip check` succeed.
- Python sources compile.
- Alembic upgrades from base, downgrades to base, and upgrades again on clean
  PostgreSQL.
- Complete pytest suite passes.
- Docker image builds.
- CodeQL reports no blocking finding.
- Vercel Preview deployment succeeds.
- Preview connects to the isolated `flagtastic-league-preview` database and
  never to the production database.

### Manual gates

- The affected workflow succeeds in the Preview environment.
- No unauthorized role can call the changed write endpoint.
- Mobile layouts have no page-level horizontal overflow at 360, 390, and 430
  pixels.
- Desktop behavior remains correct at 1280 pixels or wider.
- Tables retain readable headers and contained horizontal scrolling.
- Media changes survive reload and do not depend on local filesystem state.
- Production smoke checks confirm `/live`, `/ready`, login, and the changed
  public or private flow after merge.

### Database gates

- Migration names and constraints are deterministic.
- Upgrade and downgrade are tested against an isolated database.
- Destructive data changes include an explicit backup or recovery procedure.
- Production is migrated before application code that requires the schema is
  promoted.
- Preview and Production migration state is checked independently; a successful
  Vercel deployment is not evidence that either database was migrated.
- `alembic stamp` is never used as a substitute for applying missing schema.

## Sprint 5: Production Stabilization

**Status:** In progress

**Goal:** Close launch defects and make production behavior observable and
repeatable.

Completed:

- Deploy the application on Vercel with Supabase PostgreSQL.
- Add liveness and database-readiness endpoints.
- Integrate Sentry with privacy scrubbing.
- Configure Better Stack process and database monitors with email alerts.
- Document incident response and monitoring ownership.
- Refresh the README and architecture references to describe production.
- Establish pull-request delivery with CI, CodeQL, and Vercel Preview checks.

Remaining:

- Merge the documentation refresh after all PR checks pass.
- Record the first production release/tag from the final deployed commit.
- Run and record a post-release browser smoke test for every role.
- Review unresolved Sentry events and Better Stack incidents after the first
  real usage window.

Definition of done:

- Production health monitors remain green for 24 hours.
- No unresolved release-blocking Sentry issue exists.
- Deployment, rollback, database migration, and incident steps are documented.
- Repository documentation matches deployed behavior.

## Sprint 6: Mobile Reliability

**Goal:** Make the primary phone experience as reliable as desktop without
changing desktop workflows unexpectedly.

Scope:

- Audit Teams, Rosters, Games, Game Detail, Standings, Statistics, Login,
  Registration, Player Dashboard, Representative Dashboard, Referee Dashboard,
  Users, and Team Management at 360, 390, and 430 pixels.
- Keep the hamburger drawer operable by touch, keyboard, backdrop, Escape, and
  navigation selection.
- Prevent controls and buttons from escaping cards or viewport width.
- Convert operational form rows to stable single-column mobile layouts.
- Preserve table semantics with contained scrolling and sticky identifying
  columns where useful.
- Ensure cached team logos and player photos refresh consistently on mobile.
- Reduce unnecessary API calls and avoid duplicate page initialization.
- Keep authenticated high-traffic reads within a small, measured number of
  database connections; roster detail currently resolves in one authorization
  query plus one shared team/players/ownership connection.
- Serve versioned logos and generated profile media through immutable browser
  and Vercel CDN caching, and lazy-load images outside the initial viewport.
- Add focused browser or DOM-level regression coverage for the shared mobile
  shell and highest-traffic pages.

Definition of done:

- No audited page has page-level horizontal scrolling.
- Touch targets are at least 44 pixels where practical.
- User-visible content is not obscured by navigation or browser chrome.
- Logo/photo updates are visible after successful replacement.
- Desktop screenshots show no regression in the same flows.
- CI and Vercel Preview checks are green.

## Sprint 7: Administrative Integrity and Auditability

**Goal:** Make sensitive league changes traceable and recoverable.

Scope:

- Add an append-only administrative audit log for role changes, account
  deletion, team status/name changes, representative changes, roster
  deactivation, score changes, imports, and official assignments.
- Capture actor, action, target, timestamp, and non-sensitive before/after
  metadata.
- Add an administrator audit view with date, actor, and action filters.
- Define retention and redaction rules for audit metadata.
- Add confirmation and conflict handling for destructive operations.
- Document production backup and restore verification for Supabase.

Definition of done:

- Every listed sensitive write produces an immutable audit record.
- Audit entries never contain passwords, session tokens, CURP, raw uploads, or
  secret configuration.
- Administrators can answer who changed a record and when.
- Restore steps have been exercised against a non-production database.

## Sprint 8: Competition Operations

**Goal:** Reduce manual work for a complete tournament lifecycle.

Candidate scope, ordered only after league validation:

- Explicit season/tournament entity and active-season selection.
- Jornada publication state and schedule lock.
- Correction workflow for imported statistics.
- Playoff bracket and finals support.
- Exportable standings, rosters, statistics, and referee assignments.
- Optional account or assignment notifications.

Before implementation, each candidate requires a written rule, owner, data
model impact, authorization matrix, and acceptance test. Payment workflows and
framework rewrites remain out of scope until the league identifies a concrete
need.

## Known Risks and Controls

| Risk | Control |
|---|---|
| Mobile CSS regression | Shared breakpoints, viewport verification, Preview screenshots |
| Unauthorized cross-team changes | Backend role dependencies and representative ownership checks |
| Production schema drift | Alembic-only changes and migration CI cycle |
| Sensitive data in telemetry | Sentry scrubber, structured safe fields, no request bodies/files |
| Stateless media loss | Store photos and logos in PostgreSQL, not local `uploads/` |
| Incorrect workbook identity match | Resolve by division, team, and jersey against existing roster |
| Destructive administrator mistakes | Explicit confirmation now; audit log and recovery in Sprint 7 |
| Monitoring blind spot | Sentry, Vercel, Supabase, and Better Stack with email escalation |

## Prioritization Rule

Production incidents, authorization defects, data-integrity issues, and mobile
blockers take precedence over new features. A feature request enters a sprint
only after its league rule and acceptance criteria are understood. This keeps
the two-person team focused on a dependable tournament platform rather than an
unbounded backlog.
