# CreditLens UI v2 — Trang 1: Tổng quan và hồ sơ

Status: **implementation-ready visual specification; no runtime implementation in Cluster 1**  
Canonical route label: **Tổng quan và hồ sơ**  
Reference prototype: [`assets/overview-reference.html`](./assets/overview-reference.html)

## 1. Outcome and user priority

The page gets an underwriter from “no active case” to a valid existing intake action with the least ambiguity. It must answer, in order:

1. Am I in the right, secure application?
2. Is a case already active?
3. Should I upload documents or use a deterministic demo case?
4. What is required and what happens next?
5. Did the action start, succeed or fail, and how do I recover?

The page does not calculate risk, preview an underwriting outcome, create a provider request or invent customer/SLA/audit information.

## 2. Information hierarchy

### Desktop order

1. Global header
2. Primary navigation + main landmark
3. Case context bar
4. Page header: title, purpose, deterministic-processing badge
5. Compact privacy/legal notice
6. Four-stage workflow stepper
7. Intake workspace: upload (8 columns) + demo/status (4 columns)
8. Compact “what happens next” disclosure/help

### Mobile order

1. Mobile app bar
2. Compact case context
3. Page title and deterministic badge
4. Privacy/legal notice
5. Intake mode and primary action
6. Demo/status panel
7. Workflow as a compact vertical disclosure
8. “What happens next” help

The mobile order intentionally puts the primary task before process explanation. It is a content-order change, not only a visual CSS reorder, so screen-reader order matches the page.

## 3. Global shell geometry

All measurements are CSS pixels at 100% zoom.

### Frame 01 — `CL/Overview/Light/1440/Empty`

| Region | Geometry |
|---|---|
| Viewport | 1440 × 1024 reference; vertical content may continue |
| Global header | x0, y0, w1440, h72 |
| Sidebar | x0, y72, w256, min-h952 |
| Main region | x256, y72, w1184 |
| Main padding | 40 px left/right; 32 px top; 48 px bottom |
| Content width | 1104 px maximum |
| Grid | 12 columns × 70 px; 11 gutters × 24 px |
| Context bar | x296, y104, w1104, h48 in empty and active states |
| Page-header block | x296, y172, w1104, target h72 |

The context bar is always present to prevent loss of orientation. The 20 px gap after its 48 px height places the page header at y172; sections retain their specified internal spacing.

### Frame 02 — `CL/Overview/Light/1280/Empty`

| Region | Geometry |
|---|---|
| Viewport | 1280 × 960 reference |
| Global header | x0, y0, w1280, h72 |
| Sidebar | x0, y72, w248 |
| Main region | x248, y72, w1032 |
| Main padding | 32 px left/right; 28 px top; 40 px bottom |
| Content width | 968 px |
| Grid | 12 columns × 58.67 px; 11 gutters × 24 px |

The 8/4 split produces approximately 637/307 px panels with one 24 px inter-panel gutter. Labels remain full words; helper copy may wrap to two lines.

### Frame 03 — `CL/Overview/Light/390/Empty`

| Region | Geometry |
|---|---|
| Viewport | 390 × 844 reference; vertical scroll expected |
| Mobile app bar | x0, y0, w390, h64; sticky |
| Main | x0, y64, w390 |
| Content margins | 16 px |
| Content width | 358 px |
| Grid | 4 columns × 77.5 px; 3 gutters × 16 px |
| Bottom safe padding | max(24 px, environment safe-area inset) |

There is no page-level horizontal scroll. Panels, file slots and buttons occupy all four columns. The primary action is 48 px high and full width.

### Dark frames

Create corresponding frames `CL/Overview/Dark/{1440|1280|390}/{state}` with identical geometry and independent Dark semantic tokens. Do not create Dark mode by applying opacity or inversion to a Light screenshot.

## 4. Global header

### Desktop

- Left: existing approved CreditLens institutional lockup; rendered height 32 px, max width 210 px, preserving aspect ratio.
- Center/right: label `Quy trình xác định · Không tự động phê duyệt` with neutral/info status icon.
- Right edge: theme control and help/settings access only when those actions exist in the current product. Do not add a user avatar, institution name or live system health value without a real source.
- Border-bottom: 1 px semantic border; no drop shadow at rest.

### Mobile

- 44 × 44 px menu trigger, short product lockup, optional theme action.
- Current page appears in the first content block, not squeezed into the app bar.
- Menu trigger accessible name: `Mở điều hướng` / `Đóng điều hướng`.

## 5. Page header and notices

### Page header

- H1: `Tổng quan và hồ sơ`, token `type.page-title` (28/36 px desktop, 24/32 px mobile).
- Supporting copy: `Bắt đầu từ bộ tài liệu hoặc mở một hồ sơ minh họa xác định.`
- Badge: `Không dùng LLM để mở trang`, info/neutral role. This describes only the page interaction, not every later analysis action.
- Empty case context: `Chưa có hồ sơ đang mở`.

