# Provisional player identities

Account registration and managed roster registration now offer two explicit identification modes:

- `curp` remains the default and requires 18 characters. Existing CURP-derived completed-age and legacy import behavior remain compatible.
- `provisional` preserves a shorter school or provisional identifier (1–17 characters) and requires an explicit non-future birth date. The application does not invent missing characters or certify the document's legal status.

`players.identity_type` and `players.birth_date` keep the distinction and date private. The existing private `curp` field stores the supplied identifier for compatibility and uniqueness. Public rosters and account responses do not return the new fields.

Managers can edit a provisional identity to its definitive CURP on the same roster player. The player ID, memberships, linked account, and statistics remain attached. A conflicting identity is rejected rather than silently merged.

Use the manual player/account form for provisional documents. The existing CSV/XLSX roster import continues to expect standard CURPs.

The additive Alembic migration is idempotent so a schema applied and verified through the managed database connector is compatible with a later full Alembic upgrade. Deploy and verify the schema in preview before production code reads it. It adds no public policies or grants.
