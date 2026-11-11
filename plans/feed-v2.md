# Feed V2 — audit and diff against `feed_spec_v2`

Status: **audit, superseded as a plan by `feed-v1-design.md` (2026-11-11)**; the audit and diff below stay as the record of today and of v2. D1: no anonymous sharing without a username; D4: more points, any angle; D6: backend gets the contract only.
Source: the owner's `feed_spec_v2.md` (workspace root, Vietnamese, 2026-11-11), which replaces
every earlier Feed spec. It lands in English in `carodo-ios/docs/specs/feed.md` (with ADR 0007 and
0008 amended) once the decisions below are taken.

## What exists today

- **iOS** (`main`, Feed V1 M1 merged: `ae871a5`, `4873dc1`, polish `29c4ad3`, `e4eea4e`): a read-only
  Global feed on `SampleCommunityRepository` (no backend call yet), Feed identity (claim a
  username), per-hour items, 7 parts of day, stamp avatar, `DriveShapeThumbnail` (`Path`), stats
  pill. Deferred behind `FeedFeatures.deferredUI`: Live, Discover · Following, leaderboard
  (`LeaderboardView`, 483 lines), Profiles. Not built: publishing, hide, report/block, badges.
- **Contract** `carodo-ios/docs/api/carodo-api.yaml` 0.26.0-draft: `PUT /v1/drives/{tripId}`,
  `/v1/me/profile` (`feedOptIn`), `/v1/feed`, `/v1/leaderboard`, `/v1/users/*`, `/v1/follows`,
  `/v1/live`, `/v1/reports`, `/v1/blocks/{userId}`, `/v1/me/badges`; errors are RFC 9457 problems.
- **Backend** `carodo-app`: scaffolded, never deployed, no users; 59 uncommitted paths owned by
  another session. Routes for drives, feed, live, accounts, auth; D1 baseline with `drives`,
  `leaderboard_entries`, `follows`, `live_status`, `reports`, `blocks`, `drive_stats_hourly`.
- **No data anywhere:** no deployed server, no published drive, no user. The v2 migration items
  (FEED-MIG-01..05, section 9) have nothing to migrate: the backend baseline and the contract are
  edited in place, as the pre-release rule says.

## Diff (v2 requirement · today · v2 asks · kind · handling)

