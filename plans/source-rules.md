# Source rules: a Swift reader the architecture tests share, and `Core/Domain` by subject

Design, for the owner's approval. Written 2026-11-17 from TD-46 ([`technical-debt.md`](technical-debt.md))
and the owner's two asks that day: the reader is to be "strong enough for later rules to reuse", and
the split of `Core/Domain` goes with this work. `carodo-ios` at `c2e7d33` (tests in folders,
`d15db19`; `Core/Extensions` and `Core/Storage` dissolved, `c2e7d33`). After approval this becomes a
step-by-step plan; no code before that ([`../AGENT_WORKFLOW.md`](../AGENT_WORKFLOW.md)).

**Status (2026-11-17):** approved by the owner with D1 (by subject) and D2 (R4's never-awaiting case); plan [`source-rules-plan.md`](source-rules-plan.md). **Built:** carodo-ios `d00f412` (reader and rules) and `ca729d5` (Domain by subject) on `refactor/source-rules`; review fixes `244d9f2` (a string or a backticked keyword is never structure, balance also counts brackets and `#if`, R4 names the repository defaults one by one); merged into `main` as `b1ce357` (2,471 tests, 0 failures). Done. From here the rules stay lean: carodo-ios `AGENTS.md`, Conventions (`f531950`). Section 2's "not named at all" was wrong by one: Diagnostics asked `CLLocationManager.locationServicesEnabled()`, now in `Core/Location`.

## 1. Why

`ArchitectureTests` holds nine rules of `docs/architecture.md` by reading the sources, and
`LocalizationTests` holds the hard-coded string rule the same way. Each reads a file as lines of
text. That is cheap and has caught real mistakes, but a line of text is not Swift, so the rules
miss things a person would write without meaning to dodge them, and flag things that are not code:

| Hole | Example that passes today | Rule |
|---|---|---|
| Another spelling of a creation | `CLGeocoder.init()`, `let g: CLGeocoder = .init()` | R1, R2, R3, R7, R8 |
| A type alias | `typealias G = CLGeocoder` then `G()` | R1, R2, R3, R7, R8 |
| A number written without `_` | `111320.0` | R5 |
| An unqualified call inside the heavy type | `derive(…)` inside `SummaryRefresh` | R6 |
| An async member of a `nonisolated` type | `nonisolated enum X { static func f() async {…} }`: about 297 such members, read one by one on 2026-11-16 | R4 |
| A comment that is not a whole line, a string | `/* CLGeocoder( */`, `"CLGeocoder("`, `x // CLGeocoder(` all count as code | every rule |
| Targets not scanned | R3–R6 and R9 read only `Carodo/`, not `CarodoShared/` and `CarodoWidgets/` | R3–R6, R9 |
| Each test its own parsing | brace counting, `func ` search and a 12-line signature window in `ArchitectureTests`; regexes per line in `LocalizationTests` | all |

The last row is the reason the owner asked for a reader later rules reuse: a new rule today starts
by writing another line matcher. The next ones on the list need more than lines: "a View reads
`UserDefaults.standard`" (backlog, the audit of `UserDefaults.standard` and power reads in Views)
needs to know which file declares a `View`, and "nothing animates forever" (AGENTS.md, Resource
safety) needs a call chain.

## 2. What exists

- `CarodoTests/Rules/ArchitectureTests.swift` (253 lines): R1–R9 below and private helpers:
  `lines(containing:outside:in:)`, `names(_:in:)`, `braceDepths`, `enclosingFunction`,
  `functionName`, `signature`.
- `CarodoTests/Support/SourceFiles.swift`: the repository root (found by `project.yml`), the
  `.swift` files of a folder, a file's repository path, `isComment` (a line starting with `//`).
- `CarodoTests/Rules/LocalizationTests.swift`, `testViewsShowNoHardCodedStrings`: regexes per line,
  `#Preview` cut by splitting the file, a `verbatim:` line skipped.

The rules, numbered as the plans and `docs/architecture.md` number them (R9 is unnumbered today:
this spec names it):

| # | Rule | Test |
|---|---|---|
| R1 | Only `Core/Location` creates location managers | `testOnlyCoreLocationCreatesLocationManagers` |
| R2 | Only `Core/Motion` creates motion managers | `testOnlyCoreMotionCreatesMotionManagers` |
| R3 | Only the composition root creates a sensor adapter | `testOnlyTheCompositionRootCreatesASensor` |
| R4 | Work in a `nonisolated async` function is `@concurrent` | `testWorkInANonisolatedAsyncFunctionIsConcurrent` |
| R5 | One flat projection | `testOneFlatProjection` |
| R6 | A heavy function is reached only through its `@concurrent` entry | `testHeavyWorkIsReachedOnlyThroughItsConcurrentEntry` |
| R7 | Only `Core/MapLookup` asks Apple Maps | `testOnlyMapLookupAsksAppleMaps` |
| R8 | Only the composition root creates a lookup or a lookup cache | `testOnlyTheCompositionRootCreatesALookup` |
| R9 | No screen reads the whole journal with routes | `testNoScreenReadsTheWholeJournalWithRoutes` |

Two facts measured for this design (2026-11-17, comments left out):

- The system types of R1, R2 and R7 (`CLLocationManager`, `CMMotionManager`, `CLGeocoder`,
  `MKDirections`, … 19 names) are **not named at all** outside their folder: not as a creation,
  not as a type in a signature.
- The adapters of R3 and R8 are named elsewhere as types (`PlaceNameCache` in three stores and the
  Developer page, `JourneyMapSnapshotService` in four screens): for them only a creation counts.

## 3. Goals, non-goals

Goals:

1. **One reader** in `CarodoTests/Support/` that turns a Swift file into tokens and declarations,
   used by every source rule. No test reads source lines of its own after this.
2. **Every hole in section 1 closed**, each by a test that fails on the hole first.
3. **All three targets** scanned by every rule, unless the rule's meaning is narrower (R9: screens
   only, `Carodo/Features`).
