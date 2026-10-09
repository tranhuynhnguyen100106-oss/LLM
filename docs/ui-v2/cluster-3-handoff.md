# CreditLens UI v2 — Cluster 3 handoff

Date: 2026-10-09  
Scope: App Shell + Overview only  
Feature flag: `UI_V2_ENABLED`  
Deployment: not performed

## Scope boundary

Cluster 3 implements the shared v2 shell and the Overview reference page on top of the Cluster 2 bridge. Pages 2–8 retain their current Streamlit content and business behavior; only the flag-on shell navigation surrounds them. The native Streamlit uploader continues to own file selection, bytes, validation and the existing extraction pipeline.

No credit formula, rule, threshold, Pydantic schema, extraction rule, cross-document validation, risk classification, provider/model behavior, chat, export, Evaluation ground truth or Gold Case was changed.

## Runtime modes

- `UI_V2_ENABLED` off: run the legacy application exactly as before.
- `UI_V2_ENABLED` on: render the React App Shell and Overview, with Python-derived state and native Streamlit upload controls.
- v2 registration/render failure: show a generic notice and run the legacy application without exposing exception details.

## UI architecture

```text
Python session/domain state
  -> allowlisted AppShell / DemoPanel / WorkflowPanel view models
  -> JSON-safe typed bridge
  -> React presentation

React explicit navigation or demo action
  -> typed event with unique event id
  -> strict Python validation and idempotency guard
  -> existing Python route/demo handler

Native Streamlit upload action
  -> callback lock (requested + processing)
  -> existing upload/extraction functions
  -> existing session result/documents
```

React does not receive raw files, file bytes, provider connections, API keys, prompts, settings objects, domain models, ground truth or the full session state. Hover, focus, drawer, disclosure and reduced-motion behavior stay client-side and do not trigger Python.

## Overview implementation

- Approved HUB and CreditLens asset, product lockup and deterministic-processing message.
- Eight-destination grouped navigation with active state, focus-visible styles and compact drawer behavior.
- Persistent case context derived only from the current Python result.
- Four approved Cluster 1 workflow stages: Intake, Compute, Cross-check and Human Review.
- Four matching process cards with complete/current/upcoming/warning/error presentation states.
- Native Streamlit individual-document and 3–4 PDF folder intake modes.
- Ten deterministic demo cases with typed selection/open events and no ground-truth disclosure.
- Empty, ready, processing, success, warning, error and disabled contracts.
- Primary upload action locked while requested/processing; demo open locks immediately in React.

## Responsive and accessibility verification

| Range | Verified behavior |
|---|---|
| Desktop >= 1440 | 256 px sidebar, main x=296, four-column workflow/cards, no horizontal overflow |
| Desktop 1280–1439 | 248 px sidebar, main x=280, no horizontal overflow |
| Laptop 1024–1279 | 72 px compact rail, main x=116, wrapped process cards |
| Tablet 768–1023 | Drawer navigation, 24 px main margin, two-column workflow/cards |
| Mobile < 768 | 64 px header, 16 px margin, full-width CTA, intake before workflow, single-column cards |

Light and Dark tokens were visually checked. Keyboard focus, active-page semantics, skip link, Escape-to-close/focus-return, non-color status labels, 44/48 px controls and `prefers-reduced-motion` are implemented. Comprehensive cross-browser/screen-reader certification remains Cluster 7.

## Verification summary

- Python UI contract tests: 17 passed.
- React component tests: 10 passed.
- TypeScript typecheck: passed.
- Production frontend build: passed.
- Existing Evaluation tests: 10 passed.
- Built-in CreditLens self-test: `SELF_TEST_PASS`.
- Live flag-on browser smoke: all eight navigation destinations reached with active state and no v2 fallback.
- Live deterministic CASE-03: Python status, field count and warnings rendered correctly.
- Browser console: no warnings or errors during Overview verification.
- Additional inference requests: 0.

## Deferred

- `Deferred to Cluster 4`: migrate Extraction, Credit Analysis and Risk content.
- `Deferred to Cluster 5`: migrate Summary, Methodology and Evaluation content.
- `Deferred to Cluster 6`: migrate Settings, provider configuration and chat presentation.
- `Deferred to Cluster 7`: comprehensive automated visual regression, cross-browser, screen-reader and WCAG audit.
- `Deferred to Cluster 8`: remove legacy presentation code and perform any approved production rollout.

