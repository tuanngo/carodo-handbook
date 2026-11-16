# CARODO source audit — 2026-11-12

## Second pass — current review at `066de55`

This section supersedes the first-pass status/counts and stale evidence below. No product code was changed. The first pass found 25 items; this pass adds 14, closes L03 and L05, and narrows M04. **37 findings remain open: 6 High, 17 Medium, 14 Low.** These counts include the carried-forward backend findings; they are not 37 newly found defects. H04 was already tracked as TD-17 and is newly included in this audit, not newly discovered.

### Coverage and limits

- iOS main stayed at `066de55` during this pass, including the merged Day feature and `9db0594` concurrency teardown fix. The initial/final dirty paths were the generated Xcode project, LaunchMark asset metadata (already staged), and setup docs; none were changed by this audit.
- Repository-wide inventory and pattern coverage: **593 Swift files, 100,001 lines**: app 396 files / 69,160 lines; widget 1 / 48; shared 0; tests 196 / 30,793. Source was searched across every production/test folder for error fallbacks, unstructured tasks, cancellation, unsafe conversions/decompression, ownership, persistence boundaries and localization use. Relevant tests were read alongside each reported path.
- Recording/Tracking/Location/Motion/Connections/Persistence/Sync/Backup/Outbox/Networking/Identity/Storage/Maintenance: 88 files / 13,471 lines inventoried and scanned, with detailed tracing of write failures, recovery, trim, backup imports, sync acknowledgment and Auto Mode callbacks. Five are empty scaffolds.
- Other Core directories: 111 files / 15,801 lines inventoried and scanned, including Domain, Atlas, Replay, Feed, Journal, Diagnostics, Recognition, Formatting, Narrative, PreviewData, Achievements, Repositories, Weather and Extensions. More than 90 had executable content read; Repositories was read in full separately. Large analysis/preview/evaluation files received pattern/partial review rather than complete line-by-line tracing.
- App/Features/DesignSystem/widget: 196 files / 39,813 lines inventoried and scanned; manually traced app orchestration and the principal models/callers for Day, Explore, detail/edit/trim/replay, Feed, Garage, Places, Passport, Backup and Onboarding. Rendering and SceneKit files were not all read line by line or exercised. Configuration adds the remaining two files / 123 lines. Repositories is already included in the other-Core inventory; its separate read does not add files. The authoritative unique totals are 397 production Swift files / 69,208 lines.
- Build/config/tooling reviewed: `project.yml`, `Taskfile.yml`, shared xcconfig, the checked-in package resolution (GRDB 7.11.1), app/widget plist setup, entitlements, privacy manifest, ignore rules, test structure and teardown-check policy. No dependency upgrade/advisory claim is made; a current external advisory database was not queried.
- All 17 app/widget String Catalogs parse as JSON; 1,278 keys inventoried. All feature/widget entries have EN and VI. InfoPlist/AppShortcuts platform conventions remain separate; this is not a new proof of every placeholder, dead symbol, translation quality or rendered layout.
- Backend working copy remains `9248ba4` plus existing modified/untracked files. Reopened the prior H03/M06–M09/L09–L12 evidence; those findings remain open. Executable content in all 50 API source files / 3,716 lines was read, including auth/input/storage boundaries; the pinned root certificate literal was treated as a fixed asset. Web layout/app/assets/privacy/env/index and the Wrangler wrapper were read; landing/terms/styles/brand received relevant-section scans. No additional high-confidence backend finding was established. This is not a new exhaustive read of every web/test file or a new backend runtime pass. The first-pass handbook script checks and alternate-worktree results remain historical; the Day findings are now checked in main.
- **Meaning of coverage:** every production folder and test folder is in the inventory/pattern sweep; all ranked new findings have concrete caller traces. This is broader than the first pass, but it is not a certification that every source line, execution branch, layout or dependency has been exhaustively audited. No deployed API, real account, iCloud service, physical-device drive, battery capture, VoiceOver session, iOS 18 runtime or real-location dataset was exercised. No private data was uploaded.

### Changes to previous findings

- **Still open:** H01–H03; M01–M03, M05–M09; L01–L02, L04, L06–L13. Old line numbers are first-pass snapshot references unless refreshed here. Backend wire mismatch remains a local integration blocker, not evidence of a deployed incident.
- **M01 extended:** `GRDBCloudSyncStore.swift:30–33,36–54,132–151` observes only pending operation IDs and removes duplicates. An edit during an in-flight save can preserve `ck_pending = 1` while the observed ID array never changes; `CloudSyncService.swift:214–234` only enqueues on emissions. Once the engine consumes that save, the newer local edit may wait until another queue change/restart. Keep transient build failures pending and ensure dirty rows after acknowledgment are re-enqueued. Test with a suspended send and an intervening edit, beyond the existing test that checks only the pending bit. Confidence High for observation suppression; full engine scheduling needs a fake-engine regression/device integration check.
- **M02 current evidence:** `JourneyDetailViewModel.swift:500–503` still saves vehicle and provenance separately.
- **M03 current evidence:** `CarodoApp.swift:49–65` still installs strong captures in callbacks held by container-owned services. Treat as an ownership/teardown defect; no measured battery drain is claimed for the app-lifetime container.
- **M04 partially addressed, narrower remaining scope:** `JourneyDetailViewModel.swift:365–368` now reads route-free `passportFacts` and calls batched `PlaceVisitLog.summaries`. Do not repeat the old claim of per-point count scans. `Features/Journeys/ViewModels/PlaceVisitsPage.swift:40–46` still reads all matching journeys and routes at once for their first point/origin and navigation. Prefer a lightweight paged visit projection and fetch a full journey on selection. Effort M, fix risk Medium, confidence High for excess data read; latency remains unmeasured. Retained at Medium as a scaling candidate, behind correctness work.
- **M08 extended:** the draft public privacy page also says GPS/history/odometer never leave the device (`carodo-app/apps/web/src/pages/privacy.tsx:33–43`), while private iCloud backup is implemented. Rewrite the whole data-path explanation, distinguishing private iCloud backup from public Feed summaries, alongside the exact-time correction. This is a copy/implementation mismatch, not a finding that private iCloud backup violates product policy.
- **L12 narrowed:** `favicon.ico` has a valid redirect; the unsupported advertised assets are apple-touch-icon and icon-192/icon-512.
- **M05 current evidence:** `PlaceVisitsView.swift:303–323` still formats row dates in the recorded zone but groups months/compares years with `Calendar.current`.
- **L03 resolved:** `PlaceVisitsView.swift:345–349` now uses `PlaceMapMarker` and `DetectedPlaceMarker`.
- **L05 resolved:** `JourneyActivityCalendar.swift:144–149` now uses the catalog's `activityDayValue`.
- **L08 remains a cleanup lead:** example obsolete keys still exist, but the old count of 19 unreferenced keys was not recalculated. Do not use that count as the current removal list.
- **L13 is now on main:** `Carodo/Features/Journeys/Views/JourneyDayCalendar.swift:155–156` still offers Next Week unconditionally. The former Day worktree path is historical.

