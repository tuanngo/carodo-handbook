# References

What we learn from other people's work: open-source repositories and other apps. Reference
material for thinking, never a source of truth: a finding that shapes Carodo lands as a draft,
a spec or an ADR in the repository it binds, in our own words.

| Folder | Holds | Committed |
|---|---|---|
| [`repos/`](repos/) | Open-source repositories to read, one file per area: [`ios.md`](repos/ios.md) (iOS, maps, testing tools). Add `backend.md` and `web.md` when `carodo-app` work starts | Yes |
| [`apps/`](apps/) | Notes on apps we study, one file per app ([`carstack.md`](apps/carstack.md)): what they do, what works and why, what we take and what we refuse | Yes |
| [`screens/`](screens/README.md) | Screenshots of those apps, one folder per app | **No**, they stay on this machine |
| `apps/<app>/` | Local study material for one app: API requests (`api-requests.txt`), responses (`api-*.json`), exports | **No**, ignored: they carry device and account ids and other people's data |

## Rules

- **Code follows its licence.** MIT: copy only with the copyright and licence notice kept.
  GPL or no licence: ideas only, never code. Adding a repo as a package is a new dependency and
  needs the owner's approval first. Details: [`repos/ios.md`](repos/ios.md#licence-rules--read-before-copying-anything).
- **Clone outside the Carodo repos**, e.g. `~/code/refs/<name>`, so foreign code never lands in
  our history by accident.
- **Apps are described in words, not copied.** Screenshots can show accounts, places and routes;
  they stay in the ignored `screens/` folder. Note the pattern and the reason in `apps/<app>.md`,
  never their artwork, copy or brand.
- **Captured API traffic stays local.** Requests and responses go in `apps/<app>/`, never in a
  note: a request header such as a device id is a credential. A note quotes endpoint names and
  patterns only.
- **Privacy outranks imitation.** A pattern that exposes where someone drives is refused however
  well it works elsewhere (carodo-ios ADR 0007); say so in the app's note.
- Each note carries the date it was checked: apps and repos change.
