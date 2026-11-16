# iOS ↔ backend: BackendService (Feed V1)

Status: **built 2026-11-15 on the Simulator, uncommitted (waiting for the owner).** S1–S6 done;
D1–D5 approved as recommended. `task test` 2324 tests (27 skipped), `task lint`, `task warnings`
clean; `BackendLiveTests` (opt-in) runs the whole round (claim, sharing, publish through the outbox,
the Feed with "You" and a reaction, rename, unpublish, delete) against a fresh local backend. Left
open: PV-27 (Personal Team iPhone, then App Attest on the paid team). The 2026-11-03 "identity
first" brief this replaces had sign out everywhere and Sign in with Apple, both gone in contract 0.28.0.

**As built, beyond the plan:** `KeychainItem` is the one Keychain helper (`InstallationIdentity`
uses it); `FeedAnswers` is the one decoding of Feed answers for the mock and the backend;
`NSAllowsLocalNetworking` sits in the one Info.plist (Release never names an http URL, so only Debug
reaches a local server); a guest renewal refused means the key is unknown and a new one is attested;
a session refused twice (the second with a new key) means the account is gone. Bug found on the way:
`SoftwareAttestKey` refused to sign before its key existed (`AppAttestFormatsTests`). The local
backend's own D1 (the owner's `task dev`) predates the backend's last schema change and needs
`task app:db:reset` (its `drives.item_id` is still NOT NULL: an unpublish there answers 500).

**Review before commit (2026-11-15):** Start/Stop sharing now change the screen only once the
server takes them (a Stop that failed offline used to read as stopped while the server still
shared: P5); deleting an account whose secret is already refused counts as deleted; a key App
Attest refuses is replaced; key creation is single-flight; the ETag store keeps 16 reads; auth
failures are logged by step and status only. Backend: a retried publish or unpublish writes no row
(it wrote 2), dead `wholeMinutesS` and `shareKeys` removed, one UUID check (`isUuid`). TD-37 left
open (a failed choice change is not reverted on screen).

**Tomorrow, with the paid Apple Developer Program:** add `com.apple.developer.devicecheck.appattest-environment`
to `Carodo/Resources/Carodo.entitlements` (P6), set `CARODO_APPATTEST_FLAG = CARODO_APPATTEST`
(`Configs/Shared.xcconfig`), put the Team ID in staging's and production's `APP_ID` (carodo-app
`apps/api/wrangler.jsonc`), then attest on an iPhone against staging.

**Goal:** the Feed tab, Join the Feed, Profile, Start/Stop sharing, publishing and reactions talk to
the real `carodo-api` (`task app:dev`, later staging) instead of `LocalFeedServer`, with no screen
changing: the real transport goes in behind the seams the mock already fills.

## 1. Audit — what the code does today

Files read (carodo-ios): `Core/Networking/{APIClient,Endpoints,NetworkError}.swift` (empty, 0
lines), `Core/Networking/FeedAPI.swift` (wire types, header says contract 0.27.0),
`Core/Networking/LocalFeedServer.swift`, `Core/Outbox/{OutboxOperation,OutboxRelay,LocalFeedTransport}.swift`,
`Core/Repositories/{CommunityRepository,LocalCommunityRepository}.swift`, `Core/Domain/Community.swift`
(`CommunityError`), `Core/Identity/InstallationIdentity.swift`, `Configuration/Configuration.swift`,
`App/DependencyContainer.swift` (grep only: it has the owner's uncommitted changes), `docs/sync.md`.

| Seam | Today | What BackendService puts behind it |
|---|---|---|
| `CommunityRepository` (feed, react, sharing, identity, usernameAvailability, claimUsername, changeUsername, deleteAccount) | `LocalCommunityRepository` decodes the mock's contract JSON | `BackendCommunityRepository`: the same decoding (`FeedAPI.swift` types) of real answers |
| `FeedSharingService` (sharing, setSharing) | `LocalFeedSharing` | `BackendFeedSharing`: `GET`/`PUT /v1/me/sharing` |
| `OutboxTransport` (publishDrive, unpublishDrive, revokeShare) | `LocalFeedTransport` returns the mock's status; `OutboxSendResult.classify(status:)` maps it | `BackendFeedTransport`: the same `classify` on the real status |
| Wiring | `DependencyContainer` builds the mock, its repository and the relay (lines ~246–296) | one switch picks mock or backend |
| HTTP, signing, tokens | none: `APIClient`, `Endpoints`, `NetworkError` are empty files | to build |
| App Attest | none; vectors already in `CarodoTests/Fixtures/app-attest-vectors.json`, read by no test | to build |
| Keychain | only `InstallationIdentity` (never sent, ADR 0006) | account secret, refresh token, debug key |
| Base URL | placeholders `https://*.example.com`; `Secrets.apiKey` reads an `API_KEY` (no API key exists, ADR 0009) | real URLs; `Secrets` removed |

Assumed, not checked: that Debug's Info.plist has no ATS exception (so `http://` to a Mac would be
refused); that no screen reads `CommunityError` cases beyond the four in `Community.swift`.

## 2. Proposal — slices

