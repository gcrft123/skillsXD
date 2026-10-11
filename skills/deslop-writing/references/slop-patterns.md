# Slop patterns reference

A deeper catalogue for classifying candidates during Phase 2. Check here when a string doesn't obviously match one of the SKILL.md examples, or when you want more instances of a category to calibrate against.

## 1. Development leaks

Anything that exposes the machinery of the app to someone who isn't its developer.

| Current | Recommended | Why |
|---|---|---|
| "Error: Network request failed (ECONNREFUSED)" | "We couldn't connect. Check your internet and try again." | Raw error codes mean nothing to a non-technical user. |
| "undefined" (rendered where a name should be) | Fix the underlying data issue; if that's out of scope, at minimum render "—" or omit the field, never the literal word "undefined." | The literal value of an unset variable should never reach the screen. |
| "TODO: replace with real copy" | Write the actual copy. | A placeholder shipped to production is not a UI-copy problem to soften — it's a bug. Flag it as urgent. |
| "user_id: 8842 not found in table users" | "We couldn't find that account." | Table and column names are implementation detail. |
| "Feature flag NEW_CHECKOUT_V2 is disabled for this user" (shown in UI) | Remove the message from the user-facing surface entirely; log it instead. | Flag names should never render to end users, in any form. |
| "Something went wrong: [object Object]" | "Something went wrong on our end. Try again, and let us know if it keeps happening." | A stringified error object is a symptom of an uncaught exception, not copy to polish — still worth fixing the message so it fails gracefully. |

## 2. Confusing copy

The reader has to guess. Look for: missing antecedents, unclear consequences of an action, jargon without context, and copy that assumes knowledge the user doesn't have yet.

| Current | Recommended | Why |
|---|---|---|
| "Sync failed" | "We couldn't sync your files. Your local copy is safe — reconnect to try again." | Tells the user the actual state of their data, not just that an abstract process failed. |
| "This action cannot be undone" (no context) | "Deleting this workspace removes all 14 projects in it. This can't be undone." | Generic warnings don't communicate scope; say what's actually at stake. |
| "Continue" (after a form with unclear next step) | "Continue to payment" | If "Continue" could mean five different things depending on context, name the destination. |
| "Access denied" | "You don't have permission to view this page. Ask an admin to add you to this project." | Says what happened and what to do about it, not just the failure state. |
| "Something isn't right" | Identify what specifically is wrong and say so, or if genuinely unknown: "We hit an unexpected error. Try refreshing the page." | Vague-on-purpose copy is worse than an honest "we don't know" when the cause really is unknown. |

## 3. Slop vocabulary and constructions

Words and phrases that inflate copy without adding information. If a sentence would lose no meaning by deleting the buzzword, delete it — or better, rewrite the sentence around what's actually true.

**Words to treat as a red flag in UI copy:** leverage, unlock, elevate, empower, seamless, robust, cutting-edge, revolutionize, game-changing, holistic, transformative, best-in-class, next-level, supercharge, effortless (when the action clearly requires effort), delightful (when nothing delightful is happening), harness, streamline (as a vague claim rather than a description of what changed).

**Constructions to flag:**
- Forced excitement: "Woohoo! You're all set!" on a routine confirmation.
- Marketing tone on a functional element: "Experience Lightning-Fast Search" as a search bar's placeholder.
- Padding a simple action with a value proposition: "Save Time and Boost Productivity" on a button that just saves a file.
- Exclamation-point inflation: three exclamation points on a form validation error.
- The "not just X, it's Y" construction showing up in onboarding or marketing-adjacent in-app copy.

| Current | Recommended | Why |
|---|---|---|
| "Supercharge your workflow with our seamless integrations" | "Connect your other tools" | Says what the feature actually does. |
| "You're all set! 🎉 Time to unlock your dashboard!" | "You're all set. Go to your dashboard." | Keep the good news; drop the inflation. |
| "Effortlessly manage all your tasks in one place" | "Manage your tasks" | "Effortlessly" is a claim, not a description; let the product demonstrate ease instead of asserting it. |

## 4. Wordy copy

Not wrong, just longer than it needs to be. UI copy is read in passing, not studied — cut to the words doing actual work.

| Current | Recommended |
|---|---|
| "In order to proceed, please select an option from the list below" | "Choose an option" |
| "You have successfully completed the setup process" | "Setup complete" |
| "We were unable to process your request at this time" | "We couldn't process that" |
| "Please note that this setting will affect all users on your team" | "This affects everyone on your team" |
| "Click here to view all of your account settings and preferences" | "Account settings" |

## 5. House-voice tics — only visible across the whole corpus

The categories above are per-string. These are not: each looks fine alone and is only a problem because it recurs. Find them by reading the collected strings as one document (Phase 2, Step 1), and once you've named one, sweep for every instance.

This is the category that distinguishes a codebase whose copy is *bad* from one whose copy is *mannered* — the second is far more common in a carefully-written product, and far easier to miss.

| Tic | Instances from one real pass | Why it reads as slop |
|---|---|---|
| **Aphorism** | "A heading is a chart." · "Two columns at once is where a question lives." · "missing stays missing" | Shaped to sound wise. Says less than a plain instruction and asks the reader to decode it. |
| **Anthropomorphism** | "the chart answered" · "it wrote all of that down" · "it saved itself" · "Every mark answers the pointer" | The tool as a character. Cute once, twee by the fourth time, and it obscures who did what. |
| **Trailing rationale** | "…, which is what a student would mean by it." · "…, so the models can honestly be compared." | The product justifying its design to the user. Nobody asked; it doubles every sentence. |
| **Comma splice** | "The reshape could not be applied, that formula is invalid" | Two sentences pretending to be one. Usually a template gluing a message onto a prefix. |
| **Uniform cold opener** | Fifteen errors starting "That file…", "That link…", "That did not work." | Distancing and repetitive at scale. "This" or naming the thing is warmer and more specific. |
| **Register drift** | Lowercase fragments in onboarding, sentence case everywhere else | Reads as two products. Sometimes a deliberate convention — check before changing. |
| **No contractions at all** | "could not", "does not", "cannot", "it is" throughout | Uniformly stiff. Introducing contractions is one of the highest-leverage single changes. |
| **Explaining an absence** | "There is no chart menu to find first" | Text describing something that isn't on screen. Always deletable. |
| **In-product competitive claim** | "Nothing else in this class of tool keeps this record" | Marketing aimed at a buyer, shown to a user mid-task. |

## 6. Already fine — leave alone

Don't manufacture a rewrite for text that's already doing its job. Signs it's fine: standard, universally-understood actions ("Delete," "Cancel," "Save," "Sign in"), field labels that match their input exactly ("Email," "Password"), and short confirmations that already state the consequence ("Delete 3 files?").

**Especially: never lengthen a standard phrase.** "read-only." is finished — expanding it to "You can read it, but not change it." is a regression. This mistake is easiest to make while working down a long rewrite list with momentum.

Also leave at full length the few strings carrying information the screen genuinely doesn't: statistical cautions, security warnings, and the consequences of destructive actions. Brevity there costs the user something real.
