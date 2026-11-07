# Achievements

Status: Ready (decisions 2026-11-03, revised 2026-11-05). Phase: Passport V2 slice 3 (ledger,
stamps), slice 4 (Feed). Decisions: carodo-ios ADR 0013 (the rules), ADR 0014 (archived vehicles
keep their badges), ADR 0007 (what may reach the Feed). Storage, sync and publishing:
[`badge-ledger.md`](badge-ledger.md). Passport presentation: [`passport-v2.md`](passport-v2.md).

Badges in tiers, earned from the person's own history on the device, recognising distance already
driven. No points, no levels, no score. A badge stays private unless the person shares it.

## Purpose

Mark the moments of a driving life (the first 1,000 km, a car's 10,000th kilometre) as stamps in
the Driving Passport, without ever rewarding driving more often, longer, later or faster.

## Today

Nothing beyond a round-number distance milestone drawn on sample Feed data (`FeedMilestone`).
Contract 0.24 has `BadgePublication`, `FeedBadge` and `PUT`/`DELETE
/v1/me/badges/{badgeId}/{publicRef}`; the backend baseline has `badge_definitions` and `badges`
(no routes yet).

## Decided

- **Evaluated on the device,** always: badges read private history, which the server never has.
  One pure `AchievementEngine` gives personal records (Passport highlights, never badges) and
  milestone progress (these badges).
- **Only cumulative distance may be a badge** (ADR 0013): Road Miles and Faithful Car. Never speed,
  time of day, frequency (drive counts, driving days), streaks or rankings; night drives, driving
  days and streaks are neutral statistics with no target or progress.
- **No points, no levels,** and no infrastructure kept for them.
- **Stable ids:** badge ids and tier ids are never renamed or reused; a tier's threshold never
  changes under its id. Each unlock keeps a snapshot of its threshold.
- **An unlock is an immutable fact:** recorded once with the drive that crossed it and that
  drive's end as `earned_at`; it never goes down when drives are deleted (Recently Deleted, then
  purged). Archived vehicles keep theirs (ADR 0014).
- **The catalogue ships in the app;** slice 4 adds `GET /v1/badges/catalogue` (ETag, newer wins).
  The app accepts only metrics on its whitelist, so a served catalogue can tune thresholds and
  names but never add a kind ADR 0013 excludes.
- **Stamps in the Passport** (in the language of the Passport marks, `PassportMarks`,
  `design/passport-stamp/`): a badge is a stamp inked in the person's Driving Passport, not a medal.
  - **Shape:** the round stamp (A) for running totals (Road Miles, Faithful Car). The month
    postmark (D) stays the Passport's month strip, not a badge.
  - **Tiers** by the impression, in Copper ink only: more rings and the tier's distance in the
    band, a denser ink, a copper-foil finish at the top tiers. Never gold and silver.
  - **In the Passport:** earned stamps as inked impressions; the next one as a faint pencil
    outline with the real progress to it.
  - **In 3D:** a tapped stamp shows the stamp itself, a rubber die on a handle, on a transparent
    SceneKit stage (`scenekit-product-stages` skill); turned with a finger, pressed down to ink a
    fresh impression, with a haptic thump.
  - **Flat everywhere else:** the impression on Feed items, the Profile and share cards. Reduce
    Motion: no spin and no press.
- **The moment:** after the drive that earned it, once, never while a drive is recording, the stamp
  comes down on the page with a thump; a dot on the Passport until the person has seen it there,
  on any of their devices. Unlocks found by a backfill (first run over an existing journal, a
  restore) are inked without a moment.
- **Sharing is a choice:** earning never posts. The person shares a badge to the Feed (slice 4)
  and can hide it at any time; hiding hides its Feed item, sharing again restores the same item.

## Future candidates (not in the catalogue)

Long Hauler, Explorer, Cartographer, Trailblazer, Road Warrior, Full Circle. Each needs its own
product and safety review (fatigue, detours, routine exposure) and an ADR 0013 amendment before it
may be defined. Removed for good: Night Owl, Early Bird, Journal Keeper.

## Metrics the app accepts

| Metric | Measures | Scope | Visibility |
|---|---|---|---|
| `total_distance_m` | GPS distance of every counted drive | lifetime | Feed, by choice |
| `vehicle_distance_m` | GPS distance with one vehicle, archived ones included | vehicle | Feed, by choice |

A counted drive is completed, not in Recently Deleted, and driven by the person (not a passenger
drive). GPS distance is never the odometer (P2).

## The catalogue

| Badge | Id | Metric | Tiers (tier id: threshold) |
|---|---|---|---|
| Road Miles / Quãng đường | `road_miles` | `total_distance_m` | `km_100` 100 · `km_500` 500 · `km_1000` 1,000 · `km_5000` 5,000 · `km_10000` 10,000 · `km_25000` 25,000 · `km_50000` 50,000 km |
| Faithful Car / Bạn đồng hành | `faithful_car` | `vehicle_distance_m` | `km_1000` 1,000 · `km_5000` 5,000 · `km_10000` 10,000 · `km_50000` 50,000 km with one car |

## Data and privacy

- **Device:** `badge_unlocks` (immutable facts) and `badge_states` (seen, publication), backed up
  to iCloud with per-field merge rules (`badge-ledger.md`, carodo-ios `sync.md`).
- **Server:** `badge_definitions` (the catalogue) and `badges` (what the person chose to show,
  named by a random reference, never a vehicle or trip id). The server cannot verify a badge; App
  Attest proves the app sent it, and badges never count toward the leaderboard.
- Publishing needs "Share my drives"; nothing earned before is posted without the person's action.

## Acceptance

- Each metric, on synthetic journals, reaches each tier exactly at its threshold and not below.
- With no network, the bundled catalogue awards badges; a definition with an unknown metric or
  scope, or an excluded kind, is ignored.
- Deleting the drives that earned a tier leaves the unlock; its Journey Detail stamp goes with the
  drive.
- A journal restored or imported later gets each unlock's real `earned_at` (the crossing drive's
  end), not the import time.
- The moment shows once per new tier, after the drive, never during recording; the Passport dot
  clears when the badge is seen on any device.
- No point, level, progress or target for anything but Road Miles and Faithful Car.
- With Reduce Motion the stamp neither spins nor presses; VoiceOver reads the badge, its tier and
  what earned it.
