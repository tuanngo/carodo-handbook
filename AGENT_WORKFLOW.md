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

**Language.** Every written document is in English: plans, drafts, audits, reports, ADRs and each
repo's `docs/` alike, since a plan's result lands in `docs/`. The conversation with the owner may be
in Vietnamese; a document is never. Vietnamese appears in a document only as app copy beside its
English (`"Stopped 4 min" / "Dừng 4 phút"`), as a quoted model output, or as a phrase the owner types
(`field-tests/README.md`).

## Recommended loop

1. **Frame**: one outcome, acceptance criteria, non-goals and constraints (the brief below).
2. **Spec**: the behaviour is in a spec marked Ready, in `carodo-ios/docs/specs/` or, for a feature
   with no code yet, in `drafts/`. Open questions are asked and recorded there, not in chat.
3. **Design**: a screen gets a mockup in `design/mockups/` before code ("To draw" lists what is
   missing, in the order a new person meets the screens). The spec wins over the mockup.
4. **Plan**: audit first, then propose (below, Plan before code); no code until the owner
   approves it.
5. **Slice**: one vertical slice that can be run or reviewed (e.g. the vehicle card, then the
   Start panel, then the first saved drive).
6. **Run**: build and test on the narrowest target; location, background and battery behaviour
   only on a physical iPhone (`carodo-ios/docs/operations/device-testing.md`, Daily check).
7. **Review**: the diff, permissions, schema, privacy, battery and UX, against the checklist below.
8. **Record**: the result lands in the repo's `docs/` (spec, ADR, contract) in the same change;
   `plans/` status and `plans/backlog.md` here; what is left open goes in
   [`plans/technical-debt.md`](plans/technical-debt.md) (debt, limitation or pending validation).
9. **Commit**: one finished outcome per commit, only your own paths, lowercase conventional
   messages, no AI attribution. The agent commits by itself once the work is proven (checks pass,
   screenshots for a change on screen); UI still being polished, a matter of taste or an unproven
   device behaviour waits for the owner's review. Push only when asked. The full rules: the repo's
   `AGENTS.md` (Git).

## Plan before code

1. **Audit what is there**: the source, the data flow, the schema, the tests and the docs the
   change touches. Name every file and type you read; never assume the code matches a plan or a
   doc (code and ADRs win, AGENTS.md "Docs disagree?").
2. **Keep three things apart** in the plan: what the code does today (with its file), what you
   propose, and what you assume but have not checked.
3. **The plan states** scope, non-goals, dependencies, acceptance criteria, the files to change and
   why, the tests, and the decisions the owner must make (each with a recommendation).
4. **No code before approval.** Exception: a small change the owner asked for directly that needs
   no architecture, schema, contract or product decision.
5. **After approval, stay inside it.** A finding that needs more (a schema, a contract, a new
   service, another feature's files) stops the work and goes to the owner as a question.

## While building

- **Before editing a file**: `git status` and `git log` on it. Changed and uncommitted by someone
  else: add to it, never overwrite; being edited right now: ask (Working in parallel, below).
- **Reuse by meaning** (the repo's AGENTS.md, "Reuse before adding"): extend the one algorithm that
  answers the same question; keep apart two that answer different ones, and say which and why.
  No protocol, service or framework for a single use.
- **Tests on both sides** of every threshold, plus the edge cases (empty, one point, gaps, trim,
  joined parts) and a regression test for what the change must not move.
- **Real data where it can speak**: replay the pulled drives read-only (`task replay`, the
  `DriveDataReplayTests` replays, `.carodo` backups). They are development test data: read them in
  full, plot them, look at single stops and fixes; never commit them or send them out (the rules:
  `carodo-ios/AGENTS.md`, Development data). Synthetic tests prove the code; they never count as
  real-world validation. A result that differs
  from a known baseline is explained, never tuned away.
- **A bug found on the way**: fix it inside the approved scope, add the test that would have caught
  it, and give its root cause in the report. Outside the scope: ask first.
- **Checks after the last change**: run lint, the build (warnings) and the tests again after the
  final edit, and report that run; never quote an earlier one. A temporary debug or seed step is
  removed before the report and said so.
- **Stop at the slice.** The next phase is proposed, never started.

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
Existing behaviour (files read):
Owner decisions needed:
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
updated, and the strings added (English and Vietnamese, for the owner to review). Then, each in its
own line:

- **Behaviour changed**: what a person sees or the data does differently; "none" said outright.
- **Test evidence**: the run after the last change (counts, failures, warnings, lint).
- **Real-data verification**: what was replayed or tried on a device, with its figures; or "none".
- **Bugs found on the way**: each with its root cause and the test now guarding it.
- **Left open**: technical debt, known limitations and pending validations, each also entered in
  [`plans/technical-debt.md`](plans/technical-debt.md) with its ID.

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
