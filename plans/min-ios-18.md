# Minimum iOS 18.0: audit and proposed migration

Status: **M1–M3 approved (owner, 2026-11-09); the migration is done, checked and committed in carodo-ios
(`3f017dc`, ADR 0018).** The iOS 18 runtime is **not verified**: it must be checked on an iPhone running iOS 18 before
TestFlight; with no such device, report it as a release risk for the owner to decide, never mark it passed. The owner's
decision: raise the minimum of all of Carodo from iOS 17.0 to **iOS 18.0**; anything needing iOS 26+ still uses an
availability check. This decision replaces the "min iOS 26" proposal open since 2026-11-08 (glass nav).

## 1. Audit

| Area | Today | Impact |
|---|---|---|
| Targets | `project.yml`: `options.deploymentTarget.iOS: "17.0"` and `IPHONEOS_DEPLOYMENT_TARGET: "17.0"` (base). App, widget (`CarodoWidgets`) and tests inherit it; no target sets its own | Change 2 lines, `xcodegen generate` |
| Widget / Live Activity | No `#available` at all; WidgetKit and ActivityKit predate iOS 17 | None |
| `FoundationModels` | Weak linked (iOS 26+); comment "iOS 17–25 still launch" | Keep the weak link; fix the comment |
| Code only there to run on iOS 17 | 3 `#available(iOS 18.0, *)` branches: `PlatformCompatibility` (scroll geometry, `ScrollMetrics.isAvailable`), `Vehicle` (the `convertible.side.fill` symbol). Fallbacks at the call sites: `JourneyStorySheet` (`isAtTop = false` without scroll geometry), `AutoModeSheet` (fixed medium), `FloatingBarCollapse` | Remove the branches and fallbacks; ~6 files, behaviour on iOS 18+ unchanged |
| iOS 26 branches | 17 `#available(iOS 26.0, *)` checks, gathered in `PlatformCompatibility` | Unchanged |
| Dependencies | GRDB 7 (min iOS 13) | None |
| CI | No `.github`, `ci_scripts` or Xcode Cloud. Checks run locally through `Taskfile.yml` | None |
| Warnings | A clean `build-for-testing` (app, widget, tests), overriding `IPHONEOS_DEPLOYMENT_TARGET` on the command line without editing `project.yml`: **0 warnings at 17.0, 0 warnings at 18.0**, both builds succeed | No API Carodo uses is deprecated at iOS 18 |
| SDK | iPhoneSimulator 27.2: min deployment target 15.0, recommended 17.0 | 18.0 is valid |
| Docs (carodo-ios) | `AGENTS.md` (Stack), `README.md`, `docs/operations/setup.md:5`, `docs/design-system.md` (Shape: "Newer-than-iOS-17 APIs…"; line 458 coupé fallback), `docs/specs/navigation.md:22`, `docs/specs/auto-mode.md:76`, `docs/specs/places.md:203–204`, ADR 0012 (lines 27, 36: "iOS 17–25") | Reword. Keep the sentences about an **API** (`CKSyncEngine (iOS 17+)` in `sync.md` and ADR 0005, `moped iOS 17+` in `garage.md`, Shortcuts iOS 17+ in `auto-mode.md:60`): still true |
| Docs (workspace, handbook) | The workspace `AGENTS.md:46`; older handbook plans mention "iOS 17+" | Fix the workspace `AGENTS.md`; older plans are history, left as they are |
| Decision | No ADR records the deployment target | Add a short ADR (AGENTS: a lasting decision gets an ADR) |

## 2. Finding: iOS 18 does not run on this Xcode's simulator

`xcodebuild -downloadPlatform iOS -buildVersion 18.6 | 18.5 | 18.4 | 18.0` answers "not available for download" with
Xcode 27.2 (the same command with 26.0 starts downloading; cancelled). Runtimes installed: 26.4 and 27.2.

So iOS 18 (and 19–25, which were never released) can be checked only on a **real iPhone running iOS 18**, or with an
older Xcode installed side by side (not checked whether Xcode 27 can use an 18 runtime installed by that Xcode). This gap
already existed at iOS 17. Raising to 18 does not make it worse, but does not close it either. For every supported
version to be checkable on a simulator, the minimum would have to be iOS 26.

## 3. Proposed minimal migration (one commit, after the owner's approval)

1. `project.yml`: `17.0` → `18.0` (2 lines); the `FoundationModels` comment "iOS 18–25". `xcodegen generate`.
2. `PlatformCompatibility.swift`: `carodoOnScrollMetricsChange` calls `onScrollGeometryChange` directly; remove
   `ScrollMetrics.isAvailable`; header "newer than the iOS 18 deployment target".
3. Call sites: `JourneyStorySheet` (remove the `onAppear` fallback), `AutoModeSheet`, `FloatingBarCollapse` (remove the
   "before iOS 18" comment); `Vehicle.swift` (the coupé uses `convertible.side.fill` directly).
4. Docs as in the table above + a new ADR `docs/decisions/0018-ios-18-minimum.md`; the workspace `AGENTS.md`.
5. Checks: `task format`, `task lint`, `task warnings`, `task test`; screenshots of the screens whose branches were
   removed (the Journey story pulled down from the top, the Auto Mode sheet measuring its own height, the Journeys
   floating bar collapsing on scroll) on 26.4 and 27.2.

Not in this migration: adopting more iOS 18 APIs; touching the iOS 26 branches; Stop Location (its prototype already
targets 17, unaffected).

## 4. Risks

- **Very low for the code:** 0 new warnings, the removed branches are only fallbacks.
- **iOS 18 is not checked on a simulator** (section 2). It needs an iOS 18 iPhone for a device check before TestFlight,
  or the owner accepts the gap.
- Before release, no iOS 17 user is left behind.

## 5. Owner decisions

| # | Question | Proposal |
|---|---|---|
| M1 | Approve the migration in section 3 | Approve |
| M2 | iOS 18 has no simulator: use a real iOS 18 iPhone for a device check, accept the gap, or consider min iOS 26 | Keep 18.0 (the benefit for Slice 2, and iOS 18 users kept); add an iOS 18 device check before TestFlight if a device is available |
| M3 | Consider the 2026-11-08 "min iOS 26" proposal closed | Close |
