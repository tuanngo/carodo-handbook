# Questions for Apple

Status: **collected, not sent** (2026-11-16). Every question Carodo needs Apple to answer, in one
place, with the channel each goes to and a draft ready to send. The owner sends them; an answer is
recorded here with its date and link, and the entry it unblocks (TD-2, TD-41) is updated.

The questions come from [apple-maps-data-review.md](apple-maps-data-review.md) §2 (TD-2) and
[cinematic-replay.md](cinematic-replay.md) (Apple's terms on an exported map, TD-41). A new question
for Apple is added here, not in the plan that raised it.

## 1. Will asking change anything?

Honestly: a binding "yes" is unlikely, but asking is cheap and some of it can help everyone.

- **A written permission for Carodo alone** (§2.5 "expressly permitted in writing by Apple"): Apple
  rarely gives one. Developer Technical Support (DTS) answers technical questions and usually
  declines to interpret the license ("consult your legal counsel"). Program Support may forward a
  question to legal; an answer can take weeks or never come. **Do not plan around it.** Carodo
  already works without it (phase 1 and 1b keep Apple's data 7 days at most, identifiers for good).
- **A public answer on the Developer Forums**: likely to get a reply, sometimes from a MapKit
  engineer or DTS. Not a legal permission, but it is evidence of Apple's own reading, it is
  searchable, and it helps every developer with the same question. This is where "thousands of
  developers have this problem" pays off: one good thread is cited by all.
- **A documentation fix through Feedback Assistant**: the strongest lever. §2.5 also permits what
  the **MapKit Documentation** permits. If Apple writes in the docs what WWDC25 session 204 already
  says ("identifiers can be persisted"), or how long a geocoding result may be cached, that becomes
  permission for every app, without a private letter. Feedback reports with a clear, general ask
  ("please state in the documentation …") are the kind Apple acts on, slowly.
- **App Review**: decides in practice for a submitted build. It is not a channel to ask in advance,
  but a rejection or approval of a TestFlight external build is also an answer (TD-41's export).

So: send all three (forums post, feedback reports, one Program Support message), expect the forums
and the feedback reports to matter most, and keep shipping on the conservative design meanwhile.

## 2. The questions

Grouped by what they unblock. "Today" is what Carodo does while there is no answer.

### A. Storing and caching Map Data (TD-2)

| # | Question | Why it matters | Today |
|---|---|---|---|
| A1 | Does WWDC25 session 204's "Identifiers can be persisted and shared" count as permission under §2.5 to store `MKMapItem.Identifier` values permanently (on the device and in the user's iCloud)? Could the MapKit documentation say so? | Places and fill-ups keep only the identifier for good | Stored (phase 1b); review question 2 |
| A2 | Is a reverse-geocoding result from `CLGeocoder` (Core Location) "Map Data provided through the Apple Maps Service"? | Decides whether the address cache falls under §2.5 at all | Treated as Map Data: 7 days at most |
| A3 | What does "temporary and limited" mean in practice: is 7 days, in `Library/Caches` (not backed up, cleared by the system), acceptable? Is there a maximum? | The lifetime of both caches | 7 days (owner, 2026-11-16) |
| A4 | When the user picks a POI from a list and confirms or edits its name in their own app data (a saved place, a fuel station), is that name still Map Data, or the user's own content? | Whether a confirmed name may be stored and synced | Stored only when typed or confirmed in an editor (D1); a bare pick keeps the identifier |
| A5 | Is a coarse administrative name derived from a result (a province, a ward, an ISO 3166-2 code) still Map Data when stored as the app's own label? | A lifetime "provinces driven" on the Passport | Not stored; the Passport shows none (TD-40, phase 2 uses OpenStreetMap) |
| A6 | Does §2.4 ("display the corresponding map with the address result") apply to a place name in a list or a title on a screen with no map? | Journey titles in the list, the fuel history | Shown without a map (open) |

### B. Map imagery leaving the app (TD-41)

| # | Question | Why it matters | Today |
|---|---|---|---|
| B1 | May a user export a video or an image of an Apple map (MapKit view or `MKMapSnapshotter`) showing their own recorded route, with the Apple Maps logo and Legal link in frame, and share it on social networks? | The replay video and the share card | Development builds only |
| B2 | If yes, are there conditions (the logo's size and place, a Legal notice burned into the image, a length limit)? | How the export must look | Logo and Legal kept in frame |

Not for Apple: **O1**, checking that the ADPLA accepted in the developer account matches the public
text read on 2026-11-09 and 2026-11-16. The owner does it in the account (TD-2).

## 3. Channels and drafts

Write each one in English, generic (no user data, no coordinates), and naming the clauses.

### 3.1 Apple Developer Forums (public; tags: MapKit, Core Location)

Two threads, so each can be answered and found alone.

> **Title:** Persisting MKMapItem.Identifier and caching geocoding results — what does ADPLA Attachment 6 §2.5 allow?
>
> Attachment 6 §2.5 of the Apple Developer Program License Agreement says Map Data may not be cached
> or stored "other than on a temporary and limited basis", unless permitted in writing or in the
> MapKit Documentation. WWDC25 session 204 ("Go further with MapKit") says place identifiers "remain
> valid over time" and "can be persisted and shared".
>
> 1. May an app store `MKMapItem.Identifier` values permanently (on device and in the user's iCloud
>    private database), and resolve the name with `MKMapItemRequest` when shown?
> 2. Is a `CLGeocoder` / `MKReverseGeocodingRequest` result Map Data under §2.5, and is caching it for
>    up to 7 days in the app's Caches directory "temporary and limited"?
> 3. When a user picks a point of interest and confirms or edits its name as their own (a saved
>    place), is that name still Map Data?
>
> Could the MapKit documentation state these rules? Many apps that keep a history of places face the
> same question.

> **Title:** Exporting a video or image of an Apple map with the user's own route (ADPLA Attachment 6 §2.3)
>
> Our app lets a user export a short video (or an image via `MKMapSnapshotter`) of their own recorded
> route drawn over an Apple map, with the Apple Maps logo and Legal link kept in frame, to share on
> social networks. §2.3 forbids publicly displaying Map Data unless expressly permitted, and §3.3.3(F)
> mentions overlaying a route the developer created on an Apple map. Is such a user export permitted,
> and under which conditions?

### 3.2 Feedback Assistant (one report each, category: Developer Documentation → MapKit)

- **FB-1:** "Please state in the MapKit documentation whether `MKMapItem.Identifier` may be stored
  permanently, as WWDC25 session 204 says, so it counts under ADPLA Attachment 6 §2.5."
- **FB-2:** "Please state how long geocoding results (`CLGeocoder`, `MKReverseGeocodingRequest`) may
  be cached under §2.5 ('temporary and limited'), and whether Core Location geocoding is Map Data."
- **FB-3:** "Please document whether exporting `MKMapSnapshotter` images or recorded map video with
  the logo and Legal link is permitted under §2.3."

### 3.3 Apple Developer Program Support (developer.apple.com/contact, "Program Membership" or legal)

One message holding A1–A6 and B1–B2 as a numbered list, asking for a written answer or a referral
to the right contact. Expect "consult your counsel"; send it anyway: a written yes is the only
answer that counts as §2.5's "permitted in writing".

## 4. Answers

| Date | Channel | Questions | Answer (quoted, with link) | What it changes |
|---|---|---|---|---|
| — | — | — | Not sent yet | — |
