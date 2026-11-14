# carodo-ios UI/UX and view organisation audit, 2026-11-14: findings and the order to fix them

Status: **all eight steps done 2026-11-14**, carodo-ios `7f1cc4b`..`e99f1f4`, unpushed. TD-10, TD-13 and TD-16 closed; PV-21 (the drive flow on an iPhone) open. Audit at carodo-ios `34c519f` (`main`). Each step
below gets its own short plan, approved by the owner, before any code (AGENT_WORKFLOW.md); steps
are taken one at a time, in order, and each is one commit.

## How it was audited

- Source read with the `swiftui-pro` review rules: pattern counts over `Carodo/` and
  `CarodoWidgets/`, then the largest views (`MainTabView`, `JourneyDetailView`, `MapAtlasView`,
  `RecordingPanels`) and how every screen renders loading, failure and empty.
- 17 simulator screenshots on a simulator created for the audit (iPhone 18 Pro, iOS 27.2,
  `-carodo.sampleData YES`): Map, Journeys Explore and Day, Feed, Journey Detail, Start panel,
  recording sheet, Passport, Garage, a vehicle's page, Settings in Light and English; Journeys,
  Journey Detail and Feed in Dark, Vietnamese, accessibility-extra-large; Journeys, a vehicle's
  page and Feed in Vietnamese at xxxLarge. They were session scratch and are not kept; the launch
  arguments in `carodo-ios/docs/operations/setup.md` reproduce each one.

Not covered: no flow was tapped through (onboarding, Replay, Trim, Share, the sheets); no
VoiceOver run; no contrast measurement; nothing on an iPhone. `-carodo.debugOpenJourney` shows
Journey Detail with the floating bar still up, unlike the app (`AppRoute.journey.hidesFloatingBar`),
so that screenshot does not stand for the product.

What is sound and needs nothing: no deprecated SwiftUI API (`foregroundColor`, `cornerRadius`,
`NavigationView`: 0); navigation is value-based (`NavigationLink(value:)` 28, one
`navigationDestination(for: AppRoute.self)` per stack); no `ObservableObject`; haptics through
`sensoryFeedback`; Reduce Motion read in 41 places; APIs newer than iOS 18 kept in
`PlatformCompatibility.swift`.

## Findings

### UI/UX

| ID | Finding | Evidence |
|---|---|---|
| U1 | **Figures are lost at xxxLarge in Vietnamese**, the largest size Carodo supports (TD-16). The latest-drive card truncates its distance and time ("1… km", "24 p…"); a journey row truncates its clock time ("29,2 km · 38 phút · 2…"); the three stat tiles shrink unevenly ("53 giờ 11 phút" far smaller than "2.610 km" beside it); a vehicle's page truncates the label "Quãng đường…". Above xxxLarge the floating bar truncates its tab labels and covers content: the cap in TD-16 removes that, not the three layout faults | Screenshots: Journeys, vehicle page at xxxLarge, Vietnamese. `JourneyHeroCard`, `JourneyCards`, `StatColumn` |
| U2 | **The Feed's decorative shape crosses text.** On the invite card the Copper stroke runs through "…how long you drove" and reads as a strike-through; rows' shapes overlap the car's name. Light and Dark, English and Vietnamese, every text size | Screenshots: Feed. `FeedShapeBackground`, `FeedView` invite, `FeedRow` |
| U3 | **Failure states differ by screen.** Retry on Day, Feed and Passport; none on Journeys Explore, Garage, a vehicle's page, Places (a bare line of text) and Replay (a bare line of text): the person has to leave and come back. `LoadingView`, `ErrorView` and `EmptyStateView` in the design system have no caller, though `docs/design-system.md` lists them as the standard states | `JourneysView.swift:193`, `GarageView.swift:43`, `VehicleDetailView.swift:41`, `PlacesView.swift:21`, `ReplayView.swift:92` |
| U4 | **Two different things share one symbol.** The Map's layers button (top left) uses the symbol of the Journeys tab | Screenshot: Map |
| U5 | **Spacing is off the documented 4 pt grid.** Padding 14 (47 uses), 10 (36), 6 (28); card radii mix 14 (25), 18 (22), 20 (11), 12 (11). `Theme.Spacing` has 33 uses against about 450 literal paddings; `Theme.Colors` and `Theme.Typography` have next to none (already a Known gap in `docs/design-system.md`) | grep counts at `34c519f` |

### Code and view organisation