### Additional High findings

#### H04 — Device installation mistakes a failed database read for a first install

**Evidence.** `carodo-ios/Taskfile.yml:35–46` returns failure when the database cannot be copied. `:228–242` treats every such failure as “no database yet (first install)”, then `:245–261` proceeds to install without the schema-erase confirmation. `DatabaseManager`'s DEBUG schema reset can then erase an existing journal. This is the already recorded TD-17, omitted from the first audit's findings.

**Impact and fix.** A locked/disconnected phone or copy error can bypass the guard protecting test drives before a schema-changing install. Distinguish confirmed absence of app/database from unreadability and abort the latter before install. Test the shell decision paths with fake command results: absent, readable unchanged, changed, locked/read failure. No deletion or physical-phone failure was induced. Effort S, fix risk Low, confidence High. Development tooling only; this does not establish a RELEASE erase path.

#### H05 — Editing unknown journey metadata can erase an existing name or note

**Evidence.** `JourneyDetailViewModel.swift:305` enables Edit without requiring metadata to load; initial details are empty and `:637` also substitutes `.empty` for a failed read. `JourneyDetailView.swift:109–113` seeds the editor from those fields; `JourneyDetailViewModel.swift:311–317` saves both and `GRDBJourneyRepository.swift:1643–1648` replaces both columns. `JourneyEditSheet.swift:18–23` retains the blank initial state.

**Impact and fix.** With an existing note, opening Edit before metadata arrives or after a read failure and entering a new title saves a blank note over the unseen one. Model metadata loading/failure distinctly and allow metadata editing only after a successful read. Add suspended-read and failed-read regressions proving a stored note/name survives; retain the other detail controls' independent availability. `JourneyDetailViewModelTests.testAFailedDetailsReadStillLoadsTheVehicles` currently verifies fallback without protecting edit eligibility. Effort M, fix risk Low, confidence High.

#### H06 — Hide reports success after its durable privacy change failed

**Evidence.** `FeedPublisher.swift:95–102` catches persistence errors and returns normally; `DependencyContainer.swift:300–305` forwards a `Void` action. `FeedDriveShareRow.swift:47–50` then sets `.hidden` unconditionally, and its switch at `:71–76` changes state before the await without rollback. `FeedPublisherTests.testHideRemovesTheRowAndKeepsItHidden` covers only success.

**Impact and fix.** If hidden-state/outbox persistence fails, unpublish was never queued, yet the row tells the person their drive is hidden. This is separate from H02's overlap race. Propagate a typed error/result through the action and preserve/reconcile the prior state with visible failure unless the hidden state and outbox message were durably committed. Test failed local persistence and successful local hide while transport is offline separately. Effort M, fix risk Medium, confidence High. Current Feed transport is device-local; no production exposure is established.

### Additional Medium findings

#### M10 — Backup input can exhaust memory or CPU before being rejected

**Evidence.** `BackupFileAccess.swift:8–14` loads the entire external file. `BackupFile.swift:63–71,102–110` accepts any positive UInt32 PBKDF2 iteration count and derives the key before authentication; `:83–84` decompresses zlib without an output bound. `BackupTests.swift:51–80` checks round trips, passwords and a changed header, without resource-budget boundaries. The packed-track decoder already demonstrates bounded streaming decompression.

**Impact and fix.** A damaged/untrusted file can cause excessive allocation or lengthy derivation; iOS can terminate the process, including an active recording. Bound input bytes before allocation, stream decompression under a documented expanded-size budget and validate the supported KDF range before computation. Test limits with small synthetic payloads; do not run a resource-exhaustion demonstration on a live drive. Choose limits against large legitimate histories rather than an arbitrary small cap. Effort M, fix risk Medium, confidence High for missing limits; no exhaustion runtime was executed.

#### M11 — Interrupted Trim leaves persisted bounds and derived figures inconsistent

**Evidence.** `JourneyTrim.swift:31–35` commits trim bounds, reads the track and writes its summary in separate awaited operations. `GRDBJourneyRepository.swift:1887–1898` does not dirty `recorder_version`; launch refresh selects only older versions at `:1006–1014`. Join/split already invalidate that version for interruption recovery.

**Impact and fix.** Failure/termination after the first transaction leaves trimmed raw reads but the previous route and totals, and relaunch need not repair them. Mark the summary dirty atomically with the trim, clear it only after successful derivation, and ensure a stale derivation cannot overwrite a newer trim. Test stopping immediately after `setTrim` and running launch refresh, plus injected derive/write failure. Effort S–M, fix risk Low, confidence High.

#### M12 — A late location answer can recreate a removed parking geofence

**Evidence.** `CoreLocationServices.swift:125–135` sets `anchorWhenLocated` before requesting a fix. `:164–172` removes parking state without clearing this pending flag. The callback at `:239–242` calls `placeSpot` before the current-service guard at `:245`.

**Impact and fix.** A request begun in standby can finish after Auto Mode was switched off or recording began, restoring a geofence the new mode removed. Cancel/invalidate pending parking intent when removing the service and gate callback application against the current mode/request generation. Add a delayed-callback regression at the location-manager boundary; callback scheduling and power effects remain a device check. Effort S–M, fix risk Low, confidence High for the source path.

