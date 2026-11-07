# Backend plan

The one place for the backend plan and its status. The cross-track phases are in
[`../product/roadmap.md`](../product/roadmap.md); what the code does and why is in
[`carodo-app/AGENTS.md`](../../carodo-app/AGENTS.md) and `carodo-app/docs/` (architecture, cost
rules, storage, metrics, ADRs 0001–0008). Update the status here in the same change that moves a
slice forward. A new session starts by reading this page, then `carodo-app/AGENTS.md`.

Status: `Done` (local, tested) · `Next` · `Later`. Nothing is deployed or committed yet: the owner
rebuilds the first commit once the skeleton deploys to staging.

## Done

| Slice | Content |
|---|---|
| Skeleton | Two Workers (api, web via WebRpc), three environments (ADR 0004), D1 baseline, Biome layers, Vitest `unit` (Node) and `workers` (workerd), full-scan guard over every query |
| App Attest | Challenge, attestation (Apple's steps, pinned root), `carodo-debug` for the Simulator, assertions, shared vectors with iOS |
| Identity | Guest token, claim username, session from the account secret, refresh rotation with reuse detection, sign out everywhere, delete account (username held 90 days) |
| Jobs | Hourly cron, leases, `account.erase` (R2 then rows), pruning (challenges, holds, sessions, web sessions, drive tombstones) |
| Storage, metrics | R2 layout by id (`BLOBS`), Analytics Engine `carodo_events` / `carodo_metrics`, request metrics in place of invocation logs |
| Publish drive | `PUT` / `DELETE /v1/drives/{tripId}`: revisions, tombstones, time checks, plausibility verdict (`ranked`) without storing top speed |
| Feed read | `GET /v1/feed` Discover and Following: items are one person's drives in one hour, keyset pages on (`drove_at`, `account_id`) with sealed cursors, deleted / opted-out / hidden drives and blocks (both ways) left out, ETag and 304, Discover cached by TTL-bucketed keys with stale-while-revalidate and one computation per key (ADR 0008); rows read measured at 500 accounts and 10,000 drives |
| Live status | `PUT` / `DELETE /v1/live?tripId=`: a `live_status` row renewed for 15 minutes, a tombstone at the end so a late renewal is refused, no index on `expires_at` so a renewal writes one row, `liveOptIn` checked, listed above the Feed's first page (everyone, or the followed), pruned hourly, cleared on account deletion (ADR 0008; carodo-ios ADR 0010 changed) |

## Next, in order

1. **Profile** `GET`/`PUT /v1/me/profile`, `GET /v1/usernames/{username}`, `GET /v1/users/{id}`: a
   renamed username is held 90 days like a deleted one; turning the Feed off takes the person's
   drives off the Feed and boards (the Feed already filters on `feed_opt_in`); turning Live off
   deletes the `live_status` row. `GET /v1/users/{id}/feed` reuses the Feed's items and cursors.
2. **Leaderboard rollup and read:** a job following `drives.updated_at`, recomputing every period a
   late or changed drive falls in until it is sealed (a week 7 days, a month 14; ADR 0007); the
   rules across drives (2,000 km in a day, overlapping drives); `GET /v1/leaderboard`; the first
   Feed page's `stats` (from `drive_stats_hourly`) and `topDrivers` (each closed board's first row),
   cached with that page (contract 0.22.0-draft: one request per screen). Distinct drivers over
   72 h cannot be summed from hourly counts: the rollup writes the window's own count.
3. **Follows, blocks, reports.** (The Feed already reads `follows` and `blocks`.)
4. **Badges on the Feed:** `PUT /v1/me/badges/{badgeId}` and badge items merged into the pages.
5. **Shares** (`POST /v1/shares`, preview, public page on the web Worker; docs/storage.md).
6. **Encrypted backups** and the web pairing (ADR 0011).
7. **Staging deploy:** tooling ready (carodo-app ADR 0004, `docs/operations/deploy.md`: same
   names on both accounts, account from `.env.staging` + a Wrangler profile, `task deploy:staging`,
   debug proof accepted on staging). Owner: profile `carodo-staging`, `.env.staging`, D1 `carodo`
   with `--location apac`, R2 `carodo`, `SECRET_KEY`, the Team ID in staging's `APP_ID`. The WAF
   rule on `/v1/auth/*` waits for production's zone.

## Open decisions

