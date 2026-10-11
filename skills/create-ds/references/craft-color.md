# Craft: color, depth, and gradients

## Perceptual color uniformity

HSL lies. `hsl(60 100% 50%)` and `hsl(240 100% 50%)` claim the same lightness; yellow is blinding and blue is nearly black. Any ramp built in HSL has steps that feel uneven and hues whose 500 weights do not match.

Build in OKLCH, where L is perceptual lightness and C is chroma.

```css
--blue-500:  oklch(0.62 0.19 258);
--green-500: oklch(0.62 0.15 152);
--red-500:   oklch(0.62 0.20 25);
```

Same L means same perceived weight, so a status badge row reads as a row rather than a ransom note.

Rules:

- **Fix L per step across every hue.** That is what makes `red-600` and `blue-600` interchangeable in a layout.
- **Vary C per hue.** Maximum achievable chroma differs enormously by hue and lightness. Yellow peaks around L 0.85–0.9; blue around L 0.5. Scale the ramp's chroma arc by the hue's achievable maximum instead of using one number.
- **Clamp to gamut explicitly.** An out-of-sRGB OKLCH value gets clipped by the browser in a way that shifts hue. Compute the maximum in-gamut chroma per (L, H) and clamp there. Where P3 is available, provide it and fall back:

```css
--accent: oklch(0.62 0.19 258);                    /* clamped to sRGB */
@supports (color: color(display-p3 1 1 1)) {
  @media (color-gamut: p3) { --accent: oklch(0.62 0.24 258); }
}
```

- **Hue shift slightly across the ramp** if the existing brand does. Many good palettes warm up as they darken (hue rotating a few degrees), which reads as light behavior rather than a tint. Copy whatever the current brand color implies; do not add it from nothing.
- **Contrast is still a separate check.** OKLCH L is not WCAG contrast. Verify every foreground/background pair with an actual contrast calculation: 4.5:1 for body text, 3:1 for large text and for UI component boundaries and focus indicators. APCA is a better model, but WCAG 2 is what gets audited — hit both where they disagree.

## Layered shadows

A single `box-shadow` reads as a sticker. Real shadows have a tight, dark contact region and a broad, soft ambient one, and the opacity falls off as the blur grows.

Recipe: each layer roughly doubles both blur and y-offset while the alpha decreases; add a negative spread so the layers do not simply stack into a gray block.

```css
:root {
  --shadow-color: 250 20% 12%;   /* hue of the surface, not black — see below */
}

--shadow-xs:
  0 1px 1px -0.5px oklch(var(--shadow-color) / 0.06);

--shadow-sm:
  0 1px 1px -0.5px oklch(var(--shadow-color) / 0.06),
  0 2px 2px -1px   oklch(var(--shadow-color) / 0.06);

--shadow-md:
  0 1px 1px -0.5px oklch(var(--shadow-color) / 0.06),
  0 3px 3px -1.5px oklch(var(--shadow-color) / 0.06),
  0 6px 6px -3px   oklch(var(--shadow-color) / 0.06);

--shadow-lg:
  0 1px 1px -0.5px oklch(var(--shadow-color) / 0.05),
  0 3px 3px -1.5px oklch(var(--shadow-color) / 0.05),
  0 6px 6px -3px   oklch(var(--shadow-color) / 0.05),
  0 12px 12px -6px oklch(var(--shadow-color) / 0.05),
  0 24px 24px -12px oklch(var(--shadow-color) / 0.05);
```

**Contact shadow.** The tightest layer — 1px blur, minimal offset, higher alpha — is what makes an element sit on the surface rather than hover above it. Never omit it. A hairline border (`0 0 0 1px` at very low alpha) does a similar job and is often better on light UI.

**Direction.** Pick one light source, from above, and never contradict it. Y-offset positive, X-offset zero. An element that rises on hover increases both offset and blur proportionally.

