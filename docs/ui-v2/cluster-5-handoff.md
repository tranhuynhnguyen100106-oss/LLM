# CreditLens UI v2 — Cluster 5 handoff

Date: 2026-10-09  
Scope: Executive Summary, Human Review, Report Export, Methodology & Limitations, and Evaluation & Benchmarks only  
Feature flag: `UI_V2_ENABLED`  
Deployment: not performed

## Scope boundary

Cluster 5 migrates only pages 5–7 to the v2 presentation layer established in Clusters 1–4. Pages 1–4 remain the existing Cluster 3/4 implementations. Page 8 remains the legacy Streamlit Settings implementation.

No extraction, normalization, financial formula, threshold, Rule Engine, risk classification, case status, Pydantic schema, cross-document validation, Evaluation ground truth, Gold Case, provider/model, credential, chat, API-cost or automatic approval behavior was changed. `app.py`, `credit_underwriting_colab.py`, `.streamlit/config.toml` and the untracked `design.md` were not edited in Cluster 5.

## Runtime behavior

- `UI_V2_ENABLED` off: run the complete legacy application.
- `UI_V2_ENABLED` on:
  - page 1: Cluster 3 Overview;
  - pages 2–4: Cluster 4 core-business pages;
  - pages 5–7: Cluster 5 Summary, Methodology and Evaluation pages;
  - page 8: legacy Settings content inside the v2 shell.
- Component registration/render failure: `app.py` retains the existing generic notice and falls back to the legacy application.

## Source-of-truth architecture

```text
Existing Python facts / formulas / rules / status / evaluation report
  -> typed, allowlisted presentation adapters
  -> JSON-safe Cluster 5 view models
  -> React rendering only

Explicit Summary action
  -> existing Word / Excel / PDF / Markdown / JSON path
  -> existing optional AI explanation path only when requested

Explicit Run Evaluation event
  -> existing deterministic evaluator once
  -> report cached in Streamlit session state
  -> React filter / disclosure stays local
  -> 0 LLM API calls
```

React does not calculate credit metrics, select status, rank severity, rerun Evaluation or generate export files. The adapters map existing backend values and presentation metadata only.

## Executive Summary and Human Review

- Case identity, applicant, current backend status and highest existing alert severity are shown first.
- All six existing credit metrics reuse the same Cluster 4 presentation mapping.
- The first three risks retain backend order and show the total alert count; the Risk page remains the complete risk source.
- Findings, missing information, review questions and source evidence stay explicit and traceable.
- Deterministic content and optional AI-generated explanation are visually separated.
- Human Review reinforces that CreditLens does not approve or decline credit and preserves the existing backend status.

## Report Export

- Word, Excel and PDF continue through the existing export generators and filenames.
- Markdown and JSON continue through the existing deterministic payloads.
- Export controls remain native Streamlit actions below the React summary so downloads preserve current browser behavior.
- Optional AI explanation remains an explicit user action; rendering, layout inspection and export-option selection do not trigger inference.

## Methodology & Limitations

- Three layers are documented separately: document/data processing, deterministic analysis and optional AI interpretation.
- Six formula cards reproduce the current definitions for DTI, projected DSR, disposable income, income difference, income volatility and balance buffer.
- The five existing PDF capability categories and limitations are preserved in a semantic table.
- `SELF-TEST ≠ EVALUATION` explains the different questions answered by software regression checks and quality benchmarks.
- Limitations are grouped by document quality, extraction/data, model/provider and Evaluation/human-review scope.

## Evaluation & Benchmarks

- Initial state is report-free; Evaluation runs only after the explicit `Run Evaluation` event.
- The event is typed and idempotent at the Streamlit boundary, then invokes the existing deterministic evaluator.
- The report exposes dataset/run metadata, scorecards, field-level extraction, risk precision/recall/F1, the three-class status confusion matrix, per-class status metrics, grounding, both baselines, processing time, failure cases and limitations.
- The confusion matrix is a semantic table with an accessible text equivalent of the heatmap.
- Failure-case filtering is React-local and does not rerun Python or Evaluation.
- JSON and CSV downloads reuse the existing Evaluation exporters and filenames.
- Live verification recorded 36 synthetic/anonymized cases, 12 scenarios and `LLM API calls: 0`.

## Business parity

Parity was checked across all 10 deterministic demo cases and the saved Evaluation report:

- all summary metrics, raw values, formatted values and statuses;
- backend final status and human-review presentation;
- backend risk order, severity, explanations and evidence;
- missing information and review questions;
- existing Word, Excel, PDF, Markdown and JSON export behavior;
- formula text and PDF support matrix;
- Evaluation metadata, scorecards, tables, baselines, failure cases and export payloads.

The same `KetQuaThamDinh` and Evaluation report objects supply legacy and v2 views. No second business calculation exists in React.

## Responsive and accessibility verification

| Range | Result |
|---|---|
| Desktop 1440 | PASS — multi-column scorecards and summary sections; no horizontal overflow |
| Laptop 1100 | PASS — cards and tables adapt within the content width; no horizontal overflow |
| Tablet 800 | PASS — stacked support-page sections; no horizontal overflow |
| Mobile 390 | PASS — single-column cards and controls; no horizontal overflow |

Semantic H1/H2/H3 structure, labelled controls, native tables, status text, non-color severity labels, keyboard focus, visible focus ring, reduced-motion support and text equivalents for the confusion matrix are implemented. The local browser console reported no warning or error. Comprehensive cross-browser and screen-reader certification remains Cluster 7.

## Verification summary

- Python UI, contract, parity and export tests: 30 passed.
- Existing Evaluation suite: 10 passed.
- Combined Python regression suite: 40 passed.
- React component and contract tests: 21 passed.
- TypeScript typecheck: passed.
- Production frontend build: passed.
- Built-in CreditLens self-test: `SELF_TEST_PASS`.
- Live flag-on smoke: Summary, Methodology and Evaluation idle/success states rendered with deterministic CASE-03.
- Live Evaluation: 36 cases, 12 scenarios, `LLM API calls: 0`.
- Current-build browser warning/error log: empty.
- Additional inference requests: 0.

## Deferred

- `Deferred to Cluster 6`: migrate Settings, provider configuration and chat presentation.
- `Deferred to Cluster 7`: comprehensive automated visual regression, cross-browser, screen-reader and WCAG certification.
- `Deferred to Cluster 8`: legacy presentation removal and any approved production rollout.

