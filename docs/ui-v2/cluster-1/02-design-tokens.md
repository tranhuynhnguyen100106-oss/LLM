# CreditLens design tokens

## 1. Token model

The token system has three layers:

1. **Core:** brand constants and scales with no UI meaning, such as `brand.navy.700` or `space.4`.
2. **Semantic:** purpose-based Light/Dark roles, such as `color.surface.canvas`, `color.text.primary` and `color.state.warning.foreground`.
3. **Component aliases:** stable roles consumed by a component contract, such as `button.primary.background.default` or `metric.warning.border`.

Implementation must consume semantic/component roles. Direct core colors are reserved for the official co-brand lockup and documented brand moments. This prevents Dark mode, future brand changes and state contrast from depending on scattered hex values.

The companion `design-tokens.json` is a machine-readable handoff only. It is deliberately not imported by the current application in Cluster 1.

## 2. Color principles

- Institutional navy is the primary action/navigation anchor; crimson is a restrained brand/accent color, not a generic error color.
- Status color always appears with an icon and explicit text.
- Text and interactive controls meet at least WCAG 2.2 AA contrast in the specified pairings. Formal full-component validation remains a Cluster 7 gate.
- Dark mode is authored independently. It is not produced by inverting or lowering opacity on the Light palette.
- Evidence uses the semantic information role. Missing information uses neutral/missing, not success or danger.
- `REVIEW READY` means the deterministic workflow is ready for human review; it must never be phrased or colored as loan approval.

## 3. Core brand colors

| Token | Value | Use |
|---|---:|---|
| `brand.navy.900` | `#0B1734` | Dark on-primary text and deepest navy |
| `brand.navy.800` | `#101D40` | Primary pressed |
| `brand.navy.700` | `#172A59` | Primary hover |
| `brand.navy.600` | `#203469` | Official HUB/CreditLens primary |
| `brand.navy.300` | `#8FA6EE` | Dark primary pressed |
| `brand.navy.200` | `#B4C5FF` | Dark primary action |
| `brand.crimson.800` | `#7A111C` | Accent pressed |
| `brand.crimson.700` | `#8C1622` | Accent hover |
| `brand.crimson.600` | `#A71B28` | Official co-brand accent |
| `brand.crimson.300` | `#FF8B98` | Dark accent action |

## 4. Semantic colors — Light

| Token suffix after `color.light.` | Value | Role |
|---|---:|---|
| `surface.canvas` | `#F6F8FC` | Application background |
| `surface.subtle` | `#F1F5F9` | Quiet grouping/header row |
| `surface.muted` | `#E8EEF7` | Disabled/secondary structure |
| `surface.default` | `#FFFFFF` | Main panels and cards |
| `surface.raised` | `#FFFFFF` | Menu/popover/modal surface |
| `surface.inverse` | `#0F172A` | Inverse/high-contrast surface |
| `text.primary` | `#0F172A` | Main text |
| `text.secondary` | `#334155` | Supporting text |
| `text.muted` | `#526071` | Captions/metadata |
| `text.inverse` | `#F8FAFC` | Text on inverse surface |
| `text.disabled` | `#7C899F` | Disabled only |
| `border.subtle` | `#D8E0EC` | Card/table dividers |
| `border.strong` | `#7C899F` | Inputs and emphasized structure; ≥3:1 against default surface |
| `interactive.primary` | `#203469` | Primary action/active nav |
| `interactive.primary-hover` | `#172A59` | Hover |
| `interactive.primary-pressed` | `#101D40` | Pressed |
| `interactive.on-primary` | `#FFFFFF` | Primary content |
| `interactive.accent` | `#A71B28` | Brand/destructive accent where specified |
| `interactive.accent-hover` | `#8C1622` | Accent hover |
| `interactive.link` | `#1D4ED8` | Link/evidence action |
| `interactive.focus` | `#2563EB` | Keyboard focus ring |
| `overlay.scrim` | `rgba(15, 23, 42, 0.52)` | Modal scrim |

## 5. Semantic colors — Dark

