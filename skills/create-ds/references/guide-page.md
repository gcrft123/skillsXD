# The guide page

The guide is built out of the real components, imported from the library. It is documentation and integration test at once: if the guide looks right, the system works, and if a component breaks, the guide breaks first.

Do not reimplement components in the guide. Do not screenshot them. Import them.

## Where it lives

- **App with a dev server** — a route (`/design-system`, `/styleguide`), excluded from production routing or gated behind a flag. Best option: real bundler, real theme provider, real fonts.
- **Storybook already present** — write stories, then also build a single overview page, since Storybook's one-component-per-page structure hides cross-component inconsistency, which is exactly what needs to be visible.
- **No app shell** — a standalone page in `design-system/guide/` served by the project's dev server.

State the choice in `PROGRESS.md`.

## Layout

Three regions.

**Left: navigation.** Sticky, scroll-spied, grouped the way `inventory.md` groups components: Foundations, Inputs, Actions, Navigation, Overlays, Data display, Media, Feedback, Charts, Utility. Plus Tokens and Principles at the top. A search or command palette here is worth the fifteen minutes — the guide gets long.

**Center: content.** A stack of sections, one per component or per closely-related set (all buttons together, all text inputs together). Comfortable reading measure for prose, full width for canvases.

**Right: the controls rail.** Sticky global switches that affect the whole page:

- Theme: light / dark / system
- Direction: LTR / RTL
- Density: comfortable / compact
- Motion: normal / reduced
- Contrast: normal / more
- Content: normal / long / pseudo-localized
- Simulate: none / grayscale / deuteranopia / protanopia
- Grid overlay: off / on
- Baseline overlay: off / on

These are the review tools from Phase 6, wired into the artifact. Implement them by setting attributes on the root (`data-theme`, `dir`, `data-density`, `data-content`, `data-sim`) so the components respond exactly as they will in production, not through guide-only CSS overrides.

## The canvas plate

Every component set sits on a canvas — a bounded working surface that reads as a place where specimens are pinned, distinct from the page's own chrome.

```css
.canvas {
  position: relative;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  background-color: var(--bg-subtle);
  background-image: radial-gradient(circle at 1px 1px,
    oklch(from var(--fg) l c h / 0.10) 1px, transparent 0);
  background-size: 8px 8px;
  padding: var(--space-8);
  display: flex; flex-wrap: wrap; gap: var(--space-6);
  align-items: center;
  overflow: clip;
}
```

A dot grid at 8px reads as graph paper and makes misalignment obvious at a glance — which is the point, since a component sitting half a pixel off its neighbors is visible against a grid and invisible against flat white. A checkerboard is the alternative; use it for anything with transparency (scrims, overlays, glass surfaces) so alpha is visible.

Canvas requirements:

- The grid derives from the spacing token, so the guide is checking the system against itself.
- The grid is visible in both themes — use `oklch(from var(--fg) l c h / 0.1)` rather than a fixed gray.
- Canvases can be resized. A drag handle on the right edge, or a width control, so a component can be squeezed to 320px in place. Most responsive bugs are found this way in seconds.
- Each canvas has a small toolbar: the resize control, a "show all states" toggle, and a copy-code button.
- Specimens inside are labeled. A caption under each one, in the smallest text token, muted.

## Section anatomy

Every component section follows the same shape, which makes the guide scannable and makes gaps obvious:

1. **Name and one-sentence purpose.** What it is for, and when to reach for something else.
2. **The default canvas.** The component as it will most often be used.
3. **Variants canvas.** Every variant × size, laid out as a labeled matrix, not a pile.
4. **States canvas.** Every row of the state matrix from `inventory.md`, each labeled. Include the ones that require interaction by forcing them with a data attribute (`data-force-state="hover"`) so they can be seen side by side without the reviewer hovering each one.
5. **Anatomy.** A labeled breakdown of the parts and which token controls each: the padding, the radius, the border, the gap, the focus ring. Rendering this as the real component with pseudo-element annotations beats a static diagram, because it stays true.
6. **Usage.** Do and do not, with real rendered examples rather than prose. Short. Two or three pairs.
7. **Implementation notes.** The craft decisions for this component — half-leading compensation, the origin of the popover's transform, why the disabled state uses `aria-disabled`. This is where `CRAFT.md` content surfaces in context.
8. **Props table.** Name, type, default, description. Generated from types if the project has them.
9. **Code.** A copyable snippet of the common case, plus one of the complex case.
10. **Accessibility.** Keyboard map, roles, what is announced, and what the consumer still has to supply.

Not every section needs all ten — a Divider does not need a props table — but the order should never change. Predictable structure is what makes a long reference usable.

## Token documentation

Ahead of the components:

- **Color:** every ramp as swatches, each showing the token name, the OKLCH value, the hex fallback, and the contrast ratio against the surfaces it is used on. Flag any pair under 4.5:1 in the page itself — a guide that shows its own failures is doing its job.
- **Type:** the full scale rendered in the real font, each row showing size, line height, tracking, weight, and the token name, with a paragraph of real text at each body size. Include a specimen at 320px so the mobile scale is visible.
- **Spacing:** the scale as bars, with a live demo of the proximity hierarchy — the same form rendered with correct and flat spacing, side by side. This one teaches more than any prose.
- **Radii:** each value on a shape, plus a nested-radius demo showing correct and incorrect inner corners at a large size where the difference is unmistakable.
- **Elevation:** each shadow level on the surface it belongs on, in both themes, so the dark-mode lightness elevation is visible next to the light-mode shadow.
- **Motion:** every duration and curve as a replayable animated bar. A curve plotted beside its bar makes the difference between ease-out and ease-in-out legible to people who have never read a bezier.
- **Icons:** the full set in a searchable grid, at every size step, with copy-to-clipboard on the import line.

## Interactivity that earns its place

- **Live state toggles** on each canvas, not just static examples.
- **Prop playground** on the five or six components with real API surface (Button, TextField, Dialog, Table, Toast). Controls for the main props, with the code snippet updating live. Not worth building for all sixty.
- **Copy code** on every snippet, with a confirmation that does not shift layout.
- **Deep links** — every section has an id and the URL updates as you scroll, so a review comment can point at a specific canvas. Remember the scroll margin for the sticky header.
- **Contrast readout** on color pairs, computed live rather than hardcoded, so it stays honest when tokens change.

Skip: fake data dashboards, decorative hero sections, animated page transitions. The guide is a tool.

## The guide is a dogfooding test

Build the guide's own chrome — nav, controls rail, section headers, code blocks, tables — out of the design system's components and tokens. Every gap you hit while building it is a real gap. If the nav needs a tree component that does not exist, that is the system telling you something. If you reach for a raw hex because no token fits, add the token.

Keep a note of every workaround required to build the guide. That list is the most honest backlog the system will ever get, and it belongs at the bottom of `CRAFT.md`.

## Performance

The guide renders hundreds of components at once and will be slow if built carelessly. Virtualize or lazily mount below-the-fold sections, keep the shimmer on one shared timeline, and do not mount every chart at load. A guide that takes eight seconds to become interactive does not get used.
