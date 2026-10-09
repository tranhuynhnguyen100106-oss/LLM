# CreditLens UI v2 — Cluster 4 handoff

Date: 2026-10-09  
Scope: Document Extraction, Credit Analysis and Risk Warnings only  
Feature flag: `UI_V2_ENABLED`  
Deployment: not performed

## Scope boundary

Cluster 4 migrates only pages 2–4 to the v2 presentation layer established in Clusters 1–3. The Overview remains the Cluster 3 implementation. Pages 5–8 remain the current legacy Streamlit implementation.

No extraction, OCR, parser, normalization, financial formula, threshold, Rule Engine, risk classification, status, Pydantic schema, Evaluation, Gold Case, export, chat, provider/model, credential or inference behavior was changed. `credit_underwriting_colab.py`, `app.py`, `.streamlit/config.toml` and the untracked `design.md` were not edited in Cluster 4.

## Runtime behavior

- `UI_V2_ENABLED` off: run the complete legacy application.
- `UI_V2_ENABLED` on:
  - page 1: Cluster 3 Overview;
  - pages 2–4: Cluster 4 React presentation;
  - pages 5–8: legacy page content inside the v2 shell.
- Component registration/render failure: `app.py` shows the existing generic notice and returns to the legacy application.

## Source-of-truth architecture

```text
Existing Python extraction / formulas / rules / status
  -> typed presentation adapters
  -> allowlisted JSON-safe CorePage view model
  -> React rendering only

Local filter / details disclosure / hover / focus
  -> React-local state
  -> no Python event
  -> no Streamlit rerun
  -> no inference request
```

The CorePage component rejects browser events. React receives already-calculated values, formatted values, status, severity, thresholds and evidence references. It does not implement DTI, DSR, disposable income, income consistency, income volatility, balance buffer, confidence, mismatch or risk logic.

## UI implemented

### Document Extraction

- Document status cards with expected/detected type, page count, extraction status and confidence.
- Extracted-field cards with safe raw value, display value, declared/observed/other role, source, page, confidence, status and evidence disclosure.
- Confidence labels reuse the existing `nhan_luu_y_tin_cay` rules and the active session threshold.
- Missing fields remain explicit; no evidence or bounding-box content is invented.
- Source and confidence filters stay entirely inside React.

### Credit Analysis

- Cross-document income comparison for declared, observed and Python-calculated values.
- Difference and comparison status come from the existing `chenh_lech_thu_nhap` metric.
- Six existing metric cards: DTI, DSR, disposable income, balance buffer, income consistency and income volatility.
- Metric raw/display values, status, formula and note are copied from `ChiSoTinDung`.
- Current session thresholds are displayed as references; React does not evaluate them.

### Risk Warnings

- Risks are grouped in the existing HIGH, MEDIUM, LOW, INFO order.
- Every risk keeps its existing code, backend label, severity, explanation, difference and evidence list.
- Group and evidence disclosures are local-only interactions.
- Severity is communicated through explicit text as well as semantic color.

## State coverage

All three pages support deterministic `empty`, `loading`, `success`, `partial` and `error` states. `partial` is presentation metadata derived from existing backend status/missing-document signals; it does not replace or modify the case status.

## Business parity

Parity was checked across all 10 deterministic demo cases:

- extracted raw/display values, confidence, source and page;
- DTI, DSR, disposable income, balance buffer, income consistency and income volatility;
- active threshold values;
- risk flags, severity, explanations, differences and evidence counts;
- final case status.

The same `KetQuaThamDinh` object supplies legacy and v2 views. No second formula exists in React.

## Responsive and accessibility verification

| Range | Result |
|---|---|
| Desktop 1440 | PASS — multi-column comparison/metric layout; no horizontal overflow |
| Laptop 1100 | PASS — metrics and comparison values wrap; no horizontal overflow |
| Tablet 800 | PASS — single-column business cards; no horizontal overflow |
| Mobile 390 | PASS — stacked cards/controls/evidence; no horizontal overflow |

The live test deliberately expanded long evidence filenames. A 12 px mobile overflow was found and fixed with evidence-path wrapping, then all four widths were measured again with `scrollWidth == clientWidth`.

Semantic H1/H2/H3 structure, labelled selects, status/alert live regions, native `details`/`summary`, keyboard focus, focus-visible styles, non-color labels, 44/48 px controls, tabular financial numerals and reduced-motion rules are implemented. Comprehensive cross-browser and screen-reader certification remains Cluster 7.

## Verification summary

- Python UI and parity tests: 23 passed.
- React component and contract tests: 16 passed.
- TypeScript typecheck: passed.
- Production frontend build: passed.
- Existing Evaluation suite: 10 passed.
- Built-in CreditLens self-test: `SELF_TEST_PASS`.
- Live flag-on smoke: Extraction, Analysis and Risk rendered with deterministic CASE-03.
- Current-build browser warning/error log: empty.
- Additional inference requests: 0.

## Deferred

- `Deferred to Cluster 5`: migrate Summary, Methodology and Evaluation content.
- `Deferred to Cluster 6`: migrate Settings, provider configuration and chat presentation.
- `Deferred to Cluster 7`: comprehensive automated visual regression, cross-browser, screen-reader and WCAG certification.
- `Deferred to Cluster 8`: legacy presentation removal and any approved production rollout.
