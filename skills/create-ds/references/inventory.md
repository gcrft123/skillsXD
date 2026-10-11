# Component inventory and state matrix

Every component below ships. Variants are props, not separate components — a destructive button is `<Button variant="destructive">`, an alert dialog is `<Dialog role="alertdialog">`, a search bar is `<TextField type="search">`.

If the codebase has no plausible use for something (no charts, no commerce), build it anyway unless the user says otherwise, but build it last and say so. A design system is judged on what happens when someone needs the component you skipped.

## The list

**Foundations** (first — everything depends on them)
Text, Icon, Surface, VisuallyHidden, FocusRing, Portal, Divider, ScrollArea

**Inputs**
TextField, Textarea, Select, Combobox, Checkbox, Radio, Switch, Slider, NumberStepper, TagInput, OTPInput, RichTextEditor, ColorPicker, FileDropzone, DatePicker, TimePicker, Calendar, RatingInput, SegmentedControl, Listbox, Field (owns label, description, error, required marker)

**Actions**
Button, IconButton, SplitButton, FAB, ToggleButton, ButtonGroup, Link

**Navigation**
Tabs, Breadcrumbs, Pagination, Menu (dropdown and context menu share one primitive), Menubar, Toolbar, AppBar, Sidebar, BottomTabBar, CommandPalette, TreeView, Steps

**Overlays**
Dialog, Popover, Tooltip, HoverCard, Drawer, BottomSheet, ActionSheet, Toast, Lightbox

**Data display**
Table, DataGrid, List, DescriptionList, Card, Accordion, Avatar, AvatarGroup, Badge, Chip, Stat, Timeline, Carousel, CodeBlock, DiffViewer, JsonViewer, Kbd

**Media**
Image, VideoPlayer, AudioPlayer, QRCode

**Feedback**
Alert, Banner, ProgressBar, ProgressRing, Meter, Spinner, Skeleton, EmptyState, StatusIndicator

**Charts**
Chart (bar / line / area / pie / scatter as variants), Sparkline, Gauge, Heatmap, plus chart-internal Axis, Legend, ChartTooltip

**Utility**
ResizablePanes, SortableList, DragHandle

## Universal state matrix

Every interactive component implements all of these — implements, and shows in the guide.

| State | Requirement |
|---|---|
| default | Legible at 320px and at 200% zoom |
| hover | Behind `@media (hover: hover) and (pointer: fine)`. Must not change layout |
| active / pressed | Distinct from hover, fires on touch, immediate in and short out |
| focus-visible | Keyboard only. 2px ring, 2px offset, ≥3:1 against both adjacent surfaces |
| focus (input-like) | Text inputs and editable surfaces show focus on click too |
| disabled | Visually reduced *and* explained — see `craft-interaction.md` |
| loading | Preserves width, keeps the label, blocks re-submission |
| readonly | Distinct from disabled: selectable text, no edit affordance |
| selected / checked | Distinct from focus and from hover; survives both |
| indeterminate | Checkbox, progress, tree nodes |
| invalid | Border, message, `aria-invalid`, and a non-color cue |
| valid | Only where verification is expensive and worth confirming |
| empty | Zero items, zero results, zero permission — three different messages |
| skeleton | Box dimensions match the real layout so nothing shifts on resolve |
| open / expanded | Correct `aria-expanded` and a matching animation direction |
| dragging / drop-target | Where reorder or upload applies |

And every component is checked under:

| Condition | Check |
|---|---|
| dark theme | Elevation reads, halation absent, chroma adjusted |
| RTL | Logical properties throughout; directional icons mirrored, object icons not |
| reduced motion | Animation replaced, not deleted; state still changes |
| forced colors | Box-shadow borders vanish — transparent borders required |
| 320px viewport | Nothing overflows or clips |
| 200% zoom | WCAG 1.4.10 reflow |
| 3× content | Long labels, long names, 40-word errors |
| pseudo-localized | +35% string length |
| no JS | Degrades where it can |

## Requirements worth naming

The ones most often gotten wrong.

**Button** — variants primary, secondary, ghost, outline, link, destructive; sizes sm/md/lg plus icon-only at each with a square aspect and an accessible name. Loading keeps the label and swaps the icon slot, or holds width with a hidden label. Icon-only needs a tooltip. A one-sided icon pulls the label off-center: compensate with asymmetric padding, not by centering the box.

**TextField** — a label always exists (visually hidden at minimum; a placeholder is not a label). Description and error wired via `aria-describedby`. The error slot is reserved or grid-animated so appearing does not shift the form. 16px minimum font size on mobile. Full `inputmode` / `autocomplete` / `enterkeyhint` set. Autofill styled.

**Select / Combobox** — type-ahead, Home/End, Escape closes and restores focus, Enter commits. The listbox is portaled, width-matched to the trigger, flipped on overflow, scroll-contained, and closes on outside `pointerdown`, not `click`.

**Checkbox / Radio** — the native input stays in the DOM and is visually hidden, not `display: none`. Label click extends the target. Hit area ≥24×24 even when the box is 16×16.

**Switch** — thumb travel has spring feel but respects reduced motion; reads as on/off without color alone; `role="switch"` with `aria-checked`.

**Slider** — arrows step, Page keys big-step, Home/End bound. Value announced. Thumb hit area larger than the visual. For ranges, decide whether thumbs cross or clamp and document it.

**Dialog** — focus trap, focus restoration, `aria-labelledby`, Escape closes, scrim click closes unless destructive, body scroll locked without shift, portaled, background `inert`. Destructive dialogs focus the cancel action.

**Tooltip** — never the only source of information, never on a non-focusable element. In ~700ms, out ~150ms, with a shared group timer so neighbors are instant. No tooltip on touch, so the information must live elsewhere too.

**Toast** — `role="status"` normally, `role="alert"` for errors. The dismiss timer pauses on hover and focus and does not run at all for errors or anything with an action. Stack capped. Announced once, not on every render.

**Table** — sticky header with correct scroll margin, tabular figures and right alignment on numeric columns, resize handles that do not trigger sort, a caption or `aria-label`, and horizontal scroll that does not chain to the page. Empty, loading, and error states belong to the table, not the page.

**Menu** — roving tabindex, type-ahead, submenu open delay with a safe triangle toward the submenu, Escape closes one level.

**Tabs** — roving tabindex with arrows, `aria-controls`, manual activation unless panels are cheap, and an indicator that animates without the layout shifting when the active label goes bold. Reserve the bold width.

**EmptyState** — three distinct kinds: nothing created yet (primary action), no results for a filter (clear-filters action), no permission (who to ask). One generic empty state is a bug.

**Skeleton** — dimensions derived from real line-height and box, so resolving causes no shift. One shared shimmer timeline, or the page looks like static.

**Chart** — accessible fallback table, direct labeling preferred over a legend, colors that survive both themes and common color-vision deficiencies, and non-color encoding for any series carrying meaning. Tabular figures on axes.

## Recording completion

```
| Component | Built | States | Crafted | In guide |
|---|---|---|---|---|
| Button    |  ✓    |  ✓     |   ✓     |    ✓     |
| TextField |  ✓    |  ✓     |         |          |
```

Not done until all four columns are checked.
