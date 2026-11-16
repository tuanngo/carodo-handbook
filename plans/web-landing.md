# Web landing (carodo-app `apps/web`)

Status: **built, uncommitted** (2026-11-15). carodo-app is not committed until its first deploy;
`task check` passes (api 173, web 25). Next: the items under "Next", in that order.

## Where it is

- **Pages:** `/` (landing), `/privacy`, `/terms`, all Hono JSX, Tailwind v4 with Preflight and shadcn
  Typeset, after linkto's public pages. Web palette close to iOS, tuned for reading (owner):
  page `#FAF7F1`, text `#141311`, accent `#9C5313` / `#DC9154`, `shadow-soft`, public wash.
- **Landing, top to bottom:** app icon, badge, headline "Your private driving journal. / Every
  drive, kept on your iPhone.", App Store badge ("Coming soon", no link), trust line; a fan of three
  iPhone 18 Pro Max screens (Geofency-style): a drive **recording live** on the Hải Vân pass, the
  Hải Vân **drive page** above Đà Nẵng bay, a **frame of the exported Replay video**; "Record it.
  Keep it. Relive it." as three borderless cards with a strip of app UI each (Auto Mode, Journeys,
  Replay; own icons drawn after the app's `autostartstop` and `car.side`, never SF Symbols or the
  CarPlay mark); "Private by design." on a Charcoal band (three reasons, Privacy Policy link); FAQ
  (five questions, Auto Mode answers from the app's Help).
- **No sharing feature on the landing** (owner: a private journal).
- **Images:** Simulator screenshots of the synthetic showcase drives (`showcase/`,
  `-carodo.showcaseJournal`), never a real drive, in `apps/web/media/*.jpg` (440 px wide, ~190 KB
  for three). `scripts/build-media.mjs` (run with the styles) embeds them in
  `src/.generated/media.ts`; the Worker serves `/media/<name>.<hash>.jpg`, cached a year. No binding.
  The language switch updates `alt` (`data-i18n-alt`).
- **Dark screens (done 2026-11-15):** each hero screen has a twin `<name>-dark.jpg`, chosen by a
  `<picture>` source on `prefers-color-scheme`. The app's own setting overrides the Simulator's
  appearance; force it with `-carodo.appearance dark|light`. All six shot on the Pro Max (Showcase)
  with `-carodo.showcaseJournal` **without** `-carodo.showcaseNow` (dates stay "Sunday, 25 Oct",
  reproducible): the drive page `-carodo.debugTab journeys -carodo.debugOpenJourney 3` (wait ~30 s
  for the place names); the Replay frame at 7.5 s of `-carodo.debugOpenReplay YES
  -carodo.debugReplayExport 30` (frame grabbed with AVFoundation, no ffmpeg here); the live screen
  with `-carodo.debugStartDrive YES` and `sim_drive.py hai-van`, shot at 6:13 / 3.6 km, recorded in
  the in-memory showcase journal (the simulator's database was not touched). The light live screen
  is still the earlier one (6:33). Both exports are kept in the app's `Documents/replay-export/`
  (`replay.mov` light, `replay-dark.mov`) for the clip (3).
- **Showcase car is a Kia Sportage (owner, 2026-11-16; was a Mazda CX-5):** `showcase/drives.json`
  names it, and the app's placeholders and sample data follow (carodo-ios). Reshot the same day with
  the same arguments: the drive page (Light, Dark: the car shows faintly under the tab bar) and both
  Replay exports, then the still at 7.5 s (440 px JPEG) and the clip 7.5–14.5 s (H.264 720×1280,
  600 kbit/s, ~533 KB) cut with AVFoundation. The live screens show no car and were kept. A
  sandboxed write leaves a `<name>.mp4.sb-*` temp file beside the output: never copy it into
  `media/`.
- **Replay clip (done 2026-11-15, owner: R2):** the right phone plays 7 s of the Replay export
  (from 7.5 s, so its first frame is the still), muted, looping, no poster, hidden with Reduce
  Motion; Light and Dark (`replay-clip.mp4`, `replay-clip-dark.mp4`, ~535 KB each, H.264 720×1280,
  encoded with AVFoundation). Served from a new public R2 bucket `carodo-media` on
  `media.carodo.app`, shared by staging and production, no binding on the web; every deploy uploads
  it first. Checked in Simulator Safari, both schemes, from a local copy (the bucket does not exist
  yet).
- **Link preview (done 2026-11-15):** `/`, `/privacy`, `/terms` carry Open Graph (`og:title`,
  `og:description`, `og:url`, `og:locale`, image 1200×630) and `twitter:card` =
  `summary_large_image` (X reads the `og:` tags for the rest). Absolute URLs come from the request's
  origin, so staging previews point at staging; the 404 page has none. The card is the brand's
  `og-image.png`, served from `/media` like the screens.
- **Icons:** `apple-touch-icon.png`, `icon-192/512.png` and the maskable icon (brand export) are in
  `media/` too; `/apple-touch-icon.png` keeps its fixed name (iOS asks for it at the root), the
  manifest points at the hashed paths. They 404'd before.
- **Motion (CSS only, none with Reduce Motion):** cards and phones rise into view
  (`landing-rise`, scroll-driven), the centre phone floats, the Auto Mode arrow turns, the Journeys
  route draws, the Replay strip plays.

## Next

1. *(Check after the first deploy)* the preview in Messages, Zalo and Facebook's Sharing Debugger.
   The card is the logo only; a card with the phone fan could replace it later (same file name).
2. **Provision `carodo-media`** (owner, once): `.env.deploy` on this Mac, the bucket, the custom
   domain `media.carodo.app`, then `task media:upload` (docs/operations/deploy.md). Until then the
   right phone shows its still (the clip's URL does not resolve), which is the intended fallback.
3. *(Optional)* **Passport stamp** (`design/passport-stamp/`) as an accent: a corner of the privacy
   band, or a fourth card "Passport".
4. **Effects:** the phone fan opens as the page scrolls (side phones from 0° to ±6°, sliding out; the
   centre one rises), scroll-driven like `landing-rise`; a faint Copper glow behind the fan, as behind
   the app icon. Nothing more: the page stays calm.


## Open

- **Simulator drive distance:** the live Hải Vân drive (`showcase/sim_drive.py`, one continuous
  scenario) saved **20.1 km of the 22.9 km road** (2026-11-15). Not the restart jumps of the Prenn
  run. Suspect the Simulator interpolating straight between waypoints at 1 fix/s and cutting the
  hairpins, or the recorder dropping fixes. Check: decode the Pro Max's `trip_tracks` and compare
  with `routes/hai-van.gpx`. The landing only uses a still from it; the showcase figures come from
  `generate.py` (within 1 %, `task showcase`).
- **Simulators:** "iPhone 18 Pro Max (Showcase)" was created for screenshots (iOS 27.2); its test
  database holds that live drive. Its status bar is overridden to 9:41
  (`xcrun simctl status_bar <udid> clear` to undo). Kept for S5.
- **S5 (App Store set)** of `showcase-drives.md`: on the Pro Max (6.9"), Light and Dark, English and
  Vietnamese; the screens above are its first candidates.
- **Copy** in `apps/web/src/landing-i18n.ts` was also edited in parallel by the owner (e.g. "Record
  drives automatically", "Frequently asked questions"): keep their wording.
