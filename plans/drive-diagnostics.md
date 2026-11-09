# Drive diagnostics — TrackingLog format and Settings screen (2026-11-09)

Status: **built 2026-11-09** (carodo-ios f98cf5e slice 1, a2647dc slice 2, 23f378c slice 3); device checks open (technical-debt PV-11). Source of truth once built:
`carodo-ios/docs/tracking.md` (log format), `docs/data-model.md` (retention), `docs/specs/settings.md`
(the screen), `docs/privacy.md`.

## Today (audited)

| Part | What it does |
|---|---|
| `Core/Diagnostics/TrackingLog.swift` | `TrackingLogEntry(at, kind, detail)`, 35 kinds; free-form `detail` from builders, no coordinate; some kinds put a sub-event in the first word of the detail. No stage, no level. |
| `Core/Persistence/GRDBTrackingLog.swift` | `tracking_events (occurred_at, kind, detail)`, newest 500 kept by a `NOT IN (… LIMIT)` delete on every insert. No age limit, no clear. |
| `Settings/Views/TrackingStatusView` | Developer-only: `TrackingHealth` issues and the 50 newest lines with exact time. |
| `Developer/Views/DeveloperView` | `DeveloperLogView` (Copy, exact ISO time), `DeveloperLogFormat`. |
| `RecordingRequirement.rows`, `AutoModeSetupStatus` | Readiness rows of the Auto Mode page. |
| `Help/FAQCatalog` | `lateStart`, `notRecording` (step 3 already says 500 m / 2 min), `manualStart`. |
| `MainTabView` | One line per `onChange` of location, motion, Auto Mode, Low Power. |

Docs disagreeing with code: developer-mode.md says the Developer log keeps more than 500 rows (it
does not); tracking.md names a `carPlay` trigger (code: `shortcut`); privacy.md names the old
Tracking status path. `sid=`, `trip=`, `leadInM=` did not exist.

## Decisions (owner, 2026-11-09)

1. Stage column in **lowercase**: `sys`, `detect`, `drive`, `leadin`, `stop`, `gps`, padded so the
   pipes line up.
2. DEBUG lines are recorded in a DEBUG build or a TestFlight build with Developer unlocked; never
   in an App Store build.
3. Retention: 14 days / 3,000 rows (App Store, locked TestFlight); 60 days / 30,000 rows
   (Developer, DEBUG). Count cap by `DELETE WHERE id <= MAX(id) - cap`; recalibrate from a real DB.
4. `TrackingStatusView` becomes **Drive diagnostics** in Settings; Developer loses its Tracking
   status link and keeps `DeveloperLogView` (developer rendering + ShareLink).
5. Vietnamese name: **Chẩn đoán ghi chuyến**.
6. The four permission/toggle kinds merge into one `state` kind, written only when its
   fingerprint changes, with `changed=…`.
7. `trip=` only in the developer rendering; `sid=` made at render; no `leadInM=` (`prependedM=`
   stays, and the lead-in line says where the added start came from).

## Format

```
TimeColumn | +Rel | stage | event | key=value …
```

- Stage and level come from a static table over `Kind` (+ the event); event is the first word of
  the stored detail when it has no `=`, else the kind. No schema change.
- Header, computed at render: app, build kind, iOS, model, tz, location/precise, motion, background
  refresh, Low Power, Auto Mode.
- **Episode anchor:** `launch`, `mode to=detecting`, a drive start. Every line of an episode shows
  the anchor's hour (shared) and seconds since the anchor, so the anchor's minute never leaks
  across an hour boundary.
- **Shared** (Settings): hour only (`2026-11-09T08:xx`), whole seconds, INFO only, no audio port
  hash, no `map` lines. **Developer**: exact time to the millisecond, all levels (`lvl=debug`),
  `trip=` (8 hex).

## Screen (Settings → Info & Feedback → Drive diagnostics)

Readiness (`AutoModeSetupStatus` + `RecordingRequirement.rows`), five FAQ entries from
`FAQCatalog` (`lateStart` edited, `shortDrives`, `autoModeOff`, `notRecording` retitled,
`diagnosticsPrivacy`), the 50 newest shared lines, ShareLink (.txt), Clear log (confirmation; leaves
a `sys | cleared` line).

## Slices

1. Core: stage/level table, logfmt builders, `state` with dedup, `DiagnosticsLogFormat`, retention
   and `clear()`, Developer log on the new renderer with Share. Docs: tracking.md, data-model.md,
   privacy.md.
2. Drive diagnostics screen, strings, FAQ. Docs: settings.md, developer-mode.md. Screenshots.
3. New DEBUG lines (stop candidates, per-trip recovery, lead-in candidate) behind an injected flag.

No schema, API, entitlement or dependency change. Device checks: slice 3 lines on a real drive;
lines per drive from `task pull-db` to recalibrate retention.
