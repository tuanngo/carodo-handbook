# Audits

Source audits of the repositories and what each one taught us. An audit file records the cases it
found, how each was fixed (with the commit) and the pattern behind it, so the same mistake is
caught in review instead of found again in the next audit.

- One file per audit: `YYYY-MM-DD-<repo>-source-audit.md`.
- Each case: what went wrong, why it slipped through, the fix and its commit, the test that now
  guards it, and the rule that avoids it next time.
- A rule that binds the code (not just this audit) also lands in the repository's `AGENTS.md` or
  `docs/`; the audit links to it, never the other way round.

| Audit | Repo | Cases | State |
|---|---|---|---|
| [2026-11-07 iOS source audit](2026-11-07-ios-source-audit.md) | `carodo-ios` | 7 | All fixed and committed; device checks pending |
| [2026-11-16 `geocoded_cells` audit](2026-11-16-ios-geocoded-cells-audit.md) | `carodo-ios` | TD-2 row 1, TD-36, TD-6 | Phase 1 built (carodo-ios dd58a24); phase 2 (OSM) not started |
| [2026-11-07 backend source audit](../plans/backend-source-audit.md) | `carodo-app` | 6 | Open (still in `plans/`) |
