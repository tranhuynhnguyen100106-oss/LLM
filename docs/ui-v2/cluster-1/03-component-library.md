# CreditLens UI v2 — Component library specification

Status: **Cluster 1 specification only**  
Runtime implementation: **not included**  
Source of truth: [`02-design-tokens.md`](./02-design-tokens.md) and [`design-tokens.json`](./design-tokens.json)

## 1. Principles

1. The component layer is presentational. Credit formulas, rules, thresholds, schemas, extraction, cross-document validation, evaluation truth and provider behavior remain in Python.
2. Every component consumes semantic tokens. Brand hex values, arbitrary spacing and page-specific shadows are not accepted.
3. A state is communicated with text or icon plus color; color is never the only signal.
4. Pointer hover, focus, animation, layout inspection and component rendering are local-only. They must never produce an inference request.
5. Interactive targets are at least 44 × 44 px on touch layouts. Focus order follows reading order and the visible focus ring is never removed.
6. Loading is reserved for real work. Skeletons do not simulate progress, and indeterminate spinners are paired with a short action label.
7. Vietnamese is the primary product language. Domain abbreviations may remain in English where already established, but mixed-language labels within one control are avoided.

## 2. Ownership boundary

| Layer | Owner | Permitted responsibility | Must not own |
|---|---|---|---|
| Python / current Streamlit app | Domain source of truth | Session state, case data, deterministic computation, evaluation, provider calls, validation and error mapping | Styling decisions encoded as new business branches |
| Future component shell | Presentation | Layout, navigation affordances, component states, local disclosure, local theme selection and responsive behavior | Secrets, provider SDK calls, rules, scoring, thresholds or credit decisions |
| Native Streamlit widgets | Transitional system control | File upload, password/secret entry, large data tables, downloads and chat input where native behavior is safer | Untracked duplicated state or visual semantics that conflict with the component library |
| Hybrid adapter | Explicit typed bridge | Maps existing Python values to presentational props and maps user intent back to one domain event | Recomputing or interpreting domain results |

For every future component, the adapter must expose serializable display data only. Provider keys stay in native secret inputs and are never copied into a client component.

## 3. Shared state contract

All interactive components use the same state vocabulary:

| State | Visual contract | Behavior contract |
|---|---|---|
| Default | Neutral border/surface and primary text | Ready for interaction |
| Hover | One elevation or surface step; cursor communicates action | Pointer-only enhancement; no domain side effect |
| Focus-visible | 2 px focus ring with 2 px offset | Keyboard-visible; not triggered by pointer unless browser chooses |
| Active / pressed | One darker/lower elevation step | Lasts only during activation |
| Selected | Selected surface, leading check or marker and `aria-current`/`aria-selected` where applicable | Persists until another valid selection |
| Disabled | Muted label and disabled surface; minimum readable contrast | Not focusable unless explanation is needed; never responds to click |
| Loading / processing | Progress indicator and action-specific label | Prevent duplicate submit; keep context visible |
| Success | Success icon + concise text | Announces completion through a polite live region |
| Warning | Warning icon + action-oriented text | Does not block unless domain rules say it blocks |
| Error | Error icon, summary and recovery action | Field errors are associated with their controls; global error receives focus only after submit |

Connected and disconnected are status variants, not substitutes for success and error. Selected is not the same as hover. Empty is a content state and must tell the user what to do next.

## 4. Foundations

### 4.1 Iconography

- Use one outline icon family with 1.75–2 px optical stroke.
- Icon-token sizes: 16 px inline, 20 px controls and 24 px navigation. A 32 px empty-state illustration is an illustration asset, not a fourth icon token.
- Decorative icons use `aria-hidden="true"`. Meaningful icon-only actions require an accessible name and tooltip.
- Credit-risk severity never relies on icon shape alone; pair it with a Vietnamese label.

### 4.2 Content rules

- Sentence case for titles and controls.
- Button labels begin with a clear verb: `Tải lên`, `Mở hồ sơ`, `Phân tích`, `Thử lại`.
- Error copy uses: what happened → what remains safe → recovery action.
- Numeric financial output uses tabular numerals and a visible unit. Do not encode meaning only in decimals or abbreviations.

## 5. Shell and navigation components

### `AppShell`

**Anatomy:** global header, primary navigation, main landmark, optional context bar, status/live-region host.  
**Widths:** ≥1440: 256 px sidebar; 1280–1439: 248 px sidebar; 1024–1279: 72 px rail with on-demand drawer; <1024: drawer; <768: 64 px mobile app bar.  
**Behavior:** main scroll container remains the document; no nested whole-page scrolling; page-level horizontal scrolling is prohibited.  
**Accessibility:** a first-focus skip link targets `main`; landmarks have unique labels.

### `GlobalHeader`

**Height:** 72 px desktop, 64 px mobile.  
**Anatomy:** approved lockup, product name, deterministic-processing indicator, optional compact case status, mobile navigation trigger.  
**Rules:** the full hero is not repeated on every route. The legal statement is exposed once as a compact, persistent disclosure/notice.

### `PrimaryNavigation` and `NavigationItem`

