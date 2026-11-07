# Vehicle expenses: wash, service, tolls

Status: approved by the owner 2026-11-07. **Slice 1 built 2026-11-07** (in `carodo-ios` main, `f55e0a4`); its result is in `carodo-ios/docs/specs/garage.md` (Log for your car, Expense sheet, Paid on a drive) and `journey-detail.md` (During this drive). What follows is kept for slices 2 and 3. When the first slice is built,
its result moves to `carodo-ios/docs/specs/garage.md` (and `journey-detail.md` for the trip part),
and this draft shrinks to what is still open.

## Why

The "Log for your car" sheet (Journeys bar **+**) already logs fuel and the odometer. The owner
pays for three other things often enough to want them logged: **Car wash** (Rửa xe), **Service**
(Bảo dưỡng) and **Tolls** (Phí cầu đường). What the owner records in practice is **only the
amount**, for all three, service included. The interesting question is "what did this drive
happened on this drive" (a fill-up, a wash, a toll along the way), so the drive comes first.
The ledger of what the car costs lives in the Garage, on the vehicle page (slice 2).

## Goals

1. Log a wash, a service or a toll in a few seconds: the amount, the time (now by default), an
   optional note. Nothing else is asked.
2. An expense or a fill-up entered **while a drive is recording** belongs to that drive
   automatically.
3. An expense entered later is just an expense of the vehicle. On the drive's detail page, Carodo
   **suggests** the ones whose time falls in or just after that drive, and the person confirms
   the link. Unconfirmed, it stays an expense of the vehicle, never lost or hidden.
4. The drive's detail page shows what was paid during it, as events of the drive, not as a cost
   of the drive.

## Non-goals (later, in this order of likelihood)

- The vehicle page's **Expenses** section and **Expense history** sheet (slice 2 below).
- **Per-category details**: each category may later carry fields of its own (service: odometer,
  garage, items; toll: station; wash: probably nothing). Only amount, time and note are shared.
- **Recurring costs**: service every X km or months, road fee, insurance, monthly parking —
  reminders or a pre-filled next entry.
- **Photos** (receipts, service slips): needs storage, iCloud and `.carodo` backup decisions.
- **Passport**: a line or section of spending across all vehicles.
- Editing and deleting entries (also still missing for readings and fill-ups).

## Anti-goals

- Turning a drive into a bill: no total, no cost per km on the drive (a fill-up pays for later
  drives too). Totals belong to the Garage's ledger.
- A form. If logging a toll takes more than the amount and **Save**, the design has failed.
- An expense that disappears or is hidden because it was not linked to a drive.
- A link the person did not make or confirm, except the one made by logging during the drive.
- Spending shown to anyone else, or sent to the backend. Expenses are private history like the
  journal (P5, P7): device and the person's iCloud only.
- Inviting interaction on a driving surface while moving (iOS AGENTS.md, UI).

## Decided

**Kinds and categories (existing `vehicle_logs`, ADR 0016).** No new kind, no new table for the
entries:

| Tile | `kind` | `category` |
|---|---|---|
| Car wash / Rửa xe | `expense` | `wash` |
| Tolls / Phí cầu đường | `expense` | `toll` |
| Service / Bảo dưỡng | `service` | `general` (one general service for now; builder's call, so later service categories read old rows by name, never by NULL) |

`amount` + `currency` (minor units, ISO 4217; docs/data-model.md#money), `occurred_at`,
`time_zone`, `note`. `odometer_m` stays NULL from these sheets for now.

**No location (owner, 2026-11-07).** A wash, a service or a toll stores no GPS position. A linked
entry's place, if ever needed (a toll on the replay), is read from its drive's route at
`occurred_at`; an unlinked one has none (where the phone was when typing is not where it was
paid). A familiar wash or garage, if wanted later, is a picked place like the fuel sheet's
station, with the per-category fields (slice 3). Fill-ups keep their station rule (ADR 0017).

**Entry.** Three tiles join **Log fuel** and **Update odometer** in "Log for your car", each with
one line of where it stands ("12 days ago", "Yesterday · 45.000 ₫", "Not logged yet"). A tile
opens one amount sheet shared by all three: the category's symbol and name, the time line
("Today, 16:58 ›", editable as in the fuel sheet), the amount in large digits with the quick
amount chips and the numpad of the fuel sheet, an optional note, **Save**. Haptics as in the fuel
sheet.

**Designed to grow.** In code, each category declares what it asks for (today: amount, time,
note). Per-category fields and recurrence later extend that declaration rather than rewriting
the sheet.

**Link to a drive.**
- Logged while a drive is recording (a fill-up or any of the three): linked to that drive at once.
- Logged at any other time: no link.
- On a drive's detail page: entries of the drive's vehicle whose `occurred_at` falls inside the
  drive or within a short window after it ends are offered as suggestions to confirm; confirming
  stores the link.
- An unlinked entry is still an expense of the vehicle in every list.

**Which recording drive links (designer's call, 2026-11-07).** The automatic link is made only
when the vehicle chosen in "Log for your car" is the recording drive's vehicle. A pending Auto
Mode drive counts (it is still the person's car); a drive with no vehicle, or a different car
picked in the sheet, gets no automatic link (it can be suggested later). A drive still in Ready
has not started and gets none.

**When a drive changes (designer's call, 2026-11-07).** A link points at the drive it was made
with and is read through it:
- Merged: the entry belongs to the merged drive (read through `parent_id`).
- Split: the entry goes to the part whose time span holds its `occurred_at` (the nearest part
  when it is after both).
- Trimmed: the link stays.
- Vehicle changed: the linked entries move to the new vehicle with it (they were logged against
  the wrong car), in the same transaction.
- In Recently Deleted: the link is kept, and the entry reads as unlinked meanwhile; restored, it
  comes back. Purged, or discarded (a short or undone drive, an unanswered pending drive): the
  link is cleared, and the entry stays an expense of the vehicle.
- Sync: the link is a plain field of the entry and follows the entry's own conflict rule
  (`docs/sync.md`); a link to a drive this device does not have reads as unlinked.

**On the drive's detail page.** A "During this drive" section: each linked entry, fill-ups
included, as a row (symbol, category, amount, time). No total, no cost per km. Suggestions appear
in the same section, visibly distinct, with **Add to this drive** and **Not this drive**. A
linked row can be removed from the drive (the entry stays an expense of the vehicle).

**Declines are remembered (owner, 2026-11-07: as simple as possible, a schema change is
acceptable).** "Not this drive", and removing a row from a drive, record that drive on the entry,
and that entry is never suggested for that drive again. One remembered drive per entry is
enough: an entry's time falls near one drive.

## Changed while building slice 1 (owner, 2026-11-07)

- **One drive per entry.** An unlinked entry is suggested on its nearest drive only (the one whose
  span holds its time, else the one that ended last before it, within 30 minutes); "Not this drive"
  leaves it suggested nowhere, so one `declined_trip_id` is enough.
- **A drive changing does not move entries.** Merge and split follow `parent_id`; a vehicle change
  leaves an entry on the vehicle it was logged for; a drive that is gone or trashed just shows none
  of its entries (they stay the vehicle's and can be suggested elsewhere). Nothing is cleared.
- **From the first moment of a recording** (before the first GPS fix) a log is linked.

## Schema change (needs the owner's approval, P6)

The link needs a stored column; time alone cannot tell a confirmed link from a coincidence:

- `trip_id TEXT` (nullable, **no foreign key**, as `vehicle_id`; app-level checks) on
  `vehicle_logs` **and** `fuel_logs`, with an index for "the entries of a drive".
- `declined_trip_id TEXT` (nullable, no foreign key) on both: the drive this entry was declined
  for; never suggested there again. Cleared when the drive is purged.
- Pre-release: edited into `v1_initial` (iOS invariant 6), `docs/data-model.md`, the CloudKit
  records (`VehicleLog`, `FuelLog`), and the `.carodo` backup (`BackupVehicleLog`, the fuel
  equivalent) in the same change. CloudKit production schema deploy before a TestFlight build.
- Never sent to the backend; trip UUIDs stay device-generated (P1).

## Slices

1. **Log and link** — three tiles, the amount sheet, the `trip_id` and `declined_trip_id`
   columns, linking while recording, the drive's "During this drive" with suggestions, confirm,
   decline and remove.
2. **Garage ledger** — the vehicle page's Expenses section (this month per category, fuel
   included) and an Expense history sheet merging fill-ups. Totals live here only.
3. **Later** — per-category fields, recurring costs, photos, Passport, edit/delete.

## Left to the builder

The window after a drive's end for suggestions, the symbols, the exact copy (English and
Vietnamese per `docs/copy-and-localization.md`), the default quick amounts per category, and
where exactly the tiles sit in the bento grid.
