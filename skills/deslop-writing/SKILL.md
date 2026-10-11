---
name: deslop-writing
description: Recon every piece of user-facing text in a UI or codebase (buttons, labels, errors, tooltips, empty states, confirmations, placeholders, toasts, onboarding copy) and flag anything unclear, wordy, leaking development/internal details, or reading like AI-slop or marketing filler. Produces a table of current-vs-recommended text split into sections, with a reason for each flagged string, then asks whether to apply everything, apply specific sections, or revise specific rows before touching any file. Trigger this when the user invokes deslop-writing by name, and also whenever the user asks to audit or clean up UI copy, review interface text, fix confusing error messages or button labels, make an app's copy sound less like AI wrote it, or do a pass over user-facing strings across a project — even if they never say the word "slop."
---

# Deslop UI Writing

This skill runs in three phases: **recon** (find every string a user would actually see), **classify** (decide keep-or-rewrite for each one, with a reason), and **apply** (only after the user signs off, and only to the rows they approved).

The point of splitting it this way: rewriting UI copy without review is how you end up with confidently wrong guesses about tone, or copy that breaks because it silently dropped an interpolated variable. The table is the safety net. Nothing gets written back to a file until the user has seen it in that table and said go.

## Phase 1: Recon

### What counts as user-facing text

Anything a person using the product would read: button and link labels, headings and body copy, form labels and placeholders, validation and error messages, empty states, loading/progress text, toasts and notifications, confirmation and destructive-action dialogs, tooltips and help text, menu and nav items, onboarding and empty-inbox copy, alt text and aria-labels, email/notification templates, and — if the "UI" is a CLI — help text and prompts.

Not in scope unless the user asks for it: code comments, log statements, variable/function names (except where a name has clearly leaked into something a user sees — see the dev-leak category below), commit messages, and internal admin/debug-only tooling meant for engineers rather than end users.

### Don't sample — cover everything

Read every file under the app's UI/frontend directories, not a representative handful. `scripts/scan_ui_text.py` narrows the codebase to candidate lines, but **treat it as a file-narrowing tool, not a string-finding one.** It is a syntactic search: it catches false positives (code fragments, non-UI strings) and it misses real copy.

**The miss that matters is prose.** The scanner's line-based patterns cannot see a multi-line JSX/template text node, which is the normal shape of every sentence in a component:

```jsx
<p>
  Another tab saved this{" "}
  {ago(meta.updatedAt)}. Nothing has been overwritten.
</p>
```

A prose pass was added to cover this, but it is still heuristic. On the run that prompted it, the line-based patterns alone returned 231 candidates and missed **all thirteen** of the strings that turned out to carry the most slop — every long sentence, every onboarding body, every warning. Short labels and `aria-label` attributes were found; nothing that reads like writing was.

So: run the scanner, then **open the components and read the prose yourself.** A file with 2,000 lines and 20 candidates has not been scanned, it has been sampled. If a directory of screens comes back nearly empty, that is a scanner failure, not a clean codebase.

Read `references/file-patterns.md` for where text tends to hide by framework (React/JSX, Vue, Svelte, plain HTML/templates, i18n locale files, iOS/Android, backend-rendered templates) — it's worth a look even on a stack the scanner already covers, because i18n files in particular are easy to under-scan.

### Two checks before you classify anything

**1. Is the code reachable?** Copy in a component nothing renders is not user-facing, and reviewing it wastes the user's attention on edits that change nothing. Before a file's strings reach the table, confirm something imports it:

```bash
grep -rn "ComponentName" src --exclude-dir=node_modules | grep -v "ComponentName\.\|\.test\."
```

Watch for a component whose *stylesheet* is imported while the component itself is dead, and for vendored design systems where most exports are unused. On one run this would have put 587 lines of dead component copy into the review. Report dead files as a separate finding — that's a real thing the user wants to know — but keep them out of the copy table.

**2. What conventions already exist?** Assume the project has house rules and find them before writing a single rewrite:

```bash
# copy rules enforced as tests - these will fail if you break them
grep -rln "voice\|tone\|copy\|lower case\|lowercase\|em dash\|—" --include="*.test.*" src
# a style or design document
ls DESIGN.md STYLE.md CONTRIBUTING.md .github/ 2>/dev/null
```

A codebase careful enough to need this skill often encodes its voice in tests. One run broke two — tour lines must start lowercase, and em dashes are banned product-wide — and only found out when the suite went red *after* applying. Write the rules down during recon, and check every rewrite against them.

Conventions are not automatically right; a deliberate rule can still be the thing making the copy feel mannered. But breaking one has to be a decision you surface, not an accident.

### Reuse prior recon instead of starting over

The scanner keeps a manifest at `.deslop-writing/inventory.json` in the project root. Before scanning:

- **No manifest exists** → run a full scan: `python scripts/scan_ui_text.py <project_root>`
- **Manifest exists** → run it again the same way; it hashes each previously-scanned file and only re-scans files that changed, while still surfacing any string left over from a prior run that was never reviewed (status `unreviewed`). This is what "if not done already" means in practice — don't re-litigate strings the user already approved, kept, or rewrote in a previous pass; only review what's new or changed, plus anything still pending.
- Force a full re-scan regardless of the manifest with `--full`, if the user asks for a fresh look at everything.

The scanner prints a JSON summary (files scanned, candidates found, how many are still unreviewed) and updates the manifest on disk. Read that JSON to know what you're about to classify.

## Phase 2: Classify

### Step 1 — read the corpus as prose, before judging any single string

**Do this first. It is the step most likely to be skipped and the one that decides whether the pass is any good.**

Collect the strings into one document and read them end to end, as writing. You are looking for *recurring habits*, not defects: the same sentence shape appearing twenty times, a register that drifts, a mannerism.

This matters because **the worst slop is invisible one string at a time.** Judged alone, "A heading is a chart." passes every test below — short, unambiguous, concrete. It is only slop once you have also read "Two columns at once is where a question lives", "the chart answered", and "it wrote all of that down", and can see the app has an aphorism habit and narrates itself as a character.

A per-string pass on that codebase flagged 14 of 361 strings and declared the rest fine. The user's reply was "No. Everything uses slop grammar, phrases, pacing." They were right, and the method was what failed — not the judgment on any individual row. The real count was 109.

Tics worth naming explicitly, because each one recurs across dozens of strings once it exists:

| Tic | Looks like |
|---|---|
| **Aphorism** | "A heading is a chart." Sentences built to sound wise rather than to inform. |
| **Anthropomorphism** | "the chart answered", "it saved itself", "every mark answers the pointer" |
| **Trailing rationale** | Nearly every sentence ending ", which is…" / ", so…" / ", and it is…" |
| **Comma splice** | "The reshape could not be applied, that formula is invalid" |
| **Register drift** | Lowercase fragments in one surface, sentence case everywhere else |
| **Uniform cold opener** | Fifteen errors all starting "That file…", "That link…", "That did not work." |
| **No contractions anywhere** | "could not", "does not", "cannot" — reads stiff and formal at scale |

Write the tic list down and state it to the user before the table. Then classify **against those tics** as well as the categories below. A row's reason may simply be the tic name.

### Step 2 — decide per string

For every candidate, choose: **keep**, **rewrite**, **shorten**, or **delete**. Bias toward flagging — the review table is the safety net, so a false positive costs the user one glance at a row they'll mark "keep." A missed instance ships.

**Keep as-is** when the text is already the shortest correct form: `Delete`, `Cancel`, `Save changes`, a field label like `Email`. Don't pad the table with these.

**Never expand a string that is already a standard UI phrase.** "read-only." is finished. Rewriting it to "You can read it, but not change it." is a regression dressed up as a fix, and it is an easy one to make when you are in rewriting mode and working down a list. Before every rewrite, check you are not lengthening something conventional.

**Flag for rewrite** when a string is any of:

1. **Confusing** — the reader can't tell what it means or what happens next without guessing. Vague errors ("Invalid input"), ambiguous confirmations ("Are you sure?"), pronouns with no clear antecedent, jargon the audience won't know.
2. **A development leak** — anything that exposes the machinery behind the UI to someone who shouldn't see it: raw HTTP status codes or stack traces, `undefined`/`null`/`NaN` rendered as text, literal `TODO`/`FIXME`/`Lorem ipsum` placeholders, internal IDs, variable or feature-flag names, raw API error strings passed straight through to a banner.
3. **Slop** — corporate or AI-flavored filler that says less the more words it uses: buzzword vocabulary (leverage, unlock, seamless, robust, elevate, empower, cutting-edge, revolutionize), throat-clearing ("Please wait while we process your request"), inflated marketing tone on a plain action ("Unlock Your Personalized Dashboard Experience" on a button that just navigates), forced enthusiasm ("Oops! Something went sideways! 🎉").
4. **Wordy** — says in a sentence what a phrase would say just as clearly ("Click here to view all of your account settings and preferences" → "Account settings").
5. **Contradicted by the code** — the copy makes a claim the implementation doesn't honour. This one you cannot find by reading strings; you have to read what the handler does. Two real examples from one pass: a conflict banner reading "Nothing has been overwritten" sat directly above a button whose handler discarded the user's edits, and a delete tooltip read "Delete" on a control that deleted server-side with no confirmation and no undo. Both are more serious than anything stylistic in the same review. When you flag one, **say plainly whether copy alone fixes it** — for the delete, it doesn't; it needs a confirm step, and shipping a better label would disguise the problem.
6. **Unnecessary** — the sentence is accurate and well-written and should not exist. See "Shorten or delete" below.

