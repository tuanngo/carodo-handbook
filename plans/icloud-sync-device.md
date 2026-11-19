# iCloud sync on the iPhone (paid team)

Status: done 2026-11-19 (approved 09:24; D1–D4 as recommended, D2 = reinstall on this iPhone). Result at the end. Follows
[paid-team-attest-staging.md](paid-team-attest-staging.md) (Status 2026-11-19: the App ID carries
iCloud with container `iCloud.app.carodo.ios`, the 08:35 profile has the container).

## Brief

```text
Outcome: an Xcode build on the owner's iPhone, signed by the paid team, backs up every vehicle,
  place, drive, vehicle log and fill-up to the owner's iCloud (CloudKit Development), shows
  "Up to date" in Settings → iCloud, and the data comes back on a second install.
User story: as the owner, I turn on Back Up to iCloud and see my 28 drives reach iCloud, so a new
  iPhone or a reinstall gets them back without a .carodo file.
Existing behaviour (files read): see Audit.
Owner decisions needed: D1–D4 below.
Spec (Ready?) and mockups: docs/specs/settings.md#icloud (Built, "never run on a device yet");
  the owner's Geofency screenshot (2026-11-19) as the reference for D1.
Acceptance criteria: see below.
Non-goals: Deploy Schema Changes to Production, TestFlight, syncing badges or vehicle links,
  WeatherKit, the backend (staging deploy, App Attest: the paused slice), any schema or contract
  change.
Relevant files/docs: Configs/Local.xcconfig (gitignored), Carodo/Core/Sync/CloudSyncService.swift,
  CloudRecordCoding.swift, Carodo/App/DependencyContainer+Live.swift,
  Carodo/Features/Settings/Views/ICloudView.swift, docs/sync.md (iCloud), docs/operations/cloudkit.md,
  docs/specs/settings.md#icloud.
Constraints: P1 (recording never waits on iCloud), P5 (no record contents in logs), P7 (iCloud is
  the person's own private database), iOS invariant 1 (CloudKit is a replica, GRDB the truth).
Validation commands/device checks: task lint, task warnings, task test; task pull-db; task device;
  the device checks in step 3–7; the CloudKit Console (Development).
Allowed scope: Configs/Local.xcconfig; a fix to Core/Sync found on the device (stops and asks if
  it needs a schema, contract or entitlement change); the docs above; ICloudView only if D1 says so.
Do not: stage the App Attest slice's uncommitted files (Configuration.swift, Carodo.entitlements,
  Local.xcconfig.example, Shared.xcconfig, setup.md, sync.md, project.yml) or another session's
  (privacy.md, skills-lock.json, .agents/, .claude/skills/); deploy the schema to Production;
  reset the Development environment without the owner.
```

## 1. Audit: what the code does today

| What | Today | File |
|---|---|---|
| The engine | `CKSyncEngine` on the private database, zone `Carodo`, built and unit-tested; never run against CloudKit | `Core/Sync/CloudSyncService.swift` (557 lines), `CloudRecordCoding.swift` |
| Records | `Vehicle`, `Place`, `Trip` (+ `track` asset), `VehicleLog`, `FuelLog`; one `payload` field through `encryptedValues` | `CloudRecordCoding`, `docs/operations/cloudkit.md` |
| Not synced | vehicle links (car audio), badges (tables marked, engine does not carry them) | `docs/sync.md` iCloud |
| Compiled in? | `#if CARODO_CLOUDKIT` creates `CKContainer(identifier:)`; else `makeContainer` is nil and the service stays `.unavailable` ("Not in this build") | `App/DependencyContainer+Live.swift:65` |
| The flag | `CARODO_CLOUDKIT_FLAG = CARODO_CLOUDKIT` in `Configs/Shared.xcconfig` (committed); this Mac's `Local.xcconfig` empties it (`CARODO_CLOUDKIT_FLAG =`) | `Configs/` |
| Entitlements | iCloud CloudKit `iCloud.app.carodo.ios`, `aps-environment` development (committed); App Attest line uncommitted (other slice) | `Carodo/Resources/Carodo.entitlements` |
| Push | `remote-notification` background mode; no call to `registerForRemoteNotifications` anywhere | `project.yml:134`, `Info.plist` |
| Lifecycle | on by default (`carodo.iCloudBackup`); `start()` checks the account, restores engine state, adds `saveZone` on a first start, watches `ck_pending` rows; sign-out pauses, switch account turns off, zone deleted elsewhere turns off, encrypted-data reset re-sends | `CloudSyncService` `start`, `accountChanged`, `zoneDeleted` |
| Screen | Settings → iCloud: switch; Status and Last Synced rows; Sync Now; Delete from iCloud (confirm) | `Features/Settings/Views/ICloudView.swift` |
| The owner's data (pull 2026-11-18 20:49) | 28 drives (all `ck_pending`), 3 vehicles, 30 places, 3 vehicle logs, 1 fill-up; packed tracks 518 KB in all, the largest 109 KB | `drive-data/` |

