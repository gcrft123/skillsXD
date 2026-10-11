# Craft: layout, spacing, and containment

## Nested corner radius harmony

Concentric rounded rectangles only look right when the inner radius accounts for the padding between them. Same radius on both and the inner corner looks too round; ignore it and it looks too square.

```
inner radius = outer radius − distance between the edges
```

```css
.card {
  --card-radius: var(--radius-lg);
  --card-padding: var(--space-4);
  border-radius: var(--card-radius);
  padding: var(--card-padding);
}
.card > .thumbnail {
  border-radius: max(0px, calc(var(--card-radius) - var(--card-padding)));
}
```

`max(0px, …)` matters: when padding exceeds the outer radius, the correct inner radius is 0, not a negative value.

Where it shows up: images in cards, inputs inside a bordered group, avatars in tiles, buttons in a toolbar, a highlighted row in a rounded table, a selected item in a rounded menu, phone-frame mockups.

The focus ring case is easy to miss. With `outline-offset`, the browser already adjusts the outline's radius. A *shadow* ring does not: `box-shadow: 0 0 0 2px` outside a 6px radius gives an 8px ring, which is right, while an inset ring needs 4px. Prefer `outline`.

If the codebase uses squircle corners, the same relationship holds but visual weight differs — keep the treatment consistent everywhere or nowhere.

## Proximity-based spacing hierarchy

Related things sit closer than unrelated things. Uniform gaps force the user to read to find structure. Each level should be at least 1.5× the one below, ideally 2×.

```
icon → its label            8px
label → its input           6px
helper text → its input     6px
field → field              16px
group → group              24px
section → section          40px
```

The most common violation: a form where label-to-input equals field-to-field, so every label appears to belong to the input above it. The second: a card where title-to-body equals body-to-footer.

Check by blurring a screenshot. If the groups are no longer visible as groups, the hierarchy is not there.

Corollary: when a group has a heading, the space above the heading is larger than the space below it. A heading belongs to what follows.

## Layout shift from borders and state changes

Nothing may resize on interaction.

**Borders on hover or focus.** Adding a 1px border shifts content by 1px. In order of preference:

1. `outline` — never affects layout.
2. A transparent border at rest that gains color.
3. `box-shadow: inset 0 0 0 1px` — but it vanishes in forced-colors mode.

**Font weight on active state.** Bolding the active tab widens it and shifts its neighbors. Reserve the width:

```css
.tab::after {
  content: attr(data-label);
  font-weight: var(--font-bold);
  height: 0; visibility: hidden; pointer-events: none; display: block;
}
```

Animating `font-variation-settings: "wght"` still changes width, so combine with the reservation — or change color and indicator instead of weight.

**Content that appears.** Errors, helper text, badges, and counters all shift the form. Reserve space permanently under an input the user is typing into; elsewhere, animate the collapse so at least the shift is smooth:

```css
.error-slot {
  display: grid; grid-template-rows: 0fr;
  transition: grid-template-rows var(--duration-fast) var(--ease-out);
}
.error-slot[data-visible] { grid-template-rows: 1fr; }
.error-slot > * { overflow: hidden; }
```

**Images and media.** `aspect-ratio` plus `width: 100%`, and explicit `width`/`height` attributes so space is reserved before CSS loads.

**Font swap.** Metric-matched fallbacks, in `craft-type.md`.

## Flex and grid overflow containment

Flex and grid items default to `min-width: auto` and refuse to shrink below their content's intrinsic minimum, so a long unbroken string blows out the layout instead of truncating.

```css
.row > * { min-width: 0; }
.column > * { min-height: 0; }
.grid { grid-template-columns: minmax(0, 1fr) auto; }
```

Apply at the container level in every layout primitive. This is the single most common cause of a mystery horizontal scrollbar.

```css
.truncate { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.clamp-2 { display: -webkit-box; -webkit-box-orient: vertical; -webkit-line-clamp: 2; overflow: hidden; }
.break-anywhere { overflow-wrap: anywhere; }
```

`anywhere` rather than `break-word`, because it also affects intrinsic size calculation, which is what actually prevents the blowout.

Icons, avatars, and badges in flex rows get `flex: none`. The label gets `min-width: 0` and truncation.

## Truncation resilience

Test every component with content three times longer than the comp.

- Truncated text that is the only identifier needs the full value available — `title` at minimum, a tooltip if it matters.
- Truncate the least identifying part. `very-long-project-name-v2.final.tsx` needs middle truncation, which takes two spans or a JS measurement; CSS alone cannot do it.
- Never truncate an error message. Wrap it.
- Prefer multi-line clamp over single-line truncation for descriptions.
- Abbreviate numbers (`1.2k`) rather than truncating them, with the full value in `title`.
- Tables: allow resize, and derive default column widths from content rather than equal fractions.

## Localization text expansion

Design for +35%. German, Russian, and Finnish routinely exceed English by 30–40% at short lengths; a 6-character button label can become 20.

