# Where UI text hides, by stack

`scripts/scan_ui_text.py` covers the common web-framework cases automatically. Use this as a checklist to make sure recon didn't miss a source, and as a guide when the stack isn't one of these.

## React / JSX / TSX
- Text between tags: `<p>Like this</p>`
- Attributes: `aria-label`, `alt`, `placeholder`, `title`
- Conditional/ternary strings inside `return` blocks — the scanner's regex won't always catch these; skim components with a lot of conditional rendering by eye.
- Toast/notification calls: `toast(...)`, `notify(...)`, `showNotification(...)`

## Vue / Svelte
- Template text nodes, same as JSX.
- `:aria-label`, `:placeholder`, `:title` bound attributes — check both the static and bound forms.

## Plain HTML / server-rendered templates (Django/Jinja, Rails ERB, PHP)
- Text nodes and the same attribute set as above.
- Flash/session messages set server-side and rendered into a template — search for `flash(`, `messages.add(`, or the templating language's message-rendering tag, since these often live in controller/view code rather than the template file itself.

## i18n / locale files
This is the most commonly under-scanned source, because the actual copy lives in data files, not component code. Look for directories named `locales/`, `i18n/`, `lang/`, `translations/`, or `messages/`, containing `.json`, `.yml`/`.yaml`, or `.po` files.
- If a project uses i18n, **the locale file is the source of truth for a string** — a component like `t('checkout.error')` doesn't contain the actual text at all. Confirm this before flagging component-level strings as candidates; look up the key instead.
- Only the base/source locale (commonly `en` or `en-US`) needs a rewrite. Note in the review table that other locales will need a follow-up translation pass.

## iOS / Android (if the project includes a mobile app)
- iOS: `Localizable.strings`, or inline `Text("...")` / `String(localized:)` in SwiftUI.
- Android: `res/values/strings.xml`, or literal strings passed to Compose `Text(...)`.
- The scanner does not cover these; search by hand using the same classify criteria from SKILL.md.

## CLI tools
- Help text (usually defined via the argument-parsing library's `help=` kwargs or similar), usage strings, and any text printed to stdout/stderr that a user (not a developer debugging the tool) would read.

## Validation libraries
- Schema-based validation (zod, yup, joi, and similar) often defines the error message inline in the schema, e.g. `z.string().min(1, "Required")`. These render directly in forms and are easy to miss because they don't look like "UI code."

---

# Apply-schema

`scripts/apply_rewrites.py` takes a JSON file listing every row the user approved, in this shape:

```json
[
  {
    "file": "src/features/checkout/PaymentForm.tsx",
    "line": 42,
    "old": "Invalid input",
    "new": "Enter a valid card number",
    "action": "rewrite"
  },
  {
    "file": "src/features/onboarding/Welcome.tsx",
    "line": 12,
    "old": "Let's get you set up!",
    "new": "Let's get you set up!",
    "action": "keep"
  }
]
```

- `file` and `line` come straight from the scanner's manifest — don't retype them from memory, copy them.
- `old` must match the current file content on that line exactly (or the apply step will report drift and skip it).
- `action: "rewrite"` performs the replacement and marks the manifest entry `rewritten`. `action: "keep"` makes no file change but marks the manifest entry `kept`, so it won't be re-flagged on the next scan even though the surrounding file may change for unrelated reasons later. When `action` is `"keep"`, `new` can just repeat `old`.
- Batch every approved row from a single review round into one JSON file and run the script once — it reports a per-row result (`applied`, `skipped_drift`, `skipped_missing`) so you can see exactly what to fix by hand.