4. **Later rules reuse it**: the reader answers "which declarations does this file make, of what
   kind, with which modifiers and conformances", "which calls does this function body make",
   "which literals does this file hold". Proved by porting `LocalizationTests`' hard-coded string
   rule onto it, and by one query the backlog's audit needs (section 6).
5. **TD-46 closed**: what still cannot be read from the sources is written down once, as a known
   limitation with its reason, not left as debt.
6. **`Core/Domain` in subject folders** (section 7), so 51 flat files become a few groups a person
   finds by the thing they are about.

Non-goals:

- **No new dependency.** No SwiftSyntax, no SwiftLint, no build plugin (owner, 2026-11-17: the reader
  is our own; P6). `pilgrim-ios`, read for this, has neither SwiftSyntax nor source-reading tests.
- **No type checker.** The reader knows declarations and names, not types: `let x = make()` where
  `make` returns a `CLGeocoder` is not seen. Section 8 lists what this leaves.
- **No behaviour change in the app.** The app's code changes only where a rule, made stronger,
  finds something real; each such change is named in the report.
- **No new rule beyond R1–R9 and the string rule** in this work. The reader is ready for them; each
  new rule is its own decision.

Anti-goals (a failure even if it works):

- A rule that fails on code which is fine, so people learn to add allow-list lines without reading
  them. Every allow-list entry keeps its one-line reason.
- A reader nobody can change: it stays small (target: under 400 lines with its own tests beside
  it) and is written for the cases Carodo's code has, not all of Swift.
- A slower test run: reading all three targets stays under one second on the Mac.

## 4. The reader

`CarodoTests/Support/SwiftSource.swift` (name to settle in the plan; it must not take a name an
imported framework uses). Built once per test run for all files (a static cache), since nine rules
and the string rule read the same files.

**Tokens.** Each with its line number:

- identifier and keyword (`func`, `nonisolated`, `async`, `await`, `typealias`, …);
- attribute (`@concurrent`, `@MainActor`, `@Observable`);
- number, with its value: `111_320.0`, `111320` and `1.1132e5` are the same number;
- string literal, with its text outside interpolations and whether that text has a letter
  (`"\(a) · \(b)"` has none), for single-line, multi-line (`"""`) and raw (`#"…"#`) strings, and
  with the tokens of each interpolation read as code;
- punctuation (`(`, `)`, `{`, `}`, `.`, `:`, `=`, `,`).

Comments (`//`, `///`, `/* … */` nested) are not tokens. The reader keeps them aside with their
lines, for a rule that needs one (none today).

**Declarations.** From the tokens, a tree per file:

- a type or extension: kind (`struct`, `enum`, `class`, `actor`, `protocol`, `extension`), name,
  modifiers and attributes (`nonisolated`, `final`, `@MainActor`), conformances, its token range;
