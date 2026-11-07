# Recording polish: how a drive starts, records, ends and is dropped

A brief for the session after first run (template: [`../AGENT_WORKFLOW.md`](../AGENT_WORKFLOW.md)).
Written 2026-11-03 at the end of the first-run session; runs while the motorbike test data comes
in. Mockups first, then code. Thresholds are not changed here: they wait for the device data.

```text
Outcome:
  A drive says how it started (by hand, Auto Mode, Shortcut/CarPlay) and how it ended (by the
  person, by itself after stopping, after the car's audio went, with no signal, recovered at
  launch). While it records, the Map and the panels show what Carodo is doing, including when it
  is about to end the drive by itself. A drive that ends or is dropped by itself is never a silent
  surprise.

User story:
  As someone who lets Auto Mode record, I glance at the Map and see the drive being drawn, I see
  "Ends by itself in 3:20" when I park, I find the drive in Journeys marked "Auto Mode", and if a
  very short hop was not kept, I can see that it happened.

Spec (Ready?) and mockups:
  carodo-ios docs/specs/drive-recording.md (Panels, Ending a drive and short drives), journeys.md
  (List, Detail), navigation.md (Map), auto-mode.md; tracking.md (StopDetector, triggers).
  Mockups to draw first: design/mockups/recording-*.png (below).

Acceptance criteria:
  - trips.start_trigger and trips.end_reason are stored for every drive (schema, owner's approval,
    v1_initial pre-release); recovered and joined drives get theirs.
  - Journeys rows and the detail show the start source (a small Auto Mode / Shortcut symbol, a line
    "Started by Auto Mode · ended by itself 5 min after stopping"); a search token or filter "Auto".
  - The compact panel shows the stop countdown once a stop is confirmed ("Ends by itself in 3:20
    unless you move"), and "Car audio off: ends in 1:10" after a disconnect.
  - The Map while recording: the recorded line drawn live in copper above past drives, the position
    with accuracy, follow north-up, nothing to tap while moving (driving surfaces rule).
  - A drive that ended by itself: a quiet confirmation the next time the app opens (or a local
    notification, if approved) with Undo/Open; a dropped short drive leaves a line in Journeys for
    24 h ("A 0.3 km drive at 07:42 wasn't kept · Keep it") instead of vanishing.
  - Light, Dark, the largest Dynamic Type, VoiceOver; every string in the catalogs (en, vi).

Non-goals:
  Threshold changes (wait for the motorbike data), Replay, Share, the Live Activity on the Lock
  Screen (its own brief: a new extension surface, P6 for ActivityKit and push).

Relevant files/docs:
  Carodo/Core/Recording/DriveSessionManager.swift (trigger, finish, onDiagnostic),
  Core/Tracking/StopDetector.swift (stoppedSince, verdict), Core/Tracking/AutoModeCoordinator.swift,
  Features/Drive/Views/RecordingPanels.swift, Features/Map/Views/MapAtlasView.swift,
  Features/Journeys (rows, detail), Core/Persistence (trips), docs above.

Constraints:
  carodo-ios AGENTS.md; P1 (nothing waits on a network), P4 (a disconnect never ends a drive by
  itself), P5. Schema and any notification permission need the owner's approval (P6).

Validation:
  task build, task test, task lint; DEBUG launch arguments for the panels and the countdown; the
  iPhone for the real stop countdown and an auto-dropped drive.

Do not:
  Commit or push. Change thresholds. Touch files another session is editing without checking.
```

## What exists today (2026-11-03)

- **Start source:** `DriveSessionManager.Trigger` is `manual`, `auto` or `carPlay` (a Shortcut or
  `carodo://trip/start`) and reaches only the tracking log (`driveStarted manual`). The `trips`
  table has no column for it, so Journeys cannot tell an Auto Mode drive from one started by hand.
- **End reason:** only in the log: `driveSaved finishedBy=person`, `autoFinished stopped |
  disconnected | noSignal`; recovered drives say `launched recovered=…`.
- **Ending by itself:** auto-finish ends 5 min after a confirmed stop (90 s once the car's audio has
  gone), at the moment it stopped; it shows no summary. Nothing on screen says the countdown runs.
