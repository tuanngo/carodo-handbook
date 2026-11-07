# Journey Detail polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Polish Journey Detail with a trip-length-aware map, compact data hierarchy, DesignSystem colors and bounded rendering work while preserving existing trip facts and behavior.

**Architecture:** Keep JourneyDetailView as the orchestration point and retain one continuous scroll view. Put the adaptive map policy in a small pure view-layout type, compute route analysis once in a concurrent pure function, and pass prepared values to focused SwiftUI sections. Keep existing repositories, models, map and vehicle sheet as the data and navigation boundaries.

**Tech Stack:** Swift 6.2, SwiftUI, MapKit, Swift Charts, XCTest, XcodeGen, existing Carodo DesignSystem.

**Spec:** drafts/journey-detail-polish.md (Ready; the owner approved the adaptive map curve and 250-point chart cap).

## Global Constraints

- iOS 17+, Swift 6, iPhone only; no deployment-target change.
- Keep MapKit Standard, the existing speed-colored route and full-map presentation.
- Keep one continuous detail scroll page; no modal sheet for the main detail.
- Preserve ADR 0012: on-device Foundation Models, validated facts, template fallback, sparkle only for model-written copy.
- Keep Weather out of scope until a real integration is approved and supplies historical data.
- Keep Replay disabled until the dedicated Replay screen is wired.
- Every new user-facing string belongs to the Journeys String Catalog in English and Vietnamese with a translator comment.
- Use DesignSystem tokens for surfaces, accents, map markers and media overlays; preserve semantic speed-band colors in DesignSystem.
- Do not change schema, API contracts, permissions, capabilities, dependencies, tracking or privacy behavior.
- Do not commit, stage unrelated files, or rewrite history.

## Review Focus

- Very short loops and long routes: map height follows distance and the complete route remains framed.
- Missing, one-point or malformed route: the map and layout remain valid without fabricated data.
- Very long route: analysis and map segment construction do not run repeatedly on the main actor.
- Flat or sparse elevation: sampling preserves endpoints and important extrema without implying false detail.
- No Apple Intelligence: the same facts produce a concise template summary and no model-authorship marker.

## Files and ownership

- Modify Carodo/Features/Journeys/Views/JourneyDetailView.swift: keep orchestration; reorder the vehicle section; scope transitions to changing content rather than the entire page.
- Modify Carodo/Features/Journeys/Views/JourneyDetailSections.swift: current home of JourneyMapHeader and all detail sections; use it for Tasks 1–3, move the elevation component in Task 3, then move remaining declarations into focused files in Task 4.
- Create Carodo/Features/Journeys/Views/JourneyMapHeader.swift: map header, route framing insets, replay placeholder and expand-map control.
- Create Carodo/Features/Journeys/Views/JourneyDetailSummarySections.swift: narrative line, summary, date header and route timeline.
- Create Carodo/Features/Journeys/Views/JourneyDetailMetricsSections.swift: primary metrics, driving profile and mini-metrics.
- Create Carodo/Features/Journeys/Views/JourneyDetailElevationSection.swift: standalone compact elevation card and detail sheet, chart sampling, unit-aware axes/readout, and altitude formatting.
- Create Carodo/Features/Journeys/Views/JourneyDetailContextSections.swift: fuel, vehicle, memories and developer provenance.
- Create Carodo/Features/Journeys/Views/JourneyMapHeightPolicy.swift: pure height-fraction policy.
- Create Carodo/Core/Domain/JourneyDetailAnalysis.swift: Sendable analysis result and concurrent builder for segments, speed shares, elevation and stops.
- Modify Carodo/Features/Journeys/ViewModels/JourneyDetailViewModel.swift: await concurrent analysis once when route points are ready and expose its results.
- Modify Carodo/DesignSystem/Components/RouteViews.swift: allow JourneyRouteMap to accept prepared segments while retaining the existing default for other callers.
- Modify Carodo/DesignSystem/CarodoSurface.swift: add named map-marker and media-overlay foreground tokens using existing brand colors.
- Create CarodoTests/JourneyMapHeightPolicyTests.swift, JourneyDetailAnalysisTests.swift and ElevationChartSamplingTests.swift for pure policies and analysis.
- Modify docs/specs/journeys.md and docs/design-system.md in the implementation change to describe shipped behavior and color-token roles.

## Interfaces

