# CreditLens UI v2 — Cluster 1 verification record

Date: 2026-10-09  
Source revision: `664fac53f4516a614149364c3298ca8e0e2d27d9`  
Scope: audit/specification/prototype only  
Deployment: not performed

## 1. Worktree protection

- Start state: `design.md` was the only untracked entry.
- Protected SHA-256 at start: `E285585DE1486ACEE4617AA59CC06B4FE28D66AE993D27C4629ADC159FF78BF7`.
- Final SHA-256: `E285585DE1486ACEE4617AA59CC06B4FE28D66AE993D27C4629ADC159FF78BF7`.
- Tracked source diff: none.
- Staged files: none.
- New Cluster 1 material exists only under `docs/ui-v2/cluster-1/`.
- No commit, push or deployment was performed.

## 2. Current UI audit coverage

The local application was opened and inspected at all eight destinations:

1. Tổng quan và hồ sơ
2. Trích xuất tài liệu
3. Phân tích tín dụng
4. Cảnh báo rủi ro
5. Tóm tắt thẩm định
6. Phương pháp và giới hạn
7. Evaluation
8. Cài đặt

The audit included empty/default, selected demo, processing/result, success, warning, error, disabled, provider connected/disconnected, selected, hover/focus contract and mobile behavior where present. The production Overview page was inspected read-only and matched the same current Streamlit generation. No production state was changed.

## 3. Runtime regression

| Check | Result | Evidence |
|---|---|---|
| Built-in CreditLens self-test | PASS | `SELF_TEST_PASS`; session-isolated thresholds, five themes, four mocked LLM providers, exports and prior regression fixes |
| Evaluation unit suite | PASS | 10/10 tests |
| Fresh no-action AppTest across all eight pages | PASS | Zero exceptions and zero rendered `st.error` |
| Representative CASE-01/03/07/08/09 across pages 2–5 | PASS | Zero exceptions and zero rendered `st.error` |
| Evaluation explicit-run AppTest | PASS | 36 cases; deterministic completion |
| Mocked provider-chat unit/UI boundary | PASS | One fake request per explicit submit; zero on rerender |
| Design-token JSON parse | PASS | `python -m json.tool` returned exit 0 |
| Git whitespace check for tracked diff | PASS | `git diff --check` returned exit 0 |

No real provider credential was used. Mocked provider checks do not transmit data or call an external model.

## 4. Deterministic Evaluation snapshot

| Measure | Value |
|---|---:|
| Cases | 36 |
| Scenarios | 12 |
| Extraction accuracy | 98.33% |
| Risk F1 | 91.20% |
| Status accuracy | 97.22% |
| Status macro F1 | 92.65% |
| Grounded evidence coverage | 96.88% |
| Unsupported claim rate | 0.93% |
| Factual consistency | 94.44% |
| `llm_api_calls` | **0** |

These synthetic/anonymized regression metrics are not production-performance claims.

## 5. Prototype QA

The standalone reference was served only on localhost and checked in an in-app browser.

| View | Result |
|---|---|
| 1440 × 1024 | PASS — 256 px sidebar, 40 px main padding, 12-column 8/4 intake split, no horizontal overflow |
| 1280 × 960 | PASS — 248 px sidebar, 32 px main padding, preserved 8/4 split, no horizontal overflow |
| 390 × 844 | PASS — drawer shell, 16 px content margin, 48 px primary action, intake precedes workflow, no horizontal overflow |
| Light/Dark | PASS — semantic palettes switch locally |
| Empty/processing/success/warning/error | PASS — local state changes and recovery labels render |
| Upload modes | PASS — exact individual/folder modes; folder requirements visible |
| Mobile drawer | PASS — dialog semantics, initial focus, Escape close and focus return |
| Browser console | PASS — no warning/error entries |
| Static network/provider scan | PASS — no `fetch`, XHR, WebSocket, EventSource, remote URL or provider code |
| Minimum product text | PASS — no prototype product text below 12 px |

The fixed prototype-control overlay is outside `.cl-app`, collapsible and excluded from frame geometry. Classic non-overlay browser scrollbars may reduce the CSS layout viewport by their own platform width; grid ratios and no-overflow behavior remain unchanged.

## 6. API/token impact

- Additional real inference requests: **0**.
- Visual inspection, viewport changes, theme changes, hover/focus, prototype state changes and component rendering: **0** requests.
- Deterministic demo and Evaluation paths: `llm_api_calls = 0`.
- Business logic, provider/model behavior and API-cost behavior: unchanged.

## 7. Known items intentionally not fixed

- `Deferred to Cluster 4`: the current Extraction `Trang` column mixes integer values and `"—"`, producing a nonfatal PyArrow conversion warning before Streamlit recovers.
- `Deferred to Cluster 7`: the external harness `../apptest_creditlens.py` contains a stale navigation selector (`⚙ Cài đặt` instead of the current numbered label) and is not counted as a passing current harness.
- `Deferred to Cluster 7`: full automated WCAG/screen-reader and screenshot-diff coverage.
- `Deferred to Cluster 8`: legacy asset/CSS cleanup and any approved production rollout.

No deferred issue was changed in Cluster 1.
