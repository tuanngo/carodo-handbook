# Backend source audit — 2026-11-07

Status: **All six fixed in the worktree (uncommitted) on 2026-11-07;** APP-05 and APP-06 with the
owner's approval of contract 0.25.0-draft. Recorded 2026-11-07 and rechecked against source on that date. This is a remediation record for `carodo-app`, separate from the iOS audit.

Source baseline: `carodo-app` HEAD `9248ba4`, **with uncommitted and untracked implementation files**.
That commit alone does not reproduce the audited tree. File paths and line numbers below refer
to the inspected worktree and must be rechecked before implementation.

Related: [backend plan](backend.md),
[current implementation status](../../carodo-app/docs/architecture.md#implementation-status),
[backend rules](../../carodo-app/AGENTS.md). Product/API decisions remain in the repositories;
this file records bugs and proposed fixes, not new contracts or approval to change them.

## Priority and completion

- [x] **APP-01 · P1:** session creation can undo revocation.
- [x] **APP-02 · P2:** body-size enforcement occurs after full buffering.
- [x] **APP-03 · P2:** untrusted attestation format text enters logs.
- [x] **APP-04 · P2:** username claim can race past a deletion hold.
- [x] **APP-05 · P2:** delayed Live messages can resurrect an ended trip.
- [x] **APP-06 · P2:** Feed pagination drops rows from an oversized person/hour group.

Recommended order: APP-01, APP-02/03, APP-04, APP-05, APP-06. All findings have high confidence.
P1 is a security/correctness issue to fix first; P2 findings include abuse resistance, privacy
hardening and data correctness. Fixes must preserve the existing API and D1 cost rules. If a fix
needs a schema, contract, binding or dependency change, explain it and obtain the owner's P6
approval first. No such change has been approved by recording these findings.

Close a finding only after its regression test reproduces the old behavior and passes with the
fix, `pnpm run check` passes, and the matching `carodo-app/docs/` text is updated. Record the fix
commit, verification date and any outstanding staging checks here; do not turn a source test into
a claim of deployed behavior.

## APP-01 · P1 — Session creation can undo revocation

**Status:** Fixed 2026-11-07, uncommitted. Refresh revokes and inserts in one batch, the insert
guarded by `changes() = 1`; login inserts only while `EXISTS` the same secret hash. Regression:
`test/workers/auth/session-races.test.ts` (failed before, passes after). The same gap also let a
refresh in flight survive sign out everywhere. **Effort:** M. **Fix risk:** Medium (session state and concurrency).

**Evidence:** [sessions.ts](../../carodo-app/apps/api/src/services/auth/sessions.ts), lines 95–103
and 142–150; [lifecycle.ts](../../carodo-app/apps/api/src/services/accounts/lifecycle.ts), lines
19–39. ADR 0005 requires session revocation to take effect immediately.

**Reproduction and impact:**

1. Refresh request A revokes its old refresh row, then pauses before inserting its successor.
2. Request B detects reuse and revokes the family, or another device signs out everywhere.
3. A resumes and unconditionally inserts a live successor in the revoked family. The session
   becomes usable again.

The account-secret login flow has the same gap: it can read/validate the old account secret,
pause across secret rotation, then create a usable session afterward.

**Fix direction:** make successor creation conditional on the still-valid session/account state
within the same atomic write boundary as rotation. Login insertion must still match the current
account secret. A check before an `await` is insufficient. Preserve immediate revocation and
refresh-reuse detection without introducing a second state authority.

**Regression checks:** deterministic interleavings for refresh versus reuse, refresh versus sign
out everywhere, and old-secret login versus secret rotation. Once revocation wins, no delayed
operation may recreate a usable session. Also retain normal refresh/login tests.

## APP-02 · P2 — Body limits are enforced after full buffering

**Status:** Fixed 2026-11-07, uncommitted. `readBody` reads the stream with a running count and
cancels past the cap. Regression: `test/unit/http/request.test.ts`. **Effort:** S. **Fix risk:** Low (request-body handling).

**Evidence:** [request.ts](../../carodo-app/apps/api/src/http/request.ts), lines 13–17;
[auth.ts](../../carodo-app/apps/api/src/routes/auth.ts), lines 22–24.

**Reproduction and impact:** without `Content-Length`, send more than the endpoint's limit.
`readBody` calls `arrayBuffer()` before checking actual length. The audit reproduced a 1 MiB body
being fully buffered before refusal at a 32 KiB limit. This is a memory-exhaustion risk, including
on the unauthenticated guest-token path; the application limit does not bound memory consumption.

**Fix direction:** read the request stream with a running byte count, stop/cancel immediately
when the cap is exceeded, and preserve the exact accepted bytes used by App Attest assertions.
Keep the cheap declared-length rejection, but do not rely on that header for enforcement.

**Regression checks:** absent/misleading length, a body exactly at the cap, one byte over it,
multi-chunk overflow and early cancellation. Confirm valid assertion hashing is unchanged and
the existing failure response contract is preserved.

## APP-03 · P2 — Request-controlled attestation format text enters logs

**Status:** Fixed 2026-11-07, uncommitted. Fixed reasons `fmt` and `validation category`; other
interpolated reasons are constants. Regression: a log-capture case in
`test/workers/attest/attestation.test.ts`. **Effort:** S. **Fix risk:** Low (diagnostic text).

**Evidence:** [attestation.ts](../../carodo-app/apps/api/src/services/attest/attestation.ts),
lines 60–67. The unknown CBOR `fmt` is interpolated into a refusal and logged as its reason.

**Reproduction and impact:** submit a valid CBOR map with an unsupported `fmt` containing a
synthetic marker. Attestation is refused, but the marker appears in the warning log. This proves
arbitrary request content can enter logs; it does not establish an actual production credential
leak. The behavior violates the rule that diagnostics contain categories rather than raw input.

**Fix direction:** use a fixed refusal category for unsupported formats. Keep useful structured
logging without reflecting the untrusted value. Review other refusal paths for the same pattern.

**Regression checks:** capture the warning for an unsupported format; assert the event/category
is present and the submitted marker is absent. The client should still receive the same generic
unauthorized result.

## APP-04 · P2 — Claim can bypass the 90-day username hold

**Status:** Fixed 2026-11-07, uncommitted. The account insert is `INSERT … SELECT … WHERE NOT EXISTS`
an active hold; the session insert follows with `changes() = 1`. Regression: in
`test/workers/auth/session-races.test.ts`. **Effort:** S/M. **Fix risk:** Low/medium (conditional account creation).

**Evidence:** [claim.ts](../../carodo-app/apps/api/src/services/accounts/claim.ts), lines 86–113;
[lifecycle.ts](../../carodo-app/apps/api/src/services/accounts/lifecycle.ts), lines 58–65.

**Reproduction and impact:** a claim checks that no hold exists while another account still owns
the name. The owning account is then deleted: its username is freed and a 90-day hold is created.
The paused claim resumes and inserts the now-free username without rechecking the hold. The
protection against immediate reuse/impersonation is bypassed.

**Fix direction:** enforce the active-hold predicate in the same atomic database operation as
account creation. Account and initial session creation must remain all-or-nothing; a hold or
conflict must leave no orphaned account/session.

**Regression checks:** pause a claim across deletion and verify it fails as `username_taken`,
without revealing that the name was deleted. Retain concurrent same-name claims and expiration
of the 90-day hold as normal cases.

## APP-05 · P2 — Delayed Live messages can resurrect an ended trip

**Status:** Fixed 2026-11-07, uncommitted (contract 0.25.0-draft, owner-approved): `DELETE /v1/live`
carries `startedAt` with `tripId`; a PUT or DELETE for a trip that started before the stored one
changes nothing. Regression: two A/B cases in `test/workers/live/live.test.ts` (failed on the old
rules, pass now). **Effort:** M. **Fix risk:** Medium (message ordering and tombstone semantics).

**Evidence:** [live.ts](../../carodo-app/apps/api/src/services/live/live.ts), lines 65–70 and
109–114. An end for a different trip can replace an already-ended row; a PUT for a different
trip can then clear the tombstone.

Recheck 2026-11-07 found a simpler path: end A, start and end B, then a delayed renewal PUT(A)
revives A; and a delayed PUT(A) while B is live replaces B, so DELETE(B) then matches nothing.
Bounded by the 15-minute expiry. Ordering by `startedAt` needs `DELETE` to carry it (contract).

**Reproduction and impact:** end trip A; start and end trip B; deliver a delayed DELETE(A); then
deliver a delayed renewal PUT(B). The old DELETE replaces B's tombstone, and the renewal makes
ended B live again. Readers can see someone as driving after the drive has ended. Existing tests
cover an older end while B is active, but not after B has ended.

**Fix direction:** preserve the ordering information needed to reject stale transitions without
allowing an older trip to erase a newer end. Check whether the one-row model can uphold the full
promise for overlapping messages; do not silently weaken ADR 0008. Any schema/API change needs P6
approval before implementation.

**Regression checks:** the complete A/B sequence above, duplicate PUT/DELETE, end-before-start,
an older end while a newer trip is active, and expiry/pruning behavior. Check both stored state
and what Feed Live readers can see.

## APP-06 · P2 — Feed pagination silently drops oversized groups

**Status:** Fixed 2026-11-07, uncommitted (contract 0.25.0-draft, owner-approved): publish refuses a
21st drive in one account-hour (422 `hour_full`), counted in the same statement (at most 20 index
rows read). `ROWS` (60) ≥ the cap, asserted by `test/unit/feed/page-rows.test.ts`. Regression: in
`test/workers/drives/publish.test.ts`. **Effort:** M. **Fix risk:** Medium (pagination, grouping and D1 query cost).

**Evidence:** [read.ts](../../carodo-app/apps/api/src/services/feed/read.ts), lines 141–152.
`page()` slices raw rows to 60 before grouping, then advances its cursor by person/hour.

**Reproduction and impact:** publish 61 distinct trips for the same account/hour. The server
currently accepts this data; it has no group-size cap. The first item includes only 60 trips and
the next cursor skips the entire group, so the remaining trip is never returned. In the audit,
61 trips of 500 m produced a 30,000 m total instead of 30,500 m and an empty next page. Discover
and Following share this code. This is a boundary case, not a typical normal drive.

**Fix direction:** page complete group keys or use an explicitly bounded representation that
preserves every accepted drive's totals and pagination. Do not resolve this by loading an
unbounded group or silently dropping records. Preserve keyset pagination, sealed cursors, block
filtering and indexed/bounded D1 work. Any response-contract change needs owner approval.

**Regression checks:** 60, 61 and larger same-person/hour groups; a large group at a page boundary;
mixed accounts/hours; both Discover and Following. Assert no omissions/duplicates and correct
totals across pages. Keep the query-plan/full-scan and request-cost tests passing.

## Evidence and limits of the audit

On 2026-11-07:

- `pnpm run check` passed lint, generated-binding checks, TypeScript and all 160 existing tests
  (158 API, 2 web). These tests did not cover the counterexamples above.
- A temporary Node harness loaded the actual TypeScript services and used an in-memory SQLite
  database created from `0001_baseline.sql`, with a D1 adapter and controlled interleavings.
  It reproduced APP-01/04/05/06. APP-02 used an instrumented body reader; APP-03 captured logs
  from a synthetic CBOR request. The harness lived outside the repository and is not a permanent
  regression suite; the scenarios above must become workerd/route tests where appropriate.
- `pnpm audit --prod --json` reported zero production dependency advisories. Source and Git-history
  pattern scans found no production credential; the flagged Vitest secret was explicitly test-only.
- No load/abuse test against deployed Cloudflare resources, staging smoke test or production
  CPU/subrequest measurement was performed. Passing local checks does not establish deployment readiness.
- Documentation alignment in `carodo-app` recorded the implementation boundary; it did not fix
  any of these six findings. No schema/API/binding/dependency change was made by the audit.