| ID | Finding | Evidence |
|---|---|---|
| C1 | **`MainTabView` is 1,127 lines** (TD-13; target under 900): 11 sheets, 14 `onChange`, 4 `task`, and the app's lifecycle work (what runs on `scenePhase`, garage and journal revisions) written inside `body`, where no test reaches it | `Carodo/App/MainTabView.swift:144-431` |
| C2 | **`JourneyDetailView` holds 28 `@State` and 15 presentations**, nine of them Booleans; `notMineAfterEditor` exists only to keep two presentations from overlapping | `JourneyDetailView.swift:17-75, 96-342` |
| C3 | **`LoadState` is declared in ten view models** (TD-10), and each screen draws the three states by hand (the cause of U3) | `Features/*/ViewModels` |
| C4 | **Files holding many types:** `RecordingPanels.swift` 13, `FeedIdentityView.swift` 12, `JourneyDetailMap.swift` 11 (1,014 lines), `MapKitShared.swift` 10, `PassportSections.swift` and `PassportStampsSection.swift` 9 each, `VehicleDetailView.swift` 9 | type counts at `34c519f` |
| C5 | **`Features/Journeys` is 46 files and 12,652 lines in two flat folders** (list, Day, detail, editing, Replay, video export, share card, place visits) | folder listing |
| C6 | **View models are built inside `destination(for:)`**, which runs on every `MainTabView` body pass: a new `PassportViewModel`, `PlacesViewModel`, `VehicleDetailViewModel`, `RecentlyDeletedViewModel`, `DriveDiagnosticsModel` is allocated and thrown away each time (the view's `@State` keeps the first). Seven views declare `@State var model` without `private` | `MainTabView.swift:949-1043`; `PlacesView`, `ReplayExportView`, `JourneyTrimSheet`, `ShareCardView`, `RecentlyDeletedView`, `ReplayView`, `BackupView` |

## Order of work

| Step | What | Findings | Debt | Commit by | Depends on |
|---|---|---|---|---|---|
| 1 | One shared `LoadState` and one view for loading, failed (with Retry) and empty; the three unused design-system views are replaced by it or removed; every screen in U3 gets Retry | U3, C3 | TD-10 | agent, with screenshots | none |
| 2 | Cap Dynamic Type at xxxLarge at the root, then fix the three layout faults at xxxLarge in English and Vietnamese, then remove code written only for accessibility sizes | U1 | TD-16 | **owner review** | none |
| 3 | Keep the Feed's shape clear of text (invite card first, then rows) | U2 | none | **owner review** (check with the Feed session first) | none |
| 4 | `JourneyDetailView`: one enum for its sheets and covers, one for its confirmations | C2 | none | agent | none |
| 5 | `MainTabView`: the drive start/finish flow and its toasts into one `@Observable` coordinator, the lifecycle work into one tested place, the car-log sheets into one modifier | C1 | TD-13 | **owner review** | 4 (same presentation pattern) |
| 6 | One type per file for the files in C4; `Features/Journeys/Views` and `ViewModels` into subfolders (Detail, Replay, Share, Day, Editing). Moves only, no behaviour change; done when no other session has those files open | C4, C5 | none | agent | 4, 5 |
| 7 | View models made by a factory the view calls once; `@State private` | C6 | none | agent | 5 |
| 8 | Remove `Theme.Colors` and `Theme.Typography`; keep one spacing and radius scale and apply it when a file is touched, never as a mass rewrite. A symbol of its own for the Map's layers button (owner picks) | U4, U5 | none | **owner review** | none |

## Done

- **Step 1** (carodo-ios `7f1cc4b`, 2026-11-14): one `LoadState` in `Core/Domain` (TD-10 closed),
  `LoadFailedView` with Retry on Journeys, Day, Garage, a vehicle's page, Places, Replay, Trim and
  Recently Deleted; the three unused state views removed. Retry is `.bordered` and large, not a
  Copper fill: Start Drive keeps the screen's one fill. DEBUG `-carodo.debugReadFailure S` shows
  the failed states with sample data; screenshots (Light English, Dark Vietnamese xxxLarge) of
  Journeys, Day, Garage, Places. Left open: the failure titles of Places and Replay end with a full
  stop, the others do not (copy, for the owner); a vehicle's page and Replay cannot be put in their
  failed state with sample data (unit tests cover them).

- **Step 2a** (carodo-ios `055e6b3`, 2026-11-14, accepted by the owner): `carodoTextSizeCap()` at the
  root of `CarodoApp` caps text at xxxLarge in two halves: SwiftUI's `dynamicTypeSize` for the
  root's tree, and the window's `traitOverrides.preferredContentSizeCategory` (the person's setting,
  no larger than xxxLarge, following a change in Settings) for what iOS presents beside it. The
  SwiftUI cap alone left sheets uncapped (the Garage sheet at the largest Larger Text size, figures
  cut), and a view's `maximumContentSizeCategory` does not reach a presented controller. Fixed at
  xxxLarge: the latest-drive card's figures stack when they do not fit (`ViewThatFits`), a
  journey row's line takes two lines, `StatColumn` wraps rather than shrinking to 60 %, the Garage
  card's paint and fuel take a line each in English and its model line keeps its wrapped height.
  **Why agents kept writing `isAccessibilitySize` branches after the 2026-11-12 decision** (four
  commits: `066de55`, `600d85d`, `ef7e8a8`, `393045d`): the rule lived only in TD-16 and an
  agent's memory, while `AGENTS.md` asked for screenshots at "a large Dynamic Type size" and the
  recipe in `docs/operations/setup.md` used `accessibility-extra-large`. The rule is now in
  `AGENTS.md` (UI convention, evidence lines) and `docs/design-system.md#typography`, and the
  recipe uses xxxLarge.
- **Step 2b** (carodo-ios `5ee58ee`): the 46 `isAccessibilitySize` branches in 24 files removed with
  what only they used (Day's one-day stepper and its two strings, the CarPlay badge's dot-only
  form, the elevation chart's and share card's own caps) and the spec lines describing them.
  Screenshots at xxxLarge before and after differ only in the status bar's clock. TD-16 closed.
- **Step 3** (carodo-ios `e4a0dbf`, 2026-11-14, accepted by the owner): `feedShape(...)` clears a Feed
  row's and the invite's shape around every laid-out line of text (`Text.LayoutKey`, soft edge),
  so no stroke crosses a word; the shape shows beside short lines and between them. Replaces the
  2026-11-11 rule "under text only a thin core with a halo", whose core read as a strike-through.
  The invite's shape is now a short stub beside its last line (owner: fine).
- **Step 4** (carodo-ios `75a9977`): Journey Detail's fifteen presentations are four enums (sheet,
  cover, confirmation, failure); `notMineAfterEditor` became a confirmation that waits for the
  sheet to close. 28 `@State` to 17. Each presentation checked through its debug argument; Trim
  and Merge open only on a journal in a trip store (`-carodo.sampleJournal N`), not on
  `-carodo.sampleData`, as before.
