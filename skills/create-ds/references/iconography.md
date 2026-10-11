# Iconography

Always use a library. Hand-drawn one-off icons drift in weight, grid, and corner treatment, and the drift is visible even to people who cannot name it.

## Choosing

**If the codebase already uses a library, use that one** — even if a different one is better. Switching costs every icon a re-check and buys almost nothing.

**If several are in use**, take the one with the most call sites, unless the minority library carries the newer screens the recon identified as the aesthetic reference.

**If icons are raw SVG**, measure ten: viewBox, stroke width, cap and join style, corner radius, filled or stroked, grid consistency. Pick the library that matches those measurements most closely so the swap is invisible.

**If there are no icons at all**, pick by aesthetic fit:

| Library | Grid / stroke | Reads as | Good fit when |
|---|---|---|---|
| **Lucide** | 24px, 2px, round caps and joins | Friendly, neutral, unopinionated | Default choice. Large, maintained, tree-shakeable, works with almost any aesthetic. The living fork of Feather, which is effectively frozen. |
| **Phosphor** | 24px, six weights including duotone and fill | Geometric, slightly playful | You need weight variation, or filled variants for selected states from the same family |
| **Heroicons** | 24 outline, 24 solid, 20 solid, 16 micro | Clean, Tailwind-native | The project is Tailwind-forward; the size tiers map neatly onto dense UI |
| **Radix Icons** | 15px, crisp, minimal | Precise, developer-tool | Dense compact interfaces; pairs naturally with Radix primitives |
| **Tabler** | 24px, 2px | Neutral, utilitarian | You need breadth — one of the largest sets |
| **Material Symbols** | Variable axes: weight, fill, grade, optical size | Android / Google | The product already reads as Material, or you want the `FILL` axis to animate |
| **Remix Icon** | 24px, filled and outlined pairs | Solid, slightly heavier | Content-forward products; strong filled set |
| **Iconoir** | 24px, 1.5px | Light, airy, refined | Editorial or premium feel; thin strokes pair with lighter type |
| **Font Awesome** | Mixed | Legacy, ubiquitous | Only if already present — expensive, and the aesthetic is dated |

SF Symbols is not licensable for web use. Do not use it outside Apple platform apps.

Record the choice and the reasoning in `CRAFT.md`. If swapping libraries, list every icon with no direct equivalent and what it mapped to.

## Using

**One library, one stroke width per size, one grid.** A 1.5px set next to a 2px set is immediately visible in a toolbar.

**Match stroke weight to type weight.** 2px strokes beside a 300-weight display face look bolted on; 1.25px strokes beside a 700 bold disappear.

```
--icon-xs: 12px;  --icon-sm: 16px;  --icon-md: 20px;
--icon-lg: 24px;  --icon-xl: 32px;
```

16px inline and dense, 20px for standard buttons and menus, 24px for nav and touch targets. Do not render a 24px-grid icon at 13px — sub-pixel strokes blur. Use the library's smaller tier if it has one.

**Filled versus outlined is a state, not a style.** Outlined at rest, filled when selected, is a legitimate pattern. Mixing the two arbitrarily within a row is not. Both variants must come from the same family so the silhouettes match.

**Optical size correction.** Icons whose bounding box is fully occupied read larger than sparse ones at the same nominal size; circular icons need 2–3% more size than square ones to read equal. Good libraries handle this within their own set, which is another reason not to mix sets.

**`currentColor`, always.** Icons inherit text color; never hardcode a fill. That is what makes them correct in every state and theme for free.

```jsx
<svg width="1em" height="1em" viewBox="0 0 24 24" fill="none"
     stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round"
     aria-hidden="true" focusable="false" />
```

`width="1em"` lets icons scale with surrounding text, which is right inline. In flex rows where the icon is a sibling of the label, explicit pixel sizes are clearer. Pick one convention per component type and hold it.

**Accessibility.** Decorative icons beside a label: `aria-hidden="true"`. Icon-only controls: an accessible name on the control (`aria-label`), not on the SVG, plus a visible tooltip. Icons carrying meaning alone need a text alternative, usually visually hidden.

**Never animate stroke width** — it repaints. Animate rotation, opacity, or swap the icon.

**Directional icons mirror in RTL**, object icons do not. Arrows, chevrons, undo/redo, next/previous, indent, and text-align mirror. Clocks, checkmarks, and most object glyphs do not.

**Bundle size.** Import individually (`import { Check } from "lucide-react"`), never the barrel default, or the whole set ships. Verify tree-shaking actually works in this project's build by checking the output, not by assuming.

## The Icon component

Wrap the library rather than importing icons into feature code. The wrapper is where size tokens, stroke scaling, `aria-hidden` defaults, RTL mirroring, and `flex: none` live — and it is the seam that makes a future library swap a one-file change.

```jsx
<Icon name="check" size="sm" />
<Icon name="chevron-right" size="sm" directional />
```

Keep a map from semantic name to library icon (`"delete" → Trash2`) so feature code names intent rather than glyph. It also stops the same concept getting three different icons in three places.
