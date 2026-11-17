# Geodata from OpenStreetMap — through our server, never from the phone to OSM

Status: **proposal, awaiting the owner's decisions (2026-11-15).** No code. Needs an ADR in
`carodo-app/docs/decisions/` (and a carodo-ios one for the app side) once the decisions below are
made.

**Owner decisions already made (2026-11-15):** the app never calls an outside service directly;
OSM and any other provider are reached through the Carodo backend. The first OSM data: **city
boundaries, tunnels and toll stations.**

## 1. Today

- The app calls no third-party HTTP service. Every lookup is an Apple framework on the device:
  `CLGeocoder` for place names and provinces (`Core/Location/PlaceLookup.swift`, Provinces
  Crossed by bisection over cached cells in `Core/Recording/ProvincesCrossedSource.swift`),
  WeatherKit (`Core/Weather/WeatherLookup.swift`), `MKLocalSearch` for POIs and fuel stations
  (`Core/Location/MapKitPOISearch.swift`, `MapKitStationFinder.swift`).
- Tunnels appear only as the reason for a GPS gap (`Core/Recording/GapHealing.swift` routes a gap
  with Apple Maps after the drive; `RideProfile.swift`, `StopDetector.swift`). Tolls are only a
  manual expense category (`ExpenseLabel.swift`, `VehicleRepository.swift`).
- Invariants that bind the design: raw GPS samples never reach the backend (AGENTS P5, P7; they go
  only to the person's iCloud); the backend holds only what is public or shared; only the genuine
  app calls the API (App Attest); the server never locates anyone (carodo-app ADR 0002).

## 2. The privacy problem with a plain proxy

A proxy that takes a coordinate and asks Overpass or Nominatim on the phone's behalf sends the
person's exact positions to our server on every lookup. That breaks P5/P7 as written and makes the
backend a dependency of journey analysis. It also scales badly against the public OSM servers
(Nominatim: at most 1 request/s, no heavy use; Overpass: a shared, rate-limited service).

## 3. Proposal: country packs, matched on the device

The server **prepares** OSM data and the app **downloads it whole**, then does every match on the
device. The server learns only which country's pack was fetched, which it already knows from
`request.cf.country`; no coordinate is ever sent.

- **Build** (offline, owner-run or a scheduled CI job, never on a request path): one script in
  `carodo-app/scripts/geo/` fetches a country's features from Overpass (or a Geofabrik extract),
  simplifies them, writes compact versioned files and uploads them to R2 (`BLOBS`) through
  `scripts/wrangler.mjs`. Monthly is enough; boundaries change rarely.
- **Layers, Vietnam first:**
  - `boundaries`: admin polygons (level per D1), simplified with shared borders kept, coordinates
    quantised; a few MB at most.
  - `tunnels`: `tunnel=yes` ways on `highway=*` roads, with name and length; hundreds of features.
  - `tolls`: `barrier=toll_booth` nodes and `highway=toll_gantry`, with name and the road they sit
    on; hundreds of features.
- **Serve:** `GET /v1/geo/packs/{country}` returns a manifest (version, each layer's size and
  SHA-256); `GET /v1/geo/packs/{country}/{version}/{layer}` returns the immutable file from R2, by
  known key (C12), cached at the edge for good. Guest or member token required (P7). Cost: one
  download per device per pack version.
- **Use on the device (carodo-ios, its own plan):** Provinces Crossed by point-in-polygon instead
  of per-cell `CLGeocoder` calls (offline, no lookup budget); a GPS gap whose ends sit at a tunnel's
  portals is drawn along the tunnel instead of a routed guess; tolls passed on a drive suggest toll
  expenses and can enter the journey's facts.
- **Licence:** OSM data is ODbL. The app shows "© OpenStreetMap contributors" where the data is
  used, and the packs (a derived database we make public to the app) are offered under ODbL too.

A live proxy stays possible later for a lookup a pack cannot answer; it would need its own ADR,
changing P5/P7, with no logging and no storage of the coordinates.

## 4. Decisions for the owner

- **D1 Which "city" level?** Since 1 July 2025 Vietnam has 34 provinces and no district level.
  Options: provinces and centrally-run cities (34 polygons, small) or communes and wards (about
  3,300, larger). Recommend: provinces first; communes only if a feature needs them. Assumed, not
  checked: how far OSM has been retagged after the 2025 reform; S1 below measures it.
- **D2 Countries:** Vietnam only for V1? Recommend: yes, the pack format takes any country.
- **D3 Build tooling:** a geometry simplifier that keeps shared borders (mapshaper) is a new
  dependency of the script only (P6), or `osmium` as a local CLI. Recommend: mapshaper for the
  script, no runtime dependency in either Worker.
- **D4 Contract:** the two `/v1/geo/packs` operations go into `carodo-api.yaml` (your approval).
- **D5 Provinces Crossed source:** replace the Apple bisection with the pack, or keep Apple as the
  fallback where no pack exists. Recommend: pack first, Apple fallback outside covered countries.

## 5. Slices (after the decisions)

- **S1 Measure:** fetch Vietnam's three layers once, locally, into the scratch area (not
  committed): feature counts, raw and simplified sizes, and whether the provinces match the 2025
  map. Report the figures before building anything.
- **S2 Build script and R2 layout** (`docs/storage.md`), versioned packs, a test on a tiny fixture.
- **S3 The two endpoints**, cached, with the full-scan guard and a test per status.
- **S4 iOS** (its own plan and approval): download, store, match.