Each slice ends with `task ios:test`, `task ios:lint`, `task ios:warnings` green; nothing on the
tracking path calls the network (invariant 1).

**S1 — Byte formats against the vectors (pure).** Key id from a public key, `clientDataHash` from a
challenge, client data (`METHOD \n path-and-query \n base64(SHA-256(body))`), authenticator data,
the assertion CBOR, the `Carodo-App-Assertion` header, the `carodo-debug` attestation CBOR. Tests
read `app-attest-vectors.json`; ECDSA signatures are checked by verifying, not by comparing.

**S2 — Keys and secrets.** `AppAttestKeyStore`: in Debug a software P-256 key (CryptoKit) in the
Keychain (this device only); the `DCAppAttestService` path is written behind `isSupported` but off
until the paid team's entitlement (D4). `AccountSecretStore`: the account secret synchronizable
(`kSecAttrAccessibleAfterFirstUnlock`, iCloud Keychain), the refresh token `…ThisDeviceOnly`;
access and guest tokens in memory only.

**S3 — `APIClient`, one actor.** Builds requests from `Endpoints`; signs assertion-carrying
requests at send time, one after another; a guest token on demand (challenge → attestation → guest,
then assertion-only renewals); single-flight refresh; the 401 ladder of sync.md (refresh once →
session from the secret → new key and guest token → secret refused means the account is gone);
`ETag` / `If-None-Match` for the Feed and stats; a Problem's `code` to `NetworkError`, mapped to
`CommunityError` in the repository (`username_taken`/`reserved`/`profane`/`invalid`,
`username_change_limit`, `sharing_off`, `geo_payload_rejected`, `out_of_range`, a bad cursor).

**S4 — The three Backend types and the switch.** `BackendCommunityRepository`,
`BackendFeedSharing`, `BackendFeedTransport` on `APIClient`; `DependencyContainer` picks the
backend in Debug by default and the mock with a launch argument (D1). Publishing keeps the outbox
exactly as it is: the transport only replaces where a message goes; 422 is `rejected`, 401/429/5xx
`retryLater` (already in `classify`).

**S5 — Against the local backend.** Simulator with `task app:dev`: claim (each refusal shows its
own message), relaunch (no new claim or attestation), Start sharing, a drive published through the
outbox, the Feed with "You" and reactions, rename (limit), Stop sharing, delete. Then one Personal
Team iPhone on the Mac's LAN address (`task app:dev` has `dev:lan`).

**S6 — Record.** `LocalFeedServer` aligned with contract 0.28.2 if it stays (TD-35); `FeedAPI.swift`
header to 0.28.2; `docs/sync.md` ("Local mock", "Publishing"), `docs/architecture.md` (what is
wired); `PrivacyInfo.xcprivacy` and the privacy label for what now leaves the device (D3);
`technical-debt.md`, PV-26 updated.

## 3. Non-goals

Real App Attest (needs the paid program and the entitlement), DeviceCheck, share links, encrypted
backups, report and block, a staging deploy (backend `backend.md` slice 7). No new dependency
(CryptoKit, Security and DeviceCheck are system frameworks).

## 4. Acceptance criteria

- Every `CommunityRepository`, `FeedSharingService` and `OutboxTransport` call the screens make
  reaches `task app:dev` and shows what the mock showed for the same data.
- A fresh install gets a guest token on the first Feed read, not at launch; a relaunch reuses the
  stored key and session; two tasks needing a token at once make one refresh; signed requests never
  fail on counter order (a test that fires several at once).
- No request carries the installation id or any device id; no coordinate leaves in a body (the
  server's `geo_payload_rejected` is never seen in S5).
- Byte formats pass against the vectors; `task ios:test`, `lint`, `warnings` green.

## 5. Decisions for the owner

- **D1 The mock:** keep `LocalFeedServer` for Debug only, behind `-carodo.feedBackend mock`
  (offline UI work, synthetic drivers), aligned with 0.28.2 (TD-35); or delete it. Recommend: keep.
- **D2 Base URLs:** Debug from a build setting in a gitignored `Local.xcconfig` (the Mac's LAN
  address for an iPhone, `http://localhost:8080` for the Simulator), staging the workers.dev URL,
  production `https://api.carodo.app`; plain HTTP to the local network allowed in Debug only
  (`NSAllowsLocalNetworking`, an Info.plist change: P6). Recommend: yes.
- **D3 Privacy manifest:** the claim sends a username and publishing sends drive summaries; declare
  them in `PrivacyInfo.xcprivacy` now (S6) or at the TestFlight gate. Recommend: now, with the
  types listed for your review.
- **D4 App Attest entitlement:** stays out until the paid program (P6); Debug's software key only.
  Recommend: yes.
- **D5 `Secrets` / `API_KEY`:** remove (ADR 0009 has no API key). Recommend: yes.
- **Parallel work:** `DependencyContainer.swift` and `CarodoApp.swift` have your uncommitted
  changes; S4 adds to them and never overwrites. Tell me if you are editing them now.

## Afterwards

When S6 ships, its result lands in `carodo-ios/docs/`, this page's status moves, and PV-26 closes
on the Simulator and the iPhone.
