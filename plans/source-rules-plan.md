# Source rules Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One Swift reader in the test target that every source-reading rule uses, R1–R9 and the
hard-coded string rule rewritten on it with each hole of TD-46 closed, then `Core/Domain` in subject
folders.

**Architecture:** A tokenizer and a declaration tree, written for the Swift Carodo writes, in
`CarodoTests/Support/`; a cached tree of all three targets; small queries (creations, mentions,
calls, numbers, enclosing function, effective isolation) that the rules call. No dependency, no
target. The Domain move is a separate, pure commit after the rules.

**Tech Stack:** Swift 6, XCTest, Foundation only. XcodeGen picks up new files and folders.

**Spec:** [`source-rules.md`](source-rules.md) (approved 2026-11-17 with D1 by subject and D2 R4's
never-awaits case).

## Global Constraints

- No new package, target or tool (P6; spec section 3). Foundation and XCTest only.
- Every rule scans `Carodo`, `CarodoShared`, `CarodoWidgets`, except R9 (`Carodo/Features`) and the
  string rule (the View folders it lists today plus `CarodoWidgets`).
- Hits print as `File.swift:line: what` (today's form), allow-list entries are those strings, each
  with a one-line reason comment.
- The reader stays under 400 lines (tests excluded); reading all three targets once stays under 1 s
  on the Mac (Debug test run).
- Test fixtures are synthetic Swift snippets; no source of the app pasted into a test.
- Test target is `nonisolated` by default (`project.yml`); reader types are value types, `Sendable`.
- No `!`, `try!`, `as!` (AGENTS.md, Swift). `task format` then `task lint` pass.
- Commits: one per finished outcome (AGENTS.md, Git): commit A = reader + rules + app fixes + docs;
  commit B = the Domain move. No AI attribution (P8). Handbook changes in their own commit there.
- Every rule is seen failing on a planted line in a real file before it is called done; the
  planted lines are removed and listed in the completion report.

## Review Focus

1. **A file the reader misreads makes a rule pass silently.** Expect: a test that every scanned file
   reads with balanced braces and ends at depth 0 — Task 3, `testEveryFileReadsToBalancedScopes`.
2. **`#if … #else … #endif` with a brace opened in each branch** (common around `#available`
   shims) leaves the depth wrong after it. Expect: the reader reads only the first branch's braces —
   Task 3, `testIfElseBranchesOpeningBracesKeepDepth`.
3. **`/` as division, `a/b`, next to a string** is not a regex literal start; the app has no regex
   literals today. Expect: plain division tokens — Task 2, `testSlashIsPunctuation`.
4. **The new rule finds less than the old one** on today's code. Expect: before deleting an old
   matcher, both run on the tree and the new set contains the old set — Task 5 to 9, the
   "differential" step.
5. **Speed.** Expect: the whole tree read once in under 1 s — Task 4, `testTheTreeReadsInUnderASecond`
   (measured with `ContinuousClock`; asserted with a 3 s ceiling so a busy Mac does not fail it, the
   measured figure reported against the 1 s target).

---

### Task 1: Workspace

**Files:** none in the repo.

- [ ] **Step 1:** `git worktree add ../carodo-ios-source-rules -b refactor/source-rules` from
  `carodo-ios` `main` (`c2e7d33` or later); `task generate` inside it.
- [ ] **Step 2:** Clone a simulator for this work:
  `xcrun simctl clone E91B74EB-1AC2-4183-965F-8E0FBD710154 "Carodo source-rules"`; put its UDID as
  `SIM_ID` in the worktree's `.env`.
- [ ] **Step 3:** Baseline: `task test`. Expected: `Executed 2445 tests, with 23 tests skipped and 0
  failures`. Record the number.

### Task 2: Tokens

**Files:**
- Create: `CarodoTests/Support/SwiftSource.swift`
- Test: `CarodoTests/Rules/SwiftSourceTests.swift`

**Interfaces:**
- Produces:
  ```swift
  struct SwiftToken: Sendable, Equatable {
      enum Kind: Sendable, Equatable {
          case identifier, keyword, attribute, punctuation
          case number(Double)
          case string(text: String, hasLetter: Bool)   // text outside interpolations
      }
      let kind: Kind
      let text: String      // as written ("111_320.0", "@concurrent", "(")
      let line: Int         // 1-based
  }
  struct SwiftSource: Sendable {
      let path: String          // repository path, "Carodo/Core/…/X.swift"
      let tokens: [SwiftToken]
      let comments: [(line: Int, text: String)]
      init(path: String, text: String)
  }
  ```
  Keywords: Swift's declaration and statement keywords that rules read (`func`, `init`, `deinit`,
  `subscript`, `var`, `let`, `struct`, `enum`, `class`, `actor`, `protocol`, `extension`,
  `typealias`, `nonisolated`, `async`, `await`, `throws`, `return`, `static`, `final`, `private`,
  `fileprivate`, `public`, `internal`, `override`, `mutating`, `import`, `#if`, `#else`, `#elseif`,
  `#endif`, `#Preview`); everything else alphanumeric is an identifier.
  An interpolation's contents are emitted as ordinary tokens right after the string token.

