# Team Payment Administration

## Release Status

Implemented on `feat/admin-team-payments` and deployed to Vercel Preview.
Production rollout is pending. Preview uses its own database; entries made
there are not automatically copied into production.

## Access and Workflow

League administrators open `/admin/payments` to search teams, filter status,
review balances and history, adjust registration fees, and record each cash or
transfer payment separately. Records include the method, recipient, optional
reference and notes, and the recording administrator. The recipient defaults
to the administrator when omitted.

Proof is optional and can only be uploaded and accessed by administrators.
Accepted formats are JPG, PNG and PDF, with a maximum size of 5 MB and binary
signature validation. Representatives are never asked to submit proof.

The representative dashboard returns balances and history only for teams
explicitly linked through `team_representatives`. Switching dashboard views
does not create assignments. An account without assigned teams has an empty
team list and a zero aggregate balance.

Mobile histories display labeled fields vertically in both views; desktop
retains tables. Empty histories render a plain message. Representative metrics
and player summaries remain contained within the mobile viewport.

## Storage and API

`teams.registration_fee_cents` stores the fee in integer cents. `team_payments`
stores individual payments, optional proof bytes and metadata, recipient,
recording administrator, and timestamps. Outstanding balance is the fee less
recorded payments, floored at zero. Overpayments are not displayed as credit.

All endpoints below require the `league_admin` role:

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/api/admin/payments/teams` | Team balances and histories |
| PATCH | `/api/admin/payments/teams/{team_id}/fee` | Set registration fee |
| POST | `/api/admin/payments/teams/{team_id}/payments` | Record payment with optional multipart proof |
| GET | `/api/admin/payments/{payment_id}/proof` | Read proof with private, no-store caching |

`GET /api/me/representative-dashboard` includes assigned teams' `finance`
objects. Representatives have no access to the administrative API.

Implementation: `routes/payments.py`, `repositories/payments.py` and
`services/payment_proofs.py`. Migration `d6f1a7c2b904` creates the fee column,
ledger and index, enables row-level security and grants access to the existing
restricted backend role. Migration `e7b2c9a104f6` sets the league fee default and
updates existing teams to that configured fee while preserving payments.
Review this update before production because it replaces customized team
fees. Its downgrade restores the old default, not previous individual fees.

Apply migrations to the intended database before deploying code that reads
these fields. Preview and production migration states are independent.

## Current Limitations

- Capture is manual; Excel import and import review are not implemented.
- The received timestamp is the capture time. Original payment dates cannot
  yet be entered, so historical imports need an explicit date workflow.
- Payment editing, reversals, duplicate detection and deletion are not available.
- Transfer capture is administrative, not bank reconciliation. There is no
  separate pending-validation state.
- Unpaid balances do not block players, teams or match participation.

## Verification

Repository tests cover cash-payment balances and representative team scoping.
The payment, representative, page and UI contract suites passed together.
Browser checks with synthetic teams, players, empty histories and recorded
payments covered widths of 360, 390, 430 and 1280 pixels. Mobile checks verified
page containment and histories without horizontal overflow. An authenticated
acceptance check with operational data remains necessary before production.
