# Feed private by default — Part 1: decisions and contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

Status: **done 2026-11-19**: carodo-ios `d0186ad`, carodo-app `a276e84` (owner approved; review fixes folded in, deferred minors listed in the spec's Part 2/3 notes). Parts 2 (backend), 3 (iOS) and 4 (web
and docs) get their own plans after this one lands.

**Goal:** the binding texts (ADRs, invariant P9, the OpenAPI contract, `sync.md` Publishing) say
what the approved design decided, so the backend and the app can be built against them.

**Architecture:** documents only, no code. Each task edits one binding text; the owner reviews the
diff before it is committed (P6: contract changes need the owner's approval).

**Tech Stack:** Markdown, OpenAPI 3.1 YAML. Validation: `ruby -ryaml` (Homebrew Ruby, present);
no new dependency.

**Spec:** [`feed-private-by-default.md`](feed-private-by-default.md) (approved 2026-11-19, D1–D8,
C1–C7). Read it first; this plan does not repeat its reasons.

## Global Constraints

- English only in every document; Vietnamese only as app copy beside its English.
- Public time granularity: **15 minutes** (quarter hour: minutes 00, 15, 30, 45, seconds 0, UTC).
- Feed window: **7 days = 168 hours**. Community numbers: at least **10** distinct drivers.
- Labels: "now" for the first hour after release, "1h"–"23h", then "1d"–"6d" (C5).
- Rounding sent by the device: durations to whole minutes (multiples of 60 s), GPS distance to
  multiples of 100 m (C3).
- Error code `start_time_invalid` keeps its name (the app may branch on it); its meaning widens to
  "a time is implausible".
- Contract version: **0.29.0-draft**; breaking, no compatibility path (pre-release).
- Other sessions have uncommitted edits in `carodo-ios/docs/privacy.md`, `carodo-ios/docs/sync.md`
  (sections "The backend in the app" and "App Attest") and `carodo-app/docs/architecture.md`.
  Add to those files, never overwrite; commit only your own hunks (`git add -p`). Never `git add -A`.
- Commits: lowercase conventional, no AI attribution (P8). The workspace root `AGENTS.md` is not
  in any repository: edit it, nothing to commit.

## Review Focus

1. **A text still promising the old rule** (72 h, "finer than the hour", "within 30 days" for the
   Feed, exact `startedAt`/`endedAt`) somewhere the tasks did not name: Task 6 greps every repo.
2. **The contract no longer parses** after edits (it already fails today at lines 513 and 543):
   Task 3 fixes both and every task touching the YAML re-runs the parse.
3. **The P9 exceptions lost** while rewording (own data, live status, protocol times): Task 2
   keeps them word for word.
4. **Hide and Stop sharing drift apart:** a hide keeps a tombstone in the window (C4); Stop
   sharing deletes (D5). Both the contract (Task 3) and carodo-app ADR 0007 (Task 5) must say so.
5. **The author's immediate view contradicts "nothing finer than 15 minutes"**: P9's
   "to the person themselves" exception must cover it explicitly (Task 2, Task 3 `/v1/feed`).

---

### Task 1: carodo-ios ADR 0007 amendment

**Files:**
- Modify: `carodo-ios/docs/decisions/0007-privacy-first-feed.md`

- [ ] **Step 1: Status line** — append `, 2026-11-19 (private by default: quarter-hour times, a
  7-day Feed that deletes itself)` to the amendments.
- [ ] **Step 2: "One worldwide Feed"** — "car drives from the last 72 hours" → "car drives from
  the last 7 days".
- [ ] **Step 3: "A Feed row"** — replace "or a time finer than the hour. The server keeps a drive's
  exact start and end for its own logic ("2h ago", the busiest hour, overlaps) and never sends
  them." with:
  "or a time finer than a quarter hour. The device sends its end rounded down to the quarter hour
  and its durations to the minute; the server never receives or keeps an exact time of a drive.
  Others see a drive from the next quarter hour after it ended, all of a quarter's drives at once in
  a random order; its author sees it at once."
- [ ] **Step 4: "Community numbers"** — "over 72 hours" → "over 7 days".
- [ ] **Step 5: new bullet after "Opt-in"** — **A Feed that deletes itself:** "a drive leaves the
  Feed after 7 days and is then deleted from the server with its shape, its item and the reactions
  on it; Stop sharing and account deletion delete at once. A hidden drive keeps only a tombstone
  (trip id, revision) until the window passes."
- [ ] **Step 6: Consequence "Plausibility"** — replace with: "the server refuses a drive that lasts
  more than 24 h or reports a figure out of range, and a time or figure not rounded as the contract
  says; overlapping drives are prevented on the device (the server no longer has exact times to
  compare); App Attest already rejects anything but the genuine app."
- [ ] **Step 7: Verify** — `grep -n "72\|finer than the hour\|overlaps another" carodo-ios/docs/decisions/0007-privacy-first-feed.md`
  Expected: no output.

### Task 2: invariant P9 in the three AGENTS.md

**Files:**
- Modify: `AGENTS.md` (workspace, item 9), `carodo-ios/AGENTS.md` (P9), `carodo-app/AGENTS.md` (P9)

- [ ] **Step 1: carodo-app `AGENTS.md` P9** — replace the first sentence (through "(carodo-ios ADR
  0007).") with:
  "P9. **Coarse at rest, coarse on the way out.** The backend never receives or keeps an exact time
  of a drive (the device rounds it to the quarter hour); it may keep exact times of its own
  protocol (sessions, challenges, jobs) and of a person's own acts shown only to them (a
  reaction's `created_at`). Nothing it sends to anyone else carries a time finer than a quarter
  hour, nor appears or disappears at a finer moment, and every such time goes through
  `services/shared/coarse-time.ts` (carodo-ios ADR 0007). The exceptions, and only these:"
  Then in "To the person themselves" append: ", and their own drives on the Feed before others see
  them". Keep the other exceptions and the last line word for word.
- [ ] **Step 2: carodo-ios `AGENTS.md` P9** — first sentence becomes: "P9. **Exact on the device,
  coarse to others.** The device keeps exact times; what it sends the backend about a drive is
  rounded to the quarter hour, and nothing another person sees carries a time finer than that (the
  server's `coarse-time.ts`; a share card says the local day and part of day)." Exceptions: append
  "their own drives on the Feed before others see them" to the person's own data. Rest unchanged.
- [ ] **Step 3: workspace `AGENTS.md` item 9** — same meaning as Step 2 in its wording: title
  "Exact on the device, coarse to others", "finer than the hour" → "finer than a quarter hour", the
  device rounds a drive's times before they leave it; own-data exception gains "their own drives on
  the Feed before others see them".
- [ ] **Step 4: Verify** — `grep -n "finer than the hour" AGENTS.md carodo-ios/AGENTS.md carodo-app/AGENTS.md`
  Expected: no output.

### Task 3: contract 0.29.0-draft

**Files:**
- Modify: `carodo-ios/docs/api/carodo-api.yaml`

- [ ] **Step 1: Make it parse** — quote the two `summary` values containing ": " (report at line
  513, block-author at line 543). Run:
  `ruby -ryaml -e 'YAML.load_file("carodo-ios/docs/api/carodo-api.yaml"); puts "ok"'`
  Expected: `ok`.
- [ ] **Step 2: info** — `version: 0.29.0-draft`; "over 72 hours" → "over 7 days" in the Feed V1
  line; add a changelog paragraph after 0.28.2:
  "0.29.0 (2026-11-19, private by default; breaking): `DriveInput` carries `endedQuarter` instead
  of exact `startedAt`/`endedAt`, durations in whole minutes and distance in 100 m, refused
  otherwise; the Feed covers 7 days, others see a drive from the next quarter hour after it ended,
  its author at once; a drive older than 7 days is deleted, and Stop sharing deletes at once
  (carodo-ios ADR 0007)."
- [ ] **Step 3: `DriveInput`** — remove `startedAt`, `endedAt`; `required` becomes
  `[revision, endedQuarter, localDate, localStartHour, partOfDay, distanceM, movingDurationS, elapsedDurationS, vehicle, weather]`; add:

```yaml
        endedQuarter:
          type: string
          format: date-time
          description: |
            When the drive ended, rounded down to the quarter hour in UTC (minutes 00, 15, 30 or 45,
            seconds 0); the only time of a drive the server receives. Refused (400 validation)
            off a quarter; (422 start_time_invalid) more than 15 minutes ahead of the server or more
            than two days from `localDate` (a drive of up to 24 h, in a zone up to 14 h from UTC,
            may end two UTC days after its local start day). Older than 7 days: answered 204 and not
            stored.
```

  and set `distanceM` `multipleOf: 100`, `movingDurationS` and `elapsedDurationS` `multipleOf: 60`,
  each description adding "rounded to the nearest minute (100 m) on the device; refused (400)
  when not". `elapsedDurationS` becomes `minimum: 60` (was 30: a drive shorter than a minute is
  sent as 60), `maximum: 86400`.
- [ ] **Step 4: `PUT /v1/feed/drives/{tripId}`** — description: drop "it lands in the Feed by when
  it was driven (carodo-app ADR 0007)" → "it lands in the Feed by its `endedQuarter`, and is not
  stored when that is older than 7 days"; add "Others see it from `endedQuarter` + 15 minutes; its
  author at once." `204` description adds ", or older than 7 days (not stored)". `400` adds "a time
  off a quarter, a duration not in whole minutes, a distance not in 100 m". `422` drops the
  `startedAt or endedAt implausible` wording for "`endedQuarter` implausible".
- [ ] **Step 5: `DELETE /v1/feed/drives/{tripId}`** — "keeps a tombstone with it for 30 days" →
  "keeps a tombstone (trip id and revision only) until the drive's 7 days have passed".
- [ ] **Step 6: `/v1/me/sharing` PUT** — summary "Turning sharing off deletes every published
  drive."; description: Stop sharing deletes the drives (no mark kept); turning sharing on again,
  the app republishes the car drives of the last 7 days that are not hidden; a hidden drive's
  tombstone is unaffected.
- [ ] **Step 7: `/v1/feed`** — summary "last 7 days"; description: "newest first by the quarter hour
  its newest drive ended, so a drive published late lands in its place; items inside one quarter
  come in a random order"; "Only drives from the last 7 days"; add "A drive is on the Feed for
  others from the quarter hour after it ended (`endedQuarter` + 15 min); a member's own drives are
  on their own page at once (P9, own data)."
- [ ] **Step 8: `/v1/feed/stats`, `CommunityStats`, reaction 404** — "72 hours" → "7 days";
  `windowHours: { type: integer, const: 168 }`; stats count only drives others can see.
- [ ] **Step 9: `Ago`** — description: "Coarse relative time from when others could first see the
  drive (its end's quarter hour + 15 min): "now" for the first hour, then "1h" to "23h", "1d" to
  "6d". Every change falls on a quarter hour (ADR 0007)." Pattern narrows to
  `"^(now|[1-9]h|1[0-9]h|2[0-3]h|[1-6]d)$"`.
- [ ] **Step 10: `DriveShape`** — "deletes it within 30 days" → "deletes it with the drive when it
  leaves the 7-day Feed, on Stop sharing or account deletion". `FeedItem` description: "No route,
  place, start/end or time finer than a quarter hour".
- [ ] **Step 11: `DELETE /v1/account`** — add to "At once": "its Feed drives, items and their
  reactions are deleted".
- [ ] **Step 12: Verify**
  Run: `ruby -ryaml -e 'YAML.load_file("carodo-ios/docs/api/carodo-api.yaml"); puts "ok"'` → `ok`.
  Run: `grep -n "72\|startedAt\|endedAt\|30 days" carodo-ios/docs/api/carodo-api.yaml`
  Expected: only non-Feed hits (`/v1/shares` route `t`, account erase "Within 30 days", username
  holds, renames); none in `DriveInput`, `/v1/feed*`, `Ago`, `CommunityStats`, `DriveShape`.

### Task 4: `sync.md` Publishing to the Carodo backend

**Files:**
- Modify: `carodo-ios/docs/sync.md` (section "Publishing to the Carodo backend", **Feed** and
  **Late is normal** bullets only; another session has edits further down)

- [ ] **Step 1: Feed bullet** — "start and end instants (server only, never returned)" → "its end
  rounded down to the quarter hour (`endedQuarter`, the only time sent)"; "durations, GPS distance"
  → "durations in whole minutes, GPS distance in 100 m"; "enqueues the car drives that ended in the
  last 72 hours" → "the last 7 days"; Stop sharing "removes every row on the server" → "deletes
  every row on the server".
- [ ] **Step 2: Late is normal bullet** — "(`startedAt`, `localDate`, `partOfDay`)" →
  "(`endedQuarter`, `localDate`, `partOfDay`)"; add "A drive older than 7 days when it arrives is
  not stored."
- [ ] **Step 3: Verify** — `git -C carodo-ios diff docs/sync.md` shows the other session's hunks
  unchanged plus only these two bullets.

### Task 5: carodo-app ADR 0007 amendment

**Files:**
- Modify: `carodo-app/docs/decisions/0007-event-time-comes-from-the-device-late-is-normal.md`

- [ ] **Step 1: Status** — add "; amended 2026-11-19 (quarter-hour times, carodo-ios ADR 0007)".
- [ ] **Step 2: "Two kinds of time"** — when it happened is `endedQuarter` (kept as `ended_quarter`,
  already coarse; no exact `started_at`, no `drove_at`), `localDate`, `partOfDay`. When the server
  learnt of it: no longer stored on drives (C6).
- [ ] **Step 3: "Device times are checked"** — `endedQuarter` refused off a quarter (400), more
  than 15 minutes ahead (422), more than two days from `localDate` (422); older than 7 days: 204,
  not stored (the "more than a year old" rule goes).
- [ ] **Step 4: "Revisions"** — tombstone "for 30 days" → "until the drive's 7 days have passed";
  add "Stop sharing deletes, keeps no mark".
- [ ] **Step 5: "Late drives count" and "The Feed orders by"** — the Feed orders by the quarter of
  the newest end (`sort_quarter`); a late drive appears where it was driven, if still inside the 7
  days. The leaderboard paragraph stays a future decision, with one line added: drives are kept 7
  days only and carry no server arrival time, so a board must keep its own totals and change cursor,
  decided when it is built.
- [ ] **Step 6: Consequence** — `drives` has `revision`, `ended_quarter`, `unpublished_at` and the
  index each one needs; the contract's `DriveInput` carries `endedQuarter`.

### Task 6: sweep, owner review, commits

- [ ] **Step 1: Sweep** — run
  `grep -rn "72 hours\|72-hour\|72h\|finer than the hour\|startedAt\|deletes shapes" carodo-ios/docs carodo-app/docs carodo-ios/AGENTS.md carodo-app/AGENTS.md AGENTS.md`
  Every hit is either fixed by Tasks 1–5 or listed for Parts 2–4 (`specs/feed.md`, `privacy.md`,
  backend `storage.md`, `architecture.md` are Part 4/the parts that change behaviour). Write the
  list into the spec's "Documents and code to change" if any hit is new.
- [ ] **Step 2: Owner review** — show the owner the diffs of Tasks 1–5 (P6). Wait for approval.
- [ ] **Step 3: Commit carodo-ios** (after approval)

```bash
cd carodo-ios
git add docs/decisions/0007-privacy-first-feed.md AGENTS.md docs/api/carodo-api.yaml
git add -p docs/sync.md   # only the Publishing hunks
git commit -m "docs(feed): private by default, quarter-hour times and a 7-day feed (contract 0.29.0)"
```

- [ ] **Step 4: Commit carodo-app**

```bash
cd carodo-app
git add AGENTS.md docs/decisions/0007-event-time-comes-from-the-device-late-is-normal.md
git commit -m "docs: quarter-hour feed times, tombstones within the 7-day window"
```

- [ ] **Step 5: Status** — set this plan's status to done with the two commit hashes; the spec's
  status to "Part 1 done".