- **Feed item window** (decided in the code, the owner may widen it): drives that started in the
  same hour make one item, since `drove_at` is all the server keeps and it keeps pages exact. A
  wider window (3 hours) needs a stored slot column and gives up exact "newest first" inside it.
- **Live, real time (level 3, later):** when watching a friend drive becomes a feature, or the
  metrics show live writes matter, move live status to one Durable Object "live room": drivers keep
  sending `PUT`/`DELETE /v1/live` (the contract does not change for them). The start and the end
  are written to the object's SQLite (two rows a drive), renewals stay in memory: linkto's
  analytics live store lost a memory buffer on every eviction and now writes on arrival. After an
  eviction the rows come back unconfirmed and leave if no renewal arrives within one renewal
  interval; 24 hours after the start a row leaves regardless (a lost end never shows "driving now"
  for longer). Liveness stays "renewed recently", as linkto's "online" is "a pageview in the last
  5 minutes" (its 50-hour retention is the dashboard's today and yesterday, not presence). Viewers
  with the Feed open get changes over a hibernating WebSocket (outgoing messages are free); pushes
  are coalesced (at most one every 2 s) and an unchanged list is not resent. **No alarm:** each
  entry carries its `expiresAt` and the app hides it and ticks `elapsedS` itself; expired rows are
  dropped when a request arrives anyway. Nothing wakes the object but a driver or a viewer, so no
  loop can bill (the account is shared with other apps). Since the object
  knows whether anyone is watching, each PUT's answer can tell the app how soon to renew: rarely
  when nobody watches, often when someone does (needs a `renewAfterS` in the PUT answer). The start
  and the end are always sent: a viewer cannot reach a driver's phone except by a push, which is
  neither reliable nor cheap for this. Cost per published price (2026-10), at 1M live drives a day:
  about $100 a month (requests about $45, the start and end rows about $60) against about $250 on D1. Needs the owner's approval: a binding, a Cloudflare
  product, ADR 0008 and carodo-ios ADR 0010, a WebSocket endpoint in the contract.
- **Nearby and country (contract 0.21.0-draft, decided 2026-11-04):** one `regionCode` per account
  (ISO 3166-2, computed on the device, kept only with feedOptIn), stamped on each published drive;
  readers send `region`; answers carry the served `scope` (region → country → Global under 20
  active drivers). Done: schema, claim, publish stamping, query parsing (every scope reads Global).
  Owed: `PUT /v1/me/profile` (with regionCode, null when the Feed goes off), the region and country
  pages (cache key by scope and code; a country index on drives when its Feed is built), the
  active-driver counts per region in the rollup, scope on leaderboard entries.
- **Contract gaps found while building:** avatar upload has no endpoint (`avatarUrl` is refused);
  DeviceCheck and Sign in with Apple wait for the paid Apple Developer Program.

## iOS side owed (for the iOS track)

- Contract 0.22.0-draft: community numbers and last period's top drivers come with the first Discover
  page (`stats`, `topDrivers`); `/v1/community/stats` is gone (`Repositories.stats(scope:)` reads the
  page instead); `ago: "now"` shows "Just now" / "Vừa xong".
- `regionCode` on the device: the ISO 3166-2 code of the province or state where most of the last
  30 days' drives started (reverse geocoding on the device), refreshed about weekly, sent with the
  profile only while "Share my drives" is on (null when off); `region` on Feed, leaderboard and
  community stats reads; the "Share my drives" sheet line about appearing to the same province and
  country; the thin-scope line from the answer's `scope`. Core Location gives a province's name,
  not its code: the app maps it (a bundled table per supported country).
- `trips.revision` (a carodo-ios schema change), sent in `DriveInput` and on unpublish.
- The identity integration: [`ios-backend-integration.md`](ios-backend-integration.md).
- Live: `PUT /v1/live` at start and about every 5 minutes while recording, sent directly (never
  through the outbox), `DELETE /v1/live?tripId=<trip>` at the end (without `tripId` only when
  the person turns live status off), both with an assertion; the body now sends `vehicle`
  (a `VehicleLabel`) instead of `vehicleId` (contract 0.20.0); expires 15 minutes after the last PUT.
- Live list: count `elapsedS` up on the device every second from the value the Feed sent (never
  extrapolate the distance).
- Feed: keep the ETag and send `If-None-Match`; treat `cursor` as opaque, and on a 400 for it load
  the first page again (a server key rotation voids every cursor); `live` comes on the first page
  only.
