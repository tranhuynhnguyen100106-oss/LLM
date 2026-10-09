# CreditLens UI v2 — Prototype, handoff and approval plan

Status: **Cluster 1 handoff**  
Prototype type: static/local, deterministic, no backend and no provider call  
Reference: [`assets/overview-reference.html`](./assets/overview-reference.html)

## 1. What the reference is—and is not

The HTML reference demonstrates the proposed shell, information hierarchy, responsive order, Light/Dark semantic tokens and representative Overview states. Its controls change only local presentation state.

It is not application code, not a replacement for Streamlit, not a React migration, not a production route and not a source of domain truth. The visible case ID and values in its success state are explicitly labelled sample content. The prototype makes no network request.

## 2. Prototype controls

| Control | Options | Expected result | Network/inference impact |
|---|---|---|---:|
| Theme | Light, Dark | Swaps semantic token set and updates pressed state | 0 |
| UI state | Empty, Processing, Success, Warning, Error | Replaces the local state panel and workflow status | 0 |
| Upload mode | Tải từng tài liệu, Tải một thư mục | Switches between the exact current intake modes; selected local files never leave the browser | 0 |
| Navigation | Eight page labels | Demonstrates selected/focus state only; does not navigate away | 0 |
| Legal details | Collapsed/expanded | Reveals local approved-copy placeholder guidance | 0 |
| File/demo actions | Visual reference actions | Shows focus/disabled/pressed affordance only unless state control is used | 0 |

The standalone file includes no `fetch`, XHR, WebSocket, EventSource, external script, font or image URL. The logo is drawn as a local typographic brand lockup so the handoff remains portable; production implementation must use the approved repository asset.

The prototype-control bar is a fixed overlay outside `.cl-app` and can be collapsed. It is not part of any design frame; all coordinates in `04-overview-spec.md` are measured from the top-left of `.cl-app`, where the product header starts at y0.

## 3. Required review frames

| Frame pattern | Themes | Widths | States | Review focus |
|---|---|---|---|---|
| `CL/Overview/{Theme}/{Width}/Empty` | Light, Dark | 1440, 1280, 390 | Empty/default | Baseline hierarchy, desktop 8/4 split and intake-first mobile order |
| `CL/Overview/{Theme}/{Width}/Processing` | Light, Dark | 1440, 1280, 390 | Loading/processing | Progress, live status and duplicate-submit guard |
| `CL/Overview/{Theme}/{Width}/Success` | Light, Dark | 1440, 1280, 390 | Success | Context retention and valid next action |
| `CL/Overview/{Theme}/{Width}/Error` | Light, Dark | 1440, 1280, 390 | Error | Recovery and preserved inputs |
| `CL/Overview/{Theme}/{Width}/Warning` | Light, Dark | 1440, 390 | Warning | Local + summary warning |
| `CL/Overview/{Theme}/{Width}/ComponentStates` | Light, Dark | 1440, 390 | Disabled, connected, disconnected, selected, hover, focus-visible | Component differentiation, keyboard focus and non-color cues |

Hover, focus-visible, selected, disabled, connected and disconnected are component variants inside the frame library rather than separate full-page frames unless a visual issue requires one.

## 4. Handoff package map

| Artifact | Consumer | Use |
|---|---|---|
| `01-ui-audit.md` | Product/design/engineering/QA | Current-state evidence, IA and deferred findings |
| `02-design-tokens.md` | Design/engineering | Human-readable Light/Dark token contract |
| `design-tokens.json` | Engineering/design tooling | Machine-readable token seed; not yet imported at runtime |
| `03-component-library.md` | Design/engineering/QA | Component/state/accessibility contract |
| `04-overview-spec.md` | Design/engineering/QA | Exact Overview layout/content/behavior spec |
| `05-prototype-and-approval.md` | Product owner | Review gates and future acceptance |
| `assets/overview-reference.html` | Product/design/engineering | Local responsive visual reference |

## 5. Design-source organization

If the handoff is recreated in a design tool, use:

```text
00 Cover & decisions
01 Foundations
   Color / Light
   Color / Dark
   Typography
   Spacing & grid
   Radius, borders, shadows, motion
02 Components
   Shell & navigation
   Actions & fields
   Status & feedback
   Domain display
   Data & disclosure
03 Patterns
   Empty
   Processing
   Recovery
   Case context
04 Pages
   Overview / Light
   Overview / Dark
05 Accessibility & content
06 Handoff
```

Layer names use role and variant, for example `Button/Primary/Loading`, not appearance names such as `BlueButton`. Auto-layout/constraints must express the responsive behavior from the specification; manually positioned copies are not accepted as the only handoff.

## 6. Approval decisions before implementation

These decisions are intentionally held at the Cluster 1 checkpoint. No later-cluster implementation should infer them from the prototype.

