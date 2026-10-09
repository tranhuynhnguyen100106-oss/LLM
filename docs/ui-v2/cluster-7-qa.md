# CreditLens UI v2 — Cluster 7 QA and rollout handoff

Date: 2026-10-10 (Asia/Saigon)  
Branch: `main`  
Feature flag: `UI_V2_ENABLED` (strict opt-in)  
Rollback: set `UI_V2_ENABLED` to a non-true value; the complete legacy app and component-failure fallback remain present.

## Scope and protected boundaries

Cluster 7 performed full QA, minimal bug fixes, production build verification and feature-flag rollout preparation for all eight pages. It did not redesign the product, remove the legacy UI/fallback, or change formulas, extraction, parsing, normalization, thresholds, Rule Engine, status logic, Gold Cases, Evaluation ground truth, provider/model behavior, chat semantics or export content.

`design.md` is user-owned, untracked and excluded from the deployment commit. Its SHA-256 remained:

`E285585DE1486ACEE4617AA59CC06B4FE28D66AE993D27C4629ADC159FF78BF7`

Additional real inference requests used by Cluster 7: **0**.

## Hard-gate results

| Gate | Result | Evidence |
|---|---:|---|
| Python app/regression suite | PASS | `python -m unittest discover -v`: 51/51 |
| Existing self-test | PASS | formulas, zero division, normalization, thresholds, four providers, Word/Excel/PDF |
| Frontend tests | PASS | Vitest: 27/27 across 7 files |
| TypeScript | PASS | `tsc --noEmit` |
| Production frontend build | PASS | Vite build, source maps disabled |
| Business parity | PASS | all 10 demo cases; values, confidence, metrics, thresholds, risks, severity, status and evidence |
| Evaluation | PASS | 36 synthetic cases, 12 scenarios, 0 LLM calls |
| API-key security | PASS | allowlisted props/events, native password control, redacted errors/logs, bundle scan |
| Chat request count | PASS | Send #1 = 1, Send #2 = 1, rerun/history/model change/empty prompt = 0 |
| Legacy fallback | PASS | flag-off and component-failure tests |
| Export | PASS | valid Word, Excel, PDF, Markdown, JSON, Evaluation JSON/CSV; browser download smoke |
| Critical responsive/accessibility | PASS | five viewports, Light/Dark, skip link, drawer Escape/focus recovery, tabs, labels and reduced motion |

## Evaluation snapshot

- Dataset: 36 synthetic/anonymized cases; 12 scenarios; 720 field checks.
- Extraction accuracy: 98.33% (708/720).
- Risk detection: precision 83.82%; recall 100.00%; F1 91.20%.
- Status classification: accuracy 97.22%; macro F1 92.65%.
- Grounding, structured/evidence variant: evidence coverage 96.88%; unsupported-claim rate 0.93%; factual consistency 94.44%.
- Baseline A and B, three-class confusion matrix and all 10 documented failure cases rendered successfully.
- Provider: `not-used`; model: `deterministic-saved-output`; LLM API calls: 0.

These values are synthetic evaluation evidence, not production-performance claims. No labels, thresholds or ground truth were changed.

## Eight-page QA matrix

| Page | Empty/default | Populated | Loading/error contract | Interaction and regression |
|---|---:|---:|---:|---:|
| 1. Tổng quan / Intake | PASS | PASS | PASS | upload controls, 10 demo cases, four-step workflow |
| 2. Trích xuất tài liệu | PASS | PASS | PASS | 4 documents, 20 fields, source/page/confidence/evidence filters |
| 3. Phân tích tín dụng | PASS | PASS | PASS | six Python metrics and exact threshold references |
| 4. Cảnh báo rủi ro | PASS | PASS | PASS | severity text, ordering and evidence disclosure |
| 5. Tóm tắt thẩm định | PASS | PASS | PASS | deterministic findings, Human Review and export actions |
| 6. Phương pháp & giới hạn | PASS | PASS | PASS | layers, six formulas, PDF capability table and limitations |
| 7. Evaluation | PASS | PASS | PASS | one idempotent run event, metrics, matrix, baselines, failures and exports |
| 8. Settings / API / Chat | PASS | PASS | PASS | four providers, masked key, eight thresholds, tabs and disabled/ready chat states |

Malformed or secret-shaped frontend events are rejected without crashing. The Python source of truth remains unchanged.

## Responsive and visual regression

All eight pages were navigated and measured at each target class:

| Requested viewport | Effective content viewport | Result |
|---|---:|---:|
| 375 × 812 | 341 px | PASS |
| 430 × 900 | 391 px | PASS |
| 768 × 1024 | 698 px | PASS |
| 1280 × 900 | 1164 px | PASS |
| 1600 × 1000 | 1454 px | PASS |