- **Step 5** (carodo-ios `f813f76`, owner approved the coordinator): `DriveFlow` (`@Observable`,
  owned by the shell) holds the garage the panels offer, starts (tap, Shortcut, car connection,
  Undo), finishes and their banners, the foreground catch-up and the diagnostics lines; 5 tests.
  `MainTabView` 1,127 → 898 lines (TD-13 closed). Not done, not needed for the target: the car-log
  sheets (fuel, odometer, expense) as a modifier of their own. A drive on an iPhone is PV-21.
- **Step 6** (carodo-ios `195fda6`, `b3d486e`): `Features/Journeys/Views` and `ViewModels` in one
  folder per part (Explore, Day, Detail, Editing, Visits, Replay, Share; `JourneyPresentation` at the
  root), moves only. The seven files of C4 split into 64: each primary type with the private
  helpers only it uses; a helper used by several files got its own file and lost `private`, the
  generic names renamed (VehicleDetailSection/Symbol/Divider, FeedSwitchGroup,
  RecordingMetricDivider). Screenshots at xxxLarge before and after differ only where the
  simulator's location setting did.
- **Step 7** (carodo-ios `62a623a`): measured first. With a journey open, `destination(for:)`
  makes its `JourneyDetailViewModel` 6 times in 40 s at rest and 9 while a drive records (a probe in
  its init, simulator, sample data), each from the simplified route only; the other models built
  there only store references. No factory or cache: it would prevent no measurable cost. The seven
  `@State var model` are `private`, set from an explicit init.
- **Step 8** (carodo-ios `e99f1f4`): the Map's layers button is `square.3.layers.3d` whatever the
  layer (owner's pick, 2026-11-14). One home per kind of token: brand colours `CarodoColor`,
  colours by role and status `CarodoSurface` (warning, success, error joined it, unchanged),
  spacing `CarodoSpacing` (the 4 pt scale, from `Theme.Spacing`), motion `CarodoMotion`, text
  styles, a card's radius `.carodoCard()`. `Theme` removed (its typography and radius scale had no
  user). The ~450 spacing numbers written in place are not rewritten; new and touched code uses
  the scale (design-system Known gaps).
