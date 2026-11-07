# CARODO — working with agents

How a task moves from an idea to a reviewed change. This file holds the process only: the rules
(invariants, conventions, done) live in each repository's `AGENTS.md`, which wins when the two
disagree (`carodo-ios/AGENTS.md`, `carodo-app/AGENTS.md`, the workspace `AGENTS.md`).

## Principle

Use an agent as an implementation partner, not as an autonomous product owner. The owner holds
product intent, scope, UX quality, architecture direction, secrets and release approval, and
approves every contract (P6: schema, API, permission, entitlement, dependency, cloud service). The
agent explores, proposes, implements bounded changes, tests and reports; it makes the Swift and
iOS calls itself and explains each in a line, because the owner is new to Swift
(`carodo-ios/AGENTS.md`, "Working with the owner").

## Recommended loop

1. **Frame**: one outcome, acceptance criteria, non-goals and constraints (the brief below).
2. **Spec**: the behaviour is in a spec marked Ready, in `carodo-ios/docs/specs/` or, for a feature
   with no code yet, in `drafts/`. Open questions are asked and recorded there, not in chat.
3. **Design**: a screen gets a mockup in `design/mockups/` before code ("To draw" lists what is
   missing, in the order a new person meets the screens). The spec wins over the mockup.
4. **Plan**: the agent inspects the repo and proposes a short plan; no code yet for cross-cutting
   work.
5. **Slice**: one vertical slice that can be run or reviewed (e.g. the vehicle card, then the
   Start panel, then the first saved drive).
6. **Run**: build and test on the narrowest target; location, background and battery behaviour
   only on a physical iPhone (`carodo-ios/docs/operations/device-testing.md`, Daily check).
7. **Review**: the diff, permissions, schema, privacy, battery and UX, against the checklist below.
8. **Record**: the result lands in the repo's `docs/` (spec, ADR, contract) in the same change;
   `plans/` status and `plans/backlog.md` here.
9. **Commit**: only when the owner asks; one logical change per commit, lowercase conventional
   messages, no AI attribution. Until the owner rebuilds the first commit, nothing is committed or
   pushed.

## Working in parallel

- Good parallel tasks: a SwiftUI screen on agreed view models; unit tests for pure logic; a spec or
  contract review. Never two agents inventing the same domain model, navigation or schema; one
  integration owner.
- **The owner edits too, often at the same time.** Before a bulk or generated edit, check what
  changed recently (`git status`, file times, other sessions); re-read a file that changed since you
  read it and add to it, never overwrite it; stop and ask when a file is being edited right now.
  Stage only your own paths.
- Simulators by UDID (`SIM_ID` in `carodo-ios/.env`), never "booted": another session may have one.

## Task brief template

```text
Outcome:
User story:
Spec (Ready?) and mockups:
Acceptance criteria:
Non-goals:
Relevant files/docs:
Constraints:
Validation commands/device checks:
Allowed scope:
Do not:
```

A worked example: [`plans/first-run.md`](plans/first-run.md).

## Agent completion report

The fields are the repository's "Report" rule (`carodo-ios/AGENTS.md`, Conventions): what changed
and why, files, exact commands and their results, device checks still required, risks and
assumptions, and every schema, API, permission or dependency change. Add the specs and docs
updated, and the strings added (English and Vietnamese, for the owner to review).

## CARODO review checklist

Tracking and data
- Does recording work with no network and no account, and is `carodo://trip/start` idempotent?
- Is GPS distance kept apart from the odometer, and are units SI at rest?
- Is time stored and sent in UTC and shown in local time (a drive in its own zone)?
- Are inaccurate, stale or implausible samples filtered; does a CarPlay disconnect leave the drive?
- Are background location and battery trade-offs explained to the person?

Privacy
- Is location history private by default; does a share hide its ends and every private region?
- Does anything public stay "how, never where": no route, map or place, at most an opt-in province
  and an abstract shape? Do raw samples stay off the backend?
- Do only App Attest-backed calls reach the API, and no coordinate reach a log or analytics?
- Are real coordinates, plates, tokens and signing assets out of Git?

App quality
- Is every string in a String Catalog, in English and Vietnamese?
- Light and Dark, the largest Dynamic Type, VoiceOver labels?
- No `!`, `try!`, `DispatchQueue`, `Task.detached` or `@unchecked Sendable`; each `try?` ignorable?
- Did a contract change (P6) get the owner's approval first?

## Definition of done

The repository's "Done means" (`carodo-ios/AGENTS.md`): the acceptance criteria are met, code is
formatted and `task lint` passes, `task warnings` prints none, tests are added or updated, `task build` and `task test` were run
and their results reported, the diff is reviewed, and device checks still required and known
limitations are listed. A generated project file or an agent's claim is not proof of a build.
