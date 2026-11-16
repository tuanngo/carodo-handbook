# iOS open-source repos

Repos worth reading while building Carodo. Checked 2026-10-31 (stars, licence and last push change;
recheck before relying on one). Clones live **outside** the Carodo repos, in `~/code/oss/swift/<name>` (all of the repos below are
cloned there, 2026-11-16), so their code never lands in our history by accident.

## Licence rules — read before copying anything

| Licence | What we may do |
|---|---|
| **MIT** | Read, and copy code if we keep its copyright + licence notice (add it to an acknowledgements file). Adding the repo as a package is a new dependency: ask first (root `AGENTS.md` invariant 6). |
| **GPL-3.0** | Read for ideas only. **Never copy code**: it would force Carodo itself under GPL. Re-implement from our own understanding. |
| **No licence** | All rights reserved. Read for ideas only, never copy. |

Copying an idea, a structure or a UX pattern is fine with any of them; copying code is what the
licence governs.

## Closest to Carodo (drive recording, journal, share)

Read in depth against Carodo's source (OutRun, Pilgrim, Driveline; 2026-11-12):
[`drive-recorders-study.md`](drive-recorders-study.md): what Carodo already does, the candidates
to learn from, and Pilgrim's written lessons.

| Repo | Licence | Stack | Learn from it | Caution |
|---|---|---|---|---|
| [dglancy/Driveline](https://github.com/dglancy/Driveline) | MIT | SwiftUI, SwiftData, App Intents, Live Activity | Closest product: background drive logging; start/stop via Shortcuts + App Intents on car Bluetooth (our `carodo://trip/start` idea); route list grouped by date with place names; PNG map snapshot export (share card); GPX export; Live Activity; Spotlight indexing; "no live map while recording" to save battery; merging two drives | Manual/Shortcuts start, no automatic detection; SwiftData |
| [timfraedrich/OutRun](https://github.com/timfraedrich/OutRun) | GPL-3.0 | UIKit/Swift, mature (★880) | Long-lived, privacy-first recorder: recording lifecycle, Live Activities, stats/charts, GPX + JSON backup, calendar of workouts, Health sync | **Ideas only**; name and branding also reserved |
| [BaidetskyiYurii/MilkyWay](https://github.com/BaidetskyiYurii/MilkyWay) | none | SwiftUI, MapKit (`Map`, `MapPolyline`), `@Observable` `CLLocationManager` wrapper, iOS 17, Swift 6 | Modern SwiftUI MapKit API usage for routes; an `@Observable` location service | **Ideas only**; heavy layering (Clean Architecture + coordinators + DI library) is more than we need |
| [Abu-maha/TrailMate](https://github.com/Abu-maha/TrailMate) | none | SwiftUI, MapKit, iOS 17 | Start/Stop/Resume recording, live polyline, summary screen, GPX export, background tracking, tests | **Ideas only**; requests Always permission up front, which we don't (progressive permissions) |

## Activity trackers with good UX

| Repo | Licence | Learn from it | Caution |
|---|---|---|---|
| [sawtoothdata/FreePace](https://github.com/sawtoothdata/FreePace) | MIT | Shipped app (App Store). Route coloured by pace/elevation (our speed-coloured replay), split toasts, post-run summary with charts, history filter/search, WeatherKit capture, offline map tiles, GPX/CSV import/export, MVVM + service layer | SwiftData |
| [walktalkmeditate/pilgrim-ios](https://github.com/walktalkmeditate/pilgrim-ios) | GPL-3.0 | Product voice and calm, premium UI; full-screen map with collapsing stats bar; "follow someone's shared walk" (a future replay-of-a-shared-drive idea); share links to a web page; offline maps; privacy positioning (no feed, no accounts) | **Ideas only** |
| [Decemberease/Go-Hiking](https://github.com/Decemberease/Go-Hiking) | MIT | Small university project; basic hiking tracker | Low value; skim only |

## Maps, globe and 3D (for the replay roadmap)

| Repo | Licence | Learn from it | Caution |
|---|---|---|---|
| [artembobkin/ImmersiveMap](https://github.com/artembobkin/ImmersiveMap) | MIT | Pure Swift 6 + Metal map engine for SwiftUI: globe that morphs into a flat map, Protomaps vector tiles (PMTiles over HTTP range requests, no tile server), labels, SwiftUI markers and avatars, 3D buildings and landmark models, no WebView | Young project; depends on hosted PMTiles archives; a whole renderer to own. Candidate for the 3D/video phase, not the MVP |
| [tunacosgun/GlobeDraft-iOS](https://github.com/tunacosgun/GlobeDraft-iOS) | none | Interactive 3D Earth in SwiftUI + SceneKit | **Ideas only**; tiny project |
| [hishd/SkyWizard](https://github.com/hishd/SkyWizard) | none | SwiftUI + SceneKit + SpriteKit visual effects | **Ideas only**; mostly HTML in the repo |

## Testing tools

| Repo | Licence | Use |
|---|---|---|
| [praveetgupta/vanish](https://github.com/praveetgupta/vanish) | MIT | Drives a **real iPhone's** GPS from a Mac (teleport, follow a real route, joystick) through Apple's developer location services, nothing installed on the phone. Useful to rehearse a drive at a desk before a real field test. It does not replace real drives for background, battery and detection tuning |

## Map technology options

| Option | Good for | Cost |
|---|---|---|
| **Apple MapKit** (default) | SwiftUI `Map`, `MapPolyline`, annotations, satellite/hybrid, realistic elevation and pitched `MapCamera` (3D look), Look Around, snapshots for share cards. No key, no dependency | Limited style control; no custom 3D models; camera animation for a flyover must be built ourselves |
| **Mapbox Maps SDK** | Deep style control, vector tiles, 3D terrain and buildings, custom layers, smooth camera animation | New dependency + access token + usage pricing; needs approval |
| **Custom Metal engine** (e.g. ImmersiveMap) | Full control: globe → flat transition, custom 3D, cinematic video frames | Highest effort and maintenance; tile hosting |

Recommendation: MVP 2D replay and the first 3D flyover on **MapKit**; evaluate Mapbox or a Metal
engine only when the 3D/video phase shows MapKit's limits. Record that choice as an ADR.