| ID | Today | v2 | Kind | Handling |
|---|---|---|---|---|
| PRIV-01/02, UX-01..05 | `feedOptIn` exists, but appearing needs a claimed username (ADR 0008) | Opt-in, `sharingEnabled=false`; **Share anonymously** without a username | breaking (ADR 0008) | Account created silently on opt-in (App Attest + Keychain secret, as today), username optional. Amend ADR 0008. **D1** |
| PRIV-03/12/13 | "Someone" / "Ai đó", no link between anonymous items | Same, plus `You` for the author, grouping by internal author | missing | Build `isAuthor`, "You" |
| §5.9, MOD-02 | Block by `userId`; anonymous items carry nothing stable (ADR 0007 acceptance) | `authorPublicId`, stable and opaque, on every group, anonymous too | breaking (ADR 0007) | **D2** |
| PRIV-04 | make/model always shown | `vehicleDisplay`: makeModel · typeOnly · hidden, applied at read | missing | Contract + server read-time; iOS settings |
| PRIV-05/07, RET-03..05 | Off switch removes items | Off asks: hide or delete; changes apply at read | missing | Contract `deleteExistingPosts` |
| PRIV-06 | `publishToFeed` per drive planned | `Hide from feed` per drive, immediate | missing | Local column for the trip's feed state (schema, P6) |
| PRIV-10, TAG-02 | 7 parts of day, sent as `partOfDay` | 4 buckets from `localStartHour` (morning 5–11, afternoon 12–16, evening 17–20, night 21–4) | breaking (copy) | Follow v2; owner-approved 7-part copy retired |
| PRIV-11, §5.3 | Device sends `partOfDay`, never an hour | Sends `localStartHour` and `clientStartedAt` (UTC) | changed | Allowed by P9 (server keeps exact times for its own logic, never returns them) |
| VEH-01..05 | Spec plans two-wheelers on the Feed | Cars only; client never publishes others; banner `Feed currently supports cars only` | breaking | `VehicleClass.car` only; drop the Vehicle classes section |
| FEED-01..03 | One item per person per hour (≤ 20 drives) | One group per person per **author's local day**; short routine drives collapsed; priority order | breaking | Contract `drive_group`; iOS group row + expand |
| FEED-04, RET-01 | 72 h stats pill | Items only within 72 h | changed | Server |
| FEED-05 | Opaque cursor | Opaque cursor, limit 20 (max 50), counts groups | ok | Keep |
| FEED-06 | Last period's top drivers above page 1 | Challenge card + **Top cars this week** (7 d, makeModel only, k ≥ 10) | breaking | New endpoints; **D3** for the leaderboard |
| FEED-07, UX-08/09 | Discover · Following (deferred) | `All` · `Milestones`; sections Today · Yesterday · Earlier; no Friends | breaking | Replace header control |
| STAT-01..06 | Stats on first page; Nearby needs 20 drivers | Separate `/v1/feed/stats`, k ≥ 10 → numbers null; label `Worldwide`; `region=global` only | changed | Contract; drop region/Nearby/Area |
| §1.3 | Area ("Khánh Hòa, VN"), `regionCode`, Nearby/Country | Out of scope (Phase 2) | extra | Remove from spec and contract |
| §1.3 | Live, Following, Profiles, leaderboard (deferred UI) | Not in Phase 1 (leaderboard not mentioned) | extra | **D3** |
| SHAPE-01..08 | ≤ ~24 points, ints 0–1000, random angle per drive, privacy zone 300 m + private regions, none under 2 km | ≤ 80 points in [0,1], k·90° turn + mirror per `driveId`, trim 300 m + Home/Work rule, none under 1 km | changed (weaker) | **D4** |
| TAG `milestone` | Badges posted only when shared from the Passport (`/v1/me/badges`) | `milestone` tag on the drive post (first drive, 1k…100k km of private car distance) | breaking | Drop badge items; milestone on the post |
| TAG `rain` | — | WeatherKit on the device, `weather=rain` | new service | **D5** decided: WeatherKit, start point rounded |
| REACT-01..02 | ADR 0007: no likes | 5 fixed reactions, toggle | breaking (ADR 0007) | Accept per v2; amend ADR 0007 |
| MOD-01..03 | `/v1/reports`, `/v1/blocks/{userId}` | `/v1/feed/posts/{id}/report`, block, rate limits | changed | Contract |
| UX-06 | `[a-z0-9_.]{3,20}` | + no leading/trailing `.`/`_`, no `..`/`__`, reserved words, 3 changes / 30 days | changed | Contract + server + iOS validation |
| §6 errors | RFC 9457 problem+json | `{ "error": { code, message, details } }` | changed | Keep problem+json, carry v2 codes in `code` (one error shape across the API) |
| §6 paths | `PUT /v1/drives/{tripId}`, `/v1/me/profile` | `POST /v1/feed/posts` (upsert by `driveId`), `/v1/me/sharing-settings` | changed | Take v2 paths; keep the field name `tripId` (data model), clean cut (no client shipped) |
| UX-04 | — | `Share to Feed?` row on the end-of-drive summary, car drives only | missing | Drive summary screen |
| UX-07 | loading/empty/failed states | + opt-in card, snooze 7 days, chip, < 10 drivers, cars-only | missing | iOS |
| §12 metrics | no product analytics on iOS | event list | missing | Interface only; no event carries a time or position (P5, P9) |

## Decisions for the owner

Decided (owner, 2026-11-11):

- **D2 → block through the post.** No author id in any response; `POST /v1/feed/posts/{id}/block-author`.
- **D3 → delete.** Leaderboard, Live, Following, Profiles: code, catalog strings, spec sections and
  contract endpoints removed; recorded as Phase 2.
- **D5 → build `rain` with WeatherKit** (P6 approved). One request per car drive, at its start
  rounded to about 0.1° (~11 km), never the route; only `rain` / `clear` / `unknown` kept. Needs the
  WeatherKit capability, which, like iCloud, a Personal Team cannot sign: without it the app sends
  `weather: unknown` and never tags `rain`.

Open:

- **D1** Anonymous sharing creates an account without a username (amend ADR 0008). Implied by v2.
- **D4** Shape: v2's 80 points and four turns + mirror make a route easier to recognise and to lay
  on a grid street map than today's ~24 points at any angle. Recommended: v2's trims and
  determinism, today's density (≤ 32 points) and any angle, none under 2 km.
- **D6** Who does the backend: `carodo-app` has 59 uncommitted paths from another session.

## Proposed order once decided

1. Docs: `docs/specs/feed.md` rewritten in English from v2; ADR 0007 and 0008 amended.
2. Contract 0.27.0-draft (`carodo-api.yaml` + `sync.md`), owner approval (P6).
3. Backend (if D6 says so): settings, publish/validate, feed groups + cursor, stats k-anon,
   challenge, top cars, reactions, report, block, 72 h / 30 d jobs; tests FEED-TEST-06..20.
4. iOS slice A: `RouteShapeAnonymizer` (pure, FEED-TEST-01..05) and the drive summary builder
   (car only, tags, milestone), no UI.
5. iOS slice B: sharing settings (local + repository), the trip's feed state (schema, P6),
   publishing through the outbox, 72 h backfill on opt-in, hide per drive.
6. iOS slice C: Feed screen (chip, opt-in card with live preview and in-card username, groups,
   filters, sections, interleaved cards, every state of UX-07), Settings, end-of-drive row.