| Token suffix after `color.dark.` | Value | Role |
|---|---:|---|
| `surface.canvas` | `#081226` | Application background |
| `surface.subtle` | `#0D1931` | Quiet grouping/header row |
| `surface.muted` | `#182746` | Disabled/secondary structure |
| `surface.default` | `#101D39` | Main panels and cards |
| `surface.raised` | `#142342` | Menu/popover/modal surface |
| `surface.inverse` | `#F8FAFC` | Inverse surface |
| `text.primary` | `#F8FAFC` | Main text |
| `text.secondary` | `#D5DCEC` | Supporting text |
| `text.muted` | `#AEB8CB` | Captions/metadata |
| `text.inverse` | `#0F172A` | Text on inverse surface |
| `text.disabled` | `#7C899F` | Disabled only |
| `border.subtle` | `#33435F` | Card/table dividers |
| `border.strong` | `#64748B` | Inputs and emphasized structure; ≥3:1 against default surface |
| `interactive.primary` | `#B4C5FF` | Primary action/active nav |
| `interactive.primary-hover` | `#C7D3FF` | Hover |
| `interactive.primary-pressed` | `#8FA6EE` | Pressed |
| `interactive.on-primary` | `#0B1734` | Primary content |
| `interactive.accent` | `#FF8B98` | Brand/destructive accent where specified |
| `interactive.accent-hover` | `#FFA6B0` | Accent hover |
| `interactive.link` | `#93C5FD` | Link/evidence action |
| `interactive.focus` | `#93C5FD` | Keyboard focus ring |
| `overlay.scrim` | `rgba(2, 6, 23, 0.72)` | Modal scrim |

## 6. State colors

Each state is a four-part contract: foreground, background, border and icon. Components must use the whole set rather than choosing an isolated color.

### Light

| State | Foreground | Background | Border | Icon |
|---|---:|---:|---:|---:|
| Success | `#166534` | `#F0FDF4` | `#86EFAC` | `#15803D` |
| Warning | `#92400E` | `#FFFBEB` | `#FCD34D` | `#B45309` |
| Danger | `#991B1B` | `#FEF2F2` | `#FCA5A5` | `#B91C1C` |
| Information | `#1E40AF` | `#EFF6FF` | `#93C5FD` | `#1D4ED8` |
| Neutral/missing | `#475569` | `#F8FAFC` | `#CBD5E1` | `#64748B` |

### Dark

| State | Foreground | Background | Border | Icon |
|---|---:|---:|---:|---:|
| Success | `#86EFAC` | `#052E1A` | `#166534` | `#4ADE80` |
| Warning | `#FDE68A` | `#3B2305` | `#92400E` | `#FBBF24` |
| Danger | `#FCA5A5` | `#3B0A0A` | `#991B1B` | `#F87171` |
| Information | `#BFDBFE` | `#0B254A` | `#1D4ED8` | `#60A5FA` |
| Neutral/missing | `#CBD5E1` | `#1E293B` | `#475569` | `#94A3B8` |

### Domain-state mapping

| Domain/UI state | Semantic role | Required label |
|---|---|---|
| `REVIEW READY` | Success | `SẴN SÀNG ĐỂ XEM XÉT` |
| `HUMAN REVIEW REQUIRED` | Warning | `CẦN CON NGƯỜI XEM XÉT` |
| `INSUFFICIENT INFORMATION` | Neutral/missing | `CHƯA ĐỦ THÔNG TIN` |
| Risk `HIGH` | Danger | `RỦI RO CAO` |
| Risk `MEDIUM` | Warning | `RỦI RO TRUNG BÌNH` |
| Risk `LOW` | Information | `RỦI RO THẤP` |
| Risk `INFO` | Neutral/information | `THÔNG TIN` |
| Confidence ≥ 0.90 | Success | `TIN CẬY CAO` |
| Confidence ≥ threshold and < 0.90 | Warning | `CẦN ĐỐI CHIẾU` |
| Confidence < threshold | Danger | `CẦN XÁC MINH` |
| Missing value/source | Neutral/missing | `THIẾU DỮ LIỆU` |

## 7. Verified contrast pairings

These ratios were calculated for the exact foreground/background pairs in this specification.

| Pair | Ratio |
|---|---:|
| Light primary text / canvas | `16.79:1` |
| Light muted text / default surface | `6.42:1` |
| White / Light primary action | `11.95:1` |
| White / Light accent action | `7.42:1` |
| Dark primary text / canvas | `17.84:1` |
| Dark muted text / default surface | `8.37:1` |
| Dark on-primary / primary action | `10.43:1` |
| Dark on-accent / accent action | `7.99:1` |
| Light state foreground/background range | `6.81:1–8.01:1` |
| Dark state foreground/background range | `8.97:1–11.80:1` |
| Light strong border / default surface | `3.54:1` |
| Dark strong border / default surface | `3.51:1` |

Contrast of complete components, charts, images and focus indicators must still be verified in Cluster 7.

## 8. Typography

### Families

