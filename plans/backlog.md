# Feature backlog

Candidate features not yet in a slice, each with where it fits and what it must respect. The main
source is the CarStack study of 2026-11-03 (121 releases, 12 Jul – 1 Nov 2026, b2–b297, and its
database; [`../references/apps/carstack.md`](../references/apps/carstack.md)), read for patterns,
never copied. A feature leaves this list when it gets a slice in [`ios.md`](ios.md) and a spec in
`carodo-ios/docs/specs/`.

Status: `Done in code` · `Next` · `Later` · `Idea` · `Refused`. Phase numbers are the
[roadmap](../product/roadmap.md)'s.

## Already in code (2026-11-03)

| Feature | CarStack build | Where it landed |
|---|---|---|
| Speed bands on the detail page (CarStack: Speed Zones) | b266 | `carodo-ios/docs/specs/journeys.md` |
| Roads coloured by how often they were driven | b52, b57 | `carodo-ios/docs/specs/navigation.md` |
| Automatic journey names from places ("P. Tân Mỹ Loop") | b135 | journeys spec, Titles; `places` cache |
| Top speed and where it was reached, private | b9, b115 | ADR 0007 (revised 2026-11-03) |
| Gap healing: GPS gaps routed by Apple Maps | b206 | `carodo-ios/docs/tracking.md`, Gap healing |
| Drives stamped with the recording build | b34 | `trips.recorded_build`, `recorder_version` |
| Every raw fix kept, packed, backed up to iCloud | — (they upload points to their server) | ADR 0004, 0005 |
| Journey summary written on device | — | ADR 0012 |

## Journal and replay (phase 3)

| Feature | What it is | Carodo angle | Status |
|---|---|---|---|
| **Edit a drive** | Trim the start and end (with an automatic trim from motion), merge and unmerge drives split by a stop, rename (b14, b116, b126) | Never destructive: `trim_start_at`/`trim_end_at`, `merged_into_trip_id`, `custom_name` are reserved in the schema; raw samples untouched | Next |
| **Favourite drives** | Star a drive; a Favourites filter | Not in the first release (journeys spec, 2026-11-03): search, places and custom names find a drive. Back when replay or sharing needs "best drives"; needs `is_favorite` (P6) | Idea |
| **Route display options** | Colour the route by speed band or by elevation (b297) | The detail map and the share card share one option | Later |
| **Map pins** | Long-press to drop a pin with a note, open it in a navigation app (b153) | A new local table; private, never shared | Idea |
| **Photos of the drive** | Camera Roll photos taken during the drive shown on the detail page, usable as a card background (b43, b44) | PhotoKit with limited-library access, read by time window; nothing copied into Carodo | Later |
| **Weather along the way** | Weather at the start and along the drive (b2) | WeatherKit is a new capability (P6); the samples keep no coordinates beyond the trip's own track | Idea |

## Replay and video (phase 5)

| Feature | What it is | Carodo angle | Status |
|---|---|---|---|
| **3D replay** | Follow a small car across a 3D map, POIs shown, the car in the garage colour (b223, b232, b297) | Every fix is kept (ADR 0004), so the replay runs at 1 Hz; map technology needs an ADR first | Later |
| **Replay video export** | A 9:16 video of the whole drive or a clip (b278) | Rendered on the device; the privacy trim applies; same lengths as the replay setting (15, 30, 60, 90 s) for Reels, TikTok and Shorts, on the replay's timeline model | Later |
| **Custom vehicle marker** | The person picks the marker Replay and its video show (the wheel today), e.g. a top-down car in the vehicle's paint | The slot and the box are built (carodo-ios `ac5a361`): a new style is one case of `VehicleMarkerStyle` drawn in `VehicleMarker`. Open decisions before it is built: [vehicle-marker-slot.md](vehicle-marker-slot.md#later-the-customisation-feature--open-decisions) | Later |

## Share card (phase 4)