- [ ] **Step 1: Write failing tests** in `SwiftSourceTests`, one per case; each builds
  `SwiftSource(path: "X.swift", text: …)` and asserts on `tokens` (kinds and texts) or `comments`:
  - `testCommentsAreNotTokens`: `a // CLGeocoder(\n/* CLGeocoder( /* nested */ still */ b` →
    identifiers `a`, `b` only; two comments.
  - `testStringsAreOneToken`: `"CLGeocoder("` → one `.string(text: "CLGeocoder(", hasLetter: true)`.
  - `testRawAndMultilineStrings`: `#"a "quoted" b"#` and `"""\nline "x"\n"""` → one string token each.
  - `testInterpolationIsCode`: `"\(name) · \(year)"` → `.string(text: " · ", hasLetter: false)`
    followed by identifiers `name`, `year`; `"a \(f("b")) c"` → outer string, then `f`, `(`, string
    `b`, `)`.
  - `testNumbersByValue`: `111_320.0`, `111320`, `1.1132e5` → `.number(111320)` each; `0x10` → 16.
  - `testAttributesAndKeywords`: `@concurrent nonisolated func f() async` → attribute, keyword ×3,
    identifier, punctuation, keyword.
  - `testSlashIsPunctuation`: `let r = a/b + "x"` → `/` punctuation, string `x`.
  - `testLinesCount`: the second line's token has `line == 2` across a multi-line string.
- [ ] **Step 2:** Run `task test` with `-only-testing:CarodoTests/SwiftSourceTests` (or Xcode). Expected:
  FAIL, `SwiftSource` not defined.
- [ ] **Step 3:** Implement the tokenizer in `SwiftSource.init(path:text:)`: one pass over the
  `String`'s unicode scalars, a stack for interpolation depth inside strings.
- [ ] **Step 4:** Run the same tests. Expected: PASS.

### Task 3: Declarations and regions

**Files:**
- Modify: `CarodoTests/Support/SwiftSource.swift`
- Test: `CarodoTests/Rules/SwiftSourceTests.swift`

**Interfaces:**
- Consumes: `SwiftSource.tokens`.
- Produces:
  ```swift
  struct SwiftDeclaration: Sendable {
      enum Kind: Sendable, Equatable { case type(String), function, alias }  // type: "struct", "extension", …
      let kind: Kind
      let name: String            // "init", "deinit", "subscript" for those
      let modifiers: Set<String>  // nonisolated, static, private, final, …
      let attributes: Set<String> // "@concurrent", "@MainActor", …
      let conformances: [String]  // after ":" on a type or extension
      let isAsync: Bool
      let parent: Int?            // index into declarations
      let tokens: Range<Int>      // the whole declaration
      let body: Range<Int>?       // between its braces; nil for a requirement
      let aliasOf: String?        // for .alias
      let line: Int
  }
  enum Isolation: Sendable, Equatable { case mainActor, nonisolated, concurrent }
  extension SwiftSource {
      var declarations: [SwiftDeclaration] { get }   // computed once in init
      var previewRanges: [Range<Int>] { get }        // #Preview { … } bodies
      var debugRanges: [Range<Int>] { get }          // #if DEBUG … #endif
      func enclosingFunction(ofToken index: Int) -> Int?   // index into declarations
      func enclosingType(ofToken index: Int) -> Int?
      func isolation(of declaration: Int) -> Isolation
  }
  ```
  `isolation`: `@concurrent` on the function → `.concurrent`; its own `nonisolated` → `.nonisolated`;
  else the nearest enclosing type or extension with `nonisolated` → `.nonisolated`; `@MainActor`
  anywhere on the way → `.mainActor`; else `.mainActor` (the app's and widget's default).

