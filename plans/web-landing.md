# Web landing (carodo-app `apps/web`)

Status: **built, uncommitted** (2026-11-15). carodo-app is not committed until its first deploy;
`task check` passes (api 174, web 21). Next: the items under "Next", in that order.

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
- **Motion (CSS only, none with Reduce Motion):** cards and phones rise into view
  (`landing-rise`, scroll-driven), the centre phone floats, the Auto Mode arrow turns, the Journeys
  route draws, the Replay strip plays.

## Next

1. **Open Graph and Twitter card.** `carodo.app` is the link the app points to: a preview with image
   and title in Messages, Zalo, Facebook. The image exists: `design/brand/export/web/og-image.png`.
   Add `og:` / `twitter:` meta to `Layout`, serve the image through `/media`.
2. **Dark screenshots.** The dark page shows light app screens. Shoot the three screens with the app
   in Dark (find how to force the app's own appearance setting on the Simulator; `simctl ui
   appearance dark` alone did not change it) and serve them with `<picture>` by
   `prefers-color-scheme`.
3. **A real Replay clip** in the right phone instead of the still: 6–8 s, muted, autoplay, loop,
   `playsinline`, the current frame as poster. ~400–600 KB: serve through **Workers Static Assets**
   (a new binding: the owner's approval first, P6), or embed in the Worker as the images are (heavier
   bundle). Source: the exported `replay.mov` (`-carodo.debugReplayExport 30` on journey 3, Hải Vân).
4. *(Optional)* **Passport stamp** (`design/passport-stamp/`) as an accent: a corner of the privacy
   band, or a fourth card "Passport".
5. **Effects:** the phone fan opens as the page scrolls (side phones from 0° to ±6°, sliding out; the
   centre one rises), scroll-driven like `landing-rise`; a faint Copper glow behind the fan, as behind
   the app icon. Nothing more: the page stays calm.

Owner's call before 3: turn on Workers Static Assets for `carodo-web`, or embed the clip.

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