#### M13 — An older failed reaction rolls back newer Feed state

**Evidence.** `FeedViewModel.swift:164–177` saves the entire old item and restores it on failure without checking request/list generation. `FeedView.swift:174` starts an independent task per tap. Existing tests exercise sequential reaction/toggle and a single refusal, not overlapping requests/refresh.

**Impact and fix.** An older failure can overwrite a later successful choice or refreshed counts. Serialize/coalesce desired reactions per item, or associate reconciliation/rollback with a matching generation and ensure the final server choice agrees. Test reversed completion order, failure after a later success, and refresh during an in-flight reaction with a controllable repository. Effort M, fix risk Medium, confidence High. Current transport is local; asynchronous boundary behavior matters before integration.

#### M14 — Place-only changes fail to refresh map markers and cached visit counts

**Evidence.** `PlacesView.swift:144–146` emits a journal change and `MapAtlasView.swift:277–279` reloads, but `MapAtlasViewModel.swift:281` advances `dataRevision` only if routes changed. Place save updates only `places` (`GRDBPlaceRepository.swift:34–42`), while route versions read trip columns (`GRDBJourneyRepository.swift:176–201`). Layer request uses route revision; visit summaries at `MapAtlasViewModel.swift:459–464` key only route revision, place IDs and count. Matching uses center/radius and overlapping-place priority.

**Impact and fix.** Moving/resizing a place with the same ID can leave a marker unchanged until the map moves; even after geometry reloads, callouts can retain old counts/latest visits. Invalidate place presentation and summaries with matching-relevant place content/revision, and check revision again after awaited summary work. Test same-ID center/radius changes with unchanged route versions and a refresh while calculation is suspended. Effort S–M, fix risk Low, confidence High; no measured frame-time claim.

#### M15 — Valid imported amounts can overflow the Garage fuel total

**Evidence.** `FuelLog.swift:117–127` accepts any positive Int amount with a currency; `BackupDocument.swift:185–192` relies on that validation. `GRDBBackupStore.swift:93–99` imports those rows, and the CloudKit merge uses the same entry conversion. `FuelLog.swift:201–206` adds monthly amounts with unchecked Int arithmetic; `VehicleDetailViewModel.swift:47–48` reads the result for the screen.

**Impact and fix.** Two individually accepted same-month amounts can exceed Int capacity and trap when Garage computes the total. Define reasonable shared amount bounds and use checked aggregation with an explicit unknown/error outcome instead of wrapping, clamping to a factual total, or crashing. Test synthetic imported extreme amounts and the aggregate boundary; preserve per-currency separation. Effort M, fix risk Medium, confidence High from static reachability; no crash demonstration was run.

#### M16 — Heat indexing takes the long way across longitude 180°

**Evidence.** `RouteHeat.swift:374–394` uses raw longitude subtraction for step count, length and interpolation; `:175–177` visits every resulting step. Default cells are 20 m (`:61`). `HistoryAtlas.swift:88–95` already normalizes the shortest wrapped displacement for Footprints.

**Impact and fix.** A short valid segment crossing the antimeridian is treated as nearly 360°, producing a world-spanning false path and millions of unnecessary steps/cells. Normalize wrapped displacement consistently for length/steps/interpolation and normalize resulting coordinates; reuse a suitable existing geometry helper. Add a synthetic crossing test asserting short length, bounded steps and local cells, alongside ordinary segments. Effort M, fix risk Medium, confidence High for the arithmetic; no memory-stress benchmark was run.

#### M17 — Device database copies silently accept a failed WAL read

**Evidence.** `Taskfile.yml:38–46` copies the main database, ignores sidecar copy errors (`|| true`), then accepts it after changing journal mode. `DatabaseManager.swift:8–20` uses WAL, where recent committed pages may still be only in `-wal`.

**Impact and fix.** An absent WAL is normal, but an unreadable existing WAL can produce an apparently valid older database copy with missing drives. Before an approved schema erase this can invalidate the only safety backup. Distinguish confirmed absence from copy failure, fail closed on an incomplete copy, and obtain/verify a consistent database snapshot rather than assuming separately copied live files are coherent. Test missing vs failed WAL, a database whose newest committed rows are WAL-only, and restore verification. Effort M, fix risk Medium, confidence High for ignored error handling; actual loss frequency and live-copy consistency were not measured. Pair with H04 before the next schema-changing install.

### Additional Low findings

#### L14 — A failed sharing read can still show a join invitation

**Evidence.** `FeedViewModel.swift:61–69` promises no invite on failed reads but folds sharing failure into false and calls `latestCarDrive()`.

**Impact and fix.** The screen offers joining/start-sharing despite unknown current sharing status. Distinguish unknown/error from a confirmed disabled setting; add a failing-sharing-read regression asserting no invitation. Effort S, fix risk Low, confidence High.

#### L15 — Twenty pending drives can hide the actual newest confirmed journey

**Evidence.** `JourneyStatisticsService.swift:30–33` fetches 20 rows before filtering `!isPending`; `JourneysViewModel` uses this result for its latest-drive presentation.

**Impact and fix.** A journal with 20 recent pending drives and an older confirmed drive can return no latest confirmed journey. Filter eligibility before LIMIT, or continue paging without an arbitrary cutoff. Test 20 pending rows plus an older confirmed one and the all-pending case. Effort S, fix risk Low, confidence High.

#### L16 — Cloud payload decoding ignores its incompatible-version gate

**Evidence.** `CloudRecordCoding.swift:42–45` says version rises only for incompatible changes, but decoding at `:70–71` and incoming validation at `:122–127` never compare it with the supported version.

**Impact and fix.** An older build can accept a future incompatible record retaining familiar required fields, then rewrite it in version 1 after an edit. Reject unsupported versions explicitly while retaining optional-field forward compatibility within version 1; test both cases. Effort S, fix risk Low, confidence High for the missing gate. This is a multi-version release safeguard, not a currently deployed data-loss incident.

