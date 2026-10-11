---
name: usage
description: Show what a T3 Code thread or a single agent session (Claude Code, Codex, Grok, Cursor, Pi) cost, with tokens, cache use, plan limits, per-agent and per-turn breakdowns, and other costs such as web searches, image generation, texts, and paid APIs called from the shell, as an interactive report. Use when the user invokes usage by name (optionally with a thread or session ID), and whenever the user asks what a session or thread cost or how much of their plan it used.
---

# Usage

One script does everything: it finds the session, prices every request, reads plan limits, and prints a page that's ready to render. Don't explore files or write your own analysis; the whole skill is two steps.

1. Run the script, passing the user's argument through unchanged. Leave it empty for the current session. `<skill-dir>` is the directory this file is in. If the host has an `html_render` tool that still needs loading, load it at the same time so both happen at once.

   ```bash
   python3 -I <skill-dir>/scripts/usage.py "<argument>"
   ```

   The argument is whatever the user gave after invoking the skill. It can be a T3 thread ID, a native session ID from any supported agent, a unique prefix of either (8 characters is plenty), or a `t3-thread://v1/<id>` link. With no argument the current session is used, widened to its whole T3 thread (child threads and subagents included) when it runs inside T3 Code.

2. If the host has an `html_render` tool (T3 Code does), call it with `title` and `height` from the first two output lines and `html` set to everything after the `--- html ---` line, copied exactly. Don't preview, edit, or reformat it: the page is tested, and it loads its renderer from a local file that T3 Code inlines.

3. Reply with one short line: the `note:` or `plan:` text if the output has one, otherwise the `summary:` text. Nothing else; the page already says the rest.

Without an `html_render` tool, run the script with `--open` instead, which opens the same report in the browser, and reply with its `summary:` line. If the rendered page says the renderer didn't load, run again with `--inline` and render that output instead. If the script exits with an error, pass its message on; it says what didn't match.

Other flags: `--json` prints the raw numbers, and `--no-plan` skips the plan-limit lookup. How sessions are found and priced is documented in [references/sources.md](references/sources.md); read it only when the script fails or a provider's numbers look wrong. Users can price extra tools and APIs in [extras.json](extras.json).