| Token | Stack | Use |
|---|---|---|
| `font.family.sans` | `"Be Vietnam Pro", Inter, "Segoe UI", Arial, sans-serif` | All product text |
| `font.family.mono` | `"JetBrains Mono", "SFMono-Regular", Consolas, monospace` | Case IDs, rule codes, page references, tabular audit identifiers |

Be Vietnam Pro is selected for Vietnamese diacritics and institutional clarity. The implementation should package an approved subset or use the fallback stack; render must not depend on a third-party font request.

### Weights

Only `400`, `500`, `600` and `700` are valid. Do not request synthetic 650/720/850 weights.

### Styles

| Token | Desktop size/line | Mobile size/line | Weight | Tracking |
|---|---:|---:|---:|---:|
| `type.display` | 32/40 px | 26/34 px | 700 | `-0.02em` |
| `type.page-title` | 28/36 px | 24/32 px | 700 | `-0.015em` |
| `type.section-title` | 22/30 px | 20/28 px | 700 | `-0.01em` |
| `type.subsection-title` | 18/26 px | 18/26 px | 600 | `0` |
| `type.metric` | 32/40 px | 26/34 px | 700 | `-0.02em` |
| `type.body-lg` | 16/24 px | 16/24 px | 400 | `0` |
| `type.body` | 14/22 px | 14/22 px | 400 | `0` |
| `type.body-sm` | 13/20 px | 13/20 px | 400 | `0` |
| `type.label` | 14/20 px | 14/20 px | 600 | `0` |
| `type.label-sm` | 12/16 px | 12/16 px | 600 | `0.04em` |
| `type.caption` | 12/18 px | 12/18 px | 400 | `0` |
| `type.code` | 13/20 px | 13/20 px | 500 | `0` |

Numeric values use tabular lining figures. Supporting interface text never renders below 12 px.

## 9. Spacing and sizing

The base unit is 4 px.

| Token | Value | Typical use |
|---|---:|---|
| `space.0` | 0 | Reset |
| `space.0_5` | 2 px | Hairline optical adjustment |
| `space.1` | 4 px | Icon/label micro gap |
| `space.1_5` | 6 px | Dense inline gap |
| `space.2` | 8 px | Compact control/card gap |
| `space.3` | 12 px | Dense padding |
| `space.4` | 16 px | Default mobile/card padding |
| `space.5` | 20 px | Tablet gutter |
| `space.6` | 24 px | Desktop gutter/panel padding |
| `space.8` | 32 px | Section gap |
| `space.10` | 40 px | Desktop outer margin |
| `space.12` | 48 px | Major section separation |
| `space.16` | 64 px | Shell-level separation |
| `space.20` | 80 px | Rare hero spacing |

Controls use heights `36 px` (fine-pointer compact only), `44 px` (default and minimum touch target), and `48 px` (prominent/mobile primary). Icons use 16/20/24 px with a 44 px effective icon-button target.

## 10. Grid and breakpoints

| Breakpoint | Range | Columns | Outer margin | Gutter | Shell behavior |
|---|---|---:|---:|---:|---|
| `xs` | 0–479 | 4 | 16 px | 16 px | Mobile drawer; single content column |
| `sm` | 480–767 | 4 | 20 px | 16 px | Mobile drawer; selective two-column micro-layout |
| `md` | 768–1023 | 8 | 24 px | 20 px | Collapsed/drawer navigation; stacked main panels |
| `lg` | 1024–1279 | 12 | 24 px | 20 px | 72 px navigation rail; drawer on demand |
| `xl` | 1280–1439 | 12 | 32 px | 24 px | 248 px sidebar |
| `2xl` | ≥1440 | 12 | 40 px | 24 px | 256 px sidebar; content max 1104 px |

The app canvas may fill the viewport; the principal content column is capped at 1104 px after the sidebar. At 1440 px this is the exact width left by a 256 px sidebar and 40 px main-content padding on both sides. No page-level horizontal scrolling is allowed.

## 11. Radius, border and shadow

### Radius

| Token | Value | Use |
|---|---:|---|
| `radius.none` | 0 | Tables/flush groups where required |
| `radius.sm` | 4 px | Badges, code, compact controls |
| `radius.md` | 8 px | Inputs, buttons, table wrapper |
| `radius.lg` | 12 px | Cards, alerts, nav group |
| `radius.xl` | 16 px | Modal/drawer/large upload panel |
| `radius.full` | 999 px | Status pills only |

### Border

- `border.width.hairline = 1 px`
- `border.width.focus = 2 px`
- `border.width.emphasis = 3 px`
- `border.style.default = solid`
- `border.style.upload = dashed`
- Focus: 2 px `interactive.focus`, 2 px offset, never replaced by a shadow alone.

