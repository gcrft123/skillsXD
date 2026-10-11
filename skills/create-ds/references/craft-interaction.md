# Craft: interaction, focus, and forms

## Hover on touch devices

Touch browsers emulate hover on tap and leave it applied until the user taps elsewhere. A hover style that darkens a card therefore sticks after the tap, and a hover-triggered menu opens on first tap and swallows the intended action.

Gate every hover style:

```css
@media (hover: hover) and (pointer: fine) {
  .button:hover { background: var(--accent-hover); }
}
```

Both conditions matter. `hover: hover` alone is true on some stylus and hybrid devices; `pointer: fine` excludes coarse pointers.

Then give touch its own feedback, because without hover there is nothing until the action completes:

```css
.button:active { background: var(--accent-active); scale: 0.98; }
```

`:active` fires on touch. Keep the press-in instant (no transition) and the release short (~120ms), or the press feels laggy. On iOS, `:active` only fires if the element or an ancestor has a touch listener — attach an empty `ontouchstart` or use `-webkit-tap-highlight-color` deliberately rather than blanking it out and leaving no feedback at all.

Hover-only affordances are forbidden: a delete button that appears on row hover is invisible on touch and to keyboard users until focused. Either show it always at low emphasis, reveal it on focus-within as well, or move it into a menu.

Hit targets: 44×44 CSS px on touch (Apple), 48×48 (Material), 24×24 minimum for WCAG 2.2 SC 2.5.8. Expand the target beyond the visual with padding or a pseudo-element, not by growing the visual:

```css
.icon-button::before {
  content: ""; position: absolute; inset: -8px;   /* 24px visual → 40px target */
}
```

## focus-visible versus focus

`:focus` matches on click, which is why designers ask to remove it. `:focus-visible` matches when the browser thinks a focus indicator is warranted — keyboard, or an input that would benefit.

```css
:focus { outline: none; }
:focus-visible {
  outline: 2px solid var(--focus-ring);
  outline-offset: 2px;
  border-radius: inherit;
}
```

Exceptions where focus should always be visible regardless of input method: text inputs, textareas, contenteditable, and anything where the user needs to know where typing will go. Use `:focus` for those.

Focus ring requirements:

- 2px minimum thickness, 2px offset so it is not confused with a border.
- ≥3:1 contrast against both the component and the background behind the offset gap. See the two-tone ring in `craft-color.md`.
- Visible in forced-colors mode. `box-shadow` is dropped in high contrast, so a shadow-based ring disappears entirely — use `outline`, which is preserved.
- Not clipped. `overflow: hidden` on an ancestor clips an outline with offset; either use `overflow: clip` with `overflow-clip-margin`, or move the ring inside.
- Present on custom controls built from `div`s — those need `tabindex="0"` and explicit ring styles.

`:focus-within` is the tool for a composite control: a text field with an embedded button should show one ring around the whole field.

Do not add a ring to non-interactive containers that receive programmatic focus (a dialog, a heading focused after navigation). Give them `tabindex="-1"` and `outline: none` — the focus is for screen readers, and a ring on a whole panel is confusing.

## Disabled state affordance and explanation

A disabled control with no explanation is a dead end. The user cannot tell whether it is broken, whether they lack permission, or what they must do first.

Rules:

1. **Explain, always.** A tooltip, helper text, or inline note saying why. "Select at least one row to export" is a complete answer.
2. **Prefer `aria-disabled` over `disabled`** for buttons where an explanation exists. `disabled` removes the element from the tab order and blocks pointer events, so the tooltip can never be read by a keyboard user. `aria-disabled="true"` keeps it focusable; block the action in the handler.

```jsx
<button
  aria-disabled={!canSubmit || undefined}
  onClick={(e) => { if (!canSubmit) { e.preventDefault(); return; } submit(); }}
>
```

3. **Native `disabled` is still correct for form inputs** that should not be submitted, since disabled fields are excluded from form data. Pair with `readonly` where the value should still submit.
4. **Visual treatment:** reduce opacity to 0.5–0.6, or drop to muted foreground and a subtle surface. If the label carries information the user still needs, keep it at ≥4.5:1 — WCAG exempts disabled controls from contrast, but a label nobody can read is still a failure of the product.
5. **Cursor.** `cursor: not-allowed`. With native `disabled` this requires a wrapper, since pointer events do not reach the element.
6. **Consider not disabling at all.** Letting the user submit and showing what is wrong is usually better than a button that has been gray for five minutes with no clue why. Disable only when the action is genuinely impossible, not merely premature.