The browser chrome accounts for the requested/effective width difference. Final document width equalled scroll width at every target. The one real 375 px field-metadata overflow was fixed by stacking metadata below 480 px. A 3 px native icon intrinsic-width report did not create document overflow or clipping.

Light and Dark were applied through the existing Settings control and visually checked for canvas, surfaces, inputs, borders, CTA, state colors and logo. Representative WCAG contrast ratios:

- Light primary 16.79:1; muted 6.04:1; primary CTA 11.95:1.
- Dark primary 17.84:1; muted 9.35:1; primary CTA 10.43:1.
- Danger and warning state pairs: 6.84:1–11.80:1.

The session was restored to **Theo hệ thống** after the theme test.

## Accessibility and keyboard

- Skip link is keyboard reachable and now moves focus to `#cl-v2-main`.
- Compact navigation focuses the active route when opened; `Escape` closes it and returns focus to the menu button.
- Settings tabs respond to arrow-key navigation.
- Buttons, upload controls, selectboxes, password input, chat input and download controls expose accessible names.
- Loading/error/status/severity use semantic roles and text, not color alone.
- `focus-visible` rings and minimum 44/48 px control sizes are retained.
- `prefers-reduced-motion: reduce` disables transitions/animation in both component and native host layers.
- No keyboard trap was observed.

## Security review

- React contracts recursively reject `api_key`, authorization, password, secret, token and related fields.
- Credentials and chat content stay in Python/Streamlit native controls; they are absent from React props and generated bundle data.
- Browser DOM/console checks found no credential. Bundle scans found no provider key, bearer token, source map or test sentinel. Static prohibited-key names remain intentionally embedded as validation guards.
- Hostile HTML rendered through React remained text and did not create an image or script node.
- Every `unsafe_allow_html=True` use was reviewed: v2 occurrences are static CSS/anchors/fallback CSS; legacy dynamic title/metric values are escaped; uploaded case IDs are normalized to `[A-Za-z0-9_-]` before the remaining status-card HTML path.
- Provider errors shown to users are generic; test logs redact the synthetic key.

## Chat, API and rerun audit

- Mocked multi-turn chat retained context without duplicating history.
- One non-empty submit creates exactly one provider call.
- Rerun, history render, page change, model change and empty input create zero calls.
- Hover, focus, tooltip, disclosure, filtering and animation remain browser-local where implemented.
- Navigation, demo open and Evaluation run are the only typed domain events in their respective React surfaces; event IDs are idempotently claimed by Python.
- No real provider smoke request was required because the provider adapter and request-count tests passed.

## Export and performance

- Word, Excel and PDF signatures and content were validated; Markdown/JSON and Evaluation JSON/CSV serialization passed.
- Native v2 download buttons now use `on_click="ignore"`, preventing a download click from rerunning the script and invalidating the media URL. Browser smoke of Word, Excel and PDF produced no new download-source error.
- Final bundle: JavaScript 409.58 kB (95.86 kB gzip); CSS 42.63 kB (7.32 kB gzip).
- 21 modules transformed; build completed in 133 ms on the QA host.
- Source maps are disabled; there are no large debug dependencies in the shipped bundle.
- Component registration/assets are cached, and the UI does not perform duplicate business calculation or unnecessary inference.

## Bugs fixed within Cluster 7

1. Accessibility: skip link changed URL/scroll position but left keyboard focus behind. It now focuses the main landmark.
2. Responsive: Extraction metadata could exceed its card by 15 px at the 375 px target. Metadata stacks below 480 px.
3. Export/rerun: native download clicks could race a Streamlit rerun and return a 404 media source. All v2 download controls now use the non-rerunning download mode.
4. Test discoverability: `tests/__init__.py` ensures standard `unittest discover` includes the v2 regression suite rather than only the Evaluation package.

## Deployment and rollback procedure

1. Commit the tested Python, React, production bundle, tests and handoff documents on `main`, explicitly excluding `design.md`.
2. Push the same commit to the existing GitHub repository; do not create a new app or URL.
3. Set root-level Streamlit Community Cloud secret/environment value `UI_V2_ENABLED = "true"` for the existing app.
4. Verify all eight production pages, deterministic demo/Evaluation, Settings security state and exports.
5. Roll back immediately by setting the flag to false/unset if a production blocker appears. Component exceptions continue to fall back automatically to the legacy app.

The exact deployed commit and production smoke outcome are recorded in the final Cluster 7 completion report after the external rollout completes.

## Deferred to Cluster 8

- Legacy presentation/CSS removal.
- Dead-code and asset cleanup.
- Optional bundle splitting or dependency cleanup; current bundle has no production blocker.
- Broader automated screenshot baselines and additional assistive-technology matrix.
- Any architecture change or feature work not required by a verified Cluster 7 bug.