- **Short drives:** started by Auto Mode or a Shortcut, under 500 m or 120 s moving: dropped
  silently, never in Journeys (`drive-recording.md`); started by hand: "Discard / Keep" after the hold.
- **Map while recording:** the drive's route is drawn above the heat map (ivory under copper); no
  countdown, no state.
- **Live Activity:** not built (the widget target exists, empty).

## Decisions (owner, 2026-11-03)

All six proposals accepted as written below, plus: Settings → Tracking status moves into
Developer (shown only with Developer mode on). Proposal 5 takes the 24-hour "not kept" line, so
`trips.status` gains `dropped` (CHECK) next to `start_trigger` and `end_reason`, all in
v1_initial. `trips.revision` (carodo-app ADR 0007) landed the same day, separately.

After the mockups (`design/mockups/drive/recording-polish.png`), also decided: the Map chip reads
"Recording · <source>" only ("Recording" by hand), the figures stay in the panel; a paused drive
never ends by itself; several waiting after-end toasts collapse into one ("2 drives saved · Open
Journeys").

Later the same evening (owner): **the start source is for logic and debugging, not the UI.** No
source glyph in the panels, no red dot on the Auto Mode button, no glyph or filter in Journeys; the
Map chip reads just "Recording". The detail's "Started by Auto Mode · ended by itself…" line shows
only with Developer mode on. The countdown, the after-end toast and the dropped-drive line stay
(they are state the person needs, not the source). Step 6 shrinks to that Developer line.

## Proposals (accepted)

1. **Schema** (`trips`, v1_initial): `start_trigger` TEXT (`manual`, `auto`, `shortcut`) and
   `end_reason` TEXT (`person`, `stopped`, `disconnected`, `no_signal`, `recovered`), set by the
   session and recovery; a joined journey shows its first part's start and its last part's end.
2. **Name the sources:** "By hand" · "Auto Mode" · "Shortcut" (CarPlay automations and links are
   Shortcuts to the person). Symbols: `hand.tap`, `autostartstop`, `square.2.layers.3d`?
3. **The stop countdown** in the compact panel (and the expanded one): appears only after the stop
   is confirmed (30 s), never while moving; tapping it does nothing (a parked person may tap
   Finish instead). Reduce Motion: no ticking animation, the number only.
4. **After an automatic end:** in-app first (a toast on the next launch or on return to the app:
   "Drive saved: 12.4 km, ended 07:58 · Open"). A local notification is a permission (P6) and a
   later choice.
5. **Dropped short drives:** keep a 24-hour "not kept" line in Journeys with "Keep it" (the trip is
   held in a `dropped` state, not deleted, until then), or keep today's silent drop and show them
   only in Developer. The first needs a status value in the schema.
6. **The Map while recording:** follow north-up by default (already the rule), the live line thicker
   than past drives, the period chip replaced by "Recording · 12:48 · 6.1 km", the Auto Mode button
   showing it started the drive.

## Mockups to draw (design/mockups/recording-*.png)

| Screen | States |
|---|---|
| Map while recording | moving (live line, chip "Recording · …"), stopped with the countdown, car audio off with the short countdown, Light and Dark |
| Compact and expanded panels | started by hand / by Auto Mode / by Shortcut (the source in the panel), the countdown, paused |
| After an automatic end | the toast with Open; the dropped-drive line in Journeys with Keep it |
| Journeys and detail | rows with the source symbol; the detail line "Started by Auto Mode · ended by itself…"; the Auto filter token |

## Order

1. ~~Decide proposals 1–6 (owner)~~ done 2026-11-03. 2. ~~Mockups~~ drawn and approved 2026-11-03. 3. ~~Schema + session/recovery write the two columns~~ done 2026-11-03 (437 tests). 4. ~~Panels countdown~~ done 2026-11-03 (441 tests). 5. ~~Map while recording~~ done 2026-11-03
6. ~~The Developer-only start/end line in the detail~~ done 2026-11-03. 7. ~~After-end toast
and dropped drives~~ done 2026-11-03 (446 tests). 8. ~~Undo after Keep it~~ done 2026-11-04 (451 tests; undo only while the drive has not reached iCloud and nothing was joined into it). Each slice: build, test, lint, screenshots; specs updated in the same change.