- Checked 2026-11-14 at the owner's question: with iOS 18 the minimum, no availability check for
  an older system is left; every `#available` is iOS 26 (Liquid Glass, Apple Intelligence). The 11
  `UIGraphicsImageRenderer` (compositing on map snapshots) and one `UISelectionFeedbackGenerator`
  (inside an `MKMapView` delegate) are UIKit on purpose, not leftovers.

## Next session: flows, VoiceOver, contrast (brief)

Owner, 2026-11-14: a new session takes this, then the small leftovers. Read this file's Findings
and Done first; the code is carodo-ios `e99f1f4` or later.

```text
Outcome: an audit of what this one did not cover (How it was audited, "Not covered"), findings
  recorded here as a second pass, then fixed one step at a time like the first pass.
User story: someone using VoiceOver, larger text or a low-contrast setting can do everything the
  app offers; every flow ends where it should.
Existing behaviour (files read): steps 1-8 above; launch arguments in carodo-ios
  docs/operations/setup.md#qa-launch-arguments-debug open most states.
Owner decisions needed: (1) the two failure titles ending with a full stop ("Couldn't load your
  places.", "This drive can't be replayed right now.") while the others do not: drop the stop?
  (2) status colours (CarodoSurface.warning/success/error are system orange/green/red): tune to
  the palette or keep? Ask before changing either.
Spec (Ready?) and mockups: the owner is making Journeys mockups in parallel: do not restyle Journeys.
Acceptance criteria:
  - Flows walked on a simulator with taps (xcode-integration device-interaction, or the Xcode
    MCP), screenshots of each step: onboarding (3 pages, permission gate), Start Drive panel ->
    recording -> Hold to Finish -> summary sheet, Journey Detail -> Replay -> Export video,
    Trim, Share card (Aa, styles), Merge, Your trip editor, Garage add/edit vehicle, fuel/odometer/
    expense sheets, Feed join and profile sheets, Settings, Backup.
  - VoiceOver: every control has a short plain label (owner rule: memory voiceover-copy), order
    makes sense, nothing decorative is read; checked with the accessibility inspector or
    `xcrun simctl` + accessibility audit (XCUIApplication.performAccessibilityAudit in a UI test
    if a UI test target is approved; a new target is a P6 decision, ask first).
  - Contrast: copper text on ivory and on charcoal, secondary text, warning orange on dark,
    chips and the Feed shape behind text: measured (WCAG 2.1 AA 4.5:1 body, 3:1 large text/
    controls), numbers recorded.
  - Text at xxxLarge stays the rule (AGENTS.md, UI); never an accessibility-size branch.
Non-goals: new features, Journeys redesign, the ~450 spacing literals (Known gap: migrate only in
  files touched).
Relevant files/docs: this plan; carodo-ios AGENTS.md (UI, Copy, Resource safety);
  docs/design-system.md; docs/copy-and-localization.md (VoiceOver lines in both languages).
Constraints: a simulator of the session's own, addressed by UDID; sample data only in
  screenshots; strings in the String Catalogs with English and Vietnamese.
Validation commands/device checks: task lint, task warnings, task test; screenshots Light/Dark,
  xxxLarge, Vietnamese for every screen changed.
Allowed scope: carodo-ios views, catalogs, docs; this handbook plan and technical-debt.md.
Do not: commit with the harness's Co-Authored-By (P8); stage another session's files; run
  `task format` without checking it touched only your files.
```

Small leftovers from this pass, for the same session:

- The car-log sheets (fuel, odometer, expense, "Log for your car") from `MainTabView` into one
  modifier of their own (step 5, not needed for its target; makes the shell smaller still).
- Spacing: no mass rewrite; files the session touches move to `CarodoSpacing`.
- PV-21 (the drive flow on an iPhone) stays with the owner.

## Considered and not planned

So nobody audits them again:

- **17 `AnyView` view factories between features** (`MainTabView`, `JourneyDetailView`,
  `AutoModeSheet`, `RecordingPanels`): they sit at sheet roots, never in a list, and exist because
  a feature may not reference another feature's views. Replace with a generic only when the file
  is being reworked (step 5).
- **`MapAtlasView` keeps heading and coordinate in `@State` at the root of an 821-line view.** The
  performance audit measured this screen on an iPhone; touch it only if a new measurement shows a
  cost.
- **17 `Binding(get:set:)`** (Settings pickers, confirmation dialogs driven by an optional): correct
  as written; step 4 removes the Journey Detail ones.
- **Five `ForEach(..., id: \.offset)`** over content that does not reorder (chart points, trim bars,
  FAQ steps).
- **24 fixed font sizes:** all symbols inside fixed-size controls, as `docs/design-system.md`
  allows.