- No fixed-width buttons or tabs. `min-width` is fine, `width` is not.
- Allow two lines in nav items, or define a wrap strategy.
- Test with a pseudo-locale: accent every string and pad 40%. The point is to see the breakage.
- Logical properties everywhere — `padding-inline`, `margin-block`, `border-inline-start`, `inset-inline-end`, `text-align: start`. RTL then comes almost free.
- Mirror directional icons in RTL (`[dir="rtl"] .icon-directional { scale: -1 1; }`); do not mirror object icons.
- Never concatenate sentence fragments. Interpolate whole sentences.
- Dates, numbers, and currency go through `Intl`, never string formatting.

## Scrollbar gutter compensation

Overlay scrollbars take no space; classic scrollbars take 15–17px. Content shifts when one appears or disappears — most visibly when a modal locks body scroll.

```css
html { scrollbar-gutter: stable; }
.scroll-container { scrollbar-gutter: stable; overscroll-behavior: contain; }
```

For centered layouts, `stable both-edges` keeps the centering honest at the cost of a gutter on both sides.

For scroll lock, do not simply set `overflow: hidden` on body — that removes the scrollbar and shifts everything left. Rely on `scrollbar-gutter: stable`, or compensate:

```js
const gutter = window.innerWidth - document.documentElement.clientWidth;
document.body.style.paddingRight = `${gutter}px`;
```

On iOS, `overflow: hidden` on body does not lock scroll at all. Use the position-fixed technique (`position: fixed; top: -scrollY; width: 100%`) and restore scroll on close. Test on a real device — this one is invisible on desktop.

Do not hide scrollbars on scrollable content; that removes the only affordance that content continues.

## Mobile viewport units

`100vh` refers to the *large* viewport with browser chrome hidden, so a full-height element is taller than the visible area and its bottom is cut off.

- `svh` — small viewport, chrome visible. Safe for full-screen sheets and anything with a bottom action.
- `lvh` — large viewport. Rarely what you want.
- `dvh` — dynamic, tracks the chrome. Correct value, but it changes during scroll, so laying out against it causes jitter.

Defaults: `min-height: 100svh` for page shells, `100dvh` only where an element must always exactly fill, and plain `100%` inside a properly sized ancestor whenever possible.

The visual viewport (what the keyboard affects) is separate. To keep an input above the keyboard, read `window.visualViewport` and listen for its `resize` and `scroll`, or set `interactive-widget=resizes-content` in the viewport meta.

## Safe area insets

```html
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
```

Without `viewport-fit=cover` the insets are all zero and the page is letterboxed.

```css
.bottom-bar { padding-bottom: max(var(--space-3), env(safe-area-inset-bottom)); }
.sheet      { padding-bottom: max(var(--space-6), env(safe-area-inset-bottom)); }
.app-bar    { padding-top: max(var(--space-3), env(safe-area-inset-top)); }
.side-rail  { padding-inline: max(var(--space-4), env(safe-area-inset-left)); }
```

`max()` rather than addition, or non-notched devices get double padding. Landscape matters: left/right insets are non-zero on notched phones, and a full-bleed table will disappear under the notch.

Scrims and backgrounds extend *into* the safe area; only content is inset.

## Stacking contexts

A new stacking context traps `z-index` and, worse, traps `position: fixed` — a fixed child of a transformed ancestor positions against that ancestor, not the viewport. That is why a dropdown inside an animated card ends up clipped.

Creating properties: `transform` (any non-`none` value), `filter`, `backdrop-filter`, `perspective`, `opacity` < 1, `will-change` naming any of those, `contain: paint | layout | strict | content`, `isolation: isolate`, `mix-blend-mode` other than normal, `mask`, `clip-path`, `position: fixed`, `position: sticky`, `container-type` other than normal, and `view-transition-name`.

Do not fight it. Portal every overlay to `document.body` and position it with a positioning engine (Floating UI, or the Popover API with CSS anchor positioning). Then the only z-index that matters is the token scale.

Note that an element animating `opacity` gets a stacking context *during* the animation and loses it after, so bugs appear and disappear. Set `isolation: isolate` deliberately in those places rather than letting it flicker.

## Scroll chaining containment

When a scrollable overlay reaches its end, scroll continues into the page behind it.

```css
.modal-body, .drawer, .menu-list, .combobox-listbox { overscroll-behavior: contain; }
```

`contain` stops chaining. `none` also kills the overscroll bounce — useful on horizontal carousels where the bounce fights the swipe, and in a PWA where pull-to-refresh is unwanted.

## Scroll margin for sticky headers

An anchor jump puts the target under the sticky header.

```css
:root { --header-height: 56px; }
[id] { scroll-margin-top: calc(var(--header-height) + var(--space-2)); }
html { scroll-padding-top: calc(var(--header-height) + var(--space-2)); }
```

Setting both covers anchor jumps, `scrollIntoView`, and keyboard focus scrolling. The last matters most: tabbing to a control under a sticky header with no scroll margin hides the focused element entirely.

Also set it inside scroll containers that have their own sticky headers, such as a table with a sticky `thead`.

## Container queries

Where a component's layout depends on its own width rather than the page's, use container queries. A card in a sidebar and the same card in a main column should not need a prop.

```css
.card-host { container-type: inline-size; }
@container (min-width: 28rem) { .card { grid-template-columns: auto 1fr; } }
```

`container-type: inline-size` creates containment and a stacking context — confirm no overlay renders inside.
