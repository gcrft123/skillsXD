# Voice

Every string in a design system is a design decision. Components ship with default copy — placeholder text, error messages, empty states, aria labels, confirmation prompts — and those defaults propagate everywhere. Get them right once.

First: **read the existing product's copy** and match it. If the app says "Sign in," the system does not say "Log in." If the app is terse, the system is terse. Copy voice is part of the aesthetic thesis.

## Baseline rules

**Sentence case everywhere.** Buttons, labels, headings, menu items, table headers, tabs. Title Case Looks Like A Press Release and is harder to scan. The exceptions are proper nouns and product names.

**Buttons are verbs that match the outcome.** "Delete project", not "OK". "Save changes", not "Submit". The user should be able to read only the button and know what happens. This matters most in dialogs, where "OK" forces re-reading the whole prompt.

**Second person, active voice, present tense.** "Your changes are saved" rather than "The changes have been saved by the system."

**No exclamation marks.** No "Oops!" No "Uh oh!" Something failing is not exciting and the tone reads as nervous.

**Contractions are fine.** They match how people read.

**Do not apologize for routine states.** "No results" does not need "Sorry". Save apology for a real failure that was the product's fault.

## Error messages

Three parts, in order: what happened, why if it is useful, what to do next. Drop any part that adds nothing.

| Bad | Good |
|---|---|
| Invalid input | Enter an email address, like name@example.com |
| Error 422 | That file is larger than the 10 MB limit. Try a smaller file. |
| Something went wrong | We couldn't save your changes. Check your connection and try again. |
| Password does not meet requirements | Add a number or symbol — passwords need at least 8 characters with one of each |

Rules:

- **Never blame the user.** "Invalid" and "illegal" are accusations. Say what is needed instead.
- **Never expose internals.** No status codes, stack traces, or table names in user-facing copy. Log those; show a human sentence with a reference ID if support needs one.
- **Put the error next to the cause.** A form-level "Please fix the errors below" without field-level messages is useless.
- **State requirements before failure, not after.** Password rules belong under the field from the start.
- **Say what to do.** An error with no action is a dead end.
- **Never truncate an error.** Wrap it.

## Empty states

Three distinct kinds; a single generic message for all three is the tell that nobody thought about it.

| Kind | Content |
|---|---|
| Nothing created yet | What this area is for, in one sentence, plus the creation action. Optionally a template or sample. |
| No results for a query or filter | Echo what was searched. Offer to clear filters. Suggest a correction if obvious. |
| No permission | Say so plainly, say who can grant access, and do not show a create button that will fail. |

Also: error (with retry) and offline (distinct from error).

## Loading and progress

Say what is happening when you know. "Uploading 3 of 12" beats "Loading…". Past 10 seconds, say something about why it is taking time and, if possible, offer a cancel.

Never claim a step is complete before it is. Never show a fake progress bar.

## Confirmations and destructive actions

- Name the object and the count: "Delete 3 projects?" Not "Are you sure?"
- Say what is lost and whether it is recoverable: "This also deletes 14 files. This can't be undone."
- The confirm button repeats the verb: "Delete projects". The cancel button says "Cancel", not "No".
- Prefer undo to confirmation wherever the action is reversible. A 10-second undo toast beats a modal, and it is faster for the 99% of cases that were intentional.
- Reserve type-to-confirm for genuinely irreversible destruction of shared or expensive things. Applied everywhere, it becomes noise people learn to bypass.

## Labels, placeholders, and helper text

- **A placeholder is not a label.** It disappears on focus, fails contrast, and breaks autofill. Always have a real label, visually hidden at minimum.
- **Placeholders show format, not instruction.** "name@example.com", not "Enter your email".
- **Helper text is persistent, error text replaces it** (or sits beneath it). Do not make the user lose the format hint the moment they get it wrong.
- **Mark the minority.** If most fields are required, mark the optional ones, and vice versa. Marking every field with an asterisk communicates nothing.
- **Never rely on an asterisk alone.** Say "required" in the accessible name.

## Accessible names

They are copy too, and they are the part nobody reviews.

- Icon-only buttons need a name describing the action, not the icon: "Delete comment", not "Trash icon".
- Links named "Learn more" three times on a page are three identical destinations to a screen-reader user. Include the object: "Learn more about billing".
- The visible label should be the start of the accessible name so voice control works ("click save changes").
- `aria-label` overrides visible text — mismatched names break voice control. Prefer `aria-labelledby` pointing at the visible text.

## Numbers, dates, and units

- Abbreviate large counts (1.2k, 3.4M) with the exact value in `title`.
- Relative time for recent ("2 minutes ago"), absolute for older ("Mar 14"), with the full timestamp on hover. Never relative-only for anything auditable.
- Never format dates by hand. `Intl.DateTimeFormat`, always — US and everyone else disagree about 03/04.
- Space between number and unit ("10 MB"), except degrees and percent ("72°", "40%").
- Currency through `Intl.NumberFormat` with the currency code, never a hardcoded symbol.

## Strings live in the component, not scattered

Every default string a component ships is a prop with a sensible default, so a product can override without forking. That is also what makes localization possible later.

```jsx
<Table emptyMessage="No invoices yet" />
<Combobox noResultsMessage={(q) => `No matches for “${q}”`} />
```

Never build sentences by concatenation. Pass whole strings or interpolation functions.
