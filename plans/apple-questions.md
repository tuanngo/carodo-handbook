# Questions for Apple

Status: **researched, not sent** (2026-11-16). Every question Carodo needs Apple to answer, in one
place: what Apple's own documentation and forums already say (read first, §1), what is left to ask
(§3), the channel for each and a draft ready to send (§4). The owner sends them; an answer is
recorded in §5 with its date and link, and the entry it unblocks (TD-2, TD-41) is updated.

The questions come from [apple-maps-data-review.md](apple-maps-data-review.md) §2 (TD-2) and
[cinematic-replay.md](cinematic-replay.md) (Apple's terms on an exported map, TD-41). A new question
for Apple is added here, not in the plan that raised it.

## 1. What Apple already says (research, 2026-11-16)

Read on developer.apple.com (documentation in its Markdown form, forums) on 2026-11-16.

**Identifiers may be persisted: documented.**
- `MKMapItem.identifier` (iOS 18.0+), the symbol's own page: *"An identifier uniquely identifies a
  place, such as a business or a landmark. You can persist an identifier and use it later to recall
  information about place."* ([doc](https://developer.apple.com/documentation/mapkit/mkmapitem/identifier-swift.property))
- Apple's sample code *Interacting with nearby points of interest*, section "Persist and retrieve
  map items": the app stores the places a person looked at **as identifiers** in a SwiftData model
  named `VisitedPlace`, across launches, and turns them back into map items with `MKMapItemRequest`
  ([doc](https://developer.apple.com/documentation/mapkit/interacting-with-nearby-points-of-interest)).
  It stores no name. That is Carodo's phase 1b design.
- A DTS engineer quoted the same sentence on the forums, June 2025
  ([thread 790983](https://developer.apple.com/forums/thread/790983)).
- ADPLA Attachment 6 §2.5 allows storing what is permitted "in the MapKit … Documentation". So the
  review's **question 2 is answered by the documentation**: `places.poi_id` and
  `fuel_logs.station_poi_id` kept for good are permitted. Recorded in the review (§2) and TD-2.

**The license is not interpreted on the forums.**
- A developer asked whether names, ids and coordinates from Apple Maps may be stored permanently in
  a user's library; nine months later Apple staff replied only: *"Please review the Apple Developer
  Program License Agreement … If you have any questions about how to interpret this Agreement,
  please consult your legal counsel."* ([thread 708672](https://developer.apple.com/forums/thread/708672), March 2023).
- The same question about storing geocoded coordinates got no Apple reply
  ([thread 114220](https://developer.apple.com/forums/thread/114220), 2019).
- So a forums post that asks "may I store X under §2.5?" will get that answer. A post that asks
  for **documentation** or a **technical fact** can be answered. §4 is written that way.

**Geocoding: the documentation sets usage rules, not a storage limit.** The `CLGeocoder` overview
([doc](https://developer.apple.com/documentation/corelocation/clgeocoder)), "Tips for Using a
Geocoder Object":
- *"Send at most one geocoding request for any one user action."*
- *"If the user performs multiple actions that involve geocoding the same location, reuse the
  results from the initial geocoding request instead of starting individual requests for each
  action."* (reuse is encouraged; how long is not said)
- *"In a typical situation, you should not send more than one geocoding request per minute"* (for a
  moving user's own location).
- *"Do not start a geocoding request at a time when the user will not see the results immediately.
  For example, do not start a request if your application is inactive or in the background."*
- No page read says how long a result may be kept; `MKReverseGeocodingRequest` (iOS 26) says
  nothing either. Questions A2 and A3 stay open.
- **A finding for Carodo, not a question:** after a drive ends, `DriveFlow.confirmFinished` runs
  `enrichJourneys` (names the ends, `PlaceNameCache.request`; place detection's searches). An Auto
  Mode drive can end with the app in the background, so lookups can start then, against the last
  rule. Recorded as TD-43.

**Apple's own app, for the framing.** Maps' *Visited Places* (iOS 26) keeps the places a person has
been, on the device and end-to-end encrypted across their devices, for 3 months, a year or forever
([Apple Support](https://support.apple.com/guide/personal-safety/ipsae6d4500b/web)). Apple's terms
for its own app do not bind Carodo, but it shows the use Carodo serves (one person's own history,
never shared) is one Apple builds itself. The drafts describe Carodo that way: personal, private,
on the person's devices and their own iCloud only.

## 2. Will asking change anything?

- **Documentation (Feedback Assistant):** the strongest lever, and the one that helps every
  developer. §2.5 permits what the MapKit documentation permits; the identifier sentence above is
  exactly that kind of permission. Asking for the same for geocoding results is a concrete,
  general ask.
- **Developer Forums:** good for technical facts (error codes, identifier lifetime) and to make a
  documentation gap visible; never for a reading of the license.
- **Program Support / legal:** the only route to a written permission. Expect "consult your counsel"
  or silence. Send it once, do not wait for it.
- **App Review:** decides a submitted build; a TestFlight external review of the export (TD-41) is
  also an answer.

Carodo keeps shipping on the conservative design meanwhile (identifiers for good, Apple's names 7
days, no Apple map leaving the app until B1 is settled).

## 3. Questions still open

### A. Storing and caching Map Data (TD-2)

| # | Question | Status | Today |
|---|---|---|---|
| A1 | May `MKMapItem.Identifier` be stored permanently? | **Answered by the documentation** (§1). Not asked | Stored (phase 1b) |
| A2 | Is a `CLGeocoder` / `MKReverseGeocodingRequest` result "Map Data" under Attachment 6? | Open | Treated as Map Data |
| A3 | How long may a geocoding result be reused ("temporary and limited")? Is 7 days in `Library/Caches` acceptable? | Open; the docs encourage reuse without a limit | 7 days |
| A4 | When a person confirms or edits a POI's name as their own (a saved place, a station), is it still Map Data? | Open | Stored only when typed or confirmed (D1) |
| A5 | Is a province or ward name, or an ISO 3166-2 code, derived from a result still Map Data when kept as the app's own label? | Open | Not kept (TD-40; phase 2, OpenStreetMap) |
| A6 | Does §2.4 apply to a place name in a list or a title on a screen with no map? | Open | Shown without a map |

### B. Map imagery leaving the app (TD-41)

| # | Question | Status | Today |
|---|---|---|---|
| B1 | May a person export a video or an image of an Apple map (MapKit view or `MKMapSnapshotter`) with their own recorded route, the Apple Maps logo and Legal in frame, and post it on social networks? | Open | Development builds only |
| B2 | If yes, under which conditions (logo size and place, Legal notice in the image, length)? | Open | Logo and Legal kept in frame |

Not for Apple: **O1**, checking that the ADPLA accepted in the developer account matches the text
read (TD-2). The owner does it in the account.

## 4. Channels and drafts

English, no user data, no coordinates. Each opens with the same two lines of context:

> Carodo is a personal drive journal for iPhone: one person records their own drives and sees them
> again. Everything stays on the person's device and in their own iCloud private database; nothing
> is shared with other users or sent to our servers.

### 4.1 Feedback Assistant (Developer Documentation → MapKit / Core Location), one report each

- **FB-1 (A2, A3):** "The `MKMapItem.identifier` page says an identifier can be persisted. Please
  document the same for geocoding results (`CLGeocoder`, `MKReverseGeocodingRequest`): may an app
  reuse a result it received, and for how long, for example to show a place name in a person's own
  history? The `CLGeocoder` overview asks apps to reuse results but does not say how long."
- **FB-2 (A4):** "Please document whether a place name a person picks from MapKit results and then
  confirms or edits as their own label (for a saved place in their own history) may be kept with
  their data, as an identifier may."
- **FB-3 (B1, B2):** "Please document whether an app may let a person export an image
  (`MKMapSnapshotter`) or a video of an Apple map showing their own recorded route, with the Apple
  Maps logo and Legal link in frame, to share it, and any conditions."

### 4.2 Developer Forums (tags: MapKit, Core Location)

Ask for documentation and facts, never for a reading of the license.

> **Title:** How long can an app reuse a reverse-geocoding result? (documentation request)
>
> [context lines]
>
> We name the start and end of each drive with reverse geocoding (`CLGeocoder`, and
> `MKReverseGeocodingRequest` on iOS 26). The `CLGeocoder` overview asks apps to "reuse the results
> from the initial geocoding request" rather than ask again, and `MKMapItem.identifier` says an
> identifier "can be persisted". Is there documentation on how long a reverse-geocoding result may
> be reused, as there is for identifiers? We keep results 7 days in the Caches directory today and
> filed FB-xxxx asking for it to be documented.

> **Title:** Exporting an image or video of an Apple map with the user's own route (documentation request)
>
> [context lines]
>
> A person can export a short video or an `MKMapSnapshotter` image of their own drive on an Apple
> map, with the Apple Maps logo and Legal link in frame, to share it. Is there documentation or
> Human Interface Guidelines guidance on exporting map imagery, and on how the logo and Legal must
> appear? Filed as FB-xxxx.

### 4.3 Apple Developer Program Support (developer.apple.com/contact)

One message: the context lines, then A2–A6 and B1–B2 as a numbered list, each with what Carodo does
today, asking for a written answer or a referral to the right contact (MapKit or legal). Expect
"consult your counsel"; a written yes is the only answer that counts as §2.5's "permitted in
writing".

## 5. Answers

| Date | Channel | Questions | Answer (quoted, with link) | What it changes |
|---|---|---|---|---|
| 2026-11-16 | Documentation (`MKMapItem.identifier`; sample *Interacting with nearby points of interest*) | A1 | "You can persist an identifier and use it later to recall information about place." | Identifiers kept for good are permitted (§2.5, MapKit Documentation); review question 2 closed |
