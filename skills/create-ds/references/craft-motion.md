# Craft: motion

Motion in a UI exists to explain what changed and where it came from. If an animation does not answer one of those, delete it.

## Directional easing

Easing describes what a thing is doing, physically.

| Situation | Curve | Why |
|---|---|---|
| Entering the screen | ease-out | arrives fast, settles — feels like it was already moving |
| Leaving the screen | ease-in | accelerates away — feels like it is going somewhere |
| Moving within the screen | ease-in-out | starts and ends at rest |
| Continuous / indeterminate | linear | a spinner that eases looks broken |

```css
--ease-out: cubic-bezier(0.16, 1, 0.3, 1);      /* expo-ish; strong settle */
--ease-out-soft: cubic-bezier(0.25, 1, 0.5, 1); /* quart; gentler */
--ease-in: cubic-bezier(0.7, 0, 0.84, 0);
--ease-in-out: cubic-bezier(0.65, 0, 0.35, 1);
```

Never `ease-in-out` for an entrance. The slow start makes the UI feel unresponsive to the click that caused it.

Spring feel, where the design calls for it, comes from `linear()` rather than a bezier, since a bezier cannot overshoot in both position and velocity convincingly:

```css
--ease-spring: linear(0, 0.006, 0.025 2.8%, 0.101 6.1%, 0.539 18.9%, 0.721 25.3%,
  0.849 31.5%, 0.937 38.1%, 0.968 41.8%, 0.991 45.7%, 1.006 50.1%, 1.015 60.2%, 1.004 89.5%, 1);
```

Use springs for direct-manipulation feedback (a toggle thumb, a drag release) and bezier curves for everything else. A spring on a modal entrance reads as bouncy, not as physical.

## Duration scaling with distance

Duration should hold velocity roughly constant, not time. A drawer crossing 400px in 150ms is a teleport; a checkbox crossing 12px in 300ms is sludge.

| Distance / scope | Duration |
|---|---|
| Color, opacity, small state change (≤8px) | 100–150ms |
| Small element (checkbox, switch thumb, chip) | 120–180ms |
| Dropdown, popover, tooltip | 150–200ms |
| Accordion, inline expand | 200–250ms |
| Modal, dialog | 250–300ms |
| Drawer, sheet, full-width panel | 300–400ms |
| Full-screen transition, page | 350–500ms |

Above ~500ms, motion becomes something the user waits through. Below ~80ms, it is not perceived as motion at all — which is fine for a color change and wrong for a position change.

**Exits are faster than entrances**, by roughly 20–40%. An entrance introduces something the user needs to see; an exit is cleanup and should get out of the way. A 300ms modal in exits in 200ms.

**Repeated actions get shorter durations.** A menu the user opens forty times a day should be at the fast end. A destructive confirmation can afford to be slower, because the pause is part of the message.

Scale programmatically where the distance is dynamic:

```js
const duration = clamp(150, 120 + distancePx * 0.4, 400);
```

## Transform origin relative to trigger

A popover that scales from its own center looks like it materialized. One that scales from the point it was summoned from looks like it came out of the trigger.

Set `transform-origin` per resolved placement:

| Placement | transform-origin |
|---|---|
| bottom-start | top left |
| bottom | top center |
| bottom-end | top right |
| top-start | bottom left |
| top | bottom center |
| right | left center |
| left | right center |

Floating UI exposes the resolved placement and the arrow coordinates; derive the origin from those rather than the requested placement, because the popover may have flipped.

The entrance itself:

```css
.popover {
  opacity: 0;
  transform: scale(0.96) translateY(-4px);
  transform-origin: var(--popover-origin);
  transition:
    opacity var(--duration-fast) var(--ease-out),
    transform var(--duration-fast) var(--ease-out);
}
.popover[data-state="open"] { opacity: 1; transform: none; }
```

Scale from 0.95–0.97, not 0.8. A large scale delta reads as a zoom effect. The small translate in the direction of the trigger does most of the perceptual work.

Same principle for other components: a drawer's origin is its edge, a dialog's is the center (or the trigger, if you are doing shared-element transitions), an accordion's is its top edge, a toast's is the corner it lives in.

## Loading indicator delay and minimum display

Two thresholds, both necessary.

**Delay before showing.** If a response returns in 120ms and a spinner appeared at 0ms, the user sees a flash and the UI feels *less* responsive than showing nothing. Wait 200–400ms before showing any loading indicator. 250ms is a good default; use the lower end for things the user just clicked and the higher end for background refreshes.