**Do not animate `box-shadow`** — it repaints. Animate the opacity of a pseudo-element that carries the larger shadow:

```css
.card { position: relative; box-shadow: var(--shadow-sm); }
.card::after {
  content: ""; position: absolute; inset: 0; border-radius: inherit;
  box-shadow: var(--shadow-lg); opacity: 0;
  transition: opacity var(--duration-normal) var(--ease-out);
}
.card:hover::after { opacity: 1; }
```

## Hue-tinted shadows

Pure black shadows look dirty because a real shadow is the surface color under reduced illumination, not an absence of color. Tint the shadow toward the surface's hue and desaturate it.

- On a neutral-cool UI, shadow hue ≈ the neutral ramp's hue, L ≈ 0.2, C ≈ 0.02–0.04.
- On a colored surface (a brand-colored card), tint toward that hue more strongly.
- On a warm/cream UI, a warm brown-gray shadow, never blue-black.

Expose `--shadow-color` as a token so every shadow layer inherits it, and adjust it per theme.

## Dark-mode elevation

Shadows barely register on dark backgrounds — there is no light to subtract. Elevation must come from surface lightness instead.

```
dark surfaces
  --bg              L 0.16
  --surface         L 0.19
  --surface-raised  L 0.22
  --surface-overlay L 0.25
```

About +0.03 L per level. Keep a shadow as well, but a subtle one, and add a hairline top edge that reads as a light-catching bevel:

```css
[data-theme="dark"] .raised {
  background: var(--surface-raised);
  box-shadow:
    inset 0 1px 0 0 oklch(1 0 0 / 0.06),
    var(--shadow-md);
}
```

Never use pure black (`L 0`) as the page background. It makes shadows impossible, maximizes halation, and looks like a void where the UI is floating. `L 0.14–0.18` is the useful range. OLED-black is a deliberate, separate theme if the product wants it.

## Halation

Bright saturated content on a dark field blooms — the eye (and astigmatism, which a large fraction of users have) smears high-contrast edges. Pure white text on pure black is the worst case.

Mitigations:

- Text on dark: `L 0.92–0.96`, not 1.0. Body text can drop to 0.88.
- Background on dark: `L 0.14–0.20`, not 0.0.
- Reduce chroma on saturated elements in dark mode — a `C 0.24` accent that is fine on white is a glowing smear on near-black.
- Avoid large fields of saturated color adjacent to dark backgrounds; use the `-subtle` surface variant (low chroma, near-background lightness) instead of the full-strength accent.
- Thin light strokes on dark bloom more than thick ones; a 1px hairline may need lower alpha in dark mode than its light-mode counterpart at equal contrast.

## Saturation adjustment for dark backgrounds

Do not invert. The dark theme is a separate palette that happens to share hues.

Going from light to dark theme:

- **Raise lightness** of accent colors — a `L 0.55` brand blue disappears on a `L 0.17` background. Move it to `L 0.68–0.75`.
- **Lower chroma** by roughly 15–30%. High chroma at high lightness on dark reads as neon and halates.
- **Recheck contrast in both directions.** The same accent is now foreground where it was background.
- **Semantic colors need more adjustment than the brand.** Red and green at full chroma on dark are the worst offenders; desaturate them harder and lean on `-subtle` backgrounds with light foregrounds rather than solid fills.
- **Borders flip direction.** On light, a border is darker than the surface. On dark, a border is *lighter* — `oklch(1 0 0 / 0.08)` reads better than a darker gray.

## Gradient interpolation color space

`linear-gradient(red, blue)` in sRGB passes through a muddy purple-gray. In OKLCH it passes through the perceptually direct path.

```css
background: linear-gradient(in oklch, var(--from), var(--to));
background: linear-gradient(in oklab, var(--from), var(--to));   /* no hue travel */
```

