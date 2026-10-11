# Craft: typography and optics

## Half-leading and vertical centering

A line box distributes leading equally above and below the text, but glyphs are not centered in the em box — the ascender is taller than the descender is deep, and cap height sits below the ascender. Center a line of text in a box and it lands visually low: roughly 1–2px at body size, 4–6px at display size.

Modern fix:

```css
.text { text-box: trim-both cap alphabetic; }
```

This trims the box to cap height and baseline, after which symmetric padding is actually symmetric. Chrome 133+, Safari 18.2+. Guard with `@supports` and keep a fallback.

Fallback: compute the asymmetry from the font's real metrics and split the padding.

```
contentArea    = (ascender − descender) × fontSize     /* em-relative metrics */
halfLeading    = (lineHeight − contentArea) / 2
spaceAboveCap  = halfLeading + (ascender − capHeight) × fontSize
spaceBelowBase = halfLeading + (−descender) × fontSize
shift          = (spaceAboveCap − spaceBelowBase) / 2   /* push text down by this */
```

For a typical grotesque (ascender 0.97, descender −0.24, cap 0.73) the shift is about 0.5px at 14px and 1px at 24px.

```css
padding-block: calc(var(--pad) - var(--shift)) calc(var(--pad) + var(--shift));
```

Apply anywhere a single line is centered in a fixed-height box: buttons, chips, badges, inputs, single-character avatars, Kbd. The tell that it is missing is an icon-only button and a text button at the same height not looking like siblings.

## Icon-to-text baseline alignment

Icons are centered in their own box; text sits on a baseline. `align-items: center` aligns the icon to the line box, which includes half-leading, so the icon reads high.

Align the icon's optical center to `baseline − capHeight/2` instead.

```css
/* inline, inside a run of text */
.icon-inline { width: 1em; height: 1em; vertical-align: -0.125em; }

/* flex rows: center, then nudge */
.button > .icon { flex: none; translate: 0 var(--icon-optical-nudge, 0.5px); }
```

Derive the nudge once per font from the metrics rather than eyeballing it per component. Verify by putting a text button and an icon+text button side by side: the icon's visual mass should straddle the x-height band, not float above it.

Set `flex: none` on every icon. Without it, flex shrinks the icon before wrapping the label, and a 16px icon quietly becomes a 9px oval.

## Optical alignment

The bounding box is not the shape. Center by mass.

- **Asymmetric glyphs in icon-only buttons.** A play triangle centered by box reads left-heavy; shift it right by 6–8% of its width. Same for chevrons, send arrows, anything with a point.
- **Text with a one-sided icon.** The icon-to-label gap is part of the label block, so padding should be tighter on the icon side: `padding-inline: var(--space-3) var(--space-4)` for a leading icon.
- **Hanging punctuation.** Opening quotes and bullets hang into the margin in pull quotes: `hanging-punctuation: first last` where supported, or a negative `text-indent` on the first line.
- **All-caps labels** sit optically high in a centered box because there are no descenders. Nudge down by ~2% of cap height.
- **Centered text with letter-spacing** gains a trailing gap of one tracking unit. Compensate with a negative inline-end margin on the label span, about `-0.06em` for all-caps.
- **Circles overshoot squares.** A circle needs 2–3% more size than a square to read equal. Matters for avatars, status dots, and round badges next to square ones.

## Optical size compensation

Two separate things share the name. Do both.

**Variable `opsz`.** If the font has an optical size axis, let it run — `font-optical-sizing: auto`, or drive it explicitly with `font-variation-settings: "opsz" <px>`. Small optical sizes get more open spacing and sturdier strokes; large ones tighter fit and finer detail. Without it, display text looks clumsy and small text looks fragile.

**Non-linear stroke scaling.** Icon stroke does not scale linearly with size. Perceived weight follows roughly the square root of scale, so pick per-size values explicitly:

| Icon size | Stroke |
|---|---|
| 12–14px | 1.25px |
| 16px | 1.5px |
| 20px | 1.75px |
| 24px | 2px |
| 32px | 2.25px |
| 48px+ | 2.5px |

Match stroke weight to adjacent text weight, too. 2px strokes next to a 300-weight display face look bolted on.

## Optical tracking by size

Letter-spacing is a function of size. Larger type needs less, smaller type and all-caps need more.

| Size | Tracking | Use |
|---|---|---|
| 11–12px | +0.02 to +0.04em | labels, captions, table headers |
| 13–14px | +0.005em | secondary body, dense UI |
| 15–17px | 0 | body |
| 18–22px | −0.005 to −0.01em | subheads |
| 24–32px | −0.015 to −0.02em | headings |
| 36–48px | −0.025em | display |
| 56px+ | −0.03 to −0.04em | hero |
| all-caps, any size | +0.06 to +0.1em | eyebrows, badges |

Starting points for a neutral grotesque. A geometric face needs more positive tracking at small sizes; a high-contrast serif needs less negative tracking at display sizes. Check against the real font.

Bind tracking to the size token so it cannot be forgotten — that is why `tokens.md` pairs them.

## Tabular figures

Proportional figures are right for prose. Everything that aligns in a column or changes in place needs tabular.

```css
.tabular { font-variant-numeric: tabular-nums; }
```

Apply to: numeric table cells, prices in a list, timers and countdowns, incrementing counters and badges, stat values, chart axes and tooltips, code, timestamps, version numbers, phone numbers, and any number that animates. Do not apply to headlines or running text — tabular figures look gappy there.

Also consider `slashed-zero` for codes and IDs, `lining-nums` if the face defaults to old-style, and any stylistic set the codebase already uses (Inter's disambiguation set, for example).

## Text wrap balancing

```css
h1, h2, h3, h4, .card-title, .dialog-title { text-wrap: balance; }
p, .body, .description { text-wrap: pretty; }
```

`balance` equalizes line lengths, correct for headings up to about six lines, beyond which browsers bail out anyway. `pretty` only fixes orphans and is cheap enough for body copy.

Both are progressive enhancement — a heading must still look acceptable unbalanced. For a heading that must break at a specific point, use `<wbr>` or a non-breaking space rather than `<br>`, so it still reflows when narrow.

## Metric-matched font fallbacks

Web font loading reflows the page unless the fallback occupies the same space.

```css
@font-face {
  font-family: "Inter Fallback";
  src: local("Arial");
  size-adjust: 107%;
  ascent-override: 90%;
  descent-override: 22%;
  line-gap-override: 0%;
}
:root { --font-sans: "Inter", "Inter Fallback", system-ui, sans-serif; }
```

Compute rather than copy: `size-adjust` is the target font's average character width over the fallback's (x-height ratio is a decent proxy); the overrides are the target's `hhea` metrics over units-per-em, divided by `size-adjust`.

`next/font`, `fontaine`, and `@capsizecss/metrics` generate these. If the project uses one, confirm it is actually configured rather than assuming.

Also set `font-display: swap` with a preload for the primary weight, or `optional` if the flash matters more than the font. Self-host if at all possible.

## Rendering details to settle once

```css
body { -webkit-font-smoothing: antialiased; }
```

That makes text lighter on macOS. It is a deliberate aesthetic choice, not a default. If the existing UI does not set it, do not add it — every screen will visibly change. Record the decision in `CRAFT.md`.

Hyphenation: `hyphens: auto` with a correct `lang` on `<html>`, for narrow columns and German. Without correct `lang`, hyphenation is either off or wrong.
