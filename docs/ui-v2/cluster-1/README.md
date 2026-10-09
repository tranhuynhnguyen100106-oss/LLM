# CreditLens UI v2 — Cluster 1 design handoff

**Status:** design audit and specification only  
**Source revision:** `664fac53f4516a614149364c3298ca8e0e2d27d9` (`main`, aligned with `origin/main`)  
**Audit date:** 2026-10-09  
**Product:** CreditLens — AI Credit Underwriting Copilot

This directory is the design source of truth produced for **Cluster 1 only**. It does not implement the UI, create a React package, change Python/domain behavior, or deploy production.

## Handoff set

1. [`01-ui-audit.md`](01-ui-audit.md) — eight-page inventory, state coverage, IA and UX/accessibility audit.
2. [`02-design-tokens.md`](02-design-tokens.md) — human-readable Light/Dark token specification.
3. [`design-tokens.json`](design-tokens.json) — machine-readable design-token handoff; not wired into runtime code.
4. [`03-component-library.md`](03-component-library.md) — component anatomy, variants, states, behavior and ownership matrix.
5. [`04-overview-spec.md`](04-overview-spec.md) — development-ready specification for the Overview page at 1440, 1280 and 390 px.
6. [`05-prototype-and-approval.md`](05-prototype-and-approval.md) — prototype routes, state transitions, QA contract and decisions requiring approval.
7. [`assets/overview-reference.html`](assets/overview-reference.html) — standalone, presentation-only reference mockup. It makes no network or inference requests.
8. [`06-verification.md`](06-verification.md) — test, responsive QA, regression and worktree-protection evidence.

## Source material reviewed

- `design.md` (as-is product and architecture document).
- `credit_underwriting_colab.py`, including all eight pages, CSS, session state, LLM boundaries and self-test.
- `app.py`, `.streamlit/config.toml`, `requirements.txt`, `README.md`.
- `evaluation/` framework, dataset schema and tests.
- All brand assets in `static/`.
- Current local UI at 1440/1280/390 and all eight navigation destinations.
- Current production Overview at `https://creditlens-underwriting.streamlit.app/`.
- The Stitch reference package as visual input only; mock customer data, audit identifiers, version labels and legal claims from it were not adopted.

## Scope guardrails

- Python remains the source of truth for extracted facts, financial values, risk, evidence, Evaluation and business state.
- Native Streamlit remains the planned owner for PDF upload, password/API-key input, chat input, large dataframes, downloads and configuration forms.
- No secret may enter React props, browser logs, reports or design fixtures.
- Rendering, hover, focus, theme changes and prototype interactions must create **zero** inference requests.
- Evaluation remains explicit-run and deterministic with `llm_api_calls = 0`.
- Legacy UI remains intact until Cluster 8 and no rollout/deployment occurs in Cluster 1.

## Worktree protection

At audit start, the only worktree entry was the user-owned untracked file `design.md`. Its SHA-256 was:

```text
E285585DE1486ACEE4617AA59CC06B4FE28D66AE993D27C4629ADC159FF78BF7
```

Cluster 1 does not add, overwrite, stage, commit or delete that file.

## Handoff rule

These specifications require user approval before any runtime implementation. Runtime token CSS, Components v2 scaffolding and typed contracts belong to Cluster 2; the real shell and Overview implementation belong to Cluster 3.
