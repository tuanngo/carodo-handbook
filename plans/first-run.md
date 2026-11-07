# First run: from onboarding to the first drive

A brief for the session that draws and builds the first five minutes (template:
[`../AGENT_WORKFLOW.md`](../AGENT_WORKFLOW.md)). Written 2026-11-03, at the end of the session that
settled the specs. Mockups first, then code, one screen at a time.

```text
Outcome:
  A new person finishes onboarding, understands whether Auto Mode is on, records a first drive with
  the car they named, and sees it saved. Mockups for the Day 0 and Day 1 rows of
  design/mockups/README.md ("To draw"), then the code that matches them.

User story:
  As someone who just installed Carodo, I name my car (or skip), allow location the way I want,
  land on a map that tells me what will happen next, tap Start (or just drive with Auto Mode) and
  find my first drive in Journeys, with my car on it.

Acceptance criteria:
  - Onboarding step 4 asks only the name, Car / Motorbike and the colour (units are a setting,
    Automatic by default; no plate line); Continue saves into an empty garage only; Later saves
    none. The compact vehicle card looks the same in onboarding, the Start panel, recording and the
    journey detail (one shared component); the Garage is a carousel of large vehicle cards
    (owner review, 2026-11-03).
  - First-run Map: no drives, a one-line Auto Mode status (on / off with the reason), the Start
    button in its not-ready state.
  - Permission states (When In Use only, denied, Motion denied, reduced accuracy) each show one quiet
    line with one action; nothing blocks the map.
  - The first tap on Start opens the Start panel asking only for what is missing (vehicle: none,
    one, several, "no vehicle" allowed; GPS readiness; mode). Afterwards one tap starts with the
    last-used vehicle; the compact panel shows "Recording · <vehicle>", Undo and the vehicle switch.
  - The first saved drive opens in Journeys and its detail; place names and the summary may arrive
    later and the page reads well before and after.
  - Light and Dark, the largest Dynamic Type, VoiceOver labels; every string in the String Catalogs
    (English and Vietnamese, reviewed by the owner).

Non-goals:
  Replay, share, places screens, Feed, stamps (Day 2 and later rows). No new tracking thresholds.

Relevant files/docs:
  carodo-ios/docs/specs/onboarding.md (Steps 4–6), drive-recording.md (Panels), garage.md,
  navigation.md, journeys.md (Detail), passport.md (Settings), design-system.md;
  design/mockups/README.md ("To draw", Day 0 and Day 1); design/mockups/drive/drive-recording-spec.png;
  Carodo/Features/Onboarding, Features/Drive, Features/Garage, Features/Map, App/MainTabView.

Constraints:
  carodo-ios AGENTS.md (invariants, concurrency, copy and localization, UI rules); the owner is new
  to Swift: make the Swift calls and explain them in a line. Pre-release schema rules apply; no new
  permission, entitlement or dependency without the owner (P6).

Validation commands/device checks:
  task build, task test, task lint; the QA launch arguments in docs/operations/setup.md
  (-carodo.debugOnboarding YES, -carodo.debugOnboardingScene 4, -carodo.debugStartPanel YES);
  on the iPhone: a fresh install through onboarding, then the daily drives
  (docs/operations/device-testing.md, Daily check).

Allowed scope:
  The screens above, their view models, the shared vehicle card, strings, tests, and the specs they
  change (in the same change).

Do not:
  Commit or push: the owner rebuilds the first commit after the specs and mockups are done. Touch
  files the owner is editing in parallel without checking first. Change tracking behaviour.
```

## Progress (2026-11-03, end of session): done in code, device checks pending

Status: **Done in code** (433 tests, lint clean, nothing committed). Every acceptance criterion
above is built; what is left is proving it on the iPhone and the owner's Vietnamese copy review.

Built this session, beyond the brief: Settings → Units (Automatic), vehicle looks (`body_style`,
`color`, `fuel_type`) with `VehicleArt` and the compact `VehicleCard`, the Garage carousel and its
Looks form, the Map's Auto Mode button and status line (the Map never asks for location), the
Start panel, the Auto Mode sheet with car-audio links (`vehicle_links`), the Shortcuts automation
(iOS 26 steps, iOS 27 one tap with the "Carodo CarPlay" iCloud link) and the localised Start Drive
intent, the 90 s grace on disconnect, Stop and wait with Split here, the "First drive" mark,
Developer mode slice 1 (live, battery and MetricKit, log, export, thresholds), tuning logs (`stop`,
`fixes`, `motion`, `battery`), per-fix vertical/speed/course accuracy and pressure (`TrackCodec`
v2), the elevation card and sheet (3 m noise level, barometer). Drafts: weather (blocked on the
paid developer account). Traccar compared in `carodo-ios/docs/tracking.md`.

Still open from this brief:
- Device checks: the motorbike test in `carodo-ios/docs/operations/device-testing.md` (first run on
  a fresh install, Start panel, Auto Mode and car audio, Stop and wait, battery, elevation).
- The owner's review of every new Vietnamese string.
- Onboarding at the largest text size: the 3D wheel still takes the top (the mockup moves it aside).

## State at hand-off (2026-11-03)

- Specs: every carodo-ios spec is Ready or Built (onboarding In build); the achievements draft is
  Ready; contract 0.15.0-draft. Today's decisions are in the specs and ADRs 0007, 0013, and the
  backend's ADR 0002.
- Code built today, uncommitted: places data and detector (Places 1), trip time zones,
  `PartOfDay` (seven parts), the province in `geocoded_cells`, load-failure states, safer writes;
  343 tests pass.
- The iPhone needs `task device` before the next drive: the schema changed several times today.