Assumed, not checked:
- (a) `CKSyncEngine` receives its silent pushes without the app calling
  `registerForRemoteNotifications` (Apple's sample and docs to be read before step 6). If not,
  that call goes in the composition root: no permission prompt, no entitlement change.
- (b) A Debug build signed with development signing talks to the **Development** environment and
  its just-in-time schema creates `payload` as an encrypted field.
- (c) The iPhone is signed in to iCloud with iCloud on for Carodo (iOS Settings → Apple Account →
  iCloud → Saved to iCloud).

## 2. Owner decisions

- **D1. The screen.** The reference (Geofency) puts the state first: a large icon, "Up to Date",
  "Synced just now", a count of items; the switch and Sync Now in one card with what syncs under
  it; Erase iCloud Data on its own; an FAQ. `ICloudView` has the same functions in plain rows.
  Recommended: **prove sync first with today's screen (this plan), then the reference layout as
  its own slice** (a header with the state, the count of records in iCloud, Sync Now beside the
  switch, two Help questions), once the device shows which states really occur. A layout is a
  matter of taste: it waits for your review, the proof does not.
- **D2. The second copy (checklist step 4).** Recommended: **a second device on the same Apple
  Account** (an iPhone: the target is iPhone only, so an iPad is not assumed to work). Without one: **delete the app and install it again** on this iPhone after a
  `task pull-db` and a `.carodo` backup (deleting the app is your call: it erases the local
  database; the backup is the safety net). Which one do you have?
- **D3. Production schema.** Recommended: **not in this plan.** What is deployed is permanent;
  deploy at the first TestFlight build, after the Development schema is checked (step 4).
- **D4. Your real drives in iCloud Development.** It is your own private database, encrypted
  (P7 holds). Recommended: **yes**, they are the test data. Development can be reset later, but
  only by you.

## 3. Steps

1. **Safety first.** `task pull-db` (copy to `drive-data/`) and a `.carodo` backup from Settings →
   Backup & restore, kept off the iPhone. A `task device` may erase on a schema change (iOS
   invariant 6).
2. **Turn it on for this Mac.** Remove `CARODO_CLOUDKIT_FLAG =` from `Configs/Local.xcconfig`
   (gitignored, nothing committed); WeatherKit stays empty. `task device`. The build also carries
   the uncommitted App Attest slice: the Feed reads "can't reach" (staging not deployed), which
   this plan ignores.
3. **First backup.** Settings → iCloud: Status goes Syncing → Up to date, Last Synced "now".
   Read the sync log in Xcode's console (error codes only, P5). `task pull-db` again: no row left
   with `ck_pending = 1`, `ck_metadata` set on all 65 rows.
4. **The Development schema** (CloudKit Console → `iCloud.app.carodo.ios` → Development):
   record types `Vehicle`, `Place`, `Trip`, `VehicleLog`, `FuelLog`; each has `payload`
   **Encrypted**; `Trip` has `track` (Asset); no other field. Records (Act as iCloud Account):
   zone `Carodo` holds 28 + 3 + 30 + 3 + 1 records, payloads unreadable. A stray field stops the
   plan and goes to you (D4: resetting Development is yours).
5. **Edits travel.** Rename a vehicle, trim a drive, record a short drive: each reaches iCloud
   (its record's modification time in the Console) without opening Settings; a pending Auto Mode
   drive stays local until answered (O10).
6. **The second copy (D2).** Second device: install, open, wait; vehicles, places, drives, logs
   and fill-up arrive, routes are derived there, nothing is echoed back (the first device's
   records keep their modification time). Then an edit on one appears on the other, the
   receiving app in the background (assumption a). Reinstall instead: the journal comes back
   from iCloud alone, the `.carodo` untouched.
7. **The switches.** Off → Status off, nothing sent; on → catches up. Delete from iCloud (in
   Development only): the zone is gone in the Console, backup turns off, every drive stays on
   the iPhone; on again sends everything as new.
8. **Record.** `docs/specs/settings.md#icloud`: drop "never run on a device yet"; anything the
   device taught goes in `docs/sync.md` or `docs/operations/cloudkit.md` (e.g. how to open the
   private data in the Console). A new PV row in `technical-debt.md` for what stays unproven
   (background push without a second device, Production). A bug found: systematic debugging, a
   fix in `Core/Sync` with its unit test; anything beyond that scope is asked first.
9. **Commit** (carodo-ios, own paths only): the docs and any fix, `fix(sync): …` or
   `docs(sync): icloud sync proven on an iphone`, after `task lint`, `task warnings`, `task test`.

## 4. Acceptance criteria

- Settings → iCloud on the iPhone reads Up to date after the first backup; the pulled database
  has no `ck_pending` row.
- The Development schema has exactly the five record types, `payload` encrypted, `Trip.track` an
  asset.
- The second copy (D2) has the same count of drives, vehicles, places, logs and fill-ups, with
  routes; a drive replays there.
- Off, on and Delete from iCloud behave as `docs/specs/settings.md#icloud` says; no local row is
  lost at any step.
- Recording a drive with iCloud on and the iPhone offline completes and is sent later (P1).
- `task lint`, `task warnings`, `task test` pass; nothing of the App Attest slice or another
  session is staged.

## 5. Risks

- **R1. Stale profile.** Xcode kept an old profile without the container once; if CloudKit
  says "missing entitlement", build once in Xcode to refresh (the shell cannot: "No Accounts").
- **R2. Schema made wrong in Development** (an older build, a stray field): only a Development
  reset fixes it, the owner's call; Production is untouched until D3.
- **R3. Push** (assumption a): without registration, other devices' changes arrive only when the
  app comes to the foreground; found in step 6.
- **R4. A sync bug against the real service** that the fakes never showed (record size, asset
  upload, the zone's first save): fixed in scope only if it stays inside `Core/Sync`.

## Result (2026-11-19)

Steps 1–7 done on the owner's iPhone (Debug, CloudKit Development); step 5 covered a rename only.

- First backup: 30 drives, 3 vehicles, 30 places, 3 vehicle logs, 1 fill-up; schema exported and
  checked (five types, `payload ENCRYPTED BYTES`, `Trip.track ASSET`, nothing else).
- **Found and fixed:** `markSent` compared `updated_at` with the payload's time, which keeps
  milliseconds only and cuts them after `Date`'s own conversion; 18 places, then one more, were
  sent again at every sync. The row's time now goes through the same conversion
  (`BackupDocument.asWritten`) before an exact comparison (approach A; a revision counter or a finer
  payload were weighed and left: more write paths to keep right, or a format change still subject
  to the conversion).
- Reinstall: everything came back from iCloud, tracks byte-identical, nothing echoed. Figures are
  derived again on the new install: 22 drives read shorter at first (the lead-in not yet healed),
  2 after the gap pass, both the hidden parts of joined drives (the pass skips parts; their
  drives match). After the reinstall the end-place naming bumped 20 revisions once, each sent once.
- Off/on and Delete from iCloud then on behave as the spec says; no row lost.
- Manage Storage shows the container as "ios" though its description is "Carodo": to look at on
  TestFlight.
- Left open: PV-38 in technical-debt.md.

## D1 follow-up: the iCloud page (2026-11-19)

Approved by the owner on the iPhone: a head with the state, the last sync and the count of records
in iCloud; Sync Now with the switch; alerts before turning off and before deleting (carodo-ios
`23cb1af`). Colour (`a95afd9`): done is the system's green in icons only, switches stay copper.
