# Places: one stop area, two detected places — merge

Status: direction approved by the owner 2026-11-13 (**solutions 1 + 2**), not built. Audit and a
plan with the touched files come before code (AGENT_WORKFLOW).

## The problem

A detected place is a circle of 25–100 m around where the car stood (carodo-ios
`PlaceDetection.place(for:)`, `Place.minimumDetectedRadiusM`). A point counts as a visit only
inside a live place's circle (`newPlaces(…among:)`); anything else makes a new place. A rest stop,
a fuel station with a big forecourt or a mall car park spans 200–300 m, so two drives parked at
its two ends make **two places**, even when Apple names the same point of interest for both (same
`poi_id`). Nothing merges them today: `StopPlaceResolver.merged` only dedups Apple's answers inside
one search, and journey joins are about drives, not places.

L4 (versioned sweeps, carodo-ios `f218b10`) lets a new detection rule reach past journeys, but a
re-run only avoids making duplicates; it never merges or removes a place already made.

## Direction (owner, 2026-11-13)

1. **Merge by hand** in Places: pick two places → one. The kept place's circle grows to cover
   both (bounded by the region's 1 km maximum); the other is deleted. Visits are derived when
   read (never stored), so they follow the new circle at once. Which one is kept: a saved place
   over a detected one, then the one with a name/POI, then the older.
2. **Suggest a merge**: two live detected places with the same `poi_id` (or the same normalized
   name) within ~500 m (threshold to tune) get a card "Is this one place?" (Places screen, like
   the role suggestions); Merge does (1), Not the same dismisses the pair for good.

Not chosen: (3) merging automatically when Apple names an existing place's POI nearby — two
stations of one chain a few hundred metres apart would be merged wrongly.

## Open for the plan

- Schema: the dismissed pairs (a small table, or a column) — a P6 change, owner approval.
- iCloud: a merge is a delete plus an edit; the other device must reach the same result
  (sync rule "a change from another device does what the same local change does").
- What the merged circle may not do: swallow a private place's area, or grow past 1 km.
- Copy (English, Vietnamese) for the card and the merge action; VoiceOver.
- Tests: the suggestion on synthetic places (same POI at 499 m / 501 m, a dismissed pair), the
  merge keeping visits of both, sync of a merge between two in-memory databases.