| ID | Decision | Recommended baseline | Effect if changed |
|---|---|---|---|
| A01 | Primary typeface | Be Vietnam Pro + system fallback | Changes metrics and line wraps across every page |
| A02 | Primary visual tone | Institutional navy/crimson with restrained surfaces | Changes brand and component tokens |
| A03 | Theme set | Ship Light/Dark/System first; preserve legacy settings until separately approved | Determines theme migration scope |
| A04 | Navigation IA | Three groups containing the exact eight existing pages | Changes labels, discoverability and analytics mapping |
| A05 | Desktop shell | Full sidebar ≥1280; rail at 1024–1279 | Changes usable content width |
| A06 | Mobile priority | Intake before workflow explanation | Changes mobile DOM/content order |
| A07 | Repeated hero | Replace with compact global header + page header | Recovers vertical space on all routes |
| A08 | Case context | Persistent context bar using real session data | Requires adapter work in a future approved cluster |
| A09 | Workflow status | Derive from real session state; never hard-code current/next | Requires explicit state mapping |
| A10 | Native controls | Keep secure input, file uploader, large tables, download and chat native during migration | Reduces migration/security risk |
| A11 | Motion | 100/160/220 ms functional motion; 320 ms only for rare emphasis; reduced-motion zeroes nonessential transitions | Sets animation acceptance |
| A12 | Density | 44 px default controls, compact 36 px only on non-touch desktop | Affects tables and control-heavy pages |
| A13 | Page 7 label | Keep `Evaluation` until Vietnamese domain wording is approved | Avoids premature terminology change |
| A14 | Modal policy | No modal for navigation; only blocking confirmation/conflict/evidence focus | Prevents unnecessary interaction layers |

Approval can be recorded as `Approved`, `Approved with change`, or `Deferred` for each ID. A deferred decision keeps the current production behavior for that point.

## 7. Future implementation sequence—not executed in Cluster 1

1. Map runtime state to a documented read-only UI view model.
2. Implement tokens and foundations behind an isolated visual flag or approved branch strategy.
3. Implement components with accessibility tests and local stories/harnesses.
4. Implement Overview against the exact state matrix.
5. Verify all native-control boundaries and one-submit/one-request behavior.
6. Run visual, accessibility and deterministic regression checks.

This sequence is reference planning only. It does not authorize Cluster 2 or any runtime modification.

## 8. Acceptance gate for the future Overview implementation

### Visual

- Geometry matches the 1440, 1280 and 390 specifications within a 2 px tolerance for fixed dimensions and 4 px for text-flow-dependent height.
- Light/Dark surfaces and states use only approved semantic/component tokens.
- Logo aspect ratio and safe area match the approved repository asset.
- There is no page-level horizontal overflow at 320, 390, 768, 1024, 1280 and 1440 px.

### Behavior

- Empty, loading, processing, success, warning, error, disabled, connected, disconnected, selected, hover, focus and mobile states are reachable through deterministic test data or a local fixture.
- Visual-only interaction produces no API/provider/inference request.
- One explicit provider-backed submit, where applicable, cannot duplicate on rerender or rapid reactivation.
- Session state and next-step navigation remain consistent with the current Python source of truth.

### Accessibility

- Keyboard-only path, skip link, drawer focus trap/return, one H1, ordered stepper and live-region behavior pass manual review.
- Automated checks have no serious/critical WCAG 2.2 A/AA issue, followed by manual contrast, reflow, zoom and screen-reader review.
- Focus is visible in both themes and is not hidden by sticky regions.

### Regression and scope

- Current self-test and evaluation suite pass unchanged.
- Deterministic evaluation still reports zero LLM calls.
- No formulas, rules, thresholds, schemas, extraction, validation, ground truth, gold cases, providers, model selection or API-cost behavior changes.
- `design.md` remains a protected input unless the owner explicitly approves changing it.

## 9. Deferred by cluster

- **Deferred to Cluster 2:** implement runtime tokens, component scaffolding, view-model contracts, feature flag and legacy fallback only if Cluster 2 authorizes them.
- **Deferred to Cluster 3:** implement shell, Overview, compact mobile navigation, upload/processing composition and real workflow state.
- **Deferred to Cluster 4:** implement Extraction/Analysis/Risk components, including the nonfatal mixed-type table warning observed in current UI.
- **Deferred to Cluster 5:** implement Summary/Method/Evaluation hierarchy and responsive tables.
- **Deferred to Cluster 6:** settings/provider configuration implementation and theme migration decision.
- **Deferred to Cluster 7:** repair/replace stale UI harness selectors, comprehensive visual-regression matrix and evaluation-page QA.
- **Deferred to Cluster 8:** remove approved legacy presentation/assets and perform rollout or deployment only when explicitly authorized.

No deferred item is fixed by this Cluster 1 package.
