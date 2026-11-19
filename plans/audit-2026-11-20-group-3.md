# Audit 2026-11-20 — group 3: decisions before code

Status: **waiting for the owner's decisions** (2026-11-20). Groups 1 and 2 of the
[2026-11-20 full source audit](../audits/2026-11-20-carodo-full-source-audit.md) are fixed (carodo-ios
`5aae671`, `8f4fef9`). This file is the handoff for a fresh session: what group 3 holds, the owner's
decisions each item needs (each with a recommendation), and how to take each workstream. No code
for group 3 has been written.

## How to start the new session

1. Read this file, then the finding itself in the audit (section named by its ID) and the files it
   cites. The audit was written from reading code on 2026-11-20; **re-check every finding against
   the current code before planning** (another session may have moved it), and say which still hold.
2. Take one workstream at a time (A, B, C, D below), in the suggested order. For it: a plan with
   the brief template (`AGENT_WORKFLOW.md`), the owner's decisions marked as settled or open, then
   wait for approval.
3. Device checks still pending from groups 1–2: TRK-1 (pause > 5 min at a stop, Resume, then drive
   on, or stay parked: the drive ends about 5 min later, at the stop).

Suggested order: **B** (iCloud sync, the heaviest data risk) → **A** → **C1 + C5** → **C2 + C3**
(backend schema) → **D**.

## A. Tracking

### A1 · TRK-4 — "short drive" is judged by three different rules

- Today: live uses the vehicle class's rules plus the missed start
  (`DriveSessionManager.isShortDrive`); recovery always uses the car's thresholds and no missed
  start (`TripReplay.swift`); `resume(_:)` restores neither `missedStartM` nor `fastFixes`.
- Effect: a real short drive can be **deleted** (a 350 m bicycle ride killed mid-ride; an Auto Mode
  drive that counted only by its missed start, resumed after a termination).
- Proposal: one function decides "short" (class rules + missed start), called by live, recovery and
  resume. Recovery reads the class from the trip's `vehicle_id`; resume recounts `fastFixes` from
  the replayed fixes.
- **Decision A1-a:** when the rule cannot be decided (the class cannot be read), keep the drive for
  "Keep it?" instead of deleting it. *Recommended: keep.*
- **Decision A1-b:** `missedStartM` is not stored. Recompute it at resume from the first fix and the
  parked spot (no schema change), and add a column (P6) only if that cannot work. *Recommended:
  recompute.*
- Proof: unit tests for all three paths; **device check** (kill the app mid-drive, relaunch).

## B. iCloud sync

All four make the owner's devices silently diverge. B1, B3 and B4 need no schema change; B2 does.
Tests use two in-memory databases and out-of-order batches; `docs/sync.md` changes in the same commit.

### B1 · DAT-1 — a fetched batch that fails to apply is lost for good

- Proposal: when `applyFetched` throws, do not persist the engine state of that round (keep the
  last saved serialization), so the engine fetches the batch again.
- **Decision:** approve. *Recommended: yes.*

### B2 · DAT-2 — records skipped by an older build are never fetched after the update

- Options: (a) store `skipped_for_version` in `cloudkit_state`; when `CloudPayload.currentVersion`
  rises above it, reset the engine state to refetch the zone (schema: edit `v1_initial`, pre-release);
  (b) record it as a risk only, since no payload v2 exists yet.
- **Decision B2:** *Recommended: (a), before the first TestFlight build* (after it, a migration).

### B3 · DAT-3 — one undecodable track aborts the batch's deletions

- Proposal: decode and bound the track when the record is decoded (`TrackCodec.decode`, a size cap
  from `point_count`; never `Data(contentsOf:)` unbounded); a bad track is a failed record. Apply
  deletions before the derive loop; the loop is per trip with its own `do/catch`.
- **Decision:** approve. *Recommended: yes.* (DAT-5, a crafted sequence trapping the join, fits the
  same commit: reject sequence/segment outside `0..<TripSample.partOffset`.)

### B4 · DAT-4 — signing back in drops deletes made while signed out

