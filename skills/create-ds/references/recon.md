# Recon

The goal is not a file listing. It is a defensible answer to: *what does this UI already believe, and where does it contradict itself?*

## 1. Stack

Determine and record:

- Framework and version — React, Vue, Svelte, Angular, Astro, plain HTML. Check `package.json`, then confirm by opening a component.
- Styling system — Tailwind (which major version; v4 moves tokens into CSS and may have no config file), CSS Modules, styled-components, Emotion, vanilla-extract, Sass, plain CSS, or a mix. A mix is common and worth mapping: note which parts of the app use which.
- Existing primitives — shadcn/ui, Radix, Headless UI, MUI, Chakra, Mantine, Ant, Bootstrap, or hand-rolled. If a headless library is present, build on it instead of reimplementing accessibility.
- Build tool, TypeScript or not, path aliases, and lint rules that will constrain output.
- Test setup. If component tests exist, match their conventions.

## 2. Component census

Find every file that renders UI. Record path, export name, props, call-site count, and whether it is genuinely reusable or a page-specific chunk that happens to be extracted.

```
rg -l "export (default )?(function|const) [A-Z]" --glob "*.{tsx,jsx,vue,svelte}"
rg -c "<Button" --glob "*.{tsx,jsx}" | sort -t: -k2 -rn
```

Three patterns always show up:

- **Near-duplicates.** `Button`, `PrimaryButton`, `ActionButton`, and a raw `<button className="...">` used 40 times. These are one component; reading all four gives the real variant set.
- **Prop sprawl.** A component with 23 boolean props is several components wearing a trench coat. Split by what the render actually branches on.
- **Inline escapes.** `className="!mt-[13px]"` or `style={{ marginTop: 13 }}` next to a component means its API failed someone. Those escapes are requirements.

## 3. Measured values

Run `scripts/recon.sh`. Read the frequency tables as votes, not law — a value used 60 times in one generated file is one decision, not 60.

Get counts and locations for: hex/rgb/hsl/oklch colors, border-radius, padding/margin/gap, font sizes, weights, line heights, letter spacings, box-shadows, transition durations and curves, z-indices, breakpoints.

Then find the **grid**. If spacing clusters on multiples of 4, the grid is 4. If on 8 with a few 4s, it is 8 with a half-step. If the values are 13, 17, 23, there is no grid and you are about to introduce one — say so explicitly in `RECON.md`, because that is a visible change.

## 4. Typography

- Families, and how they load (self-hosted `@font-face`, Google Fonts, `next/font`, system stack).
- Variable or static, and which axes — `wght`, `opsz`, `slnt`, `GRAD`. An available `opsz` axis changes the guidance in `craft-type.md`.
- Real metrics. Do not guess:

```bash
python3 -c "
from fontTools.ttLib import TTFont
f = TTFont('path/to/font.woff2'); u = f['head'].unitsPerEm
print('upm', u)
print('hhea asc/desc', f['hhea'].ascent/u, f['hhea'].descent/u)
print('typo asc/desc/gap', f['OS/2'].sTypoAscender/u, f['OS/2'].sTypoDescender/u, f['OS/2'].sTypoLineGap/u)
print('cap', f['OS/2'].sCapHeight/u, 'x', f['OS/2'].sxHeight/u)
"
```

These drive half-leading compensation, icon baseline alignment, and metric-matched fallbacks. Record them.

- Fallback stack, and whether any `size-adjust` compensation exists today. It usually does not, which means there is layout shift on font load.

## 5. Icons

Identify the library from imports; count each if several are present. If icons are raw inline SVG, sample ten and measure viewBox, stroke width, cap and join style, corner rounding, filled vs stroked, and grid consistency. That measurement decides which library to standardize on — see `iconography.md`.

## 6. Motion

Collect every `transition`, `animation`, `@keyframes`, and any Framer Motion / GSAP / React Spring config. Most codebases have exactly two values applied without thought. Note that, because it means the motion system is being introduced rather than extracted.

Check for an existing `prefers-reduced-motion` block. Its absence is a finding.

## 7. Accessibility baseline

Just the facts the design system must fix at the source:

- Is `:focus-visible` used, or is there `outline: none` with no replacement?
- Are there interactive `div`s (`onClick` on a non-button)?
- Do inputs have labels, or only placeholders?
- Any `aria-live` regions? Any existing focus trap or dialog implementation?

## 8. The aesthetic thesis

Pick the three or four screens that represent the app at its best — usually the newest, or the one the team demos. Ask the user if unsure; cheap question, high payoff.

Write the thesis as one paragraph of plain description. Useful axes: density, radius, depth strategy, color breadth, gray temperature, contrast, type personality and tracking, motion appetite, and whether separation comes from borders, shadows, or background differentiation.

"Modern and clean" is useless. "Compact, cool-gray, 6px radii, hairline borders instead of shadows, one blue accent used sparingly, Inter with tight display tracking, motion only for overlays" can be checked against any decision.

## RECON.md structure

```markdown
# Recon
## Stack
## Component census          (table: path, name, call sites, verdict)
## Measured values           (frequency tables with counts)
## Typography                (families, metrics, loading)
## Icons
## Motion
## Accessibility baseline
## Inconsistencies worth resolving   (ranked, with proposed resolution)
## Aesthetic thesis          (one paragraph)
## Reference screens         (paths)
```
