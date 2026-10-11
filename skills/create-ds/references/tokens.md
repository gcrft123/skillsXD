# Tokens

Two layers. Primitives describe values. Semantics describe intent. Components may only reference semantics. That rule is what makes a theme swap possible and what keeps `--blue-500` out of a destructive button six months from now.

```css
--blue-600: oklch(0.55 0.19 258);   /* primitive: a value */
--accent: var(--blue-600);          /* semantic: a role */
--accent-fg: var(--white);
--focus-ring: var(--accent);
```

## Rationalizing measured values

Sort the recon frequencies by count. Values with real usage are real. Values used once or twice are drift and map to their nearest neighbor. Two values within 1px that are both common are the same decision made twice — pick the rounder one.

Record every mapping with its evidence:

| Measured | Count | Token | Note |
|---|---|---|---|
| 6px | 42 | `--radius-md` | dominant |
| 8px | 38 | `--radius-lg` | cards and modals only |
| 7px | 3 | `--radius-md` | drift |
| 9999px | 11 | `--radius-full` | badges, avatars |

Anything visible in the product that changes — a 13px gap becoming 12px — goes in a short "visible changes" list so a human can veto it.

## Spacing

Derive the grid from the data; default to 4px with no signal.

```
--space-0: 0;      --space-px: 1px;   --space-0-5: 2px;
--space-1: 4px;    --space-2: 8px;    --space-3: 12px;
--space-4: 16px;   --space-5: 20px;   --space-6: 24px;
--space-8: 32px;   --space-10: 40px;  --space-12: 48px;
--space-16: 64px;  --space-20: 80px;  --space-24: 96px;
```

Semantic spacing on top encodes the proximity hierarchy from `craft-layout.md`:

```
--gap-inline: var(--space-2);     /* icon to its label */
--gap-related: var(--space-3);    /* label to its input */
--gap-field: var(--space-4);      /* field to field */
--gap-group: var(--space-6);      /* group to group */
--gap-section: var(--space-10);   /* section to section */
```

Density: expose `--density: 1` and multiply control padding by it, so compact mode is one variable rather than a fork of every component.

## Radii

Three to five values plus full. Keep the padding pairs available for the nested-radius rule.

```
--radius-xs: 2px;  --radius-sm: 4px;  --radius-md: 6px;
--radius-lg: 10px; --radius-xl: 16px; --radius-full: 9999px;
```

## Typography

Pair each size with its line height, tracking, and default weight — those travel together, and pairing them is what stops tracking from being forgotten.

```
--text-xs:   0.75rem;  --leading-xs:   1rem;     --tracking-xs:   0.02em;
--text-sm:   0.875rem; --leading-sm:   1.25rem;  --tracking-sm:   0.005em;
--text-base: 1rem;     --leading-base: 1.5rem;   --tracking-base: 0;
--text-lg:   1.125rem; --leading-lg:   1.75rem;  --tracking-lg:  -0.005em;
--text-xl:   1.25rem;  --leading-xl:   1.75rem;  --tracking-xl:  -0.01em;
--text-2xl:  1.5rem;   --leading-2xl:  2rem;     --tracking-2xl: -0.015em;
--text-3xl:  1.875rem; --leading-3xl:  2.25rem;  --tracking-3xl: -0.02em;
--text-4xl:  2.25rem;  --leading-4xl:  2.5rem;   --tracking-4xl: -0.025em;
--text-5xl:  3rem;     --leading-5xl:  1.1;      --tracking-5xl: -0.03em;
```

Ship them as composite text styles (a class or a `Text` variant), not as three props to remember.

## Color

Build ramps in OKLCH so steps are perceptually even. Pin the ramp to the brand color already in use: convert it, find which step it lands on by lightness, generate the rest around it. Do not move the brand color to make the math tidy.

An 11-step ramp with even lightness and a chroma arc peaking mid-scale:

| Step | L | C (relative to hue max) |
|---|---|---|
| 50 | 0.985 | 0.03× |
| 100 | 0.96 | 0.10× |
| 200 | 0.92 | 0.25× |
| 300 | 0.86 | 0.50× |
| 400 | 0.78 | 0.80× |
| 500 | 0.70 | 1.00× |
| 600 | 0.62 | 1.00× |
| 700 | 0.53 | 0.88× |
| 800 | 0.44 | 0.72× |
| 900 | 0.36 | 0.56× |
| 950 | 0.24 | 0.40× |

Chroma must be clamped per hue — yellow and green cannot hold high chroma at high lightness, blue cannot at low. Check every generated value against sRGB and clamp deliberately rather than letting the browser clip and shift the hue. See `craft-color.md`.

Neutrals: pick a temperature and hold it. Cool gray is a fixed hue near 250–265 at chroma 0.002–0.02. Warm gray sits near 60–90. Pure gray is chroma 0. Mixing temperatures across the neutral ramp is the most common reason a UI feels muddy.

### Semantic roles

Define the full set. Missing roles are where hardcoded values sneak back in.

```
--bg, --bg-subtle, --bg-muted
--surface, --surface-raised, --surface-overlay, --surface-sunken
--fg, --fg-muted, --fg-subtle, --fg-on-accent, --fg-disabled
--border, --border-subtle, --border-strong
--accent, --accent-hover, --accent-active, --accent-subtle, --accent-fg
--success / --warning / --danger / --info, each with -subtle, -fg, -border
--focus-ring, --focus-ring-offset
--overlay-scrim
--shadow-color
```

Interactive variants are generated, not hand-picked: hover moves lightness toward the foreground by a fixed delta (0.03–0.04 L), active by double. The direction flips in dark mode — hover gets *lighter* on dark surfaces.

```css
--accent-hover: color-mix(in oklab, var(--accent), var(--fg) 8%);
```

## Elevation

Shadows and z-index are both elevation, so define them together and they cannot disagree.

```
--z-base: 0;       --z-raised: 10;   --z-sticky: 100;
--z-overlay: 1000; --z-modal: 1100;  --z-popover: 1200;
--z-toast: 1300;   --z-tooltip: 1400;
```

Never write a numeric z-index in a component. Shadow recipes are in `craft-color.md`.

## Motion

```
--duration-instant: 100ms;  --duration-fast: 150ms;
--duration-normal: 200ms;   --duration-slow: 300ms;  --duration-slower: 400ms;

--ease-out: cubic-bezier(0.16, 1, 0.3, 1);
--ease-in: cubic-bezier(0.7, 0, 0.84, 0);
--ease-in-out: cubic-bezier(0.65, 0, 0.35, 1);
```

`craft-motion.md` covers which goes where.

## Format

Emit tokens in whatever the codebase already reads.

- **Tailwind v4** — `@theme { --color-accent: …; --radius-md: …; }` in the CSS entry. Tailwind generates the utilities.
- **Tailwind v3** — extend `theme` in `tailwind.config.js` with CSS variables as values (`colors: { accent: 'var(--accent)' }`) so runtime theming still works.
- **CSS Modules / plain CSS** — `:root`, plus `[data-theme="dark"]` and `@media (prefers-color-scheme: dark)`.
- **CSS-in-JS** — a typed `theme.ts` whose values are `var(--token)` strings, keeping CSS as the source of truth so SSR needs no theme round-trip.

Theme switching: `[data-theme]` on `<html>`, with `@media (prefers-color-scheme: dark)` as the default when the attribute is absent. Set the attribute in a blocking inline script before paint or the page flashes. Set `color-scheme: light dark` too, so form controls, scrollbars, and the overscroll area follow.