Use `oklab` for two colors of similar hue or where a hue detour is unwanted, `oklch` when the hue arc is the point. `oklch shorter hue` is the default; `longer hue` sends it the long way around the wheel, which is occasionally what a rainbow needs and usually a mistake.

Fall back for older engines with `@supports (background: linear-gradient(in oklch, red, blue))`.

## Gradient banding and eased alpha ramps

Two separate problems.

**Fade to transparent goes through transparent black.** `linear-gradient(black, transparent)` interpolates the RGB channels toward `rgba(0,0,0,0)`, which in sRGB is fine for black but for any other color produces a gray cast in the middle. Always name the same color with zero alpha:

```css
/* wrong */
linear-gradient(to top, var(--scrim), transparent)
/* right */
linear-gradient(to top, var(--scrim), oklch(from var(--scrim) l c h / 0) )
```

**A linear alpha ramp does not look linear.** Perceived opacity change is fastest at the ends, so a linear scrim has a visible hard edge where it starts. Use an eased stop set approximating a sigmoid:

```css
--scrim-fade: linear-gradient(to bottom,
  oklch(from var(--scrim) l c h / 0)      0%,
  oklch(from var(--scrim) l c h / 0.013)  8.1%,
  oklch(from var(--scrim) l c h / 0.049) 15.5%,
  oklch(from var(--scrim) l c h / 0.104) 22.5%,
  oklch(from var(--scrim) l c h / 0.175) 29.0%,
  oklch(from var(--scrim) l c h / 0.259) 35.3%,
  oklch(from var(--scrim) l c h / 0.352) 41.2%,
  oklch(from var(--scrim) l c h / 0.450) 47.1%,
  oklch(from var(--scrim) l c h / 0.550) 52.9%,
  oklch(from var(--scrim) l c h / 0.648) 58.8%,
  oklch(from var(--scrim) l c h / 0.741) 64.7%,
  oklch(from var(--scrim) l c h / 0.825) 71.0%,
  oklch(from var(--scrim) l c h / 0.896) 77.5%,
  oklch(from var(--scrim) l c h / 0.951) 84.5%,
  oklch(from var(--scrim) l c h / 0.987) 91.9%,
  oklch(from var(--scrim) l c h / 1)     100%
);
```

Same idea applies to `mask-image` fades on scroll containers and text truncation fades.

**Banding** shows up in wide, low-contrast gradients — 8-bit channels cannot express the steps. Fixes: add more intermediate stops (the eased ramp above already helps), or overlay fine noise.

```css
.gradient-surface { position: relative; }
.gradient-surface::after {
  content: ""; position: absolute; inset: 0; pointer-events: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='3'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
  opacity: 0.025;
  mix-blend-mode: overlay;
}
```

Keep the opacity in the 0.015–0.04 range; above that it reads as texture rather than as dither. Remember `mix-blend-mode` creates a stacking context.

## Focus ring contrast

The focus ring must be visible against both the component and whatever is behind it. A single-color ring fails on one of them somewhere. Use a two-tone ring:

```css
:focus-visible {
  outline: 2px solid var(--focus-ring);
  outline-offset: 2px;
}
/* on colored surfaces, the offset gap shows the surface; force a light separator */
.on-accent:focus-visible {
  outline-color: var(--fg-on-accent);
  box-shadow: 0 0 0 4px oklch(from var(--accent) l c h / 0.4);
}
```

Required contrast is 3:1 against adjacent colors (WCAG 2.2 SC 1.4.11 and 2.4.13). Check the ring against the component fill *and* the page background.

## Color is never the only signal

Every state that color communicates also needs a second channel: an icon, a label, a weight change, a border, or a position. Test by rendering the guide page through a grayscale filter — if states become ambiguous, the encoding is insufficient.

```css
/* dev-only */
html[data-sim="gray"] { filter: grayscale(1); }
```

Also simulate deuteranopia and protanopia, which together cover most color-vision deficiency and which make the default red/green success/error pair nearly identical.