### Recommended order for owner review

1. **Protect existing drives first:** H01 (failed sample writes must block completion/settlement), H04 + M17 (safe device-copy/install guard), H05 (metadata editing), M11 (recoverable Trim). Each needs fault-injection/interruption tests before refactoring its code.
2. **Make privacy actions truthful and ordered:** H02 + H06 together, then M01 including edit-during-send. A durable local Hide is distinct from a pending remote acknowledgment; test offline and stale completions explicitly.
3. **Bound foreign input and eliminate reachable traps:** M10 + M15, followed by L16 before multi-version iCloud rollout. Define compatible limits first; a changed file/API/schema contract needs owner approval.
4. **Repair lifecycle and visible-state correctness:** M12, M14, M13 and M02; then M05/M06. Keep changes small and test the failing sequence rather than broad service/view rewrites.
5. **Before real Feed integration:** resolve H03 against the approved canonical contract; apply M07/M08 and shared request/response fixtures. Mock-only tests cannot close this gate. Public-web Vietnamese support M09 remains a product scheduling choice, not a recording blocker.
6. **Later or with a matching trigger:** M04 measurement, M16 global-route edge case, L14–L16, and low-severity dead-code/copy/accessibility cleanup. Do not schedule a broad rewrite or add new features merely because the inventory is large.

This is an audit/prioritization result awaiting owner selection; it is not approval to implement any item. No schema, API, permission, entitlement, dependency, deployment or product behavior changed. Open audit work is indexed in technical debt as TD-20; H04 also retains its existing TD-17 identity.

### Fresh verification for this pass

- `task lint` — exit 0; no Swift-format violations. Initial Xcode environment/cache diagnostic messages were not compiler warnings.
- `git diff --check` in iOS — exit 0. Existing owner changes were preserved.
- Python JSON parsing/inventory over the 17 catalogs — success; 1,278 keys, no missing EN/VI feature/widget entries. This does not substitute for `LocalizationTests`' other checks.
- `xcodebuild test -project Carodo.xcodeproj -scheme Carodo -destination 'platform=iOS Simulator,id=E95BFC8D-814F-413A-9B5A-552A6A67662F' -quiet -resultBundlePath /private/tmp/carodo-source-audit-second-20261112.xcresult` — exit 0. `xcrun xcresulttool get test-results summary --path /private/tmp/carodo-source-audit-second-20261112.xcresult --format json` reports **1,916 passed, 11 skipped, 0 failed**, 1,927 total, iOS 27.2 / iPhone 18 Pro Simulator. Log: `/private/tmp/carodo-source-audit-second-20261112.log`.
- The result bundle still reports **one runtime thread-priority inversion warning** (user-interactive waiting on default QoS); responsible call site was not established. Do not claim a warning-free runtime. A fresh clean `task warnings` and iOS 18/26.0 compatibility runs were not performed in this pass; the existing teardown fix is present but not independently certified across those OS versions here.
- No new regression tests were added (source remains untouched); a passing existing suite does not disprove the new fault/race findings. Device checks remain required for background recording, lock/WAL behavior, callback ordering, termination recovery, battery, iCloud and UI accessibility/layout.

### Considered and not promoted

- Day's device-calendar assignment is an accepted deferred decision (TD-18), not another newly counted time-zone bug. M05 is an internal disagreement between a page's month heading and its recorded-zone rows.
- App-lifetime strong captures are not evidence of measured battery drain; M03 is limited to ownership and teardown.
- Authentication/networking/widget scaffolds are documented as unwired; their absence is not a newly discovered regression. The current API example URLs and unused secret/config scaffolds do not prove any live request uses them.
- Developer-only trip reports intentionally include exact location and Developer identifiers after explicit sharing; no new public-log leakage was established from those paths. Do not treat the report's opt-in contents as Feed disclosure.
- Backend malformed DER handling was traced through caught parse/import errors; no unhandled-error finding was established. The bounded public-cache revocation delay is explicitly accepted in backend ADR 0008, so it is not counted as a new authorization defect.
- No broad dependency migration, SwiftUI rewrite, accessibility-size policy reversal or new cloud service is proposed by this audit.


## First-pass record — historical snapshot

The following records the earlier pass and its verification. Its original count, scopes and line numbers are historical; the second-pass section above controls current status and priorities. In particular, L03 and L05 below are resolved and M04 has been narrowed.

Status: open findings and proposed fixes. Severity reflects product impact: High for potential recording loss, a privacy control being undone, or an integration blocker; Medium for material correctness, reliability, or maintenance risk; Low for narrower user-facing or maintenance issues. Fix effort is S (hours), M (roughly a day), or L (multiple days). Locations are relative to the CARODO workspace and refer to the working copies inspected.

Findings: 25 total, including 3 High, 9 Medium, and 13 Low.

## Scope and coverage

- `carodo-ios` on `main`, initially `aa3808e` with seven modified files, moved to `7e6499e` during the audit with additional local changes. Inventoried the app, tests, widget, shared Swift, configuration, and developer tooling. Inspected recording, persistence, sync, Feed, journal, map, Garage, and UI paths for the reported issues. Rechecked affected Place Visits and map findings against the later working copy. This was a live workspace, so not every result is from an identical snapshot.
- `carodo-app` on `main` at `9248ba4`. Included modified and untracked API, database, web, configuration, scripts, tests, and docs. Compared the backend’s older Feed contract with the current iOS canonical contract and client. Local Workers checks exercised the backend and web independently.
- `carodo-ios-day` on `feat/journeys-day` at `6373615`. Reviewed the local Day/Explore delta, including six untracked Swift files, calendar queries and state, labels, accessibility, and localization. `carodo-ios-feed-v1` is a clean worktree at `e4eea4e`, an ancestor of `main`; it has no independent changes to audit and was linted separately.
- `carodo-handbook` on `main` at `a643b81`. Inventoried 24 code-like design and export files, inspected active render scripts, and checked syntax of tracked Python, shell, and JS sources. Historical vehicle-art experiments and preview assets were inventoried without detailed runtime review. Reviewed the workspace and repository `AGENTS.md` files, the handbook workflow, and relevant specs and ADRs as the basis for findings.
- Parsed 17 main iOS and widget catalogs. The initial scan covered 1,250 keys and 19 pluralized entries. The later working copy had 1,260 keys and 20 pluralized entries. Checked JSON, feature/widget EN and VI coverage, placeholder signatures, plural variants, and feature key references. A second coverage and placeholder pass found no issues in 1,254 main feature/widget keys or 1,237 Day feature/widget keys. The InfoPlist metadata fallback and intentional source-language keys were reviewed separately. The status widget has three translated labels.
- This is a static and local-test audit with repository-wide inventory and targeted tracing. It does not certify every code path. Excluded generated output, dependency internals, real drive data, credentials, deployed services, and live account/iCloud data. Physical-device recording, VoiceOver and Dynamic Type rendering, Files metadata, and cross-repo runtime integration were not verified.

