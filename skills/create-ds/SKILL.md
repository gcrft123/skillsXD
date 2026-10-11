---
name: create-ds
description: Build a production-grade design system out of an existing codebase and ship it with an interactive guide page. Recons the repo, treats the UI that already exists as ground truth, extracts tokens and components from it, builds every missing component in the same visual language, covers every state of every component, then runs repeated craft passes over typography, optics, color, elevation, motion, focus, forms, and platform edge cases. Use this skill whenever the user invokes create-ds, or asks to build, extract, formalize, unify, audit, document, theme, or clean up a design system, component library, UI kit, style guide, design tokens, component inventory, or Storybook-like reference — and also for narrower asks that mean the same work, like "make our buttons consistent", "we need design tokens", "our UI is a mess, standardize it", "add dark mode across the app", "document our components", or "build a component library from this app". Budget 45 minutes to 2 hours; do not attempt a fast version.
---

# create-ds

Turn an existing codebase into a design system a team can build on, plus an interactive guide page that demonstrates and documents it.

The defining constraint: **the UI that already exists is ground truth.** This is archaeology before it is design. A correct result makes the existing product look like it was always designed that way. A wrong result is a nice design system that no screen in the app matches.

The failure mode this skill exists to prevent: reading the request, ignoring the codebase, and emitting a generic component library with `rounded-lg` and `shadow-md` everywhere. That is not a design system. It is a replacement, and it gets thrown away.

## Time budget

| Phase | Time | Gate before moving on |
|---|---|---|
| 0. Orient | 3–5 min | Scope and delivery target agreed |
| 1. Recon | 10–15 min | `RECON.md` written, aesthetic thesis stated |
| 2. Tokens | 10–15 min | Token layer emitted in the repo's own format |
| 3. Components | 30–50 min | Every component built, every state implemented |
| 4. Craft pass | 20–30 min | All five craft references applied across the library |
| 5. Guide page | 15–25 min | Guide renders the real components |
| 6. Refine | 15–25 min, looped | A full pass produces no changes worth making |

Under an hour for a small tidy codebase, closer to two for a sprawling one. Do not stop after Phase 3 to ask whether that is enough. Phase 6 is where this crosses from adequate to good, and it is the phase agents skip.

## Deliverables

1. `design-system/RECON.md` — what the codebase does today, with evidence and counts.
2. A token layer in the codebase's own format (CSS custom properties, `@theme`, `tailwind.config.js`, `theme.ts`).
3. The component library, in the codebase's framework and file conventions, every component, every state.
4. `design-system/CRAFT.md` — the craft decisions made, so a human can audit them.
5. An interactive guide page built out of the real components, with canvas plates per component set, live state toggles, and implementation notes.
6. `design-system/PROGRESS.md` — updated at every phase boundary.

## Non-negotiables

- **Do not invent an aesthetic.** Every token value traces to something measured in Phase 1 or derived from it by a stated rule.
- **Do not rewrite working UI wholesale.** Extract, generalize, rewire. Leave app layout and business logic alone.
- **Every state, every component.** A button is not done until default, hover, active, focus-visible, disabled, and loading all exist across every variant × size × icon arrangement, and are visible in the guide.
- **No raw values in component code.** Colors, spacing, radii, durations, shadows, z-indices come from tokens. `scripts/audit.sh` checks this.
- **Nothing ships unchecked** in dark mode, RTL, reduced motion, forced colors, at 320px, and with 3× the expected content.

## Phases

### Phase 0 — Orient (3–5 min)

Find the app. Identify framework, styling approach, package manager, where components live. Then ask at most three questions, batched, and only ones you cannot answer by reading files:

- Where should the system live — a new `design-system/` directory, or an extension of the existing component directory?
- Is there a source of truth beyond the code (a Figma file, a brand guide, one screen they consider correct)?
- Anything off-limits or already being rewritten?

If the user says "just go," pick defaults, record them in `PROGRESS.md`, and continue. Do not block.

### Phase 1 — Recon (10–15 min)

Read `references/recon.md`. Run `scripts/recon.sh` from the repo root. Then read actual code — the script finds frequencies, you find intent.

Write `design-system/RECON.md`. End it with a one-paragraph **aesthetic thesis** in plain language: "Compact, cool-gray, 6px radii, hairline borders instead of shadows, one blue accent used sparingly, Inter at tight display tracking, motion only for overlays." A good thesis is falsifiable and every later decision gets checked against it.

### Phase 2 — Tokens (10–15 min)

