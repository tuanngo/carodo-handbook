# Technical debt, known limitations, pending validations

What a finished slice left open, so it is neither lost nor treated as work to do now. An entry is
added in the change that leaves it open (AGENT_WORKFLOW.md, completion report) and leaves this
file, with a line in its plan, when it is resolved. Being listed is not a priority: each entry says
what would make it worth taking up.

- **Technical debt**: a real technical problem that should be fixed at some point.
- **Known limitation**: a limit accepted on purpose; revisited only if its trigger happens.
- **Pending validation**: built and tested, not yet proven on real data or a real device.

Status: `Open` (recorded, not scheduled) · `Planned` (in a plan with a slice) · `Accepted` (a
limitation kept as it is) · `Waiting` (a validation waiting for data, a device or a tool).
IDs never change or get reused: `TD-n`, `KL-n`, `PV-n`.

## Technical debt

| ID | What | Impact | Status | Review when | Links |
|---|---|---|---|---|---|
| TD-1 | **Replay Stop Alignment.** Replay compresses a stop by the recorder's held state (and silent stops, `29f39f7`); the journal's stops come from `JourneyAnalysis.stopIntervals`. Two definitions of a finished stop on the timeline | Replay's "Stopped 12 min" can differ from the route timeline's stop; drift grows with each change to either | Open | Replay shows stop labels or highlights next to the route timeline, or either stop rule changes. First audit which part is the same question (a finished stop on the timeline: share) and which is not (moving or held at the playing moment: keep) | [smart-stops-v1.md §11.6](smart-stops-v1.md), `carodo-ios/Carodo/Core/Replay/ReplayTimeline.swift`, `carodo-ios/Carodo/Core/Domain/JourneyDetails.swift` |

## Known limitations

| ID | What | Impact | Status | Review when | Links |
|---|---|---|---|---|---|
| KL-1 | **Breaks between journeys read Stop and wait's ends.** `JourneyBreak` measures continuity on the store's `joinPair`: the drive just before by start (top-level, sure-alike), its last recorded fix across its parts, and the later drive's first recorded fix, untrimmed. When that drive is not the neighbour Merge lists, or a trim moved the ends, no break or a break on the recorded ends is shown. Prefer no suggestion to a guess | A break can be missing around joined, trimmed or unusual neighbours; not yet seen on real multi-part data | Accepted | A person reports a missing or odd break, or Merge's neighbour rule changes | [smart-stops-v1.md §11.5](smart-stops-v1.md), `carodo-ios/Carodo/Core/Domain/JourneyBreak.swift`, `GRDBJourneyRepository.joinPair` |
| KL-2 | **A stop begins only with a slow fix that has a speed.** Fixes with no speed after a moving one (no slow run begun) say nothing (`StopRule.Reading.unclear`): the drive is not stopped until a slow fix comes, or the person ends it. The recorder's slow run also ends at any known speed over 1 m/s (stricter than auto-finish's hysteresis), so its parked drift before such a stop counts until the end at the stop cuts it. Accepted: reading a stop from positions alone would hold a car crawling with no speed | Seen once in replayed data (2026-11-06: the last known speed before the parked fixes was 3.1 m/s; auto-finish still had its slow run) | Accepted | A pulled drive where a parking is never confirmed, or the end at a stop lands late | `carodo-ios/Carodo/Core/Tracking/StopRule.swift`, `RouteRecorder.noteSlowness` |

## Pending validations

| ID | What | Proven so far | Missing | Status | Review when | Links |
|---|---|---|---|---|---|---|
| PV-1 | **Saved Place on a stop** ("At Home · 8 min") | Unit tests (inside and outside the circle, private place) | No real stop in the pulled data lies inside a saved place | Waiting | A pulled database or `.carodo` with a stop at a saved place; replay it (`testSmartStopsOfBackups`) | [smart-stops-v1.md](smart-stops-v1.md), `JourneyStops.swift` |
| PV-2 | **Smart Stops on an iPhone** (route timeline lines, short-stop sum, breaks, Merge Drives) | Simulator screenshots on restored real data: Light/Dark, Vietnamese, large type | A run on a physical iPhone: layout, VoiceOver on a break's Merge button, the sheet it opens | Waiting | The next device session (`carodo-ios/docs/operations/device-testing.md`) | [smart-stops-v1.md](smart-stops-v1.md) |
| PV-3 | **Driving dynamics measurement** (shadow, `DrivingDynamics` v1) | Synthetic tests; replay of 10 real motorbike drives (2/3/5 s windows) | A controlled run against a reference (OBD or 10 Hz GNSS): does Core Location flatten real braking peaks; is the spread calibrated; 3 or 5 fixes a window. No car drive in the pulled data yet. Motorbike thresholds from field distributions | Waiting | A reference device and a closed, safe area; or the first car drives pulled | [driving-dynamics-shadow.md §7](driving-dynamics-shadow.md), [journey-v2.3-enrichment-audit.md §G](journey-v2.3-enrichment-audit.md) |
| PV-4 | **The `dynamics` tracking log line on a device** ("Speed changes" after a saved drive) | End-to-end tests through the real session, writer and store | One real drive on an iPhone, the line read in Tracking status | Waiting | The next drive with Developer mode on | `carodo-ios/Carodo/App/DependencyContainer.swift` (`logDrivingDynamics`) |
| PV-5 | **Stops with no speed and silent stops** (`StopRule`, `StopDetector.settle`, recorder rules v3) | Unit tests on both sides (100 m radius, 30 s); replay of 12 real Carodo tracks through a port of the rule: two parkings indoors confirmed at 30 s instead of 128 s and 135 s late, the rest unchanged | A real parking indoors or in a garage with auto-finish on: `autoFinished` and `stop stopped` in Tracking status against when the car stopped; a stop where the GPS was lowered and no fix came | Waiting | The next device session | `carodo-ios/docs/tracking.md` (Auto-finish, No speed, Silent stop) |
| PV-6 | **WAL on an iPhone** (`DatabasePool`, `synchronous = NORMAL`) | Tests on a file database (WAL mode, a reopen keeps every commit); `task pull-db` run against a pre-WAL install | A drive recorded with the iPhone locked (writes to `-wal` under the default file protection), and `task pull-db` right after it shows that drive | Waiting | The next device install | `carodo-ios/Carodo/Core/Persistence/DatabaseManager.swift`, `carodo-ios/Taskfile.yml` (`COPY_DB`) |
