# CARODO Handbook

The workshop: where the product is thought through before it ships. Vision, roadmap, implementation
plans, drafts of features with no code yet, mockups and the brand source live here.

**The source of truth is in each repository, not here.** What the iOS app does, how it is built
and why (specs, architecture, sync, API contract, design system, ADRs) is in
[`carodo-ios/docs/`](../carodo-ios/docs/README.md); the backend keeps its own in
[`carodo-app/docs/`](../carodo-app/docs/README.md) (architecture, cost rules, storage, metrics, ADRs).
This folder may link into them; they never link here. Rules for changing code: each repository's
`AGENTS.md`.

| Read | For |
|------|-----|
| [`product/vision.md`](product/vision.md) | What CARODO is: product loop, positioning, principles, brand |
| [`product/roadmap.md`](product/roadmap.md) | Phases of the iOS and backend tracks, built in parallel |
| [`plans/`](plans/) | Implementation plans and their status: [`ios.md`](plans/ios.md) (phases, slices A–D), [`gps-engine.md`](plans/gps-engine.md) + [`gps-perf-audit.md`](plans/gps-perf-audit.md) (tracking field test and Always/Map perf findings), [`ios-backend-integration.md`](plans/ios-backend-integration.md) (identity: App Attest, accounts, sessions), [`backend.md`](plans/backend.md) (backend slices, status, open decisions) |
| [`field-tests/`](field-tests/README.md) | Test drives: the script the owner reads on the phone before a drive, and the agent's review of its logs after |
| [`drafts/`](drafts/README.md) | Specs and designs for features with no code yet |
| [`design/mockups/`](design/mockups/README.md) | The owner's visual explorations: ideas, not specs |
| [`design/brand/brand.md`](design/brand/brand.md) | Logo mark, wordmark, lockup, app-icon sources; how to edit and regenerate them |
| [`design/vehicle-art/`](design/vehicle-art/README.md) | Archived vector explorations (rounded and detailed v4); current iOS vehicle identity uses SF Symbols |
| [`design/passport-stamp/`](design/passport-stamp/README.md) | Passport button and stamp shapes from the mark; an idea for badges, not a decision |
| [`references/`](references/README.md) | What we learn from others: open-source repos (with licence rules and map options) and notes on apps we study |
| [`AGENT_WORKFLOW.md`](AGENT_WORKFLOW.md) | How to brief an agent and what its completion report contains |

## Rules

- **Ship means land.** When a slice ships, its result (spec, ADR, contract change) lands in the
  repository's `docs/` in the same change. The draft here is then deleted, or reduced to a line
  pointing at where it landed.
- **A draft moves with its first slice.** A feature with no code is specified in `drafts/`; the
  change that adds its first code moves the spec to `carodo-ios/docs/specs/`.
- **Plans and status live here** (`plans/`), so the repository docs describe only what is built.
- **Generated assets are copied, not linked.** The brand source generates the app icon, launch
  assets and `CarodoMarkGeometry.swift`; the copies in the app are the shipped truth.
- New file names are lowercase kebab-case (`README.md` and `AGENT_WORKFLOW.md` keep their names).