Read `references/tokens.md` and `references/craft-color.md`.

Rationalize measured chaos into a scale, documenting every mapping with its evidence. Rebuild ramps in OKLCH for perceptual evenness while pinning them to the existing brand color. Build the dark theme by surface-lightness elevation, not by inversion. Two layers always: primitives and semantics, with components referencing semantics only.

### Phase 3 — Components (30–50 min)

Read `references/inventory.md` for the list and the state matrix, `references/iconography.md` before touching an icon, `references/voice.md` before writing a label, placeholder, or error string.

Per component:

1. **Look for it in the codebase first.** If a `Button` exists, extract it. Diff every call site — those are the real variants.
2. **If near-duplicates exist**, unify them and list what each call site loses, so migration is honest.
3. **If it does not exist**, build it in the established voice: same border treatment, same radius family, same durations, same label capitalization, same prop naming.
4. **Implement every state from the matrix**, and add it to the guide as you go, not at the end.
5. **Write the craft note** into `CRAFT.md` while the reasoning is fresh.

Build in dependency order: tokens → primitives (Text, Icon, Surface, FocusRing, Portal) → controls → composites → overlays → data display → charts. Overlays come after portal, focus trap, and scroll lock are settled.

### Phase 4 — Craft pass (20–30 min)

This is what separates a component dump from a design system. Work through each reference and apply it across everything already built. Each item is a specific defect to hunt for, not a box to tick.

- `references/craft-type.md` — optical alignment, optical size compensation, tracking by size, half-leading and vertical centering, icon-to-text baseline alignment, tabular figures, wrap balancing, metric-matched fallbacks.
- `references/craft-layout.md` — nested radius harmony, proximity spacing hierarchy, layout shift from borders and state changes, flex overflow containment, truncation resilience, localization expansion, scrollbar gutters, viewport units, safe areas, stacking contexts, scroll chaining, scroll margin.
- `references/craft-color.md` — perceptual uniformity, layered and contact shadows, hue-tinted shadows, dark-mode elevation, halation, saturation adjustment, gradient interpolation space, banding and eased alpha ramps.
- `references/craft-motion.md` — directional easing, duration scaling with distance, transform origin relative to trigger, loading delay and minimum display thresholds, reduced motion.
- `references/craft-interaction.md` — hover on touch, focus-visible vs focus, disabled affordance and explanation, empty states, validation timing asymmetry, focus management on submit failure, focus restoration on dismissal, default focus in destructive dialogs, iOS zoom threshold, keyboard hinting, autofill overrides.

### Phase 5 — Guide page (15–25 min)

Read `references/guide-page.md`. Build it out of the real components, importing them rather than reimplementing, so the guide is simultaneously the documentation and the integration test.

### Phase 6 — Refine (15–25 min, looped)

Read `references/review.md`. Run `scripts/audit.sh`. Then the passes a script cannot do: screenshot, timing, spacing, optical, consistency, and thesis. Two or three loops is normal. Stop when a full pass produces no changes worth making, not when you run out of enthusiasm.

## Managing context on a long run

This job is bigger than a comfortable context window.

- Write to files continuously; never hold the system in your head.
- Read reference files at the phase that needs them, not upfront.
- Read call sites with `rg` and targeted line ranges rather than whole files.
- After each phase, update `PROGRESS.md` with enough detail that a cold start could resume from it.
- If context gets tight, finish the current component cleanly, checkpoint, and say so.

## Reference map

| File | Read at |
|---|---|
| `references/recon.md` | Phase 1 — what to look for, how to read intent from code |
| `references/tokens.md` | Phase 2 — token architecture, naming, rationalizing measured values |
| `references/inventory.md` | Phase 3 — the component list and per-component state matrix |
| `references/iconography.md` | Phase 3 — picking and using an icon library |
| `references/voice.md` | Phase 3 — every string in the system |
| `references/craft-type.md` | Phase 4 |
| `references/craft-layout.md` | Phase 4 |
| `references/craft-color.md` | Phases 2 and 4 |
| `references/craft-motion.md` | Phase 4 |
| `references/craft-interaction.md` | Phase 4 |
| `references/guide-page.md` | Phase 5 |
| `references/review.md` | Phase 6 |

| Script | Use |
|---|---|
| `scripts/recon.sh` | Phase 1 — stack detection and value frequency tables |
| `scripts/audit.sh` | Phase 6 — hardcoded values, missing focus-visible, missing reduced-motion, overflow risks |
