# CreditLens UI v2 — Cluster 8 stabilization and maintenance

Date: 2026-10-10 (Asia/Saigon)

Production URL: `https://creditlens-underwriting.streamlit.app/`

Business-logic changes: none

Additional inference calls from UI/runtime changes: 0

## Final architecture

`app.py` is the entry point. With `UI_V2_ENABLED=true`, it calls
`chay_ung_dung_streamlit_v2`; otherwise, or if the v2 renderer raises, it runs
the complete legacy Streamlit application. The fallback and flag remain because
they still provide immediate production rollback after the recent rollout.

Python remains the only domain source of truth. It owns document processing,
Pydantic models, normalization, formulas, thresholds, rules, risk/status,
Evaluation, providers, chat, exports, secrets and session state.
`creditlens_ui_v2.py` maps those values to allowlisted JSON-safe view models and
validates typed events. React renders presentation and browser-local interaction
only.

```text
Python domain/session state
  -> allowlisted serializers in creditlens_ui_v2.py
  -> Streamlit Components v2 bridge
  -> React components in frontend/src

React navigation/demo/Evaluation intent
  -> typed event + unique event_id
  -> strict Python validation + idempotency claim
  -> existing Python action

API key, chat content, files and export bytes
  -> native Streamlit controls only
  -> never serialized to React
```

The eight production routes are App Shell/Overview, Extraction, Credit Analysis,
Risk, Summary, Methodology, Evaluation and Settings. Design tokens and the
approved component contract remain in `docs/ui-v2/cluster-1/02-design-tokens.md`
and `03-component-library.md`; `frontend/src/styles.css` is the runtime token and
responsive implementation.

## Cluster 8 cleanup

### Removed — confirmed dead

- Cluster 2 experimental `V2StatusCard` React component and its component tests.
- Its Python-only view model, serializer, event, handler and experimental mount.
- Its TypeScript parser/event contract and 253 lines of component-only CSS.

The scaffold had no production route or caller. The component registration name
`creditlens_v2_status_card` is intentionally retained as an internal Streamlit
registry identity to avoid unnecessary session/component identity churn.

### Retained — required

- Full legacy application, `UI_V2_ENABLED`, exception fallback and flag-off path.
- Native upload, credential, chat, download and export controls.
- Shared domain/export/provider helpers in `credit_underwriting_colab.py`.
- All active brand assets used by page icon, App Shell, reports and watermark.

### Retained — uncertain

- `static/creditlens-icon.png`, `creditlens-logo.png` and
  `hub-logo-transparent.png` have no current runtime filename reference, but may
  be source brand assets. They remain under the rule `UNCERTAIN -> KEEP`.
- Legacy renderer/CSS stays because the feature flag is still the production
  rollback mechanism. Removing it would violate the no-rollback safety gate.

## Measured frontend audit

| Metric | Before | After |
|---|---:|---:|
| Modules transformed | 21 | 20 |
| JavaScript | 409.58 kB | 405.94 kB |
| JavaScript gzip | 95.86 kB | 95.24 kB |
| CSS | 42.63 kB | 38.30 kB |
| CSS gzip | 7.32 kB | 6.74 kB |
| Runtime dependencies | 3 | 3 |
| Frontend assets | 2 | 2 |

No runtime dependency is unused: React, React DOM and the Streamlit component
library are all direct imports. Dev dependencies are not shipped. Source maps
remain disabled. Code splitting was not added: the runtime is one bounded
component asset and the measured gain would not justify extra loading states or
deployment complexity. No remote font or image request is introduced; system
fallback stacks remain available.

The payload audit found allowlisted page-specific summaries only. Raw files,
full documents, session state, credentials and chat content are not sent to
React. The Evaluation payload is intentionally larger because the page renders
its field metrics, matrices, baselines and ten failure cases; removing those
would change the approved page contract.

The render audit found one parse and one React root mount per component render.
Local filters, disclosures, tabs, drawer, hover, focus and tooltips remain in the
browser. Memoization already exists where list filtering is material; no blind
memoization or lazy-loading layer was added.

## Rerun and event model

Allowed reruns are domain actions only:

- navigation selection;
- demo selection/open;
- completed upload processing;
- explicit optional AI explanation generation;
- explicit deterministic Evaluation run.

Summary/Evaluation downloads use `on_click="ignore"`. Hover, focus, drawer,
local filter, disclosure, tooltip, responsive state and animation do not cross
the bridge. Settings stays native where rerun semantics, credentials or chat
security require Python ownership.

## Contracts and security boundary

Additive view-model changes require matching Python dataclass/serializer,
TypeScript interface/parser, renderer use and tests. Every payload is recursively
checked for secret-shaped keys and serialized with finite JSON values. Do not
place API keys, authorization values, passwords, provider errors, raw prompts,
chat messages or raw documents in a React view model, browser storage or logs.

New events require an exact Python and TypeScript contract, a bounded payload,
an 8–96 character event id, an idempotency claim, and a test proving malformed,
extra and secret-shaped fields are rejected. Pure presentation interaction must
not become an event.

## Developer workflow

From `frontend/`:

```text
pnpm install --frozen-lockfile
pnpm typecheck
pnpm test
pnpm build
```

From the repository root:

```text
python -m unittest discover -v
PowerShell: $env:CREDITLENS_SELF_TEST='1'; python credit_underwriting_colab.py
PowerShell: $env:UI_V2_ENABLED='true'; python -m streamlit run app.py
```

The committed `frontend/dist/creditlens-v2.js` and `.css` are the production
artifacts; deployment does not build them at runtime.

## Maintenance guide

- Add a component in `frontend/src`, register its discriminator and parser in
  `contracts.ts`, then dispatch it in `index.tsx`.
- Add a view-model field first to the Python dataclass and allowlisted serializer,
  then to the TypeScript interface/parser, component and contract tests. Never
  pass a domain object or session state wholesale.
- Add an event only for an explicit domain action. Define it on both sides,
  validate exact keys, claim its event id once, and test request/rerun count.
- Keep business logic in `credit_underwriting_colab.py`, `evaluation/` and their
  existing typed models. React must not calculate credit metrics or status.
- Keep API keys and chat content in native Streamlit/Python only.
- Rebuild `frontend/dist` after every frontend change and commit source plus
  matching artifacts.
- Run Python regression, self-test, frontend typecheck/tests/build, deterministic
  Evaluation, export/security/chat gates and responsive production smoke before
  deployment.
- Deploy the tested commit to the existing `main` branch and existing Streamlit
  application. Confirm `UI_V2_ENABLED=true`, then smoke all eight routes. Roll
  back by disabling the flag if a production blocker appears.

## Final verification record

- Python regression/Evaluation/UI suite: 51/51 passed.
- Built-in self-test: passed.
- TypeScript: passed.
- Frontend component/contracts: 24/24 across 6 current test files passed.
- Production frontend build: passed; 20 modules; no source maps.
- Local eight-page smoke: passed at 375, 430, 768, 1280 and 1440 px with
  zero document/component overflow.
- Light, Dark and System themes: passed. Cluster 8 fixed one verified native
  secondary/upload-button contrast regression in Dark/System.
- Deterministic Evaluation: 36 cases, 12 scenarios, LLM calls 0; Evaluation JSON
  download event passed.
- Security scan: no API key sentinel, bearer value or source map in source/build.
- Chat request-count and export-content tests: passed.

The completion report records the deployed commit and final production smoke.
No real inference was used for UI, responsive, bundle, navigation, Evaluation or
export verification.