**Minimum display once shown.** If the spinner appears at 250ms and the response lands at 280ms, it flickers. Once shown, keep it for at least 400–500ms.

```js
function useDelayedLoading(isLoading, { delay = 250, minDisplay = 400 } = {}) {
  const [show, setShow] = useState(false);
  const shownAt = useRef(0);
  useEffect(() => {
    let t;
    if (isLoading) {
      t = setTimeout(() => { shownAt.current = Date.now(); setShow(true); }, delay);
    } else if (show) {
      const elapsed = Date.now() - shownAt.current;
      t = setTimeout(() => setShow(false), Math.max(0, minDisplay - elapsed));
    }
    return () => clearTimeout(t);
  }, [isLoading]);
  return show;
}
```

**Which indicator:**

| Expected wait | Indicator |
|---|---|
| < 250ms | nothing |
| 250ms – 1s | spinner, or inline button spinner |
| 1s – 4s | skeleton matching the incoming layout |
| > 4s | determinate progress, or a message naming what is happening |
| > 10s | progress plus a reassurance line and, if possible, a cancel |

Skeletons only where the shape of the result is known. A skeleton that resolves into a differently shaped thing is worse than a spinner because it lies and then shifts.

Prefer optimistic updates over any indicator where the operation nearly always succeeds and is cheaply reversible. A like button should never spin.

The skeleton shimmer should run on one shared timeline so all skeletons on a page move together; independent per-element animations look like noise.

## Reduced motion

`prefers-reduced-motion: reduce` is requested by people who get motion sickness or vestibular symptoms from movement. It is not a request for no feedback.

Wrong:

```css
@media (prefers-reduced-motion: reduce) {
  * { animation: none !important; transition: none !important; }
}
```

This breaks any code waiting on `transitionend` or `animationend`, which silently strands overlays in a half-open state.

Right: keep the state change, remove the *movement*.

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```

Better still, handle it per component so the result is a crossfade rather than a hard cut:

```css
.dialog {
  transition: opacity var(--duration-normal) var(--ease-out),
              transform var(--duration-normal) var(--ease-out);
}
@media (prefers-reduced-motion: reduce) {
  .dialog { transition: opacity var(--duration-fast) linear; transform: none; }
}
```

Specifically remove: parallax, large translations, scale changes above ~1.1, auto-playing carousels, spinning and orbiting, anything that moves the whole viewport. Keep: opacity changes, color changes, small indicator movements, and progress feedback (a loading bar that does not advance is not accessible, it is broken).

Expose the preference as a token so JS animation libraries respect it too:

```js
const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
```

Also honor `prefers-reduced-transparency` (drop backdrop blurs) and `prefers-contrast: more` (raise border and text contrast, thicken the focus ring) while you are in this part of the stylesheet.

## Animating cheaply

Only `transform`, `opacity`, and `filter` are compositor-friendly. Animating `width`, `height`, `top`, `margin`, or `box-shadow` forces layout or paint on every frame.

For size changes that must animate, use the grid-rows technique from `craft-layout.md`, or a FLIP approach: measure, apply the final state, and animate the inverse transform back to the start.

`will-change` is a last resort and should be applied just before the animation and removed after — a permanent `will-change` promotes a layer forever and costs memory. Prefer letting the browser decide.

For entrances of elements that are being added to the DOM, use `@starting-style` where supported so the transition runs without a double render:

```css
.toast {
  opacity: 1; transform: none;
  transition: opacity 200ms var(--ease-out), transform 200ms var(--ease-out);
}
@starting-style {
  .toast { opacity: 0; transform: translateY(8px); }
}
```

And `transition-behavior: allow-discrete` plus `display: none` in the exit state, so an element can animate out and then actually leave the layout.

## Interruption

Every animation must be interruptible. A menu closed mid-open should reverse from where it is, not jump to fully open and then close. CSS transitions do this naturally; keyframe animations do not. Prefer transitions on state attributes (`data-state="open|closed"`) over `@keyframes` for anything a user can interrupt.

## The timing pass

During Phase 6, open everything in sequence and watch for these specifically:

- An entrance that feels late → the delay is in the JS, not the CSS; or the easing has a slow start.
- Something that "pops" → missing transform origin, or scale delta too large.
- Something that feels heavy → duration too long for the distance, or `ease-in-out` on an entrance.
- Something that feels twitchy → duration under 100ms on a position change, or a spring with too much overshoot.
- A hover that feels sticky → the exit transition is longer than the enter; hover-out should be equal or faster.
- Two elements animating together that arrive at different times → stagger deliberately (30–50ms) or not at all; accidental desync reads as a bug.
