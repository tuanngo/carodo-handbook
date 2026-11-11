# Roadmap

Product direction: ADR 0001 (drive journal → replay → share). Two tracks run in parallel against
the contract in `carodo-ios/docs/api/carodo-api.yaml` and the sync model in
`carodo-ios/docs/sync.md` (ADR 0003). The iOS app works fully offline at every step; sync
is added behind the repositories, never in front of them.

| Phase | iOS (`carodo-ios`) | Backend / web (`carodo-app`) |
|---|---|---|
| 0. Contract | Review OpenAPI + sync model | Review OpenAPI + sync model |
| 1. UI first | Full SwiftUI shell — **Map, Journeys, Feed** + floating Start Drive button (ADR 0007, `carodo-ios/docs/specs/navigation.md`, slice A) — on sample data via repositories; animation, responsive layout (all iPhone sizes, Dynamic Type, Light/Dark); garage; guest-first (no login gate) | Workers + D1 skeleton (carodo-ios ADR 0010), App Attest, username accounts, sessions, Apple link, account delete |
| 2. GPS engine | Slices B–D of `floating-navigation.md`: `DriveSessionManager`, recording panels, `CoreLocationSource`, `RouteRecorder`, background GPS, GRDB persistence (incl. iCloud sync columns), trip recovery, route recording — working on a real iPhone; manual Start/Stop first, then Auto Mode with short-trip discard | `/v1/published-drives`, `/v1/shares` upload, contract tests |
| 3. Journal + 2D replay | Trip list, trip detail, 2D replay (speed-coloured route, timeline scrub, overlays); iCloud backup and sync (`CKSyncEngine`, ADR 0005) | Hardening: rate limits, observability, deploy |
| 4. Share + Feed live | Share card (image, offline), "Secure your profile" (Apple link), `BackendService` and outbox, create/revoke share link, the worldwide Feed (V1) on real data with opt-in publishing, "Join the Feed" username claim, App Attest guest token (ADR 0008, 0009) | `/v1/shares`, public web preview page with privacy trim; profiles with unique usernames, guest tokens (App Attest), feed, leaderboard, live status, report/block (ADR 0007, 0008) |
| 5. Next | 3D flyover replay, then video export | Whatever 3D/video sharing needs (e.g. hosted video) |

Phase 2 is done when the exit criteria in `carodo-ios/docs/operations/device-testing.md` pass on a physical
iPhone. What the first release contains: [`carodo-ios/docs/specs/product.md`](../../carodo-ios/docs/specs/product.md); feature specs: [`carodo-ios/docs/specs/`](../../carodo-ios/docs/specs/README.md); drafts for features with no code: [`../drafts/`](../drafts/README.md).
The iOS breakdown into slices and its status: [`../plans/ios.md`](../plans/ios.md).

Open-source repos and map technology options to learn from: `carodo-handbook/references/repos/ios.md`.

Later: fuel log and fuel totals. Not planned: a parking feature (a car's last parked spot is Later), comments, route or location in the feed,
ranking by speed.

**Feed, later** (Feed V1 design, 2026-11-11, [`../plans/feed-v1-design.md`](../plans/feed-v1-design.md)):
V1 is one worldwide Feed of car drives with reactions. Removed from V1 and kept here as ideas for a
later phase, each needing its own decision and contract: Live status, the leaderboard, Following,
Profiles, milestones and badges on the Feed (private milestone vs public badge to be analysed),
the challenge card and Top cars, area / region / Nearby, two-wheelers, tabs and filters (All ·
Milestones), sections (Today · Yesterday). Their last contract (Live, leaderboard, follows,
profiles, badge publishing) is `carodo-api.yaml` 0.26.0-draft in carodo-ios history (the parent of
`f1a178c`): a later phase starts from it, re-decided, and adds its endpoints back in its own version. Report and block through a row are not later: they gate
the first App Store release (TD-8).

Rule for both tracks: a contract change is a change to the OpenAPI file and `sync.md` first.
