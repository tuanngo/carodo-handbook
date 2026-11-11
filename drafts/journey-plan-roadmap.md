# Roadmap

## V2.2

1. V2.2 — Contextual Journey & Story
In progress · Completing the facts, the regions crossed and the narrative.
2. V2.2A.1 — Journey Identity & Context
Core implemented, UI polish.
3. V2.2A.2 — Adaptive Elevation
Done (2026-11-07); device checks open.
4. V2.2A.3 — Provinces Crossed: Current phase.
5. V2.2A.4 — Contextual Summary
Deterministic narrative.
5. V2.2B — Intelligent Journey Story Apple Foundation Models.

## V2.3R — Cinematic Journey Replay (before Enrichment, plan: plans/cinematic-replay.md)

1. R.1	Cinematic Route Replay	Full-screen replay, Follow camera, timeline, distance/speed
2. R.2	Camera & Terrain	Cinematic Director (Follow, Reveal, Highlight), terrain
3. R.3	Replay Highlights & Sharing	Highlights, a 30–60 s Cinematic Recap, video

## V2.3 — Journey Enrichment (after V2.3R)

Numbered by what was built (audit: plans/journey-v2.3-enrichment-audit.md). The old labels V2.3A–D: A and B became
V2.3.2–V2.3.3, C and D are at the end.

1. V2.3.0	Foundation	One stop segmentation (`stopIntervals`), `TrackQuality`. Done `fda2612`
2. V2.3.1	Driving Dynamics Shadow	Measured and logged, not shown. Done `7ffb515` (plans/driving-dynamics-shadow.md)
3. V2.3.2	Smart Stops V1	Stops on the Route Timeline, breaks between two journeys, no activity labels. Done `365ceaa` (plans/smart-stops-v1.md)
4. V2.3.3	Journey Points	Start, End, Stop, Break open on the Map; automatic Nearby POI, at most one, not stored. Slice 1 Map: done (`3aa3e25`, `e027155`). Slice 2 Nearby POI: done (`f66dcfa`), waiting for PV-13. Slice 3 Start/End: done (`193d6ca`). Then: past Journey Points on Footprints (plans/journey-points.md)
5. V2.3.4	Walking Evidence	Core Motion during a stop (walking = left the car), read and kept soon after the drive because Core Motion keeps only ~7 days on the recording device (audit, table B and risk C.3). Not collected early yet; decide again before the first TestFlight build (plans/journey-points.md §6)
6. V2.3.5	Fuel & Charging Suggestions	Connect a stop to the Fuel Log: open a prefilled fill-up form, the person saves it (audit §G.4)
7. V2.3.6	Geographic Milestones	Cross-Border Milestones, a history of regions discovered