- JourneyMapHeightPolicy.heightFraction(distanceM: Double) -> CGFloat: clamps negative distances to zero; returns 0.40 at 0 m, interpolates linearly to 0.6667 at 100,000 m, and remains 0.6667 above 100,000 m.
- JourneyDetailAnalysis: immutable Sendable fields routeSegments: [RouteSegment], speedShares: [SpeedShare], elevation: ElevationSummary?, stops: StopSummary.
- JourneyDetailAnalysisBuilder.build(from points: [RoutePoint]) async -> JourneyDetailAnalysis: marked @concurrent; calls existing pure JourneyAnalysis functions once for the same route.
- JourneyRouteMap.init(journey:points:interactionModes:segments:): segments defaults to nil; when supplied, do not call JourneyAnalysis.segments(of:) again.
- ElevationChartSampling.maximumPoints = 250 and ElevationChartSampling.sample(_ points: [ElevationPoint]) -> [ElevationPoint]: return the original array below the cap; otherwise retain first/last, global minimum/maximum, then local extrema with greatest prominence while slots remain; fill any remaining slots evenly by route distance without exceeding the cap. Keep the full profile for figures and scrub readout.

## Task 1: Pin and implement adaptive map sizing

**Files:**
- Create: Carodo/Features/Journeys/Views/JourneyMapHeightPolicy.swift
- Create: CarodoTests/JourneyMapHeightPolicyTests.swift
- Modify: Carodo/Features/Journeys/Views/JourneyDetailSections.swift (JourneyMapHeader currently lives here)
- Modify: Carodo/Features/Journeys/Views/JourneyDetailView.swift

- [ ] Add tests for 0 m → 0.40, 8,300 m → approximately 0.422, 50,000 m → approximately 0.533, 100,000 m → 0.6667, 400,000 m → 0.6667, and negative distance → 0.40.
- [ ] Run xcodebuild test -project Carodo.xcodeproj -scheme Carodo -destination 'platform/iOS Simulator,id=<SIM_ID>' -only-testing:CarodoTests/JourneyMapHeightPolicyTests; verify the new tests fail before implementation.
- [ ] Implement JourneyMapHeightPolicy.heightFraction(distanceM:) with the formula in the interface.
- [ ] Pass journey.distanceM to JourneyMapHeader and size its Map using the fraction of the available container height; keep existing safe-area route padding and full-route camera framing.
- [ ] Re-run the targeted test and verify all boundaries pass. Confirm no fixed screen-point height was introduced.

## Task 2: Compute route analysis once off the main actor

**Files:**
- Create: Carodo/Core/Domain/JourneyDetailAnalysis.swift
- Create: CarodoTests/JourneyDetailAnalysisTests.swift
- Modify: Carodo/Features/Journeys/ViewModels/JourneyDetailViewModel.swift
- Modify: Carodo/Features/Journeys/Views/JourneyDetailSections.swift
- Modify: Carodo/DesignSystem/Components/RouteViews.swift

- [ ] Add equivalence tests that compare builder segments, speed shares, elevation and stops with the existing JourneyAnalysis functions for empty, short, loop and long synthetic routes.
- [ ] Assert adjacent speed-band segments share their transition point and an empty route yields empty segments.
- [ ] Run xcodebuild test -project Carodo.xcodeproj -scheme Carodo -destination 'platform/iOS Simulator,id=<SIM_ID>' -only-testing:CarodoTests/JourneyDetailAnalysisTests; verify the new tests fail before implementation.
- [ ] Implement the Sendable analysis result and @concurrent builder using existing pure functions; do not alter thresholds or output values.
- [ ] In JourneyDetailViewModel.load(), await one builder call after route points are available and assign its results. Keep repository reads, error fallbacks and loading behavior unchanged.
- [ ] Add the optional precomputed-segments initializer argument to JourneyRouteMap and pass prepared segments from JourneyMapHeader for Journey Detail; preserve the current calculation path for all other map callers.
- [ ] Re-run the targeted test and build the app. Review that route analysis is not recomputed on each parent body evaluation.

## Task 3: Bound elevation chart rendering

**Files:**
- Create: Carodo/Features/Journeys/Views/JourneyDetailElevationSection.swift
- Create: CarodoTests/ElevationChartSamplingTests.swift
- Modify: Carodo/Features/Journeys/Views/JourneyDetailSections.swift

