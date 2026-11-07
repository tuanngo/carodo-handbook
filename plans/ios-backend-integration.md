# iOS ↔ backend: identity first

A brief for wiring the iOS app to the backend's identity flow, which is built and tested in
`carodo-app` (run locally with `task dev`). This is a plan, not a contract: every rule the server
enforces is in `carodo-ios/docs/sync.md` ("Accounts", "App Attest") and
`carodo-ios/docs/api/carodo-api.yaml`, and those win where this page is shorter or older.

Status: Next (roadmap phase 4, "Share + Feed live"; the identity part can start now).

## Brief

```text
Outcome: the app gets a guest token, claims a username, keeps its session across launches,
  reinstalls and other iPhones, and signs out everywhere or deletes the account, against the local
  backend, on the Simulator and on a Personal Team iPhone.
User story: as a driver I join the Feed with one username, without signing in, and my profile
  follows me to a new iPhone through iCloud Keychain.
Spec (Ready?) and mockups: carodo-ios docs/specs/account.md and specs/profile.md (Ready); ADR 0008, 0009.
Acceptance criteria:
  - A fresh install gets a guest token (debug proof on the Simulator and a Personal Team build).
  - "Join the Feed" claims a username; taken, reserved and invalid names show their own message
    (Problem `code`: username_taken, username_reserved, username_invalid).
  - Relaunch: no new claim, no new attestation; an expired access token refreshes once.
  - Reinstall with iCloud Keychain on: the profile comes back (new key, POST /v1/auth/session).
  - Two tasks needing a token at once make one refresh; signed requests never fail on counter order.
  - Sign out everywhere on one device: the other gets the new secret from iCloud Keychain.
  - Delete account: the profile is gone on every device; local drives stay unless the person chose.
  - The Swift tests check every byte format against CarodoTests/Fixtures/app-attest-vectors.json.
Non-goals: real App Attest on a paid team (needs the entitlement); Sign in with Apple; publishing
  drives, shares, Feed reads (their endpoints come next); DeviceCheck.
Relevant files/docs: Core/Networking (empty today), Core/Outbox, Configuration/Configuration.swift,
  docs/sync.md, docs/api/carodo-api.yaml, carodo-app docs/operations/local.md.
Constraints: no API key and no device id in a request (ADR 0006, 0009); recording never waits on the
  network; nothing on the tracking path calls the backend.
Validation commands/device checks: task ios:test; task app:dev with the Simulator; one Personal Team
  iPhone on the Mac's LAN address.
Allowed scope: Core/Networking, a new Core/Identity/AppAttest*, Keychain helpers, Settings → Account
  wiring, tests.
Do not: commit; add a dependency; change the contract without the owner (P6).
```

## Order of work

1. **Configuration.** `Configuration.apiBaseURL`: Debug `http://localhost:8080` (an iPhone uses the
   Mac's LAN address, with `wrangler dev --ip 0.0.0.0`), staging the workers.dev URL, production
   `https://api.carodo.app`. Allow plain HTTP for local networking in Debug only
   (`NSAllowsLocalNetworking`). Remove the `Secrets` enum (`API_KEY`, `ANALYTICS_KEY`): ADR 0009 has
   no API key in the app.
2. **Byte formats first, against the vectors.** Pure functions with tests reading
   `CarodoTests/Fixtures/app-attest-vectors.json`: key id from a public key, `clientDataHash` from a
   challenge, client data for a request (`METHOD \n path-and-query \n base64(SHA-256(body))`),
   authenticator data, the `Carodo-App-Assertion` header, and the debug attestation's CBOR. Sign
   with the vectors' test key and check the server's expected values; the signatures themselves
   differ each run (ECDSA), so test them by verifying, not comparing.
3. **`AppAttestService`.** `DCAppAttestService` when `isSupported` and the entitlement is present;
   otherwise, in Debug only, a software P-256 key in the Keychain and the `carodo-debug` attestation
   (sync.md "Development"). One key per installation, kept in the Keychain (this device only);
   attest it once, with a challenge from `POST /v1/auth/challenge`.
4. **`APIClient` as one actor.** It signs assertion-carrying requests one after another and signs at
   send time (sync.md "One key, one signed request at a time"); it refreshes single-flight; it maps a
   Problem to a typed error by `code`; it follows the 401 ladder in sync.md ("On 401").
5. **Keychain.** The account secret: synchronizable, `kSecAttrAccessibleAfterFirstUnlock`. The
   refresh token: `…ThisDeviceOnly`. The access and guest tokens: in memory only.
6. **`BackendService` behind the repositories.** Guest token on demand (first Feed read), claim from
   "Join the Feed", session from the secret at launch when one exists, sign out everywhere and delete
   from Settings → Account. The outbox transport uses `APIClient`, so a retried message is signed anew.
7. **On a Personal Team iPhone** against the Mac: claim, relaunch, reinstall, then a second device
   signed in to the same iCloud account if one is at hand.

## Afterwards

When a step ships, its result lands in `carodo-ios/docs/` (architecture.md "What is wired today",
the specs) and this page's status moves; the page is deleted when the identity flow is done, leaving
a line in `plans/ios.md`.
