# Where usage data lives

`scripts/usage.py` reads everything below directly. This file is for debugging the script or extending it to a new provider.

## Resolving an ID

1. **T3 Code thread.** `~/.t3/userdata/statev2.sqlite`, opened read-only. Threads are in `orchestration_v2_projection_threads` (older ones also in `projection_threads`). Prefix matches are allowed.
2. **The thread's agent sessions.** `orchestration_v2_projection_provider_threads.payload_json` → `nativeThreadRef.{driver, nativeId}`, one row per provider the thread ran on. Older threads keep the native ID in `provider_session_runtime.resume_cursor_json` instead: `resume` for Claude, `threadId` for Codex, `sessionId` for Cursor and Grok.
3. **Child threads.** Rows whose `payload_json.lineage.parentThreadId` is the thread, recursively. Claude Code's own subagents show up here too, but their usage is read from the parent session's `subagents/` folder and deduplicated, so nothing counts twice.
4. **Native session ID.** Matched against each provider's files below. A native ID that belongs to a T3 thread reports just that session; the page links the thread.
5. **No ID.** `CLAUDE_CODE_SESSION_ID` (also `CODEX_THREAD_ID`, `GROK_SESSION_ID`, `PI_SESSION_ID` when set), then the single T3 provider thread with status `active`, then the newest transcript on disk.

## Transcripts and usage records

| Provider | Files | Usage record | Notes |
|---|---|---|---|
| Claude Code | `~/.claude/projects/<cwd>/<session>.jsonl`, plus every `*.jsonl` under `<session>/` (`subagents/agent-*.jsonl`, `subagents/workflows/<run>/agent-*.jsonl`; labels from the sibling `.meta.json`) | `type: assistant` lines, `message.usage` | One line per content block, all repeating the request's usage, with `output_tokens` still growing on the early ones. Dedupe on `message.id` + `requestId` and keep the max of each counter, as ccusage does. `cache_creation.ephemeral_1h_input_tokens` is billed at the 1-hour write rate; `speed: "fast"` and `inference_geo: "us"` carry multipliers. |
| Codex | `~/.codex/sessions/YYYY/MM/DD/rollout-*-<id>.jsonl` (and `archived_sessions`) | `event_msg` with `payload.type: token_count`, `info.last_token_usage` | Model from the latest `turn_context`, service tier from `thread_settings_applied`. Drop consecutive duplicate events. Forked and subagent rollouts start with a burst of copied parent events within 1s of `session_meta`; skip those. Subagents name their parent in `session_meta.source.subagent.thread_spawn.parent_thread_id`. `rate_limits` on token_count carries the plan windows. |
| Grok | `~/.grok/sessions/<encoded cwd>/<session>/updates.jsonl` | `params.update.sessionUpdate: turn_completed`, `update.usage` | Cost is reported in `costUsdTicks` (1 USD = 10^10 ticks), per model under `modelUsage`. |
| Pi | `~/.pi/agent/sessions/<cwd>/<time>_<session>.jsonl` | `message` entries with `usage`, plus `usage`, `compaction`, `branch_summary` entries | `usage.cost.total` is the provider-reported cost. |
| Cursor | none locally | T3 Code caches the account's billing events in `~/.t3/userdata/usage-cursor-account-cache-v1.json` | Rows are `[timestampMs, modelIdx, sessionIdx, uncached, cacheRead, cacheWrite, output, costUsd, key]` with indexes into `strings`. Session IDs may carry an `agent-` prefix. Threads newer than the last sync show no rows; T3's Usage view refreshes it. |

## Prices

LiteLLM's `model_prices_and_context_window.json`, the table ccusage and T3 Code price from. The script uses whichever is fresher of T3's copy (`~/.t3/userdata/usage-model-rates.json`) and its own (`~/.cache/agent-usage/litellm.json`), and downloads a new one when both are older than three days.

Per request: input, cache read, 5-minute and 1-hour cache writes, and output, each at its own rate; the `_above_<N>k_tokens` tier once the prompt passes N thousand tokens; `provider_specific_entry.fast` or the `_priority` rates for fast mode; `provider_specific_entry.us` for US-only inference; `search_context_cost_per_query` for server-side web searches. Provider-reported costs (Grok, Cursor, Pi) are kept as reported and split across categories in proportion to list prices. `<synthetic>` and bare family names (`opus`, `sonnet`) are never priced.

## Plan limits

- **Claude.** `GET https://api.anthropic.com/api/oauth/usage` with the Claude Code OAuth token (macOS Keychain item `Claude Code-credentials`, or `~/.claude/.credentials.json`) and `anthropic-beta: oauth-2025-04-20`. The token is passed to curl on stdin, never on the command line, and is never refreshed (refreshing would rotate Claude Code's login). `limits[]` has the 5-hour (`session`), weekly, and per-model weekly windows; `seven_day_breakdown` gives Claude Code's share of the weekly window. Cached for 60 seconds in `~/.cache/agent-usage/claude-plan.json`.
- **A session's share of a window** is its API-equivalent cost inside the window, divided by the cost of every local Claude Code request in the same window, times the window's utilization (and, for the weekly window, Claude Code's share of it). It assumes the rest of the window's usage came from this machine, so it's an estimate.
- **Codex.** The last `rate_limits` snapshot in the rollout.

## Other costs

`extras.json` holds regex rules for tool names (`tools`) and for URLs in shell commands (`http`), each with an optional per-call price. Unpriced matches are still listed so nothing is hidden. Server-side web searches reported in Claude usage are priced from LiteLLM.

## The report page

`assets/renderer.svg` holds the page's CSS and JS in a CDATA section, and each run writes the report's data the same way to `~/.cache/agent-usage/reports/usage-<id>-<time>.svg`. The page the script prints is a ~600-byte loader that fetches both by absolute path and runs the renderer on the data. That works because T3 Code's `html_render` replaces local image paths written in a page, JS strings included, with data URIs (SVG counts as an image), and serves rendered pages with only a `sandbox allow-scripts` CSP, so `fetch` of a data URI and `Function` both run. The published page carries its own copy of both files, so pruning old reports (done automatically after 14 days) never breaks a rendered report.

The agent only copies the loader, which is what keeps `/usage` fast: the render call is a few hundred output tokens instead of several thousand. `--inline` prints a self-contained page instead, for hosts that don't inline local files, and the `.html` written next to the data is always that version (it's what `--open` opens).