**Sections:**

1. Hồ sơ — pages 1–5
2. Kiểm chứng — pages 6–7
3. Hệ thống — page 8

**Item anatomy:** 20 px icon, one-line label, optional status dot.  
**States:** default, hover, focus-visible, current, disabled. Current uses a leading 3 px marker, selected surface and `aria-current="page"`.  
**Responsive:** labels remain visible on full sidebar; rail uses tooltips; mobile uses a modal drawer with focus trap, Escape/close action and focus return.

### `CaseContextBar`

**Purpose:** prevents loss of case context between pages.  
**Empty:** `Chưa có hồ sơ đang mở` plus `Về Tổng quan`.  
**Active:** case ID, source (`Tài liệu` or `Hồ sơ minh họa`), current processing status and last completed stage.  
**Rules:** display only existing state; never invent customer, version, SLA or audit values. It is sticky below the header on desktop and collapses to one summary row on mobile.

### `WorkflowStepper`

**Steps:** Tiếp nhận → Tính toán → Đối chiếu → Con người xem xét.  
**Step states:** upcoming, current, complete, warning, error.  
**Rules:** state is derived from actual session state; it must not show a hard-coded “current/next” position. Complete steps remain navigable only where the existing application already allows navigation. Mobile uses a vertical compact list or horizontal overflow-free disclosure—not a squeezed four-column row.

## 6. Headers, surfaces and layout

### `PageHeader`

**Anatomy:** eyebrow/breadcrumb only when useful, H1, one-sentence purpose, optional status chips and one primary action.  
**Spacing:** 32 px after context bar, 24 px before the first section; 24/20 px on mobile.  
**Rule:** one H1 per page.

### `SectionHeader`

**Anatomy:** H2/H3, optional helper copy, optional trailing action. Trailing actions wrap below the title below 480 px.

### `Panel`

Variants: default, raised, interactive, selected, disabled.  
Padding: 24 px desktop; 20 px tablet; 16 px mobile.  
Radius: `radius.lg`; border: `component.panel.border` (1 px `border.subtle`); hover elevation is permitted only when the whole panel is actionable.

### `Divider`

1 px semantic border, 16/24/32 px surrounding spacing. It is decorative unless it separates labelled regions requiring semantic grouping.

## 7. Actions and controls

### `Button`

| Variant | Use | Notes |
|---|---|---|
| Primary | One main action per panel or page region | Navy/accessible primary role |
| Secondary | Supporting action | Bordered neutral surface |
| Accent | Rare high-salience institutional action | Crimson role; never competes with primary in the same group |
| Ghost | Low-emphasis local action | Must retain focus and 44 px target |
| Destructive | Confirmed destructive action only | No current Cluster 1 flow requires it |

Sizes: 44 px default, 36 px compact desktop-only, 48 px touch-emphasis.  
States: default, hover, focus-visible, pressed, disabled, loading. Loading retains button width, replaces the leading icon with progress and uses a specific label (`Đang mở hồ sơ…`).

### `IconButton`

44 px on desktop and touch. The glyph inside remains 20 px. Requires accessible name, tooltip after 500–700 ms, and no critical action without adjacent text or confirmation.

### `TextField`, `NumberField`, `TextArea`

**Anatomy:** visible label, optional marker, control, helper/error text, character/unit suffix where relevant.  
**Height:** 44 px single-line; textarea minimum 96 px.  
**Error:** 2 px error border plus icon/text; connect with `aria-describedby`.  
**Number:** visible unit and locale-aware display; never silently reformats domain values.

### `SecretField`

Must remain a native secure input. It supports show/hide only if the platform safely provides it. The component layer receives at most `isConfigured: boolean`, never the value.

### `Select`, `RadioGroup`, `SegmentedControl`

- Use Select for the 10 demo cases and long option sets.
- Use RadioGroup when all options must be compared.
- Use SegmentedControl for 2–3 mutually exclusive local modes, such as the two current upload modes `Tải từng tài liệu` / `Tải một thư mục`. Demo cases remain a separate deterministic intake path.
- Keyboard: arrows within a radio/segment group, Enter/Space activation, Escape closes a popover.

### `Checkbox` and `Switch`

Checkbox confirms a selection; Switch changes a setting immediately. Settings that require save/apply must not use Switch. Labels remain clickable and describe the resulting state.

## 8. Domain display components

### `StatusBadge`

Variants: neutral, info, success, warning, danger. Anatomy: optional icon + short label. Minimum height 24 px. Badges do not act as buttons.

### `RiskBadge`

Maps only existing risk labels to state roles. It shows both category text and severity icon. Threshold computation stays in Python. No component infers risk from color or a numeric value.

### `ConfidenceBadge`

Shows a value already provided by the backend plus a visible label (`Độ tin cậy`). It does not choose thresholds or hide low-confidence evidence.

### `MetricTile`

**Anatomy:** label, value + unit, optional delta/context, optional status.  
**Layout:** 2–4 tiles desktop; one or two columns mobile depending on content length.  
**Rule:** all values are text-accessible; charts are supplementary.

### `DocumentCard`