Read `references/slop-patterns.md` for the full catalogue with more examples per category — it's meant to be a reference you check while classifying unusual cases, not something to read start to finish first.

### Step 3 — shorten or delete

Run this as a separate pass, because rewriting and cutting are different mental modes and doing them together produces rewrites that faithfully preserve length. Ask two questions of every flagged string:

**Is there a conventional phrase for this?** Bespoke labels cost the reader more than standard ones. `Leave full screen` → `Exit full screen`. `In order of` → `Sort by`. `By` → `Group by`. `Only me` → `Private`. `Load the newer version` / `Keep mine separately` → `Use theirs` / `Keep mine`. `natural order` → `Original order`.

**Does this sentence need to exist at all?** The common shape is one sentence stating a fact followed by one explaining why — where the second is the tool narrating its own reasoning to someone who did not ask:

- "5 charts is the most that fit. ~~Past this you are scrolling rather than comparing.~~"
- "Every blank takes the value from the row above. ~~Use it on a table that writes a heading once and leaves the rest of the group blank.~~"
- "Showing 12 of 40 values. ~~Search to reach the rest.~~" (the search box is directly above it)

Also delete outright: text that explains the absence of something ("There is no chart menu to find first"), captions restating what a visible control already shows, and competitive claims in places a user is trying to get work done.

Do keep full length for the few strings that tell the user something the screen genuinely does not: real statistical cautions, security warnings, destructive-action consequences.

On the run this guidance came from, the cut pass found **35 further changes after the rewrite table was already complete** — 15 whole-sentence deletions and 5 outright removals — and the user had to ask for it. Offer it unprompted.

### Examples

| Current | Issue | Recommended | Why |
|---|---|---|---|
| "Error: Request failed with status code 500" | Dev leak | "Something went wrong on our end. Try again in a minute." | User can't act on a status code; this tells them what to do instead. |
| "Invalid input" | Confusing | "Enter a valid email address (e.g. name@example.com)" | Doesn't say what's invalid or how to fix it; the fix belongs in the message. |
| "Unlock Your Personalized Dashboard Experience" (button) | Slop | "Go to dashboard" | It's a navigation button. Say where it goes. |
| "Are you sure?" [Cancel] [OK] | Confusing | "Delete this project? This can't be undone." [Cancel] [Delete project] | "OK" doesn't say what it confirms; restate the action on the button itself. |
| "No data" | Dev leak / confusing | "No projects yet — create your first one to get started." | Reads like a debug placeholder; doesn't tell the user what to do next. |
| "Please wait while we process your request..." | Wordy / slop | "Saving…" | Same information, a third of the words. |
| placeholder="Enter value" | Confusing | placeholder="MM/DD/YYYY" | Tells the user the expected format instead of restating that a value is expected. |
| "Leverage our robust analytics suite to unlock actionable insights" (tooltip) | Slop | "See how your site is performing" | Buzzword string that describes nothing concrete. |
| "Click here to view all of your account settings and preferences" | Wordy | "Account settings" | Nav/menu copy should be as short as it can be while staying clear. |
| "Delete" | — | *(keep)* | Already exactly as short and clear as it needs to be. |

## Presenting the review

Group flagged strings into sections that match how the user would actually want to approve them in chunks — usually by feature or page (`Checkout`, `Onboarding`, `Settings`), falling back to by-file if the project isn't organized by feature. Only list rows that need action; state the keep-count once in a summary line rather than listing every kept string.

Use this shape:

```
## UI copy review — <project>

Scanned <N> files, found <M> user-facing strings. <K> are already clear
and concise and need no change. <F> are flagged below across <S> sections.

### 1. <Section name> (`path/to/dir/`)

| Location | Current | Issue | Recommended |
|---|---|---|---|
| `File.tsx:12` | "..." | ... | "..." |

### 2. <Section name> (`path/to/dir/`)
...

---
Reply with **"apply all"**, **"apply sections 1, 3"**, or point me at specific
rows to revise (e.g. "row 2 in section 2, make it shorter").
```

Lead the table with the tic list from Step 1, so the user can judge the diagnosis before the 200 rows that follow from it. Flag any row that breaks a house convention you found in recon, and say which.

Then stop and wait. If an interactive input tool is available, you can offer the three choices as tappable options — either way, don't apply anything yet.

### What counts as approval

Only an instruction to *apply* is approval. A reply that **widens the scope** is a re-scope, and it sends you back to Phase 2 with a bigger net — not forward to Phase 3.

"Rewrite absolutely every bit of text" means *the table was too small*. It does not mean *start editing*. Reading it as approval and beginning to apply earns an interruption, and rightly:

> — No. Rewrite absolutely every bit of text.
> — *(starts applying)*
> — Nooooo give me the complete table first

If you have already applied anything when this happens, revert it (`git checkout -- <files>`) and say so plainly before presenting the new table.

### When the user says "rewrite everything"

Take it seriously and widen hard — but don't manufacture rows. A real UI contains many strings with no grammar, cadence, or tic to fix: `Cancel`, `Median`, `df`, `Formula`, `Copied`, column headers. Rewriting those is churn that buries the real changes.

State the split in one line and move on — "361 strings; 109 carry the voice and are rewritten below; 252 are bare labels with nothing to fix" — with two or three examples of the irreducible kind. Say plainly that you can't make `Median` less sloppy. Don't use this as cover for a thin pass: if the flagged count is under ~20% on a codebase the user says reads as slop throughout, Step 1 was done badly.

## Phase 3: Apply approved rewrites

Handle the three possible replies:

- **Apply all** → every flagged row across every section.
- **Apply specific sections** → filter to just those sections; leave the rest pending in the manifest for a later pass.
- **Revise specific rows** → redraft only those rows based on the user's feedback and re-present just that section's table before applying anything. Don't silently apply the rest of an unreviewed table alongside a revision request.

Before writing changes, check whether the project has an i18n setup (`references/file-patterns.md` explains how to spot one). If it does, the rewrite belongs in the locale/translation file, not in the component that calls `t('key')` — editing the component would change nothing a user sees. The scanner already resolves locale-file candidates down to a file + line, so this is usually automatic; just don't be tempted to "fix" the component call site instead.

Write approved rows to a JSON file matching the schema in `references/file-patterns.md`'s "apply schema" section, then run:

```
python scripts/apply_rewrites.py <manifest_path> <approved_json_path>
```

This does an exact-match replace on the specific file and line recorded during recon (not a global find-and-replace), and updates the manifest so a re-run of this skill won't re-flag anything already applied or explicitly kept. A multi-line `old` — the normal shape of JSX prose — is matched against the whole file instead, but only when it occurs exactly once; two occurrences are reported as `skipped_ambiguous` rather than guessed at. Read its output: it also reports anything it couldn't apply because the surrounding text changed since recon (`skipped_drift`). For those, re-locate the string by hand and edit it directly, then mark it in the manifest yourself.

### Copy is asserted on by tests

**Before applying, grep the test suite for the strings you are about to change:**

```bash
grep -rn "only rename it\|takes nothing" --include="*.test.*" --include="*.spec.*" .
```

Tests assert on copy in two different ways, and they need opposite responses:

- **A test asserting a message exists** (`expect(err.message).toMatch(/stops before it finishes/)`) is testing behaviour, not wording. Update the assertion to the new string. That's a rename, not a weakening — but put it in the diff summary so the user sees it.
- **A test enforcing a voice rule** (`expect(hint.line[0]).toBe(hint.line[0].toLowerCase())`) is a house convention defended in CI. Changing it changes the product's voice rules. Only do that when the user has approved the change that requires it, and **call it out prominently** — including any surface that now disagrees with the one you changed.

**Always run the full suite and linter after applying**, and report the result. On one run, copy changes broke five tests across four files; four were wording assertions and one was a voice rule. None of that is visible from the strings alone.

For rows the user says to leave as-is during review, write them to the same JSON with `"action": "keep"` so the manifest remembers the decision instead of re-flagging that exact string next time.

## Edge cases

- **Interpolated strings** (`` `Welcome back, ${name}!` ``) — review and rewrite the static parts, but preserve the interpolation syntax exactly. Don't rewrite in a way that would require the surrounding code to pass a different variable.
- **Typographic characters** — check what the project already uses before introducing any. An apostrophe in JSX *text* can trip `react/no-unescaped-entities`; a project may ban em dashes outright. Both are cheaper to check once during recon than to discover from a red build.
- **Copy changes that are really product changes** — deleting an onboarding step, removing a menu item, making a hidden field always-visible. These often fall out of a cut pass and are worth proposing, but they alter behaviour and can renumber or break things (a tour step deletion changes a progress counter and its tests). Flag them separately from the copy rows and don't fold them into a bulk apply, even when the user said "apply everything" — finish all the copy, then name what you left and why.
- **Pluralization / ICU message strings** — treat each branch (`one`, `other`, etc.) as its own string; keep them consistent with each other after rewriting.
- **Non-English locales** — only rewrite the source locale (usually `en`). Flag that translated locale files now need a human translator pass; don't auto-translate.
- **Non-web stacks** (Flutter, native iOS/Android, a CLI tool) — the scanner's regex patterns target common web frameworks. On anything else, use `references/file-patterns.md` for where to look, but expect to search by hand rather than lean on the script.