| Feature | What it is | Carodo angle | Status |
|---|---|---|---|
| **Card styles** | Speed gauges, top speed mark, fuel stops, standard / satellite / hybrid map, photo background with crop, optional footer (b9–b11, b35, b75, b141, b202) | The privacy trim hides start and end by default; top speed only if the person adds it | Later |
| **Share link analytics, short links and QR through linkto** | Views of each shared link counted by the owner's linkto.so (the main purpose: how a shared drive travels), plus a short URL and a QR code from the owner's linkto.so (custom domain, e.g. `go.carodo.app`), routed by device: iPhone without the app → App Store, else the page; aggregate view counts for the owner | Carodo's own URL stays the link of record (revocation, Universal Links, preview). Only the Carodo backend calls linkto (secret in the Worker, a service binding if on the same account), never the app. Revoke archives the linkto link and "Reset link" rotates its slug. No tracking parameters; views counted, never who. To verify: Universal Links on the short domain (redirects across domains open Safari, not the app). A new cloud service: owner approval (P6) and a privacy-policy line | Idea |
| **Hidden plates** | Licence plates in the card photo pixelated on the device (b274) | Vision text detection on the device; on by default (invariant P5) | Later |

## Garage, fuel and costs

| Feature | What it is | Carodo angle | Status |
|---|---|---|---|
| **Car from Bluetooth or CarPlay** | Match the car to its audio connection; a one-car garage picks itself (b33, b103, b205) | Also a confirming signal for Auto Mode; CarPlay never ends a drive (P4) | Next |
| **Car cards** | Swipe between cars, colour dot, model year, archive a sold car without losing its drives (b135, b294) | `vehicles` gains colour and archived-at | Later |
| **Fuel log** | Fill-ups with station suggestions (real stations only), unit price, currency with FX to a home currency, fuel stops as feed items (b3, b8, b49, b72, b86, b150, b164) | Local first; the Feed shows a fill-up only if published, never the station | Later |
| **Odometer estimate** | Last dashboard reading plus recorded GPS distance (b266) | Shown as an estimate beside the entered reading, never overwriting it (P2) | Later |
| **Maintenance, expenses, oil reminders** | Logs ahead of time, recurring expenses, oil interval reminders (CarStack "coming soon") | Local notifications only | Idea |
| **OBD-II adapter** | Read the car through a plug-in OBD-II adapter: speed, RPM, coolant temperature, fuel level, fault codes (DTC), the odometer where the car reports it | Only **Bluetooth LE or Wi-Fi** adapters: iOS cannot reach a classic-Bluetooth ELM327 without Apple's MFi programme; a Wi-Fi adapter takes over the phone's Wi-Fi while connected. Needs the Bluetooth and local-network permissions and, to read in the background, the `bluetooth-central` mode (P6). An OBD odometer is a third, separate source beside the entered reading and GPS distance (P2); many cars do not report it. The VIN identifies the car like a plate: never published or committed (P5). A connected adapter is also a strong "in the car" signal for Auto Mode. Proven only with a real adapter in a real car | Idea |

## Exploration and achievements

| Feature | What it is | Carodo angle | Status |
|---|---|---|---|
| **Roads driven for the first time** | Fog of war that opens as you drive, "% of the ward or city driven", new-road distance per drive (b15, b93, b201, b248) | New-road distance per drive planned in [new-roads.md](new-roads.md) (`trip_new_roads.new_road_m`, `visited_cells` dropped); on the device only, never in the Feed | Planned |
| **Achievements** | Tiered badges, visible on the profile; earned ones post a Feed item (b241, b248, b252) | Stamps in the Passport, not medals, with a 3D stamp in SceneKit (carodo-ios ADR 0013, decided 2026-11-03). Feed badges only about distance, a car's milestones, long drives and new roads (never named); never speed; time-of-day badges stay in the Passport (ADR 0007). Contract has `BadgeEarned`, `PUT /v1/me/badges/{badgeId}` and the catalogue endpoint; spec draft [`../drafts/achievements.md`](../drafts/achievements.md); slices Badges 1–3 in [`ios.md`](ios.md) | Next |
| **Recaps** | Weekly and monthly stories | Facts in Swift, words by Apple Intelligence (ADR 0012) | Next |