## Empty states

Three different situations, three different messages. Shipping one generic "No data" for all three is the tell that nobody thought about it.

| Situation | Content |
|---|---|
| Nothing created yet | What this area is for, one sentence. The primary creation action. Optionally a sample or template. |
| No results for a query or filter | Echo what was searched. Offer to clear filters. Suggest a correction if one is obvious. |
| No permission | Say so plainly. Say who can grant it. Do not show a create button that will fail. |

Also handle: error (with a retry), and offline (distinct from error).

Keep the illustration small or absent. A large illustration in a small panel reads as filler. The text and the action are what matter.

Empty states belong inside the component (the table's empty state, not the page's), so they inherit the right width and the surrounding chrome stays put.

## Validation timing asymmetry

The rule people internalize as "reward early, punish late":

- **Do not validate while the user is typing for the first time.** Flagging `j` as an invalid email while someone is typing `jane@…` is hostile.
- **Validate on blur**, or on submit, whichever comes first.
- **Once a field has been marked invalid, re-validate on every keystroke** so the error clears the moment it is fixed. This is the asymmetry: slow to complain, fast to forgive.
- **Clear the error on input, not on blur.** Waiting until blur to remove a resolved error leaves the user staring at a message they already fixed.
- **Positive confirmation only where verification is real** — username availability, a card that passed a Luhn check, a file that uploaded. A green check on "you typed something in this required field" is noise.

```js
const [touched, setTouched] = useState(false);
const [error, setError] = useState(null);
const mode = error ? "change" : touched ? "blur" : "none";
```

Async validation needs debouncing (~400ms), a pending state distinct from valid and invalid, and cancellation of stale requests so an old response cannot overwrite a newer one.

Error message content is covered in `voice.md`. Structurally: the message sits below the field, is referenced by `aria-describedby`, the field gets `aria-invalid="true"`, and the message is not the only indicator — an icon or border weight change carries it for color-blind users.

## Focus management on submit failure

When submission fails validation, focus must move, or a keyboard or screen-reader user is left at the submit button with no idea anything happened.

Two acceptable patterns:

**Error summary** (better for long forms): render a list of errors at the top of the form, each a link to its field. Give the container `tabindex="-1"` and focus it. Announce via `role="alert"` or a live region.

```jsx
<div ref={summaryRef} tabIndex={-1} role="alert" aria-labelledby="err-heading">
  <h2 id="err-heading">{count} problems with this form</h2>
  <ul>{errors.map(e => <li key={e.id}><a href={`#${e.id}`}>{e.message}</a></li>)}</ul>
