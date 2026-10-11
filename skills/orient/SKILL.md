---
name: orient
description: Get grounded in a codebase quickly — explore its structure, summarize what's built vs. in progress, and produce a prioritized action list plus any urgent risks. Use when starting work in an unfamiliar repo, resuming a project after time away, or when the user asks to get oriented, wants a status update, or asks what's left to do.
---

# Orient

## Gather context

Run these from the project root before anything else, all at once if your environment allows it:

```bash
pwd
git status --short 2>/dev/null || echo "Not a git repository"
git branch --show-current 2>/dev/null
git log --oneline -20 2>/dev/null
git diff --stat 2>/dev/null
git stash list 2>/dev/null
find . -maxdepth 2 -not -path '*/node_modules/*' -not -path '*/.git/*' -not -path '*/dist/*' -not -path '*/build/*' -not -path '*/.venv/*' -not -path '*/venv/*' | sort
```

## What to do

This is a read-only reconnaissance pass. Only read files, search them, and run read-only commands like the ones above (`git status`, `git log`, `git diff`, `git branch`, `git stash list`, `git remote -v`, `find`, `ls`). Don't edit, create, or delete anything while orienting — surface findings and wait for direction before acting on any of them.

1. **Read the context output first.** It already tells you whether this is a git repo, what changed recently, and the rough shape of the tree — don't re-derive it with extra commands.

2. **Identify the project.** Read whichever of these exist: README, package.json / pyproject.toml / Cargo.toml / go.mod / *.csproj / Gemfile / requirements.txt, and any top-level docs folder. Establish the language(s), framework(s), and how the project is meant to be run, built, and tested.

3. **Explore the structure deliberately.** Use file-name and text search to map the source layout — entry points, core modules, tests, config. Don't read every file indiscriminately; prioritize entry points, recently-changed files (see the diff/log above), and anything with high fan-in (imported/referenced everywhere).

4. **Find the project's own account of its status.** Look for TODO.md, ROADMAP.md, CHANGELOG.md, docs/, issue templates, or references to a project board. Search for `TODO`, `FIXME`, `HACK`, `XXX` across source. Cross-reference with recent commit messages and the diff/stash output above — that's often the most honest signal of what's mid-flight.

5. **Check whether things actually work.** Look at the test directories and CI config (`.github/workflows`, `.gitlab-ci.yml`, etc.) to see what's covered and what the last known state was. Don't run the full test suite unless asked — just note whether one exists, looks maintained, and what it covers.

6. **Watch for risk signals** while you're in there: uncommitted changes that look substantial or fragile, merge-conflict markers left in files, secrets/credentials committed in cleartext, a detached HEAD, a branch that has diverged heavily from its remote, obviously broken or half-finished code paths, or dependency manifests that look stale. Only report what you actually observe — don't manufacture urgency to fill out the report.

## Output format

Report back in exactly this structure:

### Summary
2–4 sentences: what this project is, its stack, and its overall state of maturity.

### What's done / what's in progress
Be concrete — reference actual modules, features, or files, not generic categories. Distinguish "built and looks solid" from "built but untested/unfinished" from "stubbed out."

### Action items
A prioritized, ordered list of concrete next steps. Each item should be specific enough to act on directly — "add error-path coverage for the auth module" rather than "improve tests."

### ⚠️ Needs immediate attention
Only include this section if something genuinely warrants it: risk of losing uncommitted work, secrets in the repo, a broken build, a data-destructive operation left half-done, an expiring credential, etc. If nothing qualifies, omit the section entirely — don't pad it.