- a function, initialiser or computed property: name, enclosing type, modifiers and attributes,
  `async`, `throws`, whether it has a body (a protocol requirement has none), its body's range;
- a type alias: its name and what it names;
- regions: `#if DEBUG` … `#endif` and `#Preview { … }`, so a rule can leave previews or DEBUG code
  out (the string rule leaves previews out today by splitting the file text).

The effective isolation of a function follows the code's own rule (docs/architecture.md,
Concurrency): its own `nonisolated` or `@concurrent`, else its type's or extension's, else the
target's default (main actor for the app and the widget).

**Queries** the rules use, each a function of the reader with a test of its own:

- `creations(of name:)`: `Name(`, `Name.init(`, `Name { … }` (a trailing closure), and
  `: Name = .init(`, through every alias of `Name` declared in the scanned files;
- `mentions(of name:)`: every token naming it, aliases included (R1, R2, R7, section 2);
- `calls(of function:in type:)`: qualified (`Type.f(`) anywhere, and unqualified (`f(`, `self.f(`)
  inside the type and its extensions;
- `numbers(in range:)`: every numeric literal whose value is in a range;
- `functions(where:)` and `types(where:)`: declarations filtered by kind, modifiers, conformance;
- for a token, the function and the type that enclose it.

Each hit reports `File.swift:line` and what was found, the form the tests print today, so an
allow-list entry stays a readable line.

**Tests of the reader** (`SwiftSourceTests`, Rules folder): small synthetic Swift snippets, one case
per row of section 1 and per token kind above (nested block comments, a `"` inside a raw string,
an interpolation holding a string, a `#Preview` inside `#if DEBUG`, a generic function, a function
whose signature runs over several lines, a default argument holding a closure, a property wrapper,
`init`, `deinit`, `subscript`, operator functions). Synthetic only: no source of the app pasted in.

## 5. The rules, rewritten on the reader

| # | Fails on | Change from today |
|---|---|---|
| R1, R2, R7 | A **mention** of the system type outside its folder, aliases included | From "a creation" to "any mention": stronger, and true today (section 2). Request value types that send nothing (`MKDirections.Request`, `MKMapSnapshotter.Options`) are part of the type's name and stay inside the folder too, true today |
| R3, R8 | A **creation** of the adapter outside `DependencyContainer.swift` and its own file | Creations through `.init`, an annotated `= .init(` and an alias are seen |
| R4 | An `async` function whose effective isolation is `nonisolated`, not `@concurrent`, and either (a) says `nonisolated` itself, as today, or (b) is a member of a `nonisolated` type or extension **and never awaits** | (b) is new: a function that never awaits is synchronous work on its caller's actor, the main one from a screen. A rough count finds about 34 (section 9, D2) |
| R5 | A number between 110,000 and 112,000 outside `Geo.swift` and `Core/PreviewData` | By value, not by `111_` text |
| R6 | A call of a heavy function, qualified or unqualified, in a function that is not `@concurrent` | The enclosing function comes from the declaration tree, not brace counting; the list of heavy functions stays in the test (section 8) |
| R9 | `.journeys()` called in `Carodo/Features` | Read as a call, not text |
| Strings | A user-facing initialiser or modifier given a literal with a letter in it, in a View folder or the widget, outside `#Preview`, unless the argument is `verbatim:` | Ported from regexes to tokens; the list of initialisers and modifiers stays the same |

Every rule scans `Carodo`, `CarodoShared` and `CarodoWidgets` unless its row says otherwise.
Every rule is seen failing on a planted case first (the method of the last two works: a violation
written in a real file, the test run, the line removed), and the planted lines are listed in the
completion report.

## 6. Reuse, shown

Two uses beyond R1–R9 prove the reader is reusable rather than shaped to them:

1. **The string rule** of `LocalizationTests` moves onto it (section 5).
2. **The backlog's audit query**, run once and reported, not made a rule: the Views that read
   `UserDefaults.standard` (a type conforming to `View`, or a file under `Features/*/Views`, that
   mentions `UserDefaults.standard`), and the files that read battery, heat or Low Power. The
   backlog row says "a count before a decision"; this gives the count with the reader, and the
   decision stays the owner's.

## 7. `Core/Domain` by subject

