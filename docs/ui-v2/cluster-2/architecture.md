# CreditLens UI v2 — Cluster 2 architecture handoff

Status: **experimental foundation only**  
Feature flag: `UI_V2_ENABLED` (default: off)  
Component: `V2StatusCard`  
Contract version: `1.0`  
Component version: `0.1.0`

## Scope boundary

Cluster 2 establishes a React + TypeScript build and a typed Streamlit Components v2 bridge. It does not migrate any of the eight pages, change navigation, alter the Overview page, or move business logic into the browser.

With the flag off, `app.py` calls the legacy app exactly as before. With the flag on, one experimental status card is mounted before the unchanged legacy app. A build, registration, serialization, contract or render failure is caught at this boundary; the user receives a generic notice and the legacy app still runs.

## Data flow

```text
Python source of truth
  → allowlisted V2StatusCardViewModel
  → JSON-safe serialization
  → Streamlit Components v2 `data`
  → React V2StatusCard (presentation only)

React explicit action
  → typed `status_card.action` trigger
  → strict Python event validation
  → idempotent Python handler
  → session acknowledgement only
```

Hover, focus, responsive layout, reduced motion, loading display and the technical-detail disclosure remain entirely in React and never send an event to Python. Only the explicit `acknowledge` action crosses the bridge.

## Security contract

- The Python serializer builds the payload from a fixed allowlist; it never serializes session state.
- Keys named like API keys, authorization, credentials, passwords, secrets or tokens are rejected recursively on both sides.
- React never receives provider connections, environment variables, raw documents, prompts or domain models.
- Incoming events require exact schema, component, type, action and event-id fields; extra fields are rejected.
- Build assets are read from `frontend/dist`; no runtime CDN or remote code is used.
- Fallback messages do not include exception text.

## Runtime controls

PowerShell development examples:

```powershell
$env:UI_V2_ENABLED = "1"
python -m streamlit run app.py
```

Remove the environment variable or set it to any value other than `1`, `true`, `yes`, or `on` to retain the legacy-only path.

## Build and verification

From `frontend/`:

```text
pnpm install --frozen-lockfile
pnpm typecheck
pnpm test
pnpm build
```

The deterministic artifacts `frontend/dist/creditlens-v2.js` and `frontend/dist/creditlens-v2.css` are packaged with the app so deployment does not require a frontend build step. Cluster 2 does not deploy them.

Python checks:

```text
python -m unittest tests.test_ui_v2
python -m unittest evaluation.test_evaluation
$env:CREDITLENS_SELF_TEST = "1"; python credit_underwriting_colab.py
```

## Deferred

- Shell, Overview, compact navigation and responsive intake: **Deferred to Cluster 3**.
- Extraction, Analysis and Risk page migration: **Deferred to Cluster 4**.
- Summary, Method and Evaluation page migration: **Deferred to Cluster 5**.
- Settings, provider configuration and chat presentation: **Deferred to Cluster 6**.
- Full cross-browser, screen-reader and WCAG verification: **Deferred to Cluster 7**.
- Legacy presentation cleanup and any production rollout/deployment: **Deferred to Cluster 8**.

Additional inference calls introduced by this foundation: **0**.