- Proposal: on `.signIn` keep tombstones (clear `ck_metadata`, set `ck_pending`); drop them only on
  `.switchAccounts` or a zone deletion.
- **Decision B4 (product):** a drive deleted while signed out of iCloud, then signed back in to the
  **same** account: the delete reaches iCloud. *Recommended: yes* (a private route the person chose
  to remove, P5).

Suggested commits: B1 + B3 (+ DAT-5) + B4 together; B2 on its own if (a).

## C. Backend (carodo-app)

### C1 · API-1 (P9) — an edit to a visible drive moves the Feed at the moment it arrives

- Proposal: when a revision moves `ended_at` later or changes `local_date`, recompute
  `visible_at = visibleAt(new endedAt, now)`; otherwise keep the old one. Pure server logic, no
  contract change. Also check whether the app really sends a later `endedAt` for a published trip
  (merge, resume) and say so.
- **Decision:** approve. *Recommended: yes.*

### C2 · API-2 + API-7 — one attested device can claim any number of accounts

- Proposal: an exact per-key cap in the claim's own statement; needs an index on
  `sessions(app_key_id)` (D1 schema, P6). Over the cap: **403 `claim_limit`**, as the contract
  already says (closes API-7; add 429 for the rate limits to the contract).
- **Decision C2:** the cap per App Attest key. *Recommended: 3* (a person may delete and claim
  again).

### C3 · API-3 — `sessions` and `auth_challenges` outgrow their prune

- Proposal: delete a rotated session 30 days after rotation (partial index, P6), and loop the prune
  within the run's budget instead of 1,000 rows an hour. Stateless (HMAC) challenges: not now.
- **Decision:** approve the index and the 30 days. *Recommended: yes.*

### C4 · API-4 — stopping sharing or deleting the account changes the Feed mid-quarter

- Proposal: no code; add both acts to the P9 exceptions (workspace `AGENTS.md`, both repos'
  `AGENTS.md`, carodo-ios ADR 0007), as the person removing their own data, like hiding a drive.
- **Decision:** approve the wording. *Recommended: yes.*

### C5 · Contract wording (P6)

- API-6: list 400 `username_invalid` on `PUT /v1/me/profile`.
- API-8: "a taken name may carry suggestions" (reserved names get none).
- API-9: the iOS `docs/api/carodo-api.yaml` is the only copy; fix the root `AGENTS.md` recipe that
  names a backend copy.
- **Decision:** approve all three. *Recommended: yes*, one docs commit.

### C6 · Small items

- API-10: `secureHeaders()` and a CSP on carodo-web before share pages ship. *Recommended: yes.*
- API-11, API-12: `toHex(bytes)` and `countsByItem(rows)`. *Recommended: yes.*
- API-5: a tombstone planted on a guessed trip id. *Recommended: accept the risk* (UUIDv4, needs a
  leaked id) and record it in `technical-debt.md`.

## D. Design system (XC-3, XC-5, XC-9)

- Today: about 30 cards drawn by hand in two fills and three hairline strengths; 24 disclosure
  chevrons in six styles; about 1,040 raw spacing numbers, many off the grid.
- **Decision D1:** the one card: `elevated` + 60 % hairline (`.carodoCard()`, 47 uses already)
  *recommended*, or `card`. The one chevron: `.footnote.weight(.semibold)` in `textSecondary` (15
  uses already) *recommended*.
- **Decision D2:** (a) screen by screen, one commit each with before/after screenshots
  *recommended*; or (b) one sweep.
- **Decision D3 (XC-9):** fix the doc only (drop 48 or add `xxl`, the count, `FeedItemRow` →
  `FeedRow`) and move numbers to tokens when a file is touched anyway. *Recommended: yes*; a bulk
  replacement of 1,000 values risks shifting layouts.

## Open from groups 1–2 (not group 3)

- XC-1: the dates on Garage, Passport and Day still use the device's zone, not the drive's.
- XC-10: `VehicleIdentityPresentation` and `LocalCache.maximumAgeS` kept on purpose.
- TRK-8: clearing `vehicleID` in `reset()` left alone (no bug today).
- UIB-1: a Feed avatar tap does nothing while the membership is unknown (offline launch).