### Privacy/legal notice

Visible summary:

> Dữ liệu hồ sơ chỉ được dùng trong phiên làm việc hiện tại. CreditLens hỗ trợ thẩm định; quyết định cuối cùng thuộc cán bộ tín dụng.

- Use an info `Alert` with a `Xem nguyên tắc sử dụng` disclosure link.
- Keep the summary to two lines maximum desktop and four lines mobile.
- The disclosure contains the existing approved legal text; no new policy claim is introduced.
- It is not dismissible when it carries mandatory information.

## 6. Workflow stepper

Steps and helper labels:

1. `Tiếp nhận` — Tiếp nhận và chuẩn hóa tài liệu
2. `Tính toán` — Tính toán xác định bằng Python
3. `Đối chiếu` — Đối chiếu dữ kiện và bằng chứng
4. `Con người xem xét` — Chuyên viên chịu trách nhiệm quyết định

### Empty state

Step 1 is current; steps 2–4 are upcoming. Use numeric circles, labels and connector lines. The label `Hiện tại` is visible next to step 1, not encoded only in the color.

### Active states

Step status must be mapped from real session state. Completed steps show check + `Hoàn tất`; warning/error steps retain the step number and show a secondary status icon. Clicking a step cannot bypass existing prerequisites.

### Placement

- 1440/1280: one horizontal panel, minimum h104, 24 px padding.
- 390: placed after intake; four vertically stacked rows in one Disclosure, each minimum h52.

## 7. Intake workspace

### 7.1 Upload panel — 8 columns desktop

Header:

- H2: `Bộ hồ sơ tài liệu`
- Helper: `Tải lên các tài liệu hiện có. Có thể bổ sung tài liệu còn thiếu trước khi bắt đầu.`
- Upload mode: `Tải từng tài liệu` / `Tải một thư mục`, matching the current application. Demo cases remain in the adjacent deterministic panel rather than becoming a third upload mode.

#### File slots

Use the four current document slots; do not add a new required type in the component layer:

1. `Đơn đề nghị vay vốn` — PDF, first of three documents required for a full case;
2. `Chứng từ thu nhập` — PDF, first of three documents required for a full case;
3. `Sao kê ngân hàng` — PDF, first of three documents required for a full case;
4. `Nghĩa vụ nợ · tùy chọn` — PDF, optional.

Each file is limited to 10 MB by the existing validation path. Password-protected PDFs are not supported. Folder mode accepts one folder containing 3–4 PDFs for the same case and keeps the existing classification behavior. Each `DocumentCard` contains:

- document-type label;
- accepted file rules drawn from the real uploader configuration;
- native upload action/drop region;
- filename and native remove/retry when present;
- status icon/text.

Desktop: two-column card grid; 16 px gap.  
Mobile: single column; 12 px gap.  
Minimum slot height: 112 px desktop, 104 px mobile.

#### Primary action

Label: `Chạy quy trình thẩm định`, matching the current explicit domain action. In individual mode it is disabled until at least one PDF is selected; in folder mode it is disabled until the selected folder contains exactly 3–4 PDFs. The adjacent helper explains that the first three individual document types form a full case; do not leave a disabled action unexplained.

### 7.2 Demo panel — 4 columns desktop

Header: `Hồ sơ minh họa`  
Helper: `Dùng dữ liệu xác định để xem luồng sản phẩm mà không gọi mô hình.`

Controls:

1. Select label `Chọn hồ sơ`, containing the exact existing CASE-01 through CASE-10 labels and order.
2. Read-only summary from existing case metadata only.
3. Primary/secondary action `Mở hồ sơ minh họa`.

Opening a demo case uses the existing deterministic data path and produces zero inference requests. The visual reference uses `CASE-03` solely as a clearly labelled example; it does not fabricate a production case.

### 7.3 Case status panel

When there is no active case, show a short EmptyState below the demo controls:

- title: `Chưa có hồ sơ đang mở`;
- body: `Tải tài liệu hoặc chọn một hồ sơ minh họa để tiếp tục.`

When a case is active, replace it with the real case ID, source, last completed step and supported next action. No risk rating appears here before analysis has produced it.

## 8. State specifications

Every state below is required in Light/Dark and 1440/390; Empty, Processing, Success and Error also receive 1280 review.

### Default / empty

- Case context is empty.
- Workflow step 1 current.
- File slots are empty; primary upload action is disabled with a reason.
- Demo select is available.
- No fabricated metrics, customer name, risk class or completion percentage.

### Hover

- Actionable panels use `surface.subtle` plus one stronger border/elevation step.
- File-drop region emphasizes its border; no instruction disappears.
- No network, analytics that include document content, or inference call is initiated.