## High

### H01 — A drive can be marked complete after a sample write failed

**Evidence.** `carodo-ios/Carodo/Core/Recording/TripWriter.swift:88–99,226–247` records a failed append, then still processes completion and calls `onSettled`. `carodo-ios/Carodo/Core/Persistence/GRDBJourneyRepository.swift:370–372,394–448` packs the surviving data and writes completed/sync-pending state. `carodo-ios/Carodo/App/CarodoApp.swift:57–65` reacts by running settlement and refreshing the journal. `carodo-ios/CarodoTests/TripWriterTests.swift:118–131` exercises retry after failed confirmation and acknowledges the first completion write. See `carodo-ios/AGENTS.md:144–156` for recording and recovery constraints.

**Impact and fix.** An exit before manual retry can leave a completed, partial route outside unfinished-drive recovery. Hold completion and settlement until required writes for that trip succeed. Replay the failed operations before completion and test interruption between failure and retry. Effort M, fix risk High, confidence High.

### H02 — An in-flight Feed publish can undo Hide

**Evidence.** `carodo-ios/Carodo/Core/Feed/FeedPublisher.swift:95–102,120–136` checks visibility and revision before asynchronous reads, then commits `.published` without checking either again. `carodo-ios/Carodo/Core/Persistence/FeedStateStore.swift:25–40` accepts a transition out of hidden. Publish and unpublish share a replaceable outbox key (`carodo-ios/Carodo/Core/Outbox/OutboxOperation.swift:25–30`, `carodo-ios/Carodo/Core/Outbox/OutboxStore.swift:23–35`). This conflicts with revocable sharing in `carodo-ios/AGENTS.md:107–110` and `carodo-ios/docs/sync.md:197–198`.

**Impact and fix.** The local transport can lose the hidden state or pending unpublish during overlapping work. iOS currently uses a mock Feed transport, so this is a pre-integration privacy defect. Make Hide’s revision allocation and queue update atomic. Make publish conditional on the revision and eligibility still matching, and test both completion orders. Effort M, fix risk Medium, confidence High.

### H03 — iOS and backend implement incompatible Feed contracts

**Evidence.** The canonical `carodo-ios/docs/api/carodo-api.yaml:85–91,419–431,470–478,925–955,1008–1021,1150–1154` and Swift `carodo-ios/Carodo/Core/Networking/FeedAPI.swift:47–59,80–111` define sharing preferences, `/v1/feed/drives/{tripId}`, an object-shaped route summary, and required response fields such as `isAuthor` and reactions. The backend requires different claim flags (`carodo-app/apps/api/src/services/accounts/claim.ts:51–77`), registers `/v1/drives/:tripId` (`carodo-app/apps/api/src/routes/drives.ts:14–33`), expects nested integer points (`carodo-app/apps/api/src/services/drives/input.ts:154–167`), and returns stable author IDs, username, and vehicle (`carodo-app/apps/api/src/services/feed/items.ts:37–68,82–85,107–115`). Its query has no 72-hour cutoff and groups by UTC hour (`carodo-app/apps/api/src/services/feed/read.ts:71–86,111–137`, `carodo-app/apps/api/src/services/feed/items.ts:70–79`). The backend documents its older baseline in `carodo-app/docs/architecture.md:8–32`. See the canonical-contract rules at `carodo-app/AGENTS.md:64–66,134–140,169–170`.

**Impact and fix.** Connecting the current iOS client would break enrollment/publish and nonempty Feed decoding. The old response also exposes author and vehicle details beyond the current V1 privacy contract and can return older drives. Confirm the authoritative version before integration, align routes, validators, cutoff, grouping, and public projections, then run shared contract fixtures against both implementations, including anonymous and self reads. Effort L, fix risk High, confidence High. This is a local integration blocker, with no deployment impact established.

## Medium

### M01 — CloudKit can stop retrying a pending record after local I/O fails

**Evidence.** `carodo-ios/Carodo/Core/Sync/CloudSyncService.swift:246–284` removes a pending engine entry whenever the record builder returns nil. That return also covers thrown DB, file-write, and encoding errors. `carodo-ios/Carodo/Core/Persistence/GRDBCloudSyncStore.swift:29–33` deduplicates identical queue observations. See `carodo-ios/docs/sync.md:77–81,205–209`.

**Impact and fix.** A record can remain pending in the database without the engine retrying it in the current session. Model missing and transient failures separately, keep transient failures eligible for retry, surface failure state, and test an injected read or asset-write failure. Effort M, fix risk Medium, confidence High.

### M02 — Vehicle assignment persists the vehicle and its source separately

**Evidence.** `carodo-ios/Carodo/Features/Journeys/ViewModels/JourneyDetailViewModel.swift:512–527` awaits vehicle and source writes separately. `carodo-ios/Carodo/Core/Persistence/GRDBJourneyRepository.swift:323–349` performs separate revision/sync transactions. Its `answer(.drove)` path already applies related changes atomically at `:1437–1454`.

**Impact and fix.** A failed second write can leave a new vehicle with old provenance or stale UI. Update vehicle, provenance, and sync revision in one repository transaction. Exercise clearing, replacement, and failure in a regression test. Effort M, fix risk Medium, confidence High.

