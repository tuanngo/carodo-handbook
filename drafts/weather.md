# Weather on a drive

Status: Draft (2026-11-03). **Storage and sync superseded by [`../plans/weather.md`](../plans/weather.md)** (2026-11-19): WeatherKit's terms forbid keeping Apple's figures beyond a limited cache, so only
Carodo's derived facts are stored and nothing is synced. The purpose and display below still hold.

## Purpose

A drive remembered with its weather: "Rain from 07:40, 24 °C", a wet commute next to a dry one. It
belongs to the journal (the detail page and the share card), never to tracking.

## Behaviour

- **Looked up after the drive is saved, never during it.** WeatherKit answers hourly weather for a
  past time, so nothing on the tracking path waits on a network (P1). Like place naming: once per
  drive after it is saved and at launch, newest first, a few at a time; offline is retried later.
- **What is asked:** the hour of the start at the start, the hour of the end at the end, and one
  point per full hour of driving in between, at where the drive was then. A one-hour drive costs
  two or three requests; a long trip one per hour. Each point keeps: condition (clear, cloudy, rain,
  thunderstorm, fog…), temperature, precipitation intensity and chance, wind speed, humidity, and
  day or night.
- **Shown:**
  - Journey detail, under the summary: a weather line "☂ Rain · 24 °C → 22 °C", and in the route
    timeline the condition at start and end; a drive that crossed a change shows "Rain from 08:15".
  - The summary sentence (ADR 0012) may say it when it matters ("in heavy rain").
  - Share card (opt-in like the rest): the condition symbol and temperature at the start.
  - Journeys filter token later: "Rain".
- **Units:** temperature follows the region (°C / °F) through the same Units setting; stored in
  °C (SI-like convention: Celsius at rest, converted at presentation).
- **Never:** live weather while driving, alerts, forecasts. Carodo is a journal.

## Data and privacy

- A new local table (schema, P6): `trip_weather` (`trip_id` → `trips` ON DELETE CASCADE, `at`,
  `cell` (the rounded point, like `geocoded_cells`), `condition`, `temperature_c`,
  `precipitation_mm_h`, `precipitation_chance`, `wind_mps`, `humidity`, `is_daylight`,
  `looked_up_at`) and `trips.weather_looked_up_at`.
- **What leaves the phone:** a coordinate rounded to about 1 km and an hour, to Apple's weather
  service (WeatherKit), the same kind of request as the reverse geocoding that names places. Never
  to the Carodo backend; never a route; nothing in logs (P5). Apple's attribution ("Weather" with
  the legal link) is shown where weather appears, as WeatherKit requires.
- Backed up to the person's iCloud with the trip; a shared drive may carry its start condition and
  temperature, never the points.

## Cost

WeatherKit includes 500,000 calls a month with the paid membership; at two to three calls a drive
that is far beyond a solo app's needs. Calls are cached per cell and hour, so a joined or
re-derived drive asks nothing new.

## Open questions (for the owner)

1. The paid Apple Developer account (also needed for iCloud backup, push and TestFlight).
2. Show weather on the share card by default, or only when the person turns it on?
3. The `trip_weather` table as above (P6)?

## Acceptance

- A drive saved offline gets its weather later, once; its figures and replay never wait for it.
- A one-hour drive makes at most three requests; reopening the journey makes none.
- No coordinate in the log; the request's point is rounded to its cell.
- Without WeatherKit (Personal Team, no network, a refused request) the page simply has no weather.