**Anatomy:** document type, filename/status, validation summary, page count when available, primary local action.  
**States:** empty, uploading, processing, success, warning, error, disabled.  
**Rules:** file type/size constraints are visible before upload; an error keeps prior safe state and offers retry/remove where already supported.

### `EvidenceCard` and `EvidenceReference`

**Anatomy:** claim/field, extracted value, document/page reference, confidence and warning. References are navigable only when the application can resolve them. Long source text is disclosed progressively; it is not clipped without access to the full content.

### `Alert`

Variants: info, success, warning, error. The component name `error` maps to the semantic `state.danger` token set; it does not introduce a second error palette.  
**Anatomy:** icon, title, message, optional recovery action, optional dismiss.  
**Semantics:** passive information uses `role="status"`; urgent submit failures use `role="alert"`. Repeated rerenders must not re-announce unchanged alerts.

### `EmptyState`

Contains one clear explanation, one next action and optional secondary help. It avoids celebratory illustration for risk/error states. Example: `Chưa có tài liệu` / `Tải lên bộ hồ sơ để bắt đầu trích xuất.`

### `Skeleton`, `ProgressBar`, `ProcessingPanel`

- Skeleton mirrors stable layout and is `aria-hidden`; an adjacent live label announces work.
- Determinate progress uses a real percentage only when available.
- ProcessingPanel shows current stage, completed stages and a safe instruction not to resubmit. It never exposes chain-of-thought or fabricated timing.

## 9. Data, disclosure and feedback

### `DataTable`

Native Streamlit remains the preferred owner for large, sortable or downloadable tables in the migration period.  
**Requirements:** caption/accessible name, sticky header where useful, text equivalents for status, 44 px row target on touch, horizontal scroll contained within the table, and a stacked key/value fallback below 768 px for short records. Fixed-height tables must not hide the only path to content.

### `Tabs`

Use only for peer content within one route—not primary navigation. Arrow-key navigation follows the ARIA tabs pattern; active tab is not communicated by color alone.

### `Disclosure`

Used for legal detail, methodology detail and dense evidence. Summary text remains meaningful when collapsed. State persists only within the current session where it does not alter domain state.

### `ModalDialog`

Reserved for a blocking confirmation, unresolved conflict or focused evidence preview. It is not used for normal page navigation. Requires labelled title, focus trap, Escape/close action, safe default focus and focus return. No Cluster 1 mockup introduces a destructive modal.

### `Toast`

Only for low-risk transient confirmation with a persistent equivalent in the page state. Errors requiring action stay inline. Toasts pause on hover/focus and are available to assistive technology.

### `ChatMessage` and `ChatComposer`

The native chat input remains preferred. One explicit submit maps to at most one existing provider request. Rerender, theme change, navigation, hover, focus and message expansion map to zero requests. Loading disables duplicate submit and retains the user message.

### `DownloadAction`

Use native download behavior. Label includes format where ambiguity exists, for example `Tải báo cáo PDF`. Downloading an already generated artifact creates zero inference requests.

## 10. Responsive composition rules

| Width | Navigation | Panels | Tables | Actions |
|---|---|---|---|---|
| ≥1440 | 256 px full sidebar | 12-column, max 1104 px content | Full table | Inline where labels fit |
| 1280–1439 | 248 px full sidebar | 12-column | Full/contained scroll | Inline, compact gap |
| 1024–1279 | 72 px rail + drawer | 12-column compact | Contained scroll | May wrap |
| 768–1023 | Drawer | 8-column | Contained scroll or stacked | Wrap below headings |
| 480–767 | Drawer | 4-column | Prefer stacked records | Full-width primary where useful |
| <480 | Drawer | 4-column, 16 px margins | Stacked records | 100% width, 48 px primary |

Content priority, not CSS order alone, determines mobile order. On the Overview page, intake appears before explanatory workflow cards.

## 11. Accessibility acceptance criteria

- Keyboard-only completion of navigation, demo-case selection, file intake, disclosure and retry paths.
- Visible focus for every interactive element, including sidebar items and native widgets.
- Screen-reader landmarks: header, navigation, main, complementary context and labelled regions.
- One H1 per page; headings do not skip levels for visual styling.
- Text contrast ≥4.5:1; large text and non-text UI contrast ≥3:1.
- Zoom to 200% without loss of content or functionality; reflow at 320 CSS px without page-level horizontal scroll.
- Motion respects `prefers-reduced-motion`; no essential meaning depends on animation.
- Status changes are announced once and focus is moved only after a blocking submit error or explicit dialog open.
- Touch targets are at least 44 × 44 px with at least 8 px separation where accidental activation is plausible.

## 12. Verification matrix for future implementation

Each component must be reviewed in Light and Dark at desktop and mobile for:

1. default, hover, focus-visible, pressed and selected;
2. disabled and loading/processing;
3. success, warning and error;
4. long Vietnamese labels and 200% zoom;
5. keyboard order and screen-reader name/role/value;
6. reduced motion;
7. zero network/inference calls from visual-only interactions.

This document specifies the library contract only. Component implementation belongs to later approved clusters.