### M03 — App-lifetime service callbacks form retain cycles

**Evidence.** `carodo-ios/Carodo/App/CarodoApp.swift:49–65` assigns closures to permission and recording services that strongly capture the container owning those services. Callback properties are declared in `carodo-ios/Carodo/Core/Recording/TripWriter.swift:56` and `carodo-ios/Carodo/Core/Location/LocationPermissionManager.swift:14`. See `carodo-ios/AGENTS.md:314–315` for the long-lived-service capture rule.

**Impact and fix.** Container teardown cannot release the cycle, including services and observers reachable through it. Capture owners weakly at the callback boundary and preserve their lifetime only for in-progress work. Verify teardown with a lifetime test. Effort S, fix risk Low, confidence High for the static ownership cycle.

### M04 — Place Visits repeats history scans and decodes routes for endpoint reads

**Evidence.** `carodo-ios/Carodo/Features/Journeys/ViewModels/JourneyDetailViewModel.swift:362–406` derives counts and later filters visit history again. `carodo-ios/Carodo/Core/Domain/PlaceVisitLog.swift:24–50` performs place matching across the input journeys. `carodo-ios/Carodo/Core/Persistence/GRDBJourneyRepository.swift:128–147,1130–1147` loads journeys with routes, while `carodo-ios/Carodo/Core/Persistence/GRDBPlaceRepository.swift:71–96` already demonstrates an endpoint-only read. The view regroups visits in `carodo-ios/Carodo/Features/Journeys/Views/PlaceVisitsView.swift:29–42,159–164`. See `carodo-ios/AGENTS.md:287–290,369` and `carodo-ios/docs/architecture.md:210–219`.

**Impact and fix.** History size increases route decoding and repeated matching on a user-facing path. Build one batched visit projection with the required endpoint metadata, reuse it for counts and rows, and fetch detailed journey data on navigation if needed. Benchmark a large synthetic history and preserve matching behavior. Effort M, fix risk Medium, confidence High for repeated work. User-visible latency is unmeasured.

### M05 — Place Visits can show a December visit under November

**Evidence.** `carodo-ios/Carodo/Features/Journeys/Views/PlaceVisitsView.swift:34–36,143–164` formats a row in its recorded time zone but groups months and compares years using the device calendar. A synthetic arrival at 17:30 UTC on November 30 is December 1 in Vietnam and November 30 in California. `carodo-ios/docs/data-model.md:17–21` documents recorded-zone presentation.

**Impact and fix.** Sections and the year shown can disagree with the row after travel. Group by recorded-zone year/month components, use a stable representative date to format the heading, and apply the same zone to year omission. Test month and year boundaries in both locales. Effort S, fix risk Low, confidence High.

### M06 — Username validation and instructions omit documented punctuation rules

**Evidence.** `carodo-ios/docs/api/carodo-api.yaml:848–854` and `carodo-ios/docs/decisions/0008-join-with-a-username.md:9–11` restrict leading, trailing, and repeated punctuation. `carodo-ios/Carodo/Core/Domain/Username.swift:16–24` and `carodo-app/apps/api/src/services/accounts/usernames.ts:45–57` enforce length and character set but accept names such as `.minh` and `minh__car`. `carodo-ios/Carodo/Resources/Localization/Feed.xcstrings:473–486` gives only the shorter rule.

**Impact and fix.** Accounts can be created with names outside the contract, and later enforcement could strand existing names. Align validators and fixtures for new claims while preserving stored-name decoding. Add EN “Start and end with a letter or number. Don’t repeat dots or underscores.” and VI “Bắt đầu và kết thúc bằng chữ hoặc số. Không lặp dấu chấm hay dấu gạch dưới.” Effort M, fix risk Medium, confidence High.

### M07 — Write limits run after assertion verification and storage work

**Evidence.** `carodo-app/apps/api/src/routes/drives.ts:12–14` and `carodo-app/apps/api/src/routes/live.ts:11–12` run the per-key write limiter after assertion middleware. `carodo-app/apps/api/src/http/auth.ts:67–82` performs assertion processing and storage work first. `carodo-app/AGENTS.md:124` and `carodo-app/docs/cost.md:115–120` require inexpensive rejection before expensive processing.

**Impact and fix.** Requests that are rejected by the write limit still spend verification and database work and can advance assertion state. Apply the limiter after token verification resolves the key and before the expensive assertion path. Preserve required authentication semantics and cover the rejection order in Workers tests. Effort S, fix risk Medium, confidence High.

### M08 — The public privacy page promises device-side time rounding

**Evidence.** `carodo-app/apps/web/src/pages/privacy.tsx:60–64` says times are rounded before transmission. `carodo-ios/Carodo/Core/Networking/FeedAPI.swift:63–77` encodes the exact start, and `carodo-app/apps/api/src/services/drives/input.ts:44–48,78–85` and `carodo-app/apps/api/src/services/drives/publish.ts:44–48,75–83` accept and store it. `carodo-app/AGENTS.md:73–81` permits exact internal time and requires coarse public time.

**Impact and fix.** The public copy misstates the data path if shipped. Align the page and its tests with the approved behavior. Suggested EN “The server uses exact drive times to process your summary. Other readers see the age in whole hours or coarser.” Suggested VI “Máy chủ dùng giờ chính xác để xử lý bản tóm tắt chuyến đi. Người khác chỉ thấy thời gian đã qua tính theo giờ hoặc đơn vị lớn hơn.” Effort S, fix risk Low, confidence High.

### M09 — The public web has no Vietnamese rendering path

**Evidence.** `carodo-app/apps/web/src/layout.tsx:24,47–63` hardcodes the document language and navigation in English. `carodo-app/apps/web/src/pages/landing.tsx:13–34,43–71`, `carodo-app/apps/web/src/pages/privacy.tsx:19–32`, `carodo-app/apps/web/src/pages/terms.tsx:13–26`, and `carodo-app/apps/web/src/app.tsx:37–43` render English-only landing, policy, and fallback pages. `carodo-ios/docs/copy-and-localization.md:3–5` calls for shared keys when the share page is built. The current landing and policy pages are an EN–VI coverage gap in this audit scope; the share-page-specific rule does not establish a requirement for those current pages.

