# Master plan — what comes next (2026-11-12)

One ordered list of the work between today and the first TestFlight build, so each new session
starts from the same picture. Each line points to the plan that holds its detail; this file keeps
only the order, the owner's reason and the state. Update the state column when a step lands.

Owner's decision (2026-11-12): a "wow" first, for motivation and to have something to show:
cinematic 3D Replay and a short exported intro video. Then the TestFlight gates. Refactors ride
along with the work that touches each file, never as a big-bang pass while sessions run in
parallel.

## Order

| # | Track | Step | Detail | State |
|---|---|---|---|---|
| 0 | In flight | Commit M04 (place visits by start coordinates) from the Places/Map session | [technical-debt.md](technical-debt.md) TD-20 | In progress |
| 1 | **Wow** | W1: replay stop alignment (TD-1), so labels and highlights agree with the journal | [cinematic-replay.md](cinematic-replay.md#wow-track-owner-2026-11-12) | Done 2026-11-12 (carodo-ios 969ba51) |
| 2 | **Wow** | W2: R.2B contextual camera, one behaviour at a time (Rest, Hairpin, Terrain), each proven on device drives | cinematic-replay.md, Wow track | Next (Rest first) |
| 3 | **Wow** | W3: video spike: how to turn the `MKMapView` replay into frames (ReplayKit capture vs per-frame snapshot) | cinematic-replay.md, Wow track | Planned |
| 4 | **Wow** | W4: Cinematic Recap (a 30–60 s edit) and a 9:16 video export, privacy trim on | cinematic-replay.md, Wow track | Planned |
| 5 | TestFlight gate | TD-19: iOS 18 runtime, run the tests there; decide the minimum iOS if the deinit crash repeats | technical-debt.md TD-19 | Open |
| 6 | TestFlight gate | TD-6: freeze `v1_initial`, versioned non-destructive migrations with upgrade tests | technical-debt.md TD-6 | Open |
| 7 | TestFlight gate | TD-2: Apple Maps data terms (also covers map imagery inside an exported video) | [apple-maps-data-review.md](apple-maps-data-review.md) | Open |
| 8 | TestFlight gate | TD-20: rest of the source audit (backend track: H03, M06–M09, L09–L12) | [../audits/2026-11-12-carodo-source-audit.md](../audits/2026-11-12-carodo-source-audit.md) | Open |
| 9 | Device proof | One batch of real drives covering the open pending validations (GPS, Auto Mode, onboarding, live map, places, Feed, replay R.1 checks) | technical-debt.md, Pending validations | Open |
| 10 | Release prep | Privacy Report, `CollectedDataTypes`, widget "Ready" state, Dynamic Type cap (TD-16) | technical-debt.md | Open |

## Refactors that ride along (no step of their own)

Done in the same session as the next feature that edits the file, one `refactor:` commit each:

- `MainTabView.swift` (1,125 lines): extract the drive start/finish flow first (TD-13).
- `GRDBJourneyRepository.swift` (1,950 lines): split by query family (list, detail, places, atlas).
- `Repositories.swift` (1,122 lines): one protocol per file.
- `LoadState` declared in ten view models (TD-10); DEBUG launch arguments in 26 files (TD-14).
- Perf only where measured: TD-12 (Journey Detail decodes 30 routes), M04 with `-carodo.sampleJournal`.

## Why this order

- The wow track builds on R.1 and R.2A, which are done; it does not touch the schema or the API,
  so it can run while the gates wait.
- The gates (5–8) are each small, but every tester build depends on them; none should slip past
  the wow track's end.
- Device proof (9) gathers into one or two drives what is otherwise checked one feature at a time.