</div>
```

**First invalid field** (fine for short forms): focus it, and `scrollIntoView` with the sticky-header scroll margin from `craft-layout.md`.

Either way: never scroll without moving focus, and never move focus without scrolling into view. Also restore the submit button from its loading state, or the user cannot retry.

For server-side failures that are not field-specific, focus the error banner.

## Focus restoration on dismissal

Every overlay records the element that had focus when it opened and returns focus there on close.

```js
const trigger = useRef(null);
// on open
trigger.current = document.activeElement;
// on close
trigger.current?.isConnected ? trigger.current.focus() : fallback.current?.focus();
```

`isConnected` matters: if the dialog deleted the row containing the trigger, focusing a detached node sends focus to `<body>` and the user loses their place entirely. Fall back to the nearest surviving container — the table, the list, the page heading — and give it `tabindex="-1"`.

Inside the overlay: trap focus (cycle at the boundaries), mark the background `inert` so it is neither focusable nor announced, and close on Escape at the topmost layer only.

Where focus starts when the overlay opens: the first meaningful interactive element, or the dialog container itself if the first element is destructive or if the content needs reading first. Do not autofocus a text input in a dialog on mobile — it raises the keyboard over the content the dialog is trying to show.

The native `<dialog>` element with `showModal()` handles trap, inert, Escape, and the top layer for free, and is worth using unless the animation requirements rule it out. Note that it does *not* handle focus restoration in all browsers — do that yourself.

## Default focus in destructive dialogs

Focus the safe action. A confirmation dialog whose "Delete" button is focused means Enter destroys data, and Enter is what people press to dismiss things.

- Focus Cancel, or the dialog container.
- Put the destructive action where the eye does not land first, and label it with the actual verb and object: "Delete 3 projects", not "OK".
- For genuinely irreversible destruction, require a deliberate act: type the resource name, or hold to confirm. Reserve this for the real ones — applied to everything it becomes noise people learn to bypass.
- Escape must cancel, never confirm.
- Do not auto-dismiss on scrim click for destructive dialogs; a stray click should not resolve a destructive question either way.
- Offer undo instead of confirmation wherever the operation can be reversed. A 10-second undo toast is better UX than a modal, and it is faster for the 99% of cases that were intentional.

## iOS input zoom threshold

Mobile Safari zooms the viewport when a focused input's computed font size is below 16px. The page then stays zoomed, and the layout is broken until the user pinches out.

```css
input, textarea, select { font-size: max(16px, var(--text-sm)); }
```

Or, if 14px inputs are required by the design, scale them visually without dropping below the threshold:

```css
@supports (-webkit-touch-callout: none) {
  input { font-size: 16px; transform-origin: left center; }
}
```

Do not solve it with `user-scalable=no` in the viewport meta. That disables pinch zoom entirely and is an accessibility failure (WCAG 1.4.4).

Check every input-like control, including `select`, date inputs, and any contenteditable.

## Mobile keyboard hinting

Wrong keyboard is a small, constant tax. Set all four attributes.

| Field | type | inputmode | autocomplete | enterkeyhint |
|---|---|---|---|---|
| Email | `email` | `email` | `email` | `next` |
| Password | `password` | — | `current-password` / `new-password` | `done` |
| Phone | `tel` | `tel` | `tel` | `next` |
| URL | `url` | `url` | `url` | `go` |
| Search | `search` | `search` | `off` | `search` |
| Numeric code / OTP | `text` | `numeric` | `one-time-code` | `done` |
| Card number | `text` | `numeric` | `cc-number` | `next` |
| Card expiry | `text` | `numeric` | `cc-exp` | `next` |
| Postal code | `text` | `numeric` (US) / `text` | `postal-code` | `next` |
| Quantity / decimal | `text` | `decimal` | `off` | `done` |
| Name | `text` | `text` | `name` / `given-name` / `family-name` | `next` |
| Street | `text` | `text` | `address-line1` | `next` |
| One-line message | `text` | `text` | `off` | `send` |

Use `type="text"` with `inputmode="numeric"` for codes, card numbers, and anything with leading zeros. `type="number"` brings spinners, silently strips leading zeros, changes value on scroll wheel, and rejects non-numeric input in ways that break paste.

Also set `autocapitalize="none"` and `spellcheck="false"` on emails, usernames, codes, and URLs, and `autocorrect="off"` for Safari.

Autofill is worth real attention: correct `autocomplete` tokens are what make password managers and address autofill work, which is a larger usability win than most component polish.

## Autofill style overrides

Chrome and Safari force a background on autofilled inputs, and `background-color` cannot override it.

```css
input:-webkit-autofill,
input:-webkit-autofill:hover,
input:-webkit-autofill:focus,
input:-webkit-autofill:active {
  -webkit-text-fill-color: var(--fg);
  -webkit-box-shadow: inset 0 0 0 1000px var(--surface);
  box-shadow: inset 0 0 0 1000px var(--surface);
  caret-color: var(--fg);
  border-radius: inherit;
  transition: background-color 600000s 0s, color 600000s 0s;
}
```

The huge transition delay prevents the yellow flash from ever completing. The inset shadow is what actually paints over the forced background — which means an input whose focus ring is also a box-shadow will conflict; another reason to use `outline` for rings.

Dark mode needs its own version of this block, or autofilled fields appear as light bars in a dark form. Test by actually letting the browser autofill; it does not trigger from programmatic value changes.

Firefox uses `:autofill` and is less aggressive; include both selectors. `:autofill` is now standard and worth listing alongside the `-webkit-` prefix.

## Keyboard interaction contracts

Each component has an expected key set; deviating from it is a bug regardless of how it looks. Follow the WAI-ARIA Authoring Practices patterns rather than inventing.

The ones most often gotten wrong:

- **Menu / listbox:** arrows move, they do not tab. Roving tabindex, one tab stop for the whole widget.
- **Tabs:** arrows move between tabs; Tab moves into the panel.
- **Combobox:** Down opens and moves to the first option; Escape closes and keeps the typed text; Escape again clears.
- **Dialog:** Escape closes; Tab cycles; nothing outside is reachable.
- **Tree:** Right expands then descends; Left collapses then ascends; type-ahead.
- **Table with selection:** Space selects, Shift+click and Shift+arrow extend.
- **Slider:** arrows step, Page keys big-step, Home/End go to bounds.

Anything with `onClick` on a non-button must handle Enter and Space and have a role — or, better, be a button.