**Impact and fix.** Vietnamese readers get English copy across the public site. Localize the templates with a typed EN/VI catalog, preserve the selected locale across navigation and fallback routes, and set `html lang` accordingly. For example, EN “Privacy Policy” and VI “Chính sách quyền riêng tư.” Effort M, fix risk Medium, confidence High.

## Low

### L01 — Joined journey presentation is copied into four repository reads

**Evidence.** `carodo-ios/Carodo/Core/Persistence/GRDBJourneyRepository.swift:62–70,119–122,139–147,1698–1705` independently assigns the joined end timestamp and end reason. See `carodo-ios/AGENTS.md:287–290`.

**Impact and fix.** A later joined-trip rule can drift among ID, journal, and history reads. Extract one joined-record projection, preserve query-specific ordering, and test both end fields across read paths. Effort S, fix risk Low, confidence High.

### L02 — Unreferenced design-system views remain in the product tree

**Evidence.** Source searches found declarations only for `MetricTile` and `JourneyRow` (`carodo-ios/Carodo/DesignSystem/Components/JourneyComponents.swift:3,45`), `StampRing` (`carodo-ios/Carodo/DesignSystem/Components/PassportMarks.swift:58`), and `CarodoFilterMenu` (`carodo-ios/Carodo/DesignSystem/Components/CarodoFilterMenu.swift:5`). `carodo-ios/docs/design-system.md:282,428–441` still presents unused views as current. See `carodo-ios/AGENTS.md:367–368`.

**Impact and fix.** Dead alternatives obscure the supported components and can be reused accidentally. Check previews and any generated references, remove confirmed dead views and corresponding documentation entries, and build affected targets. Effort S, fix risk Low, confidence High for the source reference check.

### L03 — Place Visits draws its saved-place map marker outside the design system

**Evidence.** `carodo-ios/Carodo/Features/Journeys/Views/PlaceVisitsView.swift:173–186` uses `SettingsIcon` as the pin. `carodo-ios/AGENTS.md:340–342` names `PlaceMapMarker`, implemented at `carodo-ios/Carodo/DesignSystem/Components/PlaceStyle.swift:28`.

**Impact and fix.** Saved-place markers can diverge between maps. Route saved roles through `PlaceMapMarker` and use the corresponding shared variant for detected places. Effort S, fix risk Low, confidence High.

### L04 — Garage numeric keys and amount fields can disagree on decimal notation

**Evidence.** `carodo-ios/Carodo/Features/Garage/Views/NumberKeypad.swift:39–44` displays the device decimal separator. `carodo-ios/Carodo/Features/Garage/Views/LogEntryParts.swift:18–24`, `carodo-ios/Carodo/Features/Garage/Views/ExpenseEntrySheet.swift:136`, `carodo-ios/Carodo/Features/Garage/Views/FuelEntrySheet.swift:379`, and `carodo-ios/Carodo/Core/Formatting/Money.swift:84–92` format an amount with the currency locale. `carodo-ios/Carodo/Features/Garage/Views/FuelEntrySheet.swift:75–76` also offers a decimal action in cases that `carodo-ios/Carodo/Core/Formatting/NumberEntry.swift:27–29` ignores.

**Impact and fix.** A Vietnamese device can show a comma on the key and a period in a USD amount, or an inert decimal key for a VND total. Pass the active field’s display separator and fractional capability into the keypad. Give the key EN “Decimal separator” and VI “Dấu thập phân,” and test mixed device/currency locales. Effort S, fix risk Low, confidence High.

### L05 — Activity summary builds a plural outside the String Catalog

**Evidence.** `carodo-ios/Carodo/Features/Journeys/Views/JourneyActivityCalendar.swift:231–234` manually chooses singular/plural and assembles count and distance. `carodo-ios/Carodo/Resources/Localization/Common.xcstrings:527` already contains a pluralized count. See `carodo-ios/AGENTS.md:327–334` and `carodo-ios/docs/copy-and-localization.md:60–66`.

**Impact and fix.** Formatting and word order cannot be owned by the translator and can drift from other summaries. Reuse the pluralized count inside a localized count-and-distance message. Example EN “1 drive · 3.8 km” and VI “1 chuyến · 3,8 km.” Effort S, fix risk Low, confidence High.

### L06 — The Journeys add-button VoiceOver hint describes only part of the menu

**Evidence.** `carodo-ios/Carodo/Resources/Localization/Garage.xcstrings:23–36` names fill-up and odometer, and `carodo-ios/Carodo/Features/Journeys/Views/JourneysView.swift:89–99` applies the hint. `carodo-ios/Carodo/Features/Garage/Views/VehicleActionsSheet.swift:58–77` includes charging and expenses.

**Impact and fix.** VoiceOver users can miss available actions. Use EN “Opens vehicle log options” and VI “Mở các mục ghi chép cho xe.” Effort S, fix risk Low, confidence High for the static mismatch.

### L07 — Deleted-vehicle text breaks the Vietnamese glossary spelling

**Evidence.** `carodo-ios/Carodo/Resources/Localization/Garage.xcstrings:653–666`, used by `carodo-ios/Carodo/Features/Garage/Views/VehicleDetailView.swift:43–44`, says “Xe này đã bị xóa.” `carodo-ios/docs/copy-and-localization.md:168` specifies “Xoá.”

**Impact and fix.** The screen differs from surrounding deletion copy. Use VI “Xe này đã bị xoá” with EN “This vehicle was removed.” Effort S, fix risk Low, confidence High.

### L08 — Manually retained localization keys include obsolete feature copy