- [ ] **Step 1: Write failing tests:**
  - `testTypesFunctionsAndAliases`: a `nonisolated enum E { static func f() async {} }`, an
    `extension E: P {}`, a `typealias G = CLGeocoder`, a `protocol Q { func r() async }` → four
    kinds, `f.isAsync`, `f.parent` is `E`, `r.body == nil`, alias `aliasOf == "CLGeocoder"`,
    extension conformances `["P"]`.
  - `testSignatureOverManyLines`: a `func g(\n a: Int,\n b: () -> Void = { }\n) async throws -> Int {`
    → one function, `isAsync`, body starts after the last `{`.
  - `testInitDeinitSubscriptAndComputed`: names `init`, `deinit`, `subscript`; a `var x: Int { 1 }`
    counts as a function with a body.
  - `testIsolation`: `@concurrent nonisolated func a() async`, `nonisolated struct S { func b() async }`,
    `struct T { func c() async }`, `nonisolated extension T { func d() }`, `@MainActor func e()` inside
    `S` → `.concurrent`, `.nonisolated`, `.mainActor`, `.nonisolated`, `.mainActor`.
  - `testEnclosingFunction`: a call token inside a closure inside `func h()` → `h`; a token at type
    level → nil.
  - `testPreviewAndDebugRanges`: `#if DEBUG\n#Preview { Text("x") }\n#endif` → the string token lies
    in both ranges.
  - `testIfElseBranchesOpeningBracesKeepDepth`: `#if A\nfunc f() {\n#else\nfunc f() {\n#endif\n}\nfunc g() {}`
    → `g.parent == nil`.
  - `testEveryFileReadsToBalancedScopes`: for every file of the three targets
    (`SourceFiles.swift(in:)`), braces balance (the reader's depth ends at 0, never below). Fails with
    the file names.
- [ ] **Step 2:** Run. Expected: FAIL (members not defined).
- [ ] **Step 3:** Implement: one pass over tokens with a scope stack; a declaration keyword starts a
  pending declaration that the next `{` at the same depth opens (or a newline-level end / `;` /
  `}` closes as a requirement); modifiers and attributes are the tokens collected since the last
  declaration end. In `#if` blocks only the first branch's tokens open or close scopes.
- [ ] **Step 4:** Run. Expected: PASS, including the balanced-scopes test over the real tree. A file
  it fails on is a reader bug to fix, never an exclusion.

### Task 4: The tree and its queries

**Files:**
- Create: `CarodoTests/Support/SourceTree.swift`
- Modify: `CarodoTests/Support/SourceFiles.swift` (keep `repo`, `swift(in:)`, `path(of:)`; `isComment`
  removed in Task 9 when its last caller goes)
- Test: `CarodoTests/Rules/SwiftSourceTests.swift`

**Interfaces:**
- Consumes: `SwiftSource`, `SwiftDeclaration`, `SourceFiles`.
- Produces:
  ```swift
  struct SourceHit: Sendable, Equatable, CustomStringConvertible {
      let path: String; let line: Int; let what: String
      var description: String { "\(fileName):\(line): \(what)" }   // fileName = last path component
  }
  struct SourceTree: Sendable {
      static let app: SourceTree          // Carodo, CarodoShared, CarodoWidgets, read once
      let files: [SwiftSource]
      init(files: [SwiftSource])          // for tests: synthetic files
      func under(_ prefixes: [String]) -> [SwiftSource]
      func excluding(_ prefixes: [String]) -> SourceTree
      var aliases: [String: String] { get }                 // alias → named type, all files
      func mentions(of type: String) -> [SourceHit]         // aliases followed
      func creations(of type: String) -> [SourceHit]        // T(, T.init(, T {, `: T = .init(`; aliases followed
      func calls(of function: String, on type: String) -> [SourceHit]  // T.f( anywhere; f( / self.f( inside T and its extensions
      func numbers(in range: ClosedRange<Double>) -> [SourceHit]
  }
  ```
  `what` is the needle as the rules print it today (`"CLGeocoder("`, `"111_320.0"`), so allow-lists
  read the same.

- [ ] **Step 1: Write failing tests** on synthetic `SourceTree(files:)`:
  - `testCreationsInEverySpelling`: `CLGeocoder()`, `CLGeocoder.init()`,
    `let g: CLGeocoder = .init()`, `typealias G = CLGeocoder` + `G()` → four hits;
    `MKDirections.Request()` is not a creation of `MKDirections`; `elevationNoteBarometer(` is not
    `Barometer`.
  - `testMentionsFollowAliases`: `func f(_ m: CLLocationManager)` and an alias use → hits.
  - `testCallsQualifiedAndUnqualified`: `SummaryRefresh.derive(x)` in a free function, `derive(x)`
    and `self.derive(x)` inside `extension SummaryRefresh` → three hits; `derive(x)` inside another
    type → none.
  - `testNumbersByValue`: `111_320.0`, `111320`, `110574` in range `110_000...112_000` → three;
    `"111320"` (a string) and a comment → none.
  - `testTheTreeReadsInUnderASecond`: `SourceTree.app` built from scratch (a fresh `init`) under
    3 s; prints the measured time.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement on the tokens: a name is a token whose previous token is not `.`
  (except `self.`) and whose previous character is not part of a longer identifier.
- [ ] **Step 4:** Run. Expected: PASS; note the time for the report.

### Task 5: R1, R2, R7 by mention; R3, R8 by creation

**Files:**
- Modify: `CarodoTests/Rules/ArchitectureTests.swift` (the five tests and `allTargets`)

**Interfaces:** Consumes `SourceTree.app`, `under`, `excluding`, `mentions(of:)`, `creations(of:)`.

- [ ] **Step 1: Differential.** In each test, compute the old hits and the new hits on today's tree
  (temporarily both); assert new ⊇ old and print the extra ones. Expected: no extra hit (section 2 of
  the spec measured none), else each is read: fix the code or add a reasoned allow entry.
- [ ] **Step 2:** Rewrite: R1, R2, R7 assert `mentions(of:)` outside their folder is `[]` for the
  same type lists as today (R7 keeps its empty `allowed`); R3, R8 assert `creations(of:)` outside
  `Carodo/App/DependencyContainer.swift` and the type's own file(s) (today's `own` tables) is `[]`.
  Remove the old matchers from these tests.
- [ ] **Step 3: Planted failures**, one at a time in a real file of `Carodo/Features`, each run and
  removed: `let g: CLGeocoder = .init()` (R7), `typealias M = CMMotionManager` (R2),
  `_ = CoreLocationSource.init(` … (R3, a real initialiser's arguments), `MapDataCache.init(` …
  (R8). Expected: each test FAILS naming the planted line.
- [ ] **Step 4:** `task test`. Expected: PASS, count = baseline + the reader's tests.

### Task 6: R5 by value, R9 as a call

**Files:** Modify `CarodoTests/Rules/ArchitectureTests.swift` (`testOneFlatProjection`,
`testNoScreenReadsTheWholeJournalWithRoutes`).

- [ ] **Step 1: Differential** as in Task 5.
- [ ] **Step 2:** R5: `numbers(in: 110_000...112_000)` outside `Carodo/Core/Domain/Geo.swift`,
  `Carodo/Core/PreviewData/` and `RouteGlyphView.swift` (today's reason kept) is `[]`. R9:
  `calls(of: "journeys", on: …)` cannot know the receiver's type, so R9 matches the token sequence
  `.` `journeys` `(` `)` in `under(["Carodo/Features"])`.
- [ ] **Step 3: Planted failures:** `let k = 111320.0` in a Feature file (R5); `try await
  repository.journeys()` in a ViewModel (R9). Expected: FAIL each, then removed.
- [ ] **Step 4:** `task test`. Expected: PASS.

### Task 7: R4 with D2 (members of `nonisolated` types that never await)

**Files:**
- Modify: `CarodoTests/Rules/ArchitectureTests.swift` (`testWorkInANonisolatedAsyncFunctionIsConcurrent`)
- Modify: the app files the findings name (only as Step 3 decides)

**Interfaces:** Consumes `declarations`, `isolation(of:)`, `body`.

- [ ] **Step 1:** Rewrite R4: a function with a body, `isAsync`, `isolation == .nonisolated`, and
  either its own `modifiers` contain `nonisolated` (case a, today's), or it awaits nowhere in its
  body (no `await` keyword token in `body`) (case b). Case (a) keeps today's `allowed` list; case (b)
  gets its own list. Run it and print the findings. Expected: case (a) = today's four; case (b)
  about 34 (spec section 9).
- [ ] **Step 2: Differential** for case (a): equal to today's set.
- [ ] **Step 3: Classify each case (b) finding**, in this order of preference, and write the reason
  line beside each kept entry:
  1. The body walks a collection whose size grows with a drive or the journal (a loop, `map`,
     `filter`, `reduce`, `sorted` over fixes, journeys, routes) → mark the function `@concurrent`.
  2. The body is a constant or a stored value (`return []`, `nil`, a property): a default of a
     protocol requirement or a sample/preview store → allowed. All of `Core/PreviewData/` and the
     `Sample*` stores are one entry by file prefix: `"SampleRepositories.swift"`, reason "preview
     data, returns fixed values".
  3. Anything else (Keychain reads in `BackendService`, `WeatherLookup`, `JourneyNarrator`): read
     the body; light work → allowed with its reason; work proportional to data → `@concurrent`.
  Dropping `async` from a protocol requirement is not done here (it changes every caller); note any
  candidate in the report instead.
- [ ] **Step 4: Planted failure:** `nonisolated enum Planted { static func f() async -> Int { (0..<10).reduce(0, +) } }`
  in a Feature file. Expected: FAIL (case b), then removed.
- [ ] **Step 5:** `task test` and `task warnings`. Expected: PASS, no warnings (a `@concurrent` added
  to a function that captures main-actor state is a compiler error to fix by passing values in).

### Task 8: R6 on the declaration tree

**Files:** Modify `CarodoTests/Rules/ArchitectureTests.swift` (`heavy`,
`testHeavyWorkIsReachedOnlyThroughItsConcurrentEntry`; remove `braceDepths`, `enclosingFunction`,
`functionName`, `signature`).

**Interfaces:** Consumes `calls(of:on:)`, `enclosingFunction(ofToken:)`, `isolation(of:)`.

- [ ] **Step 1:** `heavy` becomes `[(type: String, function: String, entry: String)]`:
  `("SummaryRefresh", "derive", "SummaryRefresh.deriving")`, `("CloudRecordCoding", "incoming",
  "CloudRecordCoding.decoding")`, `("AchievementEngine", "crossings",
  "AchievementEngine.changes(of:catalogue:stored:)")`, `("DriveShapeMaker", "shape",
  "DriveShapeMaker.shaping")`.
- [ ] **Step 2: Differential:** new hits ⊇ old hits (old: none). New unqualified hits inside the
  heavy types: each must sit in a `.concurrent` function (today `SummaryRefresh.run` and the entries,
  spec section 1); a call from a `.mainActor` or `.nonisolated` synchronous function is a finding to
  fix through the entry.
- [ ] **Step 3: Planted failure:** an unqualified `derive(` call added to a non-`@concurrent`
  function in `extension SummaryRefresh` (in its own file). Expected: FAIL, then removed.
- [ ] **Step 4:** `task test`. Expected: PASS.

### Task 9: The string rule on the reader; old helpers gone

**Files:**
- Modify: `CarodoTests/Rules/LocalizationTests.swift` (`testViewsShowNoHardCodedStrings`)
- Modify: `CarodoTests/Support/SourceFiles.swift` (remove `isComment`)

- [ ] **Step 1: Differential:** today's regex hits and the new hits on the tree; both `[]` today,
  and the test's own samples (`Text("Hello")`, `Button("Save") {`, `.navigationTitle("Map")`,
  `accessibilityAction(named: "Spin")`, `LocalizedStringResource("x.y", defaultValue: "Hi")` caught;
  `Text(.Onboarding.carTitle)` and `Text("\(name) · \(year)")` not) kept as synthetic
  `SourceTree(files:)` cases.
- [ ] **Step 2:** Rewrite: a hit is an identifier from today's two lists (initialisers: `Text`,
  `Button`, `Label`, `Toggle`, `TextField`, `SecureField`, `Picker`, `Section`, `Menu`, `Link`,
  `LabeledContent`, `LocalizedStringResource`; modifiers after `.`: `navigationTitle`,
  `accessibilityLabel`, `accessibilityHint`, `accessibilityValue`, `alert`, `confirmationDialog`,
  `help`; `accessibilityAction` with label `named:`) followed by `(` and then a string token with
  `hasLetter`, not inside `previewRanges`, not after a `verbatim:` label; same folders and the
  `StartDriveIntent.swift` exclusion with its reason.
- [ ] **Step 3: Planted failure:** `Text("Planted")` in a View, and `Text("x")` in a comment that
  must NOT fail. Expected: one hit, then removed.
- [ ] **Step 4:** Grep: no test calls `components(separatedBy: "\n")` on a source file any more, and
  `SourceFiles.isComment` has no caller; remove it. `task format`, `task lint`, `task test`,
  `task warnings`. Expected: all pass.

### Task 10: The audit counts, docs, commit A

**Files:**
- Modify: `docs/architecture.md` (Concurrency paragraph from "`ArchitectureTests` (R4) lists…" to
  "…reviewed by hand."; the Sensors and Map lookups rule lines)
- Modify: `AGENTS.md` only if a rule's wording there changes (the recipes for a sensor and an Apple
  Maps request say "`ArchitectureTests` fails on a manager created elsewhere": becomes "named
  elsewhere")
- Handbook (its own commit): `plans/technical-debt.md`, `plans/backlog.md`, `plans/source-rules.md`

- [ ] **Step 1: Audit query, run once** (a temporary test, deleted before the commit, or an XCTest
  that prints and is not kept): the files under `Features/*/Views` or declaring a type conforming to
  `View` that mention `UserDefaults` then `.standard`; the files that mention `ProcessInfo` `.thermalState`,
  `isLowPowerModeEnabled`, `UIDevice` `.batteryLevel`/`.batteryState`. Record the counts and file
  names for the report and the backlog row.
- [ ] **Step 2:** `docs/architecture.md`: R1, R2, R7 "no file outside the folder names the type";
  R3, R8 "no creation, in any spelling, outside the container"; R4 both cases; R5 by value; the
  closing sentence lists only what section 8 of the spec says stays unprovable.
- [ ] **Step 3:** Self-review against AGENTS.md (Self-review list); `git diff --stat` holds only this
  work.
- [ ] **Step 4: Commit A** (stage own paths):
  `refactor(tests): one swift reader for the source rules; r1-r9 and the string rule on it` with a
  body naming the holes closed and any app function made `@concurrent`.
- [ ] **Step 5: Handbook commit:** TD-46 → resolved with the hash; a new `KL-n` "What source rules
  cannot read" (spec section 8); backlog's `UserDefaults.standard` row with the counts; this plan's
  and the spec's status lines.

### Task 11: `Core/Domain` by subject, commit B

**Files:**
- Move: 46 files of `Carodo/Core/Domain/` into `Journey/`, `Places/`, `Vehicle/`, `Feed/`,
  `Passport/`, `Map/` (spec section 7 table); `Geo`, `Percentiles`, `StableHash`, `LoadState`,
  `Calendar+Zone` stay.
- Move: their tests under `CarodoTests/Core/Domain/` the same way (a test follows its subject's
  file; a test of several goes with the first it names).
- Modify: `ArchitectureTests` R5's `Geo.swift` path (unchanged: Geo stays), any rule or doc naming a
  moved path (`grep -rn 'Core/Domain/' docs AGENTS.md CarodoTests`), `AGENTS.md` architecture block
  (`Domain/` line: its subject folders).

- [ ] **Step 1:** Before moving, read each file's main type; a file the table puts against its main
  type's feature moves where that feature is, and the report lists the change from the table.
- [ ] **Step 2:** `git mv` the files; `task generate`.
- [ ] **Step 3:** `task lint`, `task test` (same count as after commit A), `task warnings`.
  Expected: pass.
- [ ] **Step 4: Commit B:** `refactor(domain): core/domain in subject folders` (pure moves and the
  doc lines).

### Task 12: Review and merge

- [ ] **Step 1:** One fresh reviewer over `main..refactor/source-rules` (superpowers:requesting-code-review),
  with the spec and this plan.
- [ ] **Step 2:** Fix what it finds into commit A or B (amend while unpushed, own commits only).
- [ ] **Step 3:** In `carodo-ios`: `git merge --no-ff refactor/source-rules`; `task test` on `main`.
  Push only when the owner asks.
- [ ] **Step 4:** Ask the owner before removing the worktree, the branch and the cloned simulator.
