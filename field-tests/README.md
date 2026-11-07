# Field tests: a script before the drive, a review after it

How the owner and an agent prepare a test drive, run it and read it back, so both work from the
same context. The checks themselves come from `plans/` (open device checks) and
`carodo-ios/docs/operations/device-testing.md` ("Checks by when they can be made"); this folder
holds one file per planned drive: its script, then its results.

## The loop

1. **Prepare (at the desk, the day before or before leaving).** The owner says what the drive is;
   the agent writes `field-tests/YYYY-MM-DD-<slug>.md` from `_template.md`, installs the build if
   asked (`task device`; a schema change erases the iPhone's drives, so install before the first
   drive of the day, never between two) and sends the script to the owner's phone.
2. **Drive.** The owner follows the script on the phone. The driver never touches the phone while
   moving: every step marked **passenger** is skipped on a drive alone. Odd moments are noted with
   the clock time, nothing else (Apple Notes is fine: `12:41 map line jumped`).
3. **Review (back at the desk).** The owner pastes the time notes; the agent pulls the database,
   reads the logs, matches every note to the events around it, fills **Results** in the same file,
   ticks what passed in `plans/`, adds coarse numbers to device-testing.md Results, and proposes
   the next step (a fix, a threshold to tune, a check to repeat). No code changes without the
   owner's go-ahead.

## Asking the agent

Before a drive (Vietnamese or English, any wording; these are the facts the agent needs):

```text
Chuẩn bị field test: <ngày, giờ>, <tuyến: ví dụ nhà → trường, ~20 phút, có kẹt xe>,
<có passenger hay đi một mình>, <xe: ô tô / xe máy>, <Auto Mode hay Start tay>.
Muốn kiểm tra: <các mục, hoặc "các mục còn mở trong plans">. <Cài build mới: có/không>.
```

After a drive:

```text
Review field test <file hoặc ngày>. Ghi chú giờ:
12:41 ...
12:55 ...
<số km đồng hồ trip của xe, % pin đầu/cuối nếu có>
```

## Rules for the agent

- **One file per drive**, named `YYYY-MM-DD-<slug>.md`, built from `_template.md`. The script and
  its results stay together; nothing is deleted after the review.
- **Phone first.** Short lines, numbered steps, no tables, no code blocks in the script part; at
  most ~10 steps, ordered as they happen on the road. Each step: when, what to look at, what is
  good, what to note.
- **Every step names its moment:** **parked** (before leaving), **passenger** (read or done while
  moving), **after parking**, **logs** (the agent, at the desk). A drive alone keeps only parked,
  after parking and logs.
- **Safety wins.** No step asks the driver to look at or touch the phone while moving; a step that
  needs it is passenger-only, or is moved to a stop or to the logs.
- **Private by default** (P5). No coordinates, addresses, place or street names, plates or real
  traces in these files: "Home", "school", "the long light", "the tunnel" are enough. Times are the
  owner's own and may stay. Databases stay in `drive-data/` and are never committed.
- **Evidence over memory.** A result says which log line or number shows it (`autoFinished
  walkedAway`, `points=1180 in 20 min`); "seems fine" is not a result. A device behaviour is
  "passed" only after it was seen on the iPhone.
- **Tools at the review:** `task pull-db` (or `pull-all` with several iPhones), `task drives`,
  `task events`, `task replay`, Developer → Tracking status on the phone if needed. They print no
  coordinates.
- **Close the loop:** tick the matching items in `plans/` with the date, and say which open checks
  are still not run.

## Files

- [`_template.md`](_template.md): the script and results skeleton.