### Shadow

| Token | Light | Dark | Use |
|---|---|---|---|
| `shadow.none` | `none` | `none` | Default flat structure |
| `shadow.xs` | `0 1px 2px rgba(15,23,42,.06)` | `0 1px 2px rgba(0,0,0,.28)` | Controls |
| `shadow.sm` | `0 4px 10px rgba(15,23,42,.08)` | `0 4px 12px rgba(0,0,0,.32)` | Raised card/dropdown |
| `shadow.md` | `0 12px 28px rgba(15,23,42,.12)` | `0 14px 32px rgba(0,0,0,.40)` | Drawer/popover |
| `shadow.overlay` | `0 24px 56px rgba(15,23,42,.18)` | `0 24px 64px rgba(0,0,0,.52)` | Modal |

## 12. Motion

| Token | Value | Use |
|---|---:|---|
| `motion.duration.instant` | 0 ms | Immediate state |
| `motion.duration.fast` | 100 ms | Press/selection |
| `motion.duration.normal` | 160 ms | Hover/focus/disclosure |
| `motion.duration.slow` | 220 ms | Page/drawer transition |
| `motion.duration.emphasis` | 320 ms | Rare progress/layout transition |
| `motion.ease.standard` | `cubic-bezier(.2,0,0,1)` | General |
| `motion.ease.enter` | `cubic-bezier(0,0,.2,1)` | Enter |
| `motion.ease.exit` | `cubic-bezier(.4,0,1,1)` | Exit |

Movement is functional, non-looping and limited to opacity plus at most 4 px translation. Under `prefers-reduced-motion: reduce`, duration becomes 0 ms and translation/parallax/ambient motion is removed.

## 13. Z-index

| Token | Value | Layer |
|---|---:|---|
| `z.base` | 0 | Page content |
| `z.sticky` | 100 | Header/case context |
| `z.dropdown` | 300 | Select/menu |
| `z.drawer` | 400 | Mobile navigation |
| `z.modal` | 500 | Modal/dialog |
| `z.toast` | 600 | Notifications |
| `z.tooltip` | 700 | Tooltip |
| `z.skip-link` | 800 | Keyboard skip link |

No arbitrary z-index may be introduced outside this scale.

## 14. Canonical names and component aliases

The Markdown name is the design-facing canonical token; the JSON path is its machine-readable equivalent. Implementations must transform names mechanically rather than maintain a second value table.

| Canonical token | JSON path |
|---|---|
| `type.page-title` | `font.style.pageTitle` |
| `type.body-sm` | `font.style.bodySmall` |
| `radius.sm` / `md` / `lg` / `xl` | `radius.small` / `medium` / `large` / `xlarge` |
| `motion.ease.standard` | `motion.easing.standard` |
| `z.sticky` | `zIndex.sticky` |
| `z.skip-link` | `zIndex.skipLink` |
| `color.{theme}.state.error` | `color.{theme}.state.danger` |

`Error` is the component/content term; `danger` is the semantic token key. They are one palette, not two meanings.

The component alias layer resolves to semantic tokens and contains no independent color values:

| Component alias | Resolves to |
|---|---|
| `component.panel.background` | `color.{theme}.surface.default` |
| `component.panel.border` | `border.width.hairline` + `color.{theme}.border.subtle` |
| `component.panel.hover` | `color.{theme}.surface.subtle` + `shadow.{theme}.sm` |
| `component.button.primary.background` | `color.{theme}.interactive.primary` |
| `component.button.primary.foreground` | `color.{theme}.interactive.onPrimary` |
| `component.input.background` | `color.{theme}.surface.default` |
| `component.input.border` | `color.{theme}.border.strong` |
| `component.navigation.selected` | `color.{theme}.surface.muted` + `color.{theme}.interactive.accent` marker |
| `component.alert.info` | `color.{theme}.state.information` four-part set |
| `component.alert.error` | `color.{theme}.state.danger` four-part set |
| `component.focus.ring` | 2 px `color.{theme}.interactive.focus`, 2 px offset |
| `component.upload.border` | 1 px dashed `color.{theme}.border.strong` |
| `component.badge.radius` | `radius.full` |

## 15. Legacy-theme decision

The current application also exposes `Ấm áp` and `Hiện đại`. Cluster 1 defines the requested Light and Dark v2 foundations plus `Theo hệ thống` as automatic selection. Whether Warm/Modern remain separate v2 themes is an explicit approval decision; until then the legacy UI and settings behavior remain unchanged.