### Focus-visible

- Ring is not clipped by panels or sticky regions.
- Focus order: skip link → header actions → navigation/current route → case context → page action/content in reading order.
- The desktop 8/4 visual layout does not change DOM order: upload precedes demo.

### Selected

- Selected demo case shows selected field value and optional check; summary is linked with `aria-describedby`.
- Selected navigation uses `aria-current="page"`.
- File selection is not shown as success until validation confirms it.

### Disabled

- Disabled primary action retains legible label and exposes the reason immediately below.
- Disabled does not mean “processing”; processing controls show progress and a live label.

### Loading / processing

- Case context shows `Đang xử lý`.
- `ProcessingPanel` replaces the relevant panel body while preserving file/case identifiers.
- Show a real stage name, such as `Đang trích xuất tài liệu…`; do not expose hidden reasoning or an invented time remaining.
- Submit controls prevent duplicate activation. Navigation remains available unless existing state safety requires otherwise.
- `aria-live="polite"` announces stage changes once.

### Success

- Success Alert: `Hồ sơ đã sẵn sàng` plus a real next action, typically `Đến Trích xuất tài liệu` or the existing next valid page.
- Workflow reflects completed/current stages from session state.
- Previously selected files/case remain visible.
- Focus moves to the success summary only when it resulted from an explicit submit and doing so improves recovery/orientation.

### Warning

- Warning stays next to the affected document or field and is also summarized above the primary action when it affects readiness.
- Use specific recovery copy, for example `Bổ sung tài liệu` only where an existing validation state supports it.
- User can inspect the affected item without losing other selections.

### Error

- Inline Error Alert includes what failed and one safe recovery action (`Thử lại`, `Thay tệp`, or `Kiểm tra cấu hình`) mapped from the existing error.
- Preserve safe user inputs and filenames.
- Do not show provider secrets, stack traces or raw exceptions.
- A failed external action must never be retried automatically through rerender.

### Connected / disconnected

Overview does not use provider connectivity as a page-success signal. If connectivity is relevant to a later action, it appears as a compact status with text (`Đã kết nối` / `Chưa kết nối`) and a link to Settings. Demo opening remains available and deterministic.

## 9. Content and truncation rules

- H1: one line desktop, up to two lines at 320 px.
- Navigation: one line desktop; tooltip on the 72 px rail.
- Filenames: wrap to two lines, then middle-truncate while preserving extension; full name available on focus/hover.
- Case ID: tabular/monospace style, selectable, never hidden by ellipsis without an accessible full value.
- Helper copy: no fixed-height clipping.

## 10. Interaction contract

| User action | Local UI result | Domain event | Inference requests |
|---|---|---|---:|
| Change theme | Apply semantic tokens | None | 0 |
| Open/close navigation | Drawer/rail state | None | 0 |
| Expand legal/workflow help | Disclosure state | None | 0 |
| Hover/focus a control | Visual state | None | 0 |
| Select a demo case | Update local selection/summary | Existing case-selection state only | 0 |
| Open demo case | Show deterministic processing/result state | Existing demo-load action | 0 |
| Select/upload documents | Native uploader state | Existing upload/validation action | 0 unless the existing explicit analysis action is later invoked |
| Click a future provider-backed action | Loading and duplicate-submit guard | Exactly one existing explicit provider action | At most the existing single request; never from the component itself |

## 11. Accessibility annotations

- `main` receives the skip-link target and has `tabindex="-1"` only if needed for programmatic focus.
- File inputs retain visible labels and native semantics; drag-and-drop is never the only input method.
- Errors are linked to the relevant control and summarized after explicit submit.
- Stepper is an ordered list. Current step uses `aria-current="step"`.
- Status badges include visible text. Decorative connector lines are hidden from assistive technology.
- At 200% zoom and 320 CSS px, no controls overlap, no fixed content hides focused elements, and page-level horizontal scrolling is absent.
- Reduced-motion mode removes panel lift/translation and shortens nonessential transitions to zero.

## 12. Visual QA checklist

- [ ] Approved logo asset is crisp on 1× and 2× displays; no unofficial mark is introduced.
- [ ] Exact 1440/1280/390 geometry and content order match this document.
- [ ] Light/Dark roles use tokens; no page-local hex colors.
- [ ] Empty, loading, processing, success, warning, error, disabled, connected/disconnected, selected, hover, focus and mobile states are reviewed.
- [ ] No repeated full hero pushes the intake below the initial viewport unnecessarily.
- [ ] No fake version, customer, SLA, audit, connection or case result appears.
- [ ] Keyboard, 200% zoom, 320 px reflow, screen-reader labels and reduced motion are checked.
- [ ] Visual-only checks record `additional inference calls = 0`.
- [ ] No business logic, evaluation truth or provider behavior changed while implementing the page.