51 files, about 7,000 lines, flat. Most files hold a model and the pure functions on it together
(`JourneyStops.swift`, `FuelLog.swift`, `RouteHeat.swift`), so a split into "models" and "analyses"
would cut files in two or put them in the wrong half. A split by **subject**, the thing the file is
about, keeps each file whole and matches how the app's features are named (my proposal; D1):

| Folder | Files |
|---|---|
| `Domain/Journey/` | Journey, JourneyActivityDay, JourneyAnalysis, JourneyBreak, JourneyContext, JourneyDetailAnalysis, JourneyDetails, JourneyFilter, JourneyMerge, JourneyPoint, JourneyStops, StopPosition, SlowMoving, DrivingDynamics, ElevationTerrain, TrackQuality, RouteSimplifier, RouteStamp, PartOfDay, Commute |
| `Domain/Places/` | Place, PlaceDetection, PlaceVisitLog, POICandidate, StopPlaceResolver, FrequentPlaces, DrivePurpose, PrivacyZone, PrivateRegionRedaction, ProvincesCrossed |
| `Domain/Vehicle/` | Vehicle, VehicleIdentityLine, VehicleLink, VehicleLog, DriveLog, FuelLog, GarageAnalysis |
| `Domain/Feed/` | Community, DriveShape, DriveShapeMaker, FeedPublication, Username |
| `Domain/Passport/` | Achievements, PassportAnalysis, PassportExploration |
| `Domain/Map/` | RouteHeat, NewRoads |
| `Domain/` (stays) | Geo, Percentiles, StableHash, LoadState, Calendar+Zone: shared by every subject |

The plan checks each file against what it declares before it moves; a file that fits two subjects
goes where its main type's feature is. Rules that name a Domain path (R5's `Geo.swift`) and docs that
name one (two places today) follow. Tests follow their subject (`CarodoTests/Core/Domain/<Subject>/`).
A pure move: one commit of its own, after the reader, with no other session open.

## 8. What stays unprovable (TD-46 becomes a known limitation)

The reader reads Swift as written, not as typed. What follows cannot be held by reading, and is
recorded once as a known limitation (`KL-n`), closing TD-46:

- **Which functions are heavy.** "Walks a whole drive's fixes or the whole journal" is about data
  size, not syntax. R6's list stays a list, joined by one line when someone writes a heavy
  function; the complexity budget (docs/architecture.md) and review catch a missing one, and PV-27's
  measurement shows whether the listed ones were the right ones.
- **An async member that awaits and also does heavy work** (R4's case (b) sees only those that
  never await). Same remedy as above: R6's list.
- **Values passed around**: a system manager made by a function returning it, a closure holding a
  creation, `type(of:)`, generics. R1, R2 and R7 hold the strongest form (no mention at all), which
  covers these for system types; R3 and R8 do not see them.
- **Macros and generated code** are read as written, not expanded.

## 9. Decisions for the owner

- **D1. Domain by subject** (section 7), instead of the split into models and analyses suggested
  earlier in the conversation. Recommended: by subject, because most files hold both halves.
- **D2. R4's new case**: an async member of a `nonisolated` type that never awaits. A rough count
  (a script, not the reader) finds about 34: repository protocol default implementations, the
  sample stores, `BackendService` reading its key, `WeatherLookup`, `JourneyNarrator`. Each is
  either made `@concurrent`, made synchronous (no `async`), or listed with its reason. The sample
  and preview stores can be one entry by folder. Recommended: take it; the alternative is R4 as
  today, and section 8 grows by this case.

My calls, for checking while reading: the reader lives in the test target (not a module, no
target, P6); R1, R2 and R7 widen from "creation" to "mention"; the hard-coded string rule moves onto
the reader; the audit query of section 6 is run once, not kept as a test; the Domain move is its own
commit after the reader.

## 10. Done means

- Every rule and the string rule on the reader, each seen failing first; `SwiftSourceTests` green.
- `task lint`, `task warnings`, `task test` pass; the test count rises only by the reader's tests.
- `docs/architecture.md` (Concurrency, Sensors, Map lookups) states the rules as the reader holds
  them and drops "tripwires, not proofs" for what is now held; it names what is not (section 8).
- `technical-debt.md`: TD-46 resolved, the KL for section 8 added; this file's status line updated.
- The audit counts of section 6 in the completion report, and the backlog row updated with them.
- `Core/Domain` in subject folders, in its own commit, with its tests and docs.