**Evidence.** Generated-symbol and raw-key searches identified 19 unreferenced app feature keys in the inspected snapshot. Examples: `carodo-ios/Carodo/Resources/Localization/Common.xcstrings:1223` (`odometer.entered`), `carodo-ios/Carodo/Resources/Localization/Drive.xcstrings:2147` (`recording.title`), `carodo-ios/Carodo/Resources/Localization/Journeys.xcstrings:508,2590` (`detail.alongTheWay`, `list.filteredEmpty`), `carodo-ios/Carodo/Resources/Localization/Map.xcstrings:23` (`autoMode.menuTitle`), and `carodo-ios/Carodo/Resources/Localization/Passport.xcstrings:1679` (`stamps.statistics`). The unreferenced `LoginView` also carries sign-in copy and an empty action, and is explicitly documented as an unreachable scaffold in `carodo-ios/docs/architecture.md:35`.

**Impact and fix.** Obsolete manual keys remain in translation inventory and generated APIs. Verify dynamic and platform consumers before removal, and decide explicitly whether the documented login scaffold is still needed. Preserve auto-extracted system metadata. Effort S, fix risk Low, confidence High for the static scan.

### L09 — Drive and live parsers duplicate a UUID rule that already exists

**Evidence.** `carodo-app/apps/api/src/services/drives/publish.ts:21–27` and `carodo-app/apps/api/src/services/live/live.ts:29,45–48,103–106` independently apply the same rule. `carodo-app/apps/api/src/lib/platform/ids.ts:18–22` already contains the same UUID predicate. See `carodo-app/AGENTS.md:88–89`.

**Impact and fix.** The supported ID syntax can drift among endpoints. Reuse the predicate through one normalized parser and preserve each error response shape. Effort S, fix risk Low, confidence High.

### L10 — The session foreign key has no child-side index

**Evidence.** `carodo-app/apps/api/migrations/0001_baseline.sql:47–61` declares `sessions.app_key_id` without a leading index, contrary to `carodo-app/AGENTS.md:119`. An in-memory SQLite query plan for deleting a parent key showed a session table scan. No active app-key deletion path was established.

**Impact and fix.** Future app-key deletion or retention jobs could scan all sessions. With schema approval, add a leading index and a schema/query-plan regression check, or document the deliberate exception. Effort S, fix risk Low, confidence High.

### L11 — The public web’s home link has no accessible name

**Evidence.** `carodo-app/apps/web/src/layout.tsx:42–46` puts only `CarodoLockup` inside the home anchor. The SVG is `aria-hidden` in `carodo-app/apps/web/src/brand.tsx:54–65`.

**Impact and fix.** A screen reader can encounter an unnamed link. Give the anchor a localized accessible name, EN “Carodo home” and VI “Trang chủ Carodo,” and assert the name in a rendered markup or accessibility test. Effort S, fix risk Low, confidence High for markup.

### L12 — Public pages advertise icons the Worker does not serve

**Evidence.** `carodo-app/apps/web/src/layout.tsx:29–32` and `carodo-app/apps/web/src/assets.ts:20–26` advertise icon URLs. `carodo-app/apps/web/src/app.tsx:19–27,33–45` registers the SVG favicon and manifest with a fallback for other requests, and the Worker has no static asset binding for the other icon paths.

**Impact and fix.** Browser or home-screen icon requests can return 404. Serve the advertised icons or remove the unsupported links, and test every local URL referenced by the rendered head and manifest. Effort S, fix risk Low, confidence High.

### L13 — The Day week strip offers a Next Week action at its latest week

**Evidence.** `carodo-ios-day/Carodo/Features/Journeys/Views/JourneyDayCalendar.swift:151–154` always adds the action. `carodo-ios-day/Carodo/Features/Journeys/ViewModels/JourneyDayViewModel.swift:114,197–203` exposes `canShowNextWeek` and silently rejects the move at the current week.

**Impact and fix.** The accessibility action list offers navigation that cannot do anything. Expose Next Week only when `canShowNextWeek` is true, using the same boundary as the visual calendar. Verify with VoiceOver at the current week and a prior week. Effort S, fix risk Low, confidence High for the static behavior.

## Verification

- Backend and web: `task check` passed on rerun with local Workerd loopback access. Biome checked 117 files, both Wrangler binding checks and TypeScript checks passed, and 175 API tests plus 10 web tests passed. The restricted first run was blocked by loopback and log-write permissions.
- iOS formatting: `task lint` initially reported three line-length errors in the main worktree. A fresh run on the later main working copy exited 0, and no temporary `QAROOM` map logs remained. Both alternate worktrees passed `task lint`. `git diff --check` passed for iOS main, Day, and backend.
- Main iOS: the first simulator stalled, including on a focused retry that reached simulator app installation. Switched to the simulator that completed the Day suite. All 23 focused tests passed (`TripWriterTests`, `FeedPublisherTests`, `LocalizationTests`, and `PlaceVisitLogTests`). Result bundle: `/private/tmp/carodo-source-audit-20261112-main-retry.xcresult`.
- Main iOS full suite: `xcodebuild test-without-building` passed on the alternate iPhone 18 Pro simulator with 1,883 passed, 11 skipped, and zero failures. The skips require real-drive inputs, opt-in performance flags, or a schema dump path. Xcode also reported one thread-priority inversion runtime warning whose call site was not verified. Result bundle: `/private/tmp/carodo-source-audit-20261112-main-full-retry.xcresult`.
- Day worktree: 47 focused tests passed on the iPhone 18 Pro simulator (`DayCalendarTests`, `JourneyDayViewModelTests`, `JourneysViewModelTests`, and `LocalizationTests`). Result bundle: `/private/tmp/carodo-source-audit-20261112-day.xcresult`.
- Handbook: Python AST parsing, `bash -n`, and `node --check` passed for the inventoried Python, shell, and JS files. Preview generators were not run because they rewrite tracked exports.

## Scope decisions

- The Day worktree intentionally assigns drives to the device’s current calendar day. Recorded-zone day assignment is explicitly deferred in `carodo-ios-day/docs/specs/journeys.md:161–166,198–201`. The separate Place Visits mismatch is reported because a single view disagrees with its own row dates.
- Mock-only iOS Feed and the older local backend have independent tests. A pass in either suite does not verify their wire compatibility. No source fixes, commits, or deployments were made as part of this audit.