- [ ] Add tests for unchanged arrays below the cap, no more than 250 points at/above the cap, first/last and global-extrema retention, and retention of a synthetic local peak and valley when the cap has room.
- [ ] Run xcodebuild test -project Carodo.xcodeproj -scheme Carodo -destination 'platform=iOS Simulator,id=<SIM_ID>' -only-testing:CarodoTests/ElevationChartSamplingTests; verify the new tests fail before implementation.
- [ ] Implement ElevationChartSampling.sample(_:) as a deterministic pure function using the single maximumPoints = 250 limit.
- [ ] Use sampled points only for compact and detailed Chart marks; keep the full ElevationSummary for climb/descent, extrema, scrub readout and accessibility. Use straight interpolation, a subtle CarodoSurface.accent area, a readable unit-aware distance/elevation axis in the detail sheet, and the existing GPS/barometer quality note.
- [ ] Re-run the targeted test and verify the chart remains valid for flat and sparse routes. Task 3 leaves JourneyElevationSection.swift as the standalone owner of its compact card and detail sheet; the other sections move in Task 4.

## Task 4: Refine hierarchy and split the view file

**Files:**
- Create: Carodo/Features/Journeys/Views/JourneyMapHeader.swift
- Create: Carodo/Features/Journeys/Views/JourneyDetailSummarySections.swift
- Create: Carodo/Features/Journeys/Views/JourneyDetailMetricsSections.swift
- Create: Carodo/Features/Journeys/Views/JourneyDetailContextSections.swift
- Modify: Carodo/Features/Journeys/Views/JourneyDetailSections.swift
- Modify: Carodo/Features/Journeys/Views/JourneyDetailView.swift

- [ ] Move each remaining named view to its assigned file without changing its initializer, data flow or behavior. JourneyMapHeader moves from JourneyDetailSections.swift here; JourneyDetailElevationSection is already a standalone component from Task 3. Remove moved declarations from the original file.
- [ ] Put the vehicle section immediately after elevation and before optional fuel/memories; keep the existing VehicleCard and selection-sheet behavior.
- [ ] Change driving conditions to a compact speed-distribution bar with a visible textual legend; keep moving, stopped and top-speed figures below it. Use existing SpeedBand semantic colors.
- [ ] Keep primary metrics compact and visually prioritize distance; preserve GPS-distance labeling and the existing title and narrative.
- [ ] Handle same-place start/end as a loop without duplicating a location name unnecessarily; retain the loop title supplied by JourneyDetailViewModel.
- [ ] Scope detail-content animation to sections whose data changes; do not animate Map as a side effect of changing JourneyDetails.
- [ ] Add or update focused tests for loop wording and missing optional sections, then run the relevant test classes and compile.

## Task 5: Use named design tokens and finish visual validation

**Files:**
- Modify: Carodo/DesignSystem/CarodoSurface.swift
- Modify: Carodo/DesignSystem/Components/RouteViews.swift
- Modify: Carodo/Features/Journeys/Views/JourneyDetailContextSections.swift
- Modify: Carodo/Features/Journeys/Views/JourneyDetailElevationSection.swift
- Modify: Carodo/Resources/Localization/Journeys.xcstrings only if visible copy changes.
- Modify: docs/specs/journeys.md
- Modify: docs/design-system.md

- [ ] Add named marker and media-overlay tokens using existing brand values; replace inline white/black styles in Journey Detail. Keep SpeedBand colors in DesignSystem and use CarodoSurface.accent for brand-accent linework.
- [ ] Confirm every new visible string has English/Vietnamese translations and translator comments; avoid adding copy if existing keys cover the refined layout.
- [ ] Update journeys spec for adaptive map, summary preservation, section order and Replay placeholder status; update design-system docs only for new token roles.
- [ ] Run xcrun swift-format format -i -r -p Carodo CarodoTests for touched Swift files, then xcrun swift-format lint --strict -r -p Carodo CarodoTests.
- [ ] Run xcodebuild test -project Carodo.xcodeproj -scheme Carodo -destination 'platform/iOS Simulator,id=<SIM_ID>' and xcodebuild -project Carodo.xcodeproj -scheme Carodo -destination 'generic/platform=iOS Simulator' build; record exact outcomes.
- [ ] Capture simulator screenshots for an 8.3 km urban loop and a 100+ km trip in Light and Dark; inspect top, middle and lower scroll positions, large Dynamic Type and VoiceOver labels.
- [ ] Profile a long trip with Instruments only if the build or visual check shows lag; compare route-analysis and chart work before claiming a runtime performance gain.
- [ ] Do not claim Replay or Weather is implemented; keep Replay disabled and Weather absent.

## Completion notes

The implementation phase must update carodo-ios/docs/specs/journeys.md and docs/design-system.md in the same change. No project.yml edit is expected; after adding Swift files, run xcodegen generate to refresh the generated project. Do not claim physical-device tracking validation for this UI-only work.