## Places and automation

Seen in Geofency (geofency.com): named zones, frequent places, webhooks on arrival and departure.
Carodo's angle is the car: *arriving by car*, not just arriving.

| Feature | What it is | Carodo angle | Status |
|---|---|---|---|
| **Frequent places** | Places where drives often start or end, found on the device and offered as Home, Work, … for the person to confirm | Derived from drive ends already stored (the `places` cache), so no extra GPS. Pays off across the app: titles ("Home → Work"), the share card's privacy trim hides a confirmed Home by default, commute totals. Never leaves the device except the person's own iCloud (ADR 0005). With roles and private regions: `carodo-ios/docs/specs/places.md`; slices in [`ios.md`](ios.md) | Places 1 done in code |
| **Zones** | Named circles the person draws (Home, Work, Gym); per zone: drives in and out, time between zones ("Home → Work, 23 min on average") | Two tiers: labelling a finished drive by its ends costs nothing (no monitoring); live arrival and departure events need a region monitor, and iOS allows 20 per app, one already used by the parking geofence (`docs/tracking.md`). Zone names and centres are location history: private, never in the Feed | Idea |
| **Home automation on arrival** | Open the garage, turn the lights on, when *arriving home by car*; close it when *leaving by car* | Not wired to the tracking path: an arrival event goes out after the fact and nothing waits on it (P1). Options to weigh in a draft: HomeKit directly (a new capability, P6; to verify on a device whether iOS lets an app operate a garage door, a "secure" accessory, from the background or only with the person's confirmation), App Intents the person uses in their own Shortcuts automations, or a webhook to the person's own server (e.g. Home Assistant) that sends the zone and the event, never coordinates. A garage door that opens by mistake is a security risk: confirmation on by default | Idea |
| **Drive purpose** | "School run", "To work", "Home from work", "Errand" as journal titles and totals, from saved places, stops and weekdays | Journal only, derived when read; never on the Feed, a card or a link (it tells a routine and a household; ADR 0007). Needs Places 2 (`carodo-ios/docs/specs/places.md`, Purpose) | Idea |
| **Monitored places** | Live arrival and departure for a few chosen places (Geofency's `Monitored`; its `Frequent` are Carodo's suggestions) | A `monitoring` column on `places` (`off`, `arrival`, `departure`, `both`) added with the first slice that needs it; iOS allows 20 regions per app and Auto Mode's parking geofence takes one, so the UI shows the slots left. iBeacon is out of scope | Idea |
| **Webhooks** | Send arrival, departure and drive-ended events to a URL the person sets (Geofency's main integration: entry and exit URLs per place, JSON, retry on error, motion state) | Opt-in, the person's own endpoint, retried through the outbox; the payload names the zone and the event, coordinates only if the person turns them on (P5). **HTTPS with a valid certificate only**: never an option to skip validation (the Geofency backup had it off) | Idea |
| **Time at places** | "Home at 18:42", "45 h at Work this week" (Geofency's visits: 37,653 in 8 years) | Derived from the gap between two drives at a place: no stored visits, no extra GPS | Idea |
| **Import a Geofency backup** | Seed Home, Work, School and private regions from the person's own `.geofency` file | Read on the device; only the person's `Monitored` places with a role become suggestions to confirm; nothing uploaded | Idea |
| **Last parked, per vehicle** | Where each car was last parked, with walking directions | The end of the vehicle's last drive, data already stored; directions handed to Apple Maps or Google Maps (Carodo cannot read their "Parked Car"). A line on the vehicle page, never a main function (carodo-ios ADR 0001, `docs/specs/garage.md`). Not a zone: zones are places the person names | Later |

## Feed and community (phase 4)

| Feature | What it is | Carodo angle | Status |
|---|---|---|---|
| **AI caption suggestion when publishing** | The on-device model suggests a one-line headline for a published drive; the driver keeps, edits or drops it | From public facts only, checked like the summary (ADR 0012); the driver's own words, reportable; never generated on the reader's device. Needs a `caption` field (owner approval) and moderation (`carodo-ios/docs/specs/feed.md`) | Idea |
| **Feed V1: Global feed and Feed identity on the mock** | Paged Global feed (anonymous "Someone" by default, sentence headline, shape as a `Path`), the Feed identity screen (claim a username), Option D navigation; Live, Following, leaderboard and Profiles behind `FeedFeatures.deferredUI` | carodo-ios `main` (built 2026-11-10 on `feat/feed-v1`, merged), plan [feed-v1.md](feed-v1.md); publishing ("Share my drives"), the anonymous account and the schema columns follow (M0 decisions in §9 of the plan) | Built (mock) |
| **Part of day on Feed items** | "Morning drive", "Night drive" on each item, true for the driver's own clock | The device computes it in the drive's zone (`trips.time_zone`) and sends a `partOfDay` enum, never the zone itself (a zone tells the region; ADR 0007). In the contract since 0.12 (approved 2026-11-03); on iOS since Feed V1 (the headline sentence); backend still to do | Built (iOS) |
| **Feed summary** | What happened in the last 72 h (b248) | Exists on sample data | Done in code (sample) |
| **Leaderboard periods** | This and last week, this and last month; drives and distance (b77, b104) | Week · Month · Year, this one and the last; ranked by distance or (month, year) active days; drives and driving time shown, never ranked; never by speed (ADR 0007) | Done in code (sample) |
| **Public profiles** | Profile cards with stats, avatar, achievements (b25, b26, b182) | `GET /v1/users/{userId}` (contract approved 2026-11-03); `carodo-ios/docs/specs/profile.md`; badges join it with Badges 3 | Done in code (sample) |
| Route shapes on Feed items | b32 | — | **Changed 2026-11-03**: a route on a map stays refused; a soft abstract shape (rotated, unscaled, trimmed, no start or end) is in (carodo-ios ADR 0007, contract 0.15 `DriveShape`) |

## App and operations

| Feature | What it is | Carodo angle | Status |
|---|---|---|---|
| **In-app changelog** | "What's new" in the app instead of TestFlight's sheet (b241) | Ships in the app bundle; no backend needed | Later |
| **Feedback chat** | Support chat from the app (b198) | Mail compose or a form first | Idea |
| **Interactive Live Activity** | Pause / resume and log fuel from the Lock Screen and the island (b10, b204) | Live Activity is on the Unscheduled list | Later |
| **One-tap automation** | Install the "start a drive when the car connects" Shortcut in one tap (iOS 27, b264) | Pairs with `carodo://trip/start` | Next |
| **Map lookups held like the sensors** | The rules of the location runtime for `CLGeocoder`, `MKLocalSearch`, `MKDirections` and `MKMapSnapshotter` (six files in three folders; `Core/MapLookup` holds eight of them since 2026-11-16): one folder creates, the composition root owns, a row in `ArchitectureTests` ([`location-runtime.md`](location-runtime.md), section 10) | Goes with TD-43 (geocoding that may start in the background) | Later |
| **Audit: `UserDefaults.standard` and power reads in Views** | A count before a decision: `UserDefaults.standard` read directly in 21 View files across 8 features; battery, heat and Low Power read in `BatteryMonitor`, `DriveFlow` and one Journeys view ([`location-runtime.md`](location-runtime.md), section 10) | An audit first; gathering only if it finds something | Idea |
| **Temporary full accuracy when location is Approximate** (I1) | Ask iOS for full accuracy for one drive when the person gave Approximate (the location audit of 2026-11-16, I1) | A product and permission-copy decision (P6); its own work | Idea |
| **Absolute altitude from the barometer** (I2) | `CMAltimeter`'s absolute altitude beside the relative pressure (the location audit, I2) | A schema decision (P6); its own work | Idea |
| **`CarodoTests/` in folders** | The test files (about 250, flat) in folders that mirror `Carodo/`: pure moves, one `refactor(tests)` commit, with no other session open | No behaviour; only when the tree is quiet | Later |
| **New iPhone restore** | Everything comes back on a new phone (b259) | iCloud sync (ADR 0005) | Later (phase 4) |
