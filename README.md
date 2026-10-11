# skillsXD

A set of agent skills to help improve your coding. Each one is a folder with a `SKILL.md` in the [Agent Skills](https://agentskills.io) format, so they work in Claude Code, Codex, Cursor, Gemini CLI, and any other agent that loads skills.

## Skills

| Skill | What it does |
| --- | --- |
| [create-ds](skills/create-ds) | Builds a design system out of an existing codebase. It treats the UI that's already there as ground truth, extracts tokens and components from it, builds the missing components in the same style, and ships an interactive guide page. Expect it to take 45 minutes to 2 hours. |
| [deslop-writing](skills/deslop-writing) | Audits every piece of user-facing text in an app (buttons, errors, tooltips, empty states, toasts) and flags anything unclear, wordy, leaking internals, or sounding AI-written. It shows a table of current and recommended text and asks before changing any file. |
| [orient](skills/orient) | A read-only pass over a repo that reports what's built, what's in progress, a prioritized list of next steps, and anything that needs attention right away. |
| [usage](skills/usage) | Reports what a T3 Code thread or a single Claude Code, Codex, Grok, Cursor, or Pi session cost: tokens, cache use, plan limits, per-turn breakdowns, and extras like web searches and paid APIs. Renders as an interactive page. |

Agents pick a skill up on their own when a request matches its description. You can also ask for one by name, like "run orient" (or `/orient` in agents that turn skills into slash commands).

## Install

With the [skills CLI](https://github.com/vercel-labs/skills), from a clone of this repo:

```bash
npx skills add .                      # choose skills and agents interactively
npx skills add . --skill orient -g    # one skill, installed for your user
```

Or copy (or symlink) a skill's folder into your agent's skills directory, such as `~/.claude/skills/` for Claude Code.

## Requirements

`usage` and the `deslop-writing` scripts need Python 3 and use only the standard library. `deslop-writing` reads YAML locale files only when PyYAML is installed. The `create-ds` scripts are Bash and use ripgrep when it's available, falling back to grep.

`usage` reads the agents' session logs from this machine, so it only covers sessions run here. It downloads LiteLLM's price table every few days and caches it in `~/.cache/agent-usage/`. Plan limits are available for Claude and Codex. To price tools and APIs that don't show up as model tokens, edit [skills/usage/extras.json](skills/usage/extras.json).
