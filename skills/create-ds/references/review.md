# The refinement loop

Phase 6 is not a final check. It is where the work becomes good. Budget real time for it and expect two or three full passes.

Each pass has a stated lens. Looking at everything for everything at once finds nothing; looking at everything for one class of defect finds all of them.

Run `scripts/audit.sh` first — it catches the mechanical failures so human attention goes to what a script cannot see.

## Pass 1 — Optical

Lens: *is this actually centered, actually aligned, actually the same size?*

- Icon-only buttons: is the glyph optically centered, or box-centered? Play, chevron, send, and plus are the usual offenders.
- Text in every fixed-height control: is it sitting low? Compare an icon-only button and a text button of the same height side by side — they should read as siblings.
- Icons beside text: does the icon straddle the x-height, or float above it?
- Circles beside squares at nominally the same size: does the circle read smaller?
- Baselines across a row: do a badge, a label, and a value share a baseline, or are they each centered in their own box?
- Optical size of the same component at different sizes: does the small one look like a shrunk large one, or like a correctly drawn small one? Padding ratios usually need to be looser at small sizes, not proportional.

## Pass 2 — Spacing

Lens: *does the spacing explain the structure?*

- Blur a screenshot. Are the groups still legible as groups?
- Any place where the gap inside a group equals the gap between groups is a defect.
- Heading spacing: more above than below, always.
- Optical versus measured padding: a button with a trailing chevron needs less trailing padding than leading, because the chevron has visual air built in. Same for cards containing images that bleed.
- The compact density: is it actually usable, or did everything collapse into a wall?

## Pass 3 — Timing

Lens: *does every motion explain what changed?*

Open every overlay, menu, accordion, toast, and tab in sequence, several times. Watch for:

| Symptom | Cause |
|---|---|
| Feels late | Delay in JS, or an easing with a slow start |
| Pops into existence | Missing transform origin, or scale delta too large |
| Feels heavy | Duration too long for the distance, or ease-in-out on an entrance |
| Feels twitchy | Under 100ms on a position change, or too much spring overshoot |
| Hover feels sticky | Exit transition longer than the entrance |
| Two things arrive out of sync | Accidental desync — stagger deliberately at 30–50ms, or not at all |
| Spinner flashes | No delay threshold |
| Spinner flickers | No minimum display threshold |

Then run the whole sweep again with reduced motion on. Every state change must still happen, and nothing may be stuck half-open.

## Pass 4 — Color and depth

- Grayscale the page. Are any states now ambiguous? Selected versus hover? Error versus success?
- Deuteranopia and protanopia simulation. Same question.
- Dark theme: does elevation read? Is anything glowing? Is anything pure black or pure white?
- Contrast: every text/surface pair, every border, every focus ring, against every surface it lands on.
- Shadows: is the light source consistent? Is there a contact layer? Is any shadow pure black?
- Gradients: any gray dead zone in the middle? Any banding in a wide, low-contrast one?

## Pass 5 — Resilience

- 320px. Then 280px, which is a real phone width in some markets.
- 200% browser zoom and 400% zoom with reflow.
- Every string replaced with a 3× longer one. Then with a pseudo-localized one.
- Every list rendered empty, with one item, and with 500 items.
- Every async state: loading, error, retry, offline.
- RTL, reading the whole page. Padding, icons, chart axes, progress direction, drawer side.
- Forced colors mode (Windows high contrast). Shadow-based borders will have vanished; check that everything still has an edge.
- Keyboard only, top to bottom, with no mouse. Every control reachable, focus always visible, focus never lost, Escape always doing the least surprising thing.
- Long words with no break opportunity in every text slot — a 60-character unbroken string in a card title, a label, a table cell.

## Pass 6 — Consistency

- Grep the finished library for raw values that drifted outside the tokens (the audit script does this; read the output rather than trusting the exit code).
- Compare every component's border treatment. Do some use a border and others a shadow for the same visual weight?
- Compare every component's transition duration. Do two similar components disagree?
- Compare prop names across components. `isOpen` versus `open`, `onDismiss` versus `onClose`, `variant` versus `kind`, `size` versus `scale`. Pick one and rename.
- Compare label capitalization across all default copy.
- Compare the empty state, loading state, and error state treatments across every component that has them.

## Pass 7 — Thesis

Reread the aesthetic thesis from Phase 1. Walk the guide page with it in mind.

Anything that contradicts the thesis is wrong even if it is objectively nicer. If a shadow appeared in a system whose thesis says "hairline borders instead of shadows," either the shadow goes or the thesis was wrong — and if the thesis was wrong, fix the thesis and re-audit everything against the corrected version. Do not quietly let both coexist.

Last question, and the honest one: **would a screen from the existing app, rebuilt in this system, look like the same product?** If not, the ground truth was not respected somewhere. Find where.

## Stopping

Stop when a full pass produces no changes worth making. Not when the list is exhausted, not when time is up, and not when it feels like enough — those all arrive earlier than the real stopping point.

Then write the closing section of `CRAFT.md`: what was decided, what was deliberately left undone, and what the first three things to fix next are. A system that documents its own known gaps is trusted; one that pretends to be finished is not.
