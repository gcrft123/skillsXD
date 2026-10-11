#!/usr/bin/env python3
"""Cost, token, and plan usage report for one agent session or T3 Code thread.

    usage.py [ID] [--json] [--open] [--no-plan] [--out DIR]

ID is a T3 thread ID, a native agent session ID (Claude Code, Codex, Grok, Pi,
Cursor), a unique prefix of either, or a t3-thread:// link. Without an ID the
current session is used, widened to its T3 thread when there is one.

Prints a short header and a self-contained HTML report (for T3's html_render),
and writes the same HTML and a JSON copy under ~/.cache/agent-usage/reports.
Standard library only. Prices come from LiteLLM's model table, the source that
ccusage and T3 Code's own usage view also price from.
"""
import json
import os
import re
import sqlite3
import subprocess
import sys
import threading
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone

HOME = os.path.expanduser("~")
T3_HOME = os.environ.get("T3CODE_HOME") or os.path.join(HOME, ".t3")
T3_DATA = os.path.join(T3_HOME, "userdata")
T3_DB = os.path.join(T3_DATA, "statev2.sqlite")
CLAUDE_HOME = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(HOME, ".claude")
CODEX_HOME = os.environ.get("CODEX_HOME") or os.path.join(HOME, ".codex")
GROK_HOME = os.environ.get("GROK_HOME") or os.path.join(HOME, ".grok")
PI_SESSIONS = os.path.join(HOME, ".pi", "agent", "sessions")
CACHE_DIR = os.path.join(os.environ.get("XDG_CACHE_HOME") or os.path.join(HOME, ".cache"), "agent-usage")
SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LITELLM_URL = "https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json"
RATES_MAX_AGE_S = 3 * 86400
FORK_COPY_MAX_GAP_MS = 1000
PROVIDER_NAMES = {"claude": "Claude Code", "codex": "Codex", "grok": "Grok", "pi": "Pi", "cursor": "Cursor"}
T3_DRIVERS = {"claudeAgent": "claude", "codex": "codex", "grok": "grok", "pi": "pi", "cursor": "cursor"}


def die(msg):
    print("usage: " + msg, file=sys.stderr)
    sys.exit(2)


def ts_ms(value):
    """ISO string, epoch seconds, or epoch ms -> epoch ms (or None)."""
    if isinstance(value, (int, float)):
        return value if value > 1e11 else value * 1000
    if isinstance(value, str) and value:
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp() * 1000
        except ValueError:
            return None
    return None


def n(value):
    return int(value) if isinstance(value, (int, float)) and value > 0 else 0


# ---------------------------------------------------------------------------
# Records and sources


class Rec:
    """One billed model request, normalized across providers."""

    __slots__ = ("ts", "prov", "model", "src", "key", "inp", "cr", "cw", "cw1h", "out",
                 "reas", "ws", "speed", "geo", "reported", "ctx", "cost", "parts")

    def __init__(self, ts, prov, model, src, key=None, inp=0, cr=0, cw=0, cw1h=0, out=0,
                 reas=0, ws=0, speed="standard", geo=None, reported=None):
        self.ts, self.prov, self.model, self.src, self.key = ts, prov, model, src, key
        self.inp, self.cr, self.cw, self.cw1h, self.out, self.reas = inp, cr, cw, cw1h, out, reas
        self.ws, self.speed, self.geo, self.reported = ws, speed, geo, reported
        self.ctx = inp + cr + cw + cw1h
        self.cost, self.parts = 0.0, None

    @property
    def tokens(self):
        return self.ctx + self.out


class Source:
    """One transcript (or Cursor account slice) that belongs to the report."""

    def __init__(self, prov, sid, role, label, files=(), thread=None):
        self.prov, self.sid, self.role, self.label = prov, sid, role, label
        self.files, self.thread = list(files), thread
        self.cwd = self.branch = self.title = None


class Scan:
    """Everything parsed out of the sources."""

    def __init__(self):
        self.recs, self.keys = [], {}
        self.prompts = []  # (ts, text)
        self.tools = Counter()
        self.tool_seen = set()
        self.bash = []  # Bash commands, for external API detection
        self.times = []
        self.rate_limits = {}  # provider -> latest snapshot
        self.titles = []

    def add(self, rec):
        """Claude Code writes one line per content block and repeats the request's usage on each,
        with output_tokens still growing on the early ones. Keep one record per request and the
        largest value of every counter (what ccusage does)."""
        if rec.key is not None:
            seen = self.keys.get(rec.key)
            if seen is not None:
                for f in ("inp", "cr", "cw", "cw1h", "out", "reas", "ws"):
                    setattr(seen, f, max(getattr(seen, f), getattr(rec, f)))
                seen.ctx = seen.inp + seen.cr + seen.cw + seen.cw1h
                if rec.reported is not None:
                    seen.reported = max(seen.reported or 0, rec.reported)
                return
            self.keys[rec.key] = rec
        self.recs.append(rec)

    def tool(self, tid, name, inp):
        if tid and tid in self.tool_seen:
            return
        if tid:
            self.tool_seen.add(tid)
        self.tools[name] += 1
        if isinstance(inp, dict):
            cmd = inp.get("command") or inp.get("cmd") or inp.get("url")
            if isinstance(cmd, list):
                cmd = " ".join(map(str, cmd))
            if isinstance(cmd, str) and "http" in cmd:
                self.bash.append(cmd[:4000])


# ---------------------------------------------------------------------------
# Parsers. Each mirrors the format notes in references/sources.md.


def parse_claude(path, src, scan, main):
    with open(path, "rb") as fh:
        for line in fh:
            if b'"timestamp"' not in line:
                if b'"ai-title"' in line or b'"summary"' in line:
                    try:
                        o = json.loads(line)
                    except ValueError:
                        continue
                    t = o.get("aiTitle") or (o.get("summary") if o.get("type") == "summary" else None)
                    if main and t:
                        scan.titles.append(t)
                continue
            try:
                o = json.loads(line)
            except ValueError:
                continue
            kind = o.get("type")
            t = ts_ms(o.get("timestamp"))
            if t:
                scan.times.append(t)
            if main and src.cwd is None and o.get("cwd"):
                src.cwd, src.branch = o.get("cwd"), o.get("gitBranch")
            msg = o.get("message")
            if not isinstance(msg, dict):
                continue
            if kind == "assistant":
                content = msg.get("content")
                if isinstance(content, list):
                    for b in content:
                        if isinstance(b, dict) and b.get("type") == "tool_use":
                            scan.tool(b.get("id"), b.get("name") or "?", b.get("input"))
                u, model = msg.get("usage"), msg.get("model")
                if not isinstance(u, dict) or not model or model == "<synthetic>" or not t:
                    continue
                mid, rid = msg.get("id"), o.get("requestId")
                cc = u.get("cache_creation") if isinstance(u.get("cache_creation"), dict) else {}
                cw_total = n(u.get("cache_creation_input_tokens"))
                cw1h = min(cw_total, n(cc.get("ephemeral_1h_input_tokens")))
                stu = u.get("server_tool_use") if isinstance(u.get("server_tool_use"), dict) else {}
                cost = o.get("costUSD")
                scan.add(Rec(
                    t, "claude", model, src,
                    key=None if mid is None and rid is None else "c:%s:%s" % (mid, rid),
                    inp=n(u.get("input_tokens")), cr=n(u.get("cache_read_input_tokens")),
                    cw=cw_total - cw1h, cw1h=cw1h, out=n(u.get("output_tokens")),
                    reas=n((u.get("output_tokens_details") or {}).get("thinking_tokens")),
                    ws=n(stu.get("web_search_requests")),
                    speed="fast" if u.get("speed") == "fast" else "standard",
                    geo=u.get("inference_geo"),
                    reported=cost if isinstance(cost, (int, float)) and cost > 0 else None))
            elif kind == "user" and main and not o.get("isMeta") and not o.get("isSidechain"):
                c = msg.get("content")
                text = None
                if isinstance(c, str):
                    text = c
                elif isinstance(c, list) and not any(isinstance(b, dict) and b.get("type") == "tool_result" for b in c):
                    text = " ".join(b.get("text", "") for b in c if isinstance(b, dict) and b.get("type") == "text")
                text = (text or "").strip()
                if text and t and not text.startswith(("<", "Caveat:")):
                    scan.prompts.append((t, text))


def parse_codex(path, src, scan, main):
    model, speed, last_sig, saw_meta = "", "standard", None, False
    suppress, anchor = False, 0
    with open(path, "rb") as fh:
        for line in fh:
            if not (b'"token_count"' in line or b'"turn_context"' in line or b'"session_meta"' in line
                    or b'"thread_settings_applied"' in line or b'"user_message"' in line
                    or b'_call"' in line):
                continue
            try:
                o = json.loads(line)
            except ValueError:
                continue
            p = o.get("payload")
            if not isinstance(p, dict):
                continue
            t = ts_ms(o.get("timestamp"))
            if t:
                scan.times.append(t)
            kind, ptype = o.get("type"), p.get("type")
            if kind == "session_meta":
                if saw_meta:
                    continue
                saw_meta = True
                src.cwd = src.cwd or p.get("cwd")
                spawn = ((p.get("source") or {}).get("subagent") or {}).get("thread_spawn") if isinstance(p.get("source"), dict) else None
                if t and (isinstance(p.get("forked_from_id"), str) or (isinstance(spawn, dict) and spawn.get("parent_thread_id"))):
                    suppress, anchor = True, t
            elif kind == "turn_context":
                model = p.get("model") or model
            elif ptype == "thread_settings_applied":
                tier = (p.get("thread_settings") or {}).get("service_tier")
                speed = "fast" if tier in ("priority", "fast") else "ultrafast" if tier == "ultrafast" else "standard"
            elif ptype == "user_message" and main and t:
                scan.prompts.append((t, p.get("message") or ""))
            elif ptype in ("function_call", "custom_tool_call", "local_shell_call"):
                args = p.get("arguments") or p.get("input") or p.get("action")
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except ValueError:
                        args = {"command": args}
                scan.tool(p.get("call_id"), p.get("name") or ptype, args)
            elif ptype == "token_count":
                if isinstance(p.get("rate_limits"), dict):
                    scan.rate_limits["codex"] = (t or 0, p["rate_limits"])
                last = (p.get("info") or {}).get("last_token_usage") if isinstance(p.get("info"), dict) else None
                if not isinstance(last, dict) or not t or not model:
                    continue
                sig = json.dumps(last, sort_keys=True)
                if sig == last_sig:
                    continue
                last_sig = sig
                if suppress:
                    if t - anchor < FORK_COPY_MAX_GAP_MS:
                        anchor = t
                        continue
                    suppress = False
                inp, cached, cw = n(last.get("input_tokens")), n(last.get("cached_input_tokens")), n(last.get("cache_write_input_tokens"))
                out = n(last.get("output_tokens"))
                rec = Rec(t, "codex", model, src, inp=max(0, inp - cached - cw), cr=cached, cw=cw, out=out,
                          reas=min(out, n(last.get("reasoning_output_tokens"))), speed=speed)
                if rec.tokens:
                    scan.add(rec)


def parse_grok(path, src, scan, main):
    with open(path, "rb") as fh:
        for line in fh:
            if b'"turn_completed"' not in line and b'"tool_call"' not in line:
                continue
            try:
                o = json.loads(line)
            except ValueError:
                continue
            params = o.get("params") or {}
            upd = params.get("update") or {}
            meta = params.get("_meta") or {}
            t = meta.get("agentTimestampMs") or ts_ms(o.get("timestamp"))
            if t:
                scan.times.append(t)
            if upd.get("sessionUpdate") == "tool_call":
                scan.tool(upd.get("toolCallId"), upd.get("title") or upd.get("kind") or "tool", upd.get("rawInput"))
                continue
            if upd.get("sessionUpdate") != "turn_completed" or not isinstance(upd.get("usage"), dict) or not t:
                continue
            u, pid, sid = upd["usage"], upd.get("prompt_id"), params.get("sessionId", "")
            if main:
                scan.prompts.append((t - (upd.get("elapsed_ms") or 0), ""))
            per_model = u.get("modelUsage") if isinstance(u.get("modelUsage"), dict) else {}
            entries = [(m, v) for m, v in per_model.items() if isinstance(v, dict)] or [("grok", u)]
            top_cost = u.get("costUsdTicks")
            ticked = sum(v.get("costUsdTicks") or 0 for _, v in entries if isinstance(v.get("costUsdTicks"), (int, float)))
            unticked = sum(n(v.get("inputTokens")) + n(v.get("outputTokens")) for _, v in entries if not isinstance(v.get("costUsdTicks"), (int, float)))
            for model, v in entries:
                cached, cw, inp = n(v.get("cachedReadTokens")), n(v.get("cacheCreationTokens")), n(v.get("inputTokens"))
                out = n(v.get("outputTokens"))
                ticks = v.get("costUsdTicks")
                if not isinstance(ticks, (int, float)) and isinstance(top_cost, (int, float)) and unticked:
                    ticks = max(0, top_cost - ticked) * (n(v.get("inputTokens")) + out) / unticked
                rec = Rec(t, "grok", model, src, key="g:%s:%s:%s" % (sid, pid, model) if pid else None,
                          inp=max(0, inp - cached - cw), cr=cached, cw=cw, out=out,
                          reas=min(out, n(v.get("reasoningTokens"))),
                          reported=ticks / 1e10 if isinstance(ticks, (int, float)) else None)
                if rec.tokens:
                    scan.add(rec)


def parse_pi(path, src, scan, main):
    with open(path, "rb") as fh:
        for line in fh:
            if b'"usage"' not in line and b'"role":"user"' not in line:
                continue
            try:
                o = json.loads(line)
            except ValueError:
                continue
            t = ts_ms(o.get("timestamp"))
            if not t:
                continue
            scan.times.append(t)
            m = o.get("message") if o.get("type") == "message" else o
            if not isinstance(m, dict):
                continue
            if m.get("role") == "user" and main:
                c = m.get("content")
                scan.prompts.append((t, c if isinstance(c, str) else ""))
            u = m.get("usage")
            if not isinstance(u, dict):
                continue
            model = m.get("responseModel") or m.get("model")
            label = "%s/%s" % (m.get("provider"), model) if m.get("provider") and model else "Tools/summaries"
            cost = (u.get("cost") or {}).get("total") if isinstance(u.get("cost"), dict) else None
            out = n(u.get("output"))
            rec = Rec(t, "pi", label, src, key="p:%s:%s:%s" % (o.get("id"), o.get("timestamp"), label),
                      inp=n(u.get("input")), cr=n(u.get("cacheRead")), cw=n(u.get("cacheWrite")), out=out,
                      reas=min(out, n(u.get("reasoning"))),
                      reported=cost if isinstance(cost, (int, float)) and cost > 0 else None)
            if rec.tokens or rec.reported:
                scan.add(rec)


PARSERS = {"claude": parse_claude, "codex": parse_codex, "grok": parse_grok, "pi": parse_pi}


def cursor_rows(sid):
    """Cursor bills on its servers; T3 Code caches the account's usage events."""
    path = os.path.join(T3_DATA, "usage-cursor-account-cache-v1.json")
    try:
        doc = json.load(open(path))
    except (OSError, ValueError):
        return [], None
    strings = doc.get("strings") or []
    want = {sid, sid[6:] if sid.startswith("agent-") else "agent-" + sid}
    idx = {i for i, s in enumerate(strings) if s in want}
    rows, until = [], None
    for acct in (doc.get("accounts") or {}).values():
        until = max(until or 0, acct.get("untilMs") or 0)
        for r in acct.get("records") or []:
            if len(r) >= 9 and r[2] in idx:
                rows.append(r)
    return [(r, strings[r[1]]) for r in rows], until


# ---------------------------------------------------------------------------
# Locating sessions


def t3_connect():
    if not os.path.exists(T3_DB):
        return None
    try:
        db = sqlite3.connect("file:%s?mode=ro" % T3_DB, uri=True, timeout=3)
        db.execute("select 1 from orchestration_v2_projection_threads limit 1")
        return db
    except sqlite3.Error:
        return None


def t3_thread(db, q):
    if not db or not q:
        return None
    for table in ("orchestration_v2_projection_threads", "projection_threads"):
        try:
            rows = db.execute("select thread_id, title, project_id, created_at, deleted_at from %s "
                              "where thread_id = ? or thread_id like ? limit 3" % table,
                              (q, q.replace("%", "") + "%")).fetchall()
        except sqlite3.Error:
            continue
        exact = [r for r in rows if r[0] == q]
        if exact or len(rows) == 1:
            return (exact or rows)[0]
        if len(rows) > 1:
            die("'%s' matches more than one T3 thread; use more characters." % q)
    return None


def t3_natives(db, tid):
    """(provider, native id) pairs a T3 thread ran on, in first-seen order."""
    out = []
    try:
        for drv, payload in db.execute("select driver, payload_json from orchestration_v2_projection_provider_threads "
                                       "where thread_id = ? order by first_run_ordinal", (tid,)):
            ref = (json.loads(payload).get("nativeThreadRef") or {})
            if ref.get("nativeId"):
                out.append((T3_DRIVERS.get(ref.get("driver") or drv, drv), ref["nativeId"]))
    except sqlite3.Error:
        pass
    try:
        for prov, cursor in db.execute("select provider_name, resume_cursor_json from provider_session_runtime where thread_id = ?", (tid,)):
            c = json.loads(cursor or "{}")
            p = T3_DRIVERS.get(prov, prov)
            nid = c.get("resume") if p == "claude" else c.get("threadId") if p == "codex" else c.get("sessionId")
            if nid:
                out.append((p, nid))
    except (sqlite3.Error, ValueError):
        pass
    seen, uniq = set(), []
    for item in out:
        if item not in seen:
            seen.add(item)
            uniq.append(item)
    return uniq


def t3_children(db, tid):
    try:
        return db.execute("select thread_id, title from orchestration_v2_projection_threads "
                          "where json_extract(payload_json, '$.lineage.parentThreadId') = ? and deleted_at is null", (tid,)).fetchall()
    except sqlite3.Error:
        return []


def t3_thread_for_native(db, nid):
    if not db or not nid:
        return None
    like = "%" + nid + "%"
    for sql in ("select thread_id from orchestration_v2_projection_provider_threads where payload_json like ? limit 1",
                "select thread_id from provider_session_runtime where resume_cursor_json like ? limit 1"):
        try:
            row = db.execute(sql, (like,)).fetchone()
        except sqlite3.Error:
            row = None
        if row and not row[0].startswith(("thread:", "import:")):
            return t3_thread(db, row[0])
    return None


def glob_files(pattern):
    import glob
    return sorted(glob.glob(pattern))


def claude_files(sid):
    mains = glob_files(os.path.join(CLAUDE_HOME, "projects", "*", sid + ".jsonl"))
    subs = []
    for d in glob_files(os.path.join(CLAUDE_HOME, "projects", "*", sid)):
        for dp, _, fns in os.walk(d):
            subs += [os.path.join(dp, f) for f in fns if f.startswith("agent-") and f.endswith(".jsonl")]
    return mains, sorted(subs)


def codex_files(sid):
    found = []
    for base in ("sessions", "archived_sessions"):
        root = os.path.join(CODEX_HOME, base)
        found += glob_files(os.path.join(root, "*", "*", "*", "rollout-*%s*.jsonl" % sid))
        found += glob_files(os.path.join(root, "rollout-*%s*.jsonl" % sid))
    return found


def codex_children(sid, after_mtime):
    """Codex subagent rollouts name their parent in session_meta."""
    kids = []
    root = os.path.join(CODEX_HOME, "sessions")
    for dp, _, fns in os.walk(root):
        for f in fns:
            p = os.path.join(dp, f)
            if not f.endswith(".jsonl") or sid in f:
                continue
            try:
                if os.path.getmtime(p) < after_mtime:
                    continue
                with open(p, "rb") as fh:
                    first = fh.readline()
            except OSError:
                continue
            if sid.encode() in first and b"parent_thread_id" in first:
                kids.append(p)
    return kids


def find_native(q):
    """Locate a native session by full ID or unique prefix. -> (provider, id, files) or None."""
    q = q.strip()
    mains, _ = claude_files(q + "*")
    ids = {os.path.basename(p)[:-6] for p in mains}
    if len(ids) == 1:
        return "claude", ids.pop()
    files = codex_files(q)
    if files:
        m = re.search(r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\.jsonl$", files[0])
        return "codex", m.group(1) if m else q
    grok = glob_files(os.path.join(GROK_HOME, "sessions", "*", q + "*", "updates.jsonl"))
    if grok:
        return "grok", os.path.basename(os.path.dirname(grok[0]))
    pi = [p for p in glob_files(os.path.join(PI_SESSIONS, "*", "*.jsonl")) if q in os.path.basename(p)]
    if pi:
        return "pi", q
    rows, _ = cursor_rows(q)
    if rows:
        return "cursor", q
    if len(ids) > 1:
        die("'%s' matches more than one Claude session; use more characters." % q)
    return None


def current_session(db):
    """The session this script was launched from."""
    for prov, var in (("claude", "CLAUDE_CODE_SESSION_ID"), ("claude", "CLAUDE_SESSION_ID"),
                      ("codex", "CODEX_THREAD_ID"), ("codex", "CODEX_SESSION_ID"),
                      ("grok", "GROK_SESSION_ID"), ("pi", "PI_SESSION_ID")):
        v = os.environ.get(var, "").strip()
        if v and not v.startswith("$"):
            return prov, v
    if db:
        try:
            rows = db.execute("select thread_id, driver, payload_json from orchestration_v2_projection_provider_threads "
                              "where status in ('active', 'running') order by updated_at desc").fetchall()
        except sqlite3.Error:
            rows = []
        if len(rows) == 1:
            ref = json.loads(rows[0][2]).get("nativeThreadRef") or {}
            return T3_DRIVERS.get(rows[0][1], rows[0][1]), ref.get("nativeId") or rows[0][0]
    # Newest transcript wins; a running session is the one being written to.
    best = None
    cwd = os.getcwd()
    for root, prov in ((os.path.join(CLAUDE_HOME, "projects"), "claude"), (os.path.join(CODEX_HOME, "sessions"), "codex"),
                       (os.path.join(GROK_HOME, "sessions"), "grok"), (PI_SESSIONS, "pi")):
        if not os.path.isdir(root):
            continue
        for dp, dns, fns in os.walk(root):
            if "subagents" in dns:
                dns.remove("subagents")
            for f in fns:
                if not f.endswith(".jsonl") or (prov == "grok" and f != "updates.jsonl"):
                    continue
                p = os.path.join(dp, f)
                try:
                    mt = os.path.getmtime(p)
                except OSError:
                    continue
                bonus = 60 if prov == "claude" and cwd.replace("/", "-").replace(".", "-") in dp else 0
                if not best or mt + bonus > best[0]:
                    best = (mt + bonus, prov, p)
    if not best:
        die("no agent sessions found on this machine.")
    _, prov, p = best
    if prov == "grok":
        return prov, os.path.basename(os.path.dirname(p))
    m = re.search(r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\.jsonl$", p)
    return prov, m.group(1) if m else os.path.basename(p)[:-6]


def native_sources(prov, sid, role, label, thread=None):
    """All Sources for one native session, including its own subagents."""
    out = []
    if prov == "claude":
        mains, subs = claude_files(sid)
        if mains:
            out.append(Source("claude", sid, role, label, mains, thread))
        for p in subs:
            meta, aid = {}, os.path.basename(p)[:-6].replace("agent-", "")
            try:
                meta = json.load(open(p[:-6] + ".meta.json"))
            except (OSError, ValueError):
                pass
            name = meta.get("description") or ("Workflow agent " if "workflows" in p else "Subagent ") + aid[:7]
            out.append(Source("claude", aid, "subagent", name, [p], thread))
    elif prov == "codex":
        files = codex_files(sid)
        if files:
            out.append(Source("codex", sid, role, label, files, thread))
            for p in codex_children(sid, os.path.getmtime(files[0]) - 60):
                out.append(Source("codex", os.path.basename(p)[-41:-6], "subagent", "Codex subagent", [p], thread))
    elif prov == "grok":
        files = glob_files(os.path.join(GROK_HOME, "sessions", "*", sid, "updates.jsonl"))
        if files:
            out.append(Source("grok", sid, role, label, files, thread))
    elif prov == "pi":
        files = [p for p in glob_files(os.path.join(PI_SESSIONS, "*", "*.jsonl")) if sid in os.path.basename(p)]
        if files:
            out.append(Source("pi", sid, role, label, files, thread))
    elif prov == "cursor":
        out.append(Source("cursor", sid, role, label, [], thread))
    return out


def resolve(arg, db):
    """-> (target dict, [Source])"""
    q = (arg or "").strip()
    if q.startswith("t3-thread://"):
        q = q.rstrip("/").rsplit("/", 1)[-1]
    q = re.sub(r"^thread:", "", q)
    widen = False
    if not q or q.lower() in ("current", "this", "${claude_session_id}"):
        prov, q = current_session(db)
        widen = True
    else:
        prov = None
    thread = t3_thread(db, q) if not prov else None
    native = None
    if not thread:
        native = (prov, q) if prov else find_native(q)
        if not native:
            die("no T3 thread or agent session matches '%s'." % q)
        if widen:
            thread = t3_thread_for_native(db, native[1])
    if thread:
        tid, title = thread[0], thread[1]
        sources, seen = [], set()

        def add_thread(t_id, t_title, role, depth):
            for p, nid in t3_natives(db, t_id):
                if (p, nid) in seen:
                    continue
                seen.add((p, nid))
                label = "Main · " + PROVIDER_NAMES.get(p, p) if role == "main" else (t_title or "Child thread")
                sources.extend(native_sources(p, nid, role, label, t_id))
            if depth < 4:
                for c_id, c_title in t3_children(db, t_id):
                    add_thread(c_id, c_title, "child", depth + 1)

        add_thread(tid, title, "main", 0)
        project = None
        try:
            row = db.execute("select title from projection_projects where project_id = ?", (thread[2],)).fetchone()
            project = row[0] if row else None
        except sqlite3.Error:
            pass
        return {"kind": "thread", "id": tid, "title": title, "project": project, "deleted": bool(thread[4])}, sources
    p, nid = native
    host = t3_thread_for_native(db, nid)
    target = {"kind": "session", "id": nid, "provider": p, "title": None,
              "t3": {"id": host[0], "title": host[1]} if host else None}
    return target, native_sources(p, nid, "main", "Main · " + PROVIDER_NAMES.get(p, p))


# ---------------------------------------------------------------------------
# Pricing (LiteLLM model_prices_and_context_window.json)


def load_rates():
    """Freshest of T3 Code's cached copy and ours; refresh ours when both are stale."""
    best = (0, None, "none")
    for path, label in ((os.path.join(T3_DATA, "usage-model-rates.json"), "T3 Code cache"),
                        (os.path.join(CACHE_DIR, "litellm.json"), "skill cache")):
        try:
            doc = json.load(open(path))
        except (OSError, ValueError):
            continue
        fetched = doc.get("fetchedAtMs") or os.path.getmtime(path) * 1000
        if isinstance(doc.get("document"), dict) and fetched > best[0]:
            best = (fetched, doc["document"], label)
    if time.time() * 1000 - best[0] > RATES_MAX_AGE_S * 1000:
        try:
            raw = subprocess.run(["curl", "-sSfL", "-m", "8", LITELLM_URL], capture_output=True, timeout=10).stdout
            doc = json.loads(raw)
            if isinstance(doc, dict) and len(doc) > 100:
                os.makedirs(CACHE_DIR, exist_ok=True)
                now = time.time() * 1000
                with open(os.path.join(CACHE_DIR, "litellm.json"), "w") as fh:
                    json.dump({"fetchedAtMs": now, "document": doc}, fh)
                best = (now, doc, "LiteLLM")
        except (OSError, ValueError, subprocess.SubprocessError):
            pass
    overrides = {}
    try:
        overrides = json.load(open(os.path.join(SKILL_DIR, "extras.json"))).get("models") or {}
    except (OSError, ValueError):
        pass
    return best[1] or {}, best[0], overrides


class Pricer:
    UNPRICEABLE = {"<synthetic>", "synthetic", "opus", "sonnet", "haiku", "fable", "default", "auto"}

    def __init__(self, table, overrides):
        self.table = {k.lower(): v for k, v in table.items() if isinstance(v, dict)}
        for name, o in overrides.items():
            self.table[name.lower()] = {
                "input_cost_per_token": o.get("inputPerMTok", 0) / 1e6,
                "output_cost_per_token": o.get("outputPerMTok", 0) / 1e6,
                "cache_read_input_token_cost": o.get("cacheReadPerMTok", o.get("inputPerMTok", 0)) / 1e6,
                "cache_creation_input_token_cost": o.get("cacheWritePerMTok", o.get("inputPerMTok", 0)) / 1e6}
        self.memo = {}
        self.unpriced = set()

    def entry(self, model, prov):
        k = (model, prov)
        if k in self.memo:
            return self.memo[k]
        m = model.lower().split("[")[0].strip()
        if prov == "cursor":
            m = re.sub(r"(?:-thinking)?(?:-(?:none|minimal|low|medium|high|xhigh|max))?(?:-fast)?$", "", m.replace("cursor-", "", 1))
        bare = m.rsplit("/", 1)[-1]
        e = None
        if bare not in self.UNPRICEABLE:
            cands = [m, bare, re.sub(r"-\d{8}$", "", bare)]
            if bare.startswith("grok"):
                cands.append("xai/" + bare)
            if bare.startswith(("gpt", "o1", "o3", "o4", "codex")):
                cands.append("openai/" + bare)
            if bare.startswith("claude"):
                cands.append("anthropic/" + bare)
            if bare.startswith("gemini"):
                cands.append("gemini/" + bare)
            for c in cands:
                v = self.table.get(c)
                if v and isinstance(v.get("input_cost_per_token"), (int, float)) and isinstance(v.get("output_cost_per_token"), (int, float)):
                    e = v
                    break
        self.memo[k] = e
        return e

    @staticmethod
    def tier(e, ctx):
        best = None
        for key in e:
            mt = re.fullmatch(r"input_cost_per_token_above_(\d+)k_tokens", key)
            if mt and ctx > int(mt.group(1)) * 1000 and (best is None or int(mt.group(1)) > best):
                best = int(mt.group(1))
        return "_above_%dk_tokens" % best if best else ""

    def price(self, r):
        e = self.entry(r.model, r.prov)
        if e is None:
            if r.reported is None:
                self.unpriced.add(r.model)
            r.cost = r.reported or 0.0
            r.parts = {"other": r.cost} if r.cost else {}
            return
        sfx = self.tier(e, r.ctx)

        def rate(name, fallback):
            v = e.get(name + sfx, e.get(name))
            return v if isinstance(v, (int, float)) else fallback

        i = rate("input_cost_per_token", 0)
        if r.speed != "standard" and isinstance(e.get("input_cost_per_token_priority"), (int, float)):
            i = e["input_cost_per_token_priority"]
        o = rate("output_cost_per_token", 0)
        cr = rate("cache_read_input_token_cost", i)
        cw = rate("cache_creation_input_token_cost", i * 1.25 if e.get("litellm_provider") == "anthropic" else i)
        v1h = e.get("cache_creation_input_token_cost_above_1hr" + sfx, e.get("cache_creation_input_token_cost_above_1hr"))
        cw1h = v1h if isinstance(v1h, (int, float)) else cw * 1.6 if e.get("litellm_provider") == "anthropic" else cw
        mult = 1.0
        spec = e.get("provider_specific_entry") if isinstance(e.get("provider_specific_entry"), dict) else {}
        if r.speed == "fast" and isinstance(spec.get("fast"), (int, float)):
            mult *= spec["fast"]
        elif r.speed != "standard" and isinstance(e.get("output_cost_per_token_priority"), (int, float)):
            o = e["output_cost_per_token_priority"]
            cr = e.get("cache_read_input_token_cost_priority", cr)
        if r.geo == "us" and isinstance(spec.get("us"), (int, float)):
            mult *= spec["us"]
        parts = {"input": r.inp * i * mult, "cache_write": (r.cw * cw + r.cw1h * cw1h) * mult,
                 "cache_read": r.cr * cr * mult, "output": r.out * o * mult}
        listed = sum(parts.values())
        if r.reported is not None and listed > 0:
            scale = r.reported / listed
            parts = {k: v * scale for k, v in parts.items()}
        elif r.reported is not None:
            parts = {"other": r.reported}
        sq = (e.get("search_context_cost_per_query") or {}).get("search_context_size_medium") if isinstance(e.get("search_context_cost_per_query"), dict) else None
        if r.ws:
            parts["web_search"] = r.ws * (sq if isinstance(sq, (int, float)) else 0.01)
        r.parts = parts
        r.cost = sum(parts.values())

    def cache_savings(self, r):
        e = self.entry(r.model, r.prov)
        if not e or not r.cr:
            return 0.0
        i = e.get("input_cost_per_token") or 0
        cr = e.get("cache_read_input_token_cost", i)
        return max(0.0, r.cr * (i - cr))


# ---------------------------------------------------------------------------
# Plan usage


def claude_plan():
    """Account-wide limits from Claude's OAuth usage endpoint (same as /usage in Claude Code)."""
    cache = os.path.join(CACHE_DIR, "claude-plan.json")
    try:
        c = json.load(open(cache))
        if time.time() - c.get("at", 0) < 60:
            return c
    except (OSError, ValueError):
        pass
    creds = None
    try:
        raw = subprocess.run(["security", "find-generic-password", "-s", "Claude Code-credentials", "-w"],
                             capture_output=True, text=True, timeout=6).stdout.strip()
        creds = json.loads(raw).get("claudeAiOauth") if raw else None
    except (OSError, ValueError, subprocess.SubprocessError):
        pass
    if not creds:
        try:
            creds = json.load(open(os.path.join(CLAUDE_HOME, ".credentials.json"))).get("claudeAiOauth")
        except (OSError, ValueError):
            creds = None
    if not creds or not creds.get("accessToken"):
        return {"error": "No Claude login found"}
    tier = (creds.get("rateLimitTier") or "").lower()
    sub = (creds.get("subscriptionType") or "").lower()
    mult = re.search(r"(\d+)x", tier)
    plan = {"max": "Claude Max", "pro": "Claude Pro", "team": "Claude Team", "enterprise": "Claude Enterprise"}.get(sub, "Claude " + sub.title() if sub else "Claude")
    if mult and sub == "max":
        plan += " " + mult.group(1) + "x"
    out = {"plan": plan, "at": time.time()}
    if (creds.get("expiresAt") or 0) / 1000 < time.time():
        out["error"] = "Claude login token expired; open Claude Code once to refresh it"
        return out
    try:
        r = subprocess.run(["curl", "-sS", "-m", "6", "-H", "@-", "https://api.anthropic.com/api/oauth/usage"],
                           input="Authorization: Bearer %s\nanthropic-beta: oauth-2025-04-20\n" % creds["accessToken"],
                           capture_output=True, text=True, timeout=8)
        out["usage"] = json.loads(r.stdout)
        if not isinstance(out["usage"], dict) or "error" in out["usage"]:
            out["error"] = "Claude usage endpoint refused the request"
            out.pop("usage", None)
    except (OSError, ValueError, subprocess.SubprocessError):
        out["error"] = "Claude usage endpoint unreachable"
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(cache, "w") as fh:
            json.dump(out, fh)
    except OSError:
        pass
    return out


def local_claude_cost(since_ms, pricer):
    """API-equivalent cost of every local Claude Code request since `since_ms`, by dedupe key."""
    costs = {}
    root = os.path.join(CLAUDE_HOME, "projects")
    since_s = since_ms / 1000
    for dp, _, fns in os.walk(root):
        for f in fns:
            if not f.endswith(".jsonl"):
                continue
            p = os.path.join(dp, f)
            try:
                if os.path.getmtime(p) < since_s:
                    continue
                fh = open(p, "rb")
            except OSError:
                continue
            with fh:
                for line in fh:
                    if b'"usage"' not in line or b'"assistant"' not in line:
                        continue
                    try:
                        o = json.loads(line)
                    except ValueError:
                        continue
                    msg = o.get("message") or {}
                    u = msg.get("usage")
                    t = ts_ms(o.get("timestamp"))
                    if not isinstance(u, dict) or not t or t < since_ms or msg.get("model") in (None, "<synthetic>"):
                        continue
                    key = "c:%s:%s" % (msg.get("id"), o.get("requestId"))
                    cc = u.get("cache_creation") if isinstance(u.get("cache_creation"), dict) else {}
                    cw = n(u.get("cache_creation_input_tokens"))
                    c1 = min(cw, n(cc.get("ephemeral_1h_input_tokens")))
                    r = Rec(t, "claude", msg["model"], None, inp=n(u.get("input_tokens")), cr=n(u.get("cache_read_input_tokens")),
                            cw=cw - c1, cw1h=c1, out=n(u.get("output_tokens")),
                            speed="fast" if u.get("speed") == "fast" else "standard", geo=u.get("inference_geo"))
                    pricer.price(r)
                    if key not in costs or costs[key][1] < r.cost:
                        costs[key] = (t, r.cost)
    return costs


# ---------------------------------------------------------------------------
# Formatting helpers


def pretty_model(m):
    s = m.rsplit("/", 1)[-1].split("[")[0]
    s = re.sub(r"-\d{8}$", "", s)
    mt = re.fullmatch(r"claude-([a-z]+)-(\d+)(?:-(\d+))?", s)
    if mt:
        return "%s %s%s" % (mt.group(1).title(), mt.group(2), "." + mt.group(3) if mt.group(3) else "")
    if s.startswith("gpt-"):
        head, *rest = s[4:].split("-")
        return "GPT-" + head + "".join(" " + w.title() for w in rest)
    if s.startswith("grok-"):
        head, *rest = s[5:].split("-")
        return "Grok " + head + "".join(" " + w.title() for w in rest)
    return s


def pretty_tool(name):
    if name.startswith("mcp__"):
        parts = name.split("__")
        server = parts[1].replace("claude_ai_", "").replace("plugin_", "").replace("_", " ")
        return "%s · %s" % (server, "__".join(parts[2:]) or "?")
    return name


def tok(v):
    for d, s in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
        if v >= d:
            x = v / d
            return ("%.1f" % x).rstrip("0").rstrip(".") + s if x < 100 else "%d%s" % (round(x), s)
    return str(int(v))


def usd(v):
    if v is None:
        return "—"
    if v >= 1000:
        return "${:,.0f}".format(v)
    if v >= 1:
        return "$%.2f" % v
    if v >= 0.01:
        return "$%.3f" % v
    return "<$0.01" if v > 0 else "$0"


def dur(ms):
    s = int(ms / 1000)
    if s < 60:
        return "%ds" % s
    m = s // 60
    if m < 60:
        return "%dm" % m
    h, m = divmod(m, 60)
    if h < 48:
        return "%dh %02dm" % (h, m)
    return "%dd %dh" % divmod(h, 24)


def until(iso):
    t = ts_ms(iso)
    if not t:
        return ""
    left = t - time.time() * 1000
    return "resets in " + dur(left) if left > 0 else "reset"


def local_time(ms, with_date=True):
    d = datetime.fromtimestamp(ms / 1000)
    clock = d.strftime("%-I:%M %p")
    return d.strftime("%b %-d, ") + clock if with_date else clock


# ---------------------------------------------------------------------------
# Report


def extras_rules():
    try:
        return json.load(open(os.path.join(SKILL_DIR, "extras.json")))
    except (OSError, ValueError):
        return {}


def other_costs(scan, recs):
    rows, total = [], 0.0
    ws = sum(r.ws for r in recs)
    if ws:
        c = sum((r.parts or {}).get("web_search", 0) for r in recs)
        rows.append(["Web search (server tool)", "%d searches" % ws, round(c, 4)])
        total += c
    rules = extras_rules()
    for rule in rules.get("tools", []):
        rx = re.compile(rule["match"])
        hits = sum(v for k, v in scan.tools.items() if rx.search(k))
        if hits:
            c = hits * rule["usd"] if isinstance(rule.get("usd"), (int, float)) else None
            rows.append([rule["label"], "%d %s%s" % (hits, rule.get("unit", "call"), "" if hits == 1 else "s"), None if c is None else round(c, 4)])
            total += c or 0
    for rule in rules.get("http", []):
        rx = re.compile(r"https?://[^\s'\"]*(?:%s)" % rule["match"])
        hits = sum(1 for cmd in scan.bash if rx.search(cmd))
        if hits:
            c = hits * rule["usd"] if isinstance(rule.get("usd"), (int, float)) else None
            rows.append([rule["label"], "%d %s%s from shell" % (hits, rule.get("unit", "request"), "" if hits == 1 else "s"), None if c is None else round(c, 4)])
            total += c or 0
    return rows, total


def build(target, sources, scan, pricer, rates_at, plan):
    recs = sorted(scan.recs, key=lambda r: r.ts)
    for r in recs:
        pricer.price(r)
    token_cost = sum(r.cost - (r.parts or {}).get("web_search", 0) for r in recs)
    others, other_total = other_costs(scan, recs)
    total = token_cost + other_total
    times = sorted(scan.times + [r.ts for r in recs])
    t0, t1 = (times[0], times[-1]) if times else (time.time() * 1000,) * 2
    active = sum(min(b - a, 300000) for a, b in zip(times, times[1:]))
    provs = sorted({s.prov for s in sources if any(r.src is s for r in recs)} or {s.prov for s in sources})
    models = Counter()
    for r in recs:
        models[pretty_model(r.model)] += r.cost
    # Title and meta line
    main = next((s for s in sources if s.role == "main"), sources[0] if sources else None)
    title = target.get("title") or next((t for t in reversed(scan.titles) if t), None)
    if not title:
        p = next((p for _, p in sorted(scan.prompts) if p.strip()), "")
        title = (p.strip().splitlines() or [""])[0][:80] or "%s session %s" % (PROVIDER_NAMES.get(main.prov, main.prov) if main else "Agent", target["id"][:8])
    meta = []
    if target["kind"] == "thread":
        meta.append("T3 thread " + target["id"][:8] + (" (deleted)" if target.get("deleted") else "") + (" · " + target["project"] if target.get("project") else ""))
    else:
        meta.append(PROVIDER_NAMES.get(target["provider"], target["provider"]) + " session " + target["id"][:8])
        if target.get("t3"):
            meta.append("in T3 thread " + target["t3"]["id"][:8])
    meta.append(", ".join(m for m, _ in models.most_common(3)) or "no billed requests")
    meta.append(local_time(t0) + " – " + (local_time(t1, False) if datetime.fromtimestamp(t0 / 1000).date() == datetime.fromtimestamp(t1 / 1000).date() else local_time(t1)))
    # Totals
    sums = defaultdict(float)
    for r in recs:
        for k, v in (r.parts or {}).items():
            sums[k] += v
    tin, tcr, tcw, tout = (sum(getattr(r, a) for r in recs) for a in ("inp", "cr", "cw", "out"))
    tcw += sum(r.cw1h for r in recs)
    ttot = tin + tcr + tcw + tout
    saved = sum(pricer.cache_savings(r) for r in recs)
    hit = tcr / (tin + tcr + tcw) if (tin + tcr + tcw) else 0
    main_recs = [r for r in recs if r.src is not None and r.src.role == "main"]
    peak = max((r.ctx for r in main_recs or recs), default=0)
    peak_model = max(main_recs or recs, key=lambda r: r.ctx).model if recs else None
    pe = pricer.entry(peak_model, "claude") if peak_model else None
    limit_ctx = (pe or {}).get("max_input_tokens")
    prompts = sorted(scan.prompts)
    tiles = [
        ["Tokens", tok(ttot), "%s out · %s cached" % (tok(tout), tok(tcr))],
        ["Requests", str(len(recs)), "%d turn%s" % (len(prompts), "" if len(prompts) == 1 else "s") if prompts else "model calls"],
        ["Duration", dur(t1 - t0), "active " + dur(active)],
        ["Cache hit", "%d%%" % round(hit * 100), "saved " + usd(saved) if saved else "of prompt tokens"],
        ["Peak context", tok(peak), "of " + tok(limit_ctx) if isinstance(limit_ctx, int) else "largest prompt"],
        ["Tool calls", str(sum(scan.tools.values())), ("top: %s %d" % (pretty_tool(scan.tools.most_common(1)[0][0]), scan.tools.most_common(1)[0][1])) if scan.tools else "none"],
    ]
    if len(prompts) > 1 and total:
        tiles.append(["Per turn", usd(total / len(prompts)), "average"])
    if others:
        tiles.append(["Other costs", usd(other_total) if other_total else "—", "%d item%s%s" % (len(others), "" if len(others) == 1 else "s", "" if other_total else ", not priced")])
    cats = [[lab, round(sums.get(k, 0), 4)] for k, lab in (("input", "Input"), ("cache_write", "Cache write"), ("cache_read", "Cache read"), ("output", "Output"))]
    if sums.get("other"):
        cats.append(["Provider-billed", round(sums["other"], 4)])
    if other_total:
        cats.append(["Other", round(other_total, 4)])
    cats = [c for c in cats if c[1] > 0]
    # Timeline: requests, bucketed to keep the page small. Repeated strings go through `lab`.
    lab, lab_ix = [], {}

    def L(text):
        if text not in lab_ix:
            lab_ix[text] = len(lab)
            lab.append(text)
        return lab_ix[text]

    # Columnar and rounded: every character here is one the agent has to copy into html_render.
    # s = seconds from t0, c = cost (3 significant digits), k = thousands of tokens, m/a = model and
    # agent label indexes, n = requests per point. Constant m/a/n columns are left out.
    nb = 60
    if len(recs) <= nb:
        groups = [[r] for r in recs]
    else:
        span = max(1, recs[-1].ts - recs[0].ts)
        buckets = defaultdict(list)
        for r in recs:
            buckets[min(nb - 1, int((r.ts - recs[0].ts) / span * nb))].append(r)
        groups = [buckets[b] for b in sorted(buckets)]
    cols = {"s": [], "c": [], "k": [], "m": [], "a": [], "n": []}
    for rs in groups:
        top = max(rs, key=lambda r: r.cost)
        cols["s"].append(round((rs[-1].ts - t0) / 1000))
        cols["c"].append(float("%.3g" % sum(r.cost for r in rs)))
        cols["k"].append(round(sum(r.tokens for r in rs) / 1000))
        cols["m"].append(L(pretty_model(top.model)))
        cols["a"].append(L(top.src.label if top.src else ""))
        cols["n"].append(len(rs))
    tl = {k: v for k, v in cols.items() if k in "sck" or len(set(v)) > 1}
    for k in "ma":
        if k not in tl and cols[k]:
            tl[k + "0"] = cols[k][0]
    # Breakdown tables
    def group(keyf):
        g = defaultdict(lambda: [0, 0, 0, 0, 0.0])
        for r in recs:
            row = g[keyf(r)]
            row[0] += 1
            row[1] += r.inp + r.cr + r.cw + r.cw1h
            row[2] += r.out
            row[3] += r.cr
            row[4] += r.cost
        return sorted(([k] + [v[0], v[1], v[2], v[3], round(v[4], 4)] for k, v in g.items()), key=lambda x: -x[-1])

    tok_cols = ["Requests", "Input", "Output", "Cached", "Cost"]
    tok_fmt = ["n", "t", "t", "t", "$"]
    tabs = [{"name": "Model", "cols": tok_cols, "fmt": tok_fmt, "rows": group(lambda r: pretty_model(r.model))}]
    if len({id(r.src) for r in recs}) > 1:
        tabs.append({"name": "Agent", "cols": tok_cols, "fmt": tok_fmt, "rows": group(lambda r: r.src.label if r.src else "?")})
    if len(provs) > 1:
        tabs.append({"name": "Provider", "cols": tok_cols, "fmt": tok_fmt, "rows": group(lambda r: PROVIDER_NAMES.get(r.prov, r.prov))})
    if prompts:
        starts = [p[0] for p in prompts]
        import bisect
        turn = defaultdict(lambda: [0, 0, 0.0])
        for r in recs:
            i = max(0, bisect.bisect_right(starts, r.ts) - 1)
            turn[i][0] += 1
            turn[i][1] += r.tokens
            turn[i][2] += r.cost
        rows = []
        for i, (ts, text) in enumerate(prompts):
            line = " ".join(re.sub(r"\[[^\]]*\]\(t3-citation://[^)]*\)", "", text).split())
            rows.append(["%d. %s" % (i + 1, (line[:50] + "…") if len(line) > 50 else line or "(turn)"), turn[i][0], turn[i][1], round(turn[i][2], 4)])
        rows.sort(key=lambda x: -x[-1])
        tabs.append({"name": "Turn", "cols": ["Requests", "Tokens", "Cost"], "fmt": ["n", "t", "$"], "rows": rows[:12]})
    if scan.tools:
        tabs.append({"name": "Tool", "cols": ["Calls"], "fmt": ["n"], "rows": [[pretty_tool(k), v] for k, v in scan.tools.most_common(15)]})
    # Plan usage
    limits, plan_note, plan_name = [], None, None
    if plan:
        plan_name = plan.get("plan")
        u = plan.get("usage") or {}
        if plan.get("error"):
            plan_note = plan["error"]
        claude_recs = [r for r in recs if r.prov == "claude"]
        my_keys = {r.key: r.cost for r in claude_recs if r.key}
        windows = {}
        for lim in u.get("limits") or []:
            if not isinstance(lim, dict) or not isinstance(lim.get("percent"), (int, float)):
                continue
            kind = lim.get("kind")
            model = ((lim.get("scope") or {}).get("model") or {}).get("display_name") if isinstance(lim.get("scope"), dict) else None
            label = {"session": "5-hour window", "weekly_all": "Weekly · all models"}.get(kind, "Weekly · " + model if model else kind.replace("_", " ").title())
            row = {"label": label, "pct": lim["percent"], "reset": until(lim.get("resets_at")), "sev": lim.get("severity") or "normal", "note": ""}
            if kind == "session" and lim.get("resets_at"):
                windows["session"] = (ts_ms(lim["resets_at"]) - 5 * 3600 * 1000, row)
            if kind == "weekly_all":
                start = ts_ms(((u.get("seven_day_breakdown") or {}).get("window_started_at"))) or (ts_ms(lim.get("resets_at")) or 0) - 7 * 86400 * 1000
                windows["weekly"] = (start, row)
            limits.append(row)
        if not limits:
            for key, label in (("five_hour", "5-hour window"), ("seven_day", "Weekly · all models")):
                w = u.get(key)
                if isinstance(w, dict) and isinstance(w.get("utilization"), (int, float)):
                    limits.append({"label": label, "pct": w["utilization"], "reset": until(w.get("resets_at")), "sev": "normal", "note": ""})
        # Session share of each window: its API-equivalent cost over all local Claude Code cost in the
        # window, scaled by the window's utilization (and Claude Code's share of the weekly breakdown).
        active = [s for s, _ in windows.values() if any(r.ts >= s for r in claude_recs)]
        if my_keys and active:
            local = local_claude_cost(min(active), pricer)
            cc_share = 1.0
            for row in (u.get("seven_day_breakdown") or {}).get("rows") or []:
                if row.get("key") == "claude_code" and isinstance(row.get("percent"), (int, float)):
                    cc_share = row["percent"] / 100
            for name, (start, row) in windows.items():
                mine = sum(r.cost for r in claude_recs if r.key and r.ts >= start)
                allc = sum(c for t, c in local.values() if t >= start)
                if mine and allc:
                    share = min(1.0, mine / allc) * (cc_share if name == "weekly" else 1.0)
                    row["note"] = "this %s ≈ %s%% of the limit" % ("thread" if target["kind"] == "thread" else "session", fmt_pct(row["pct"] * share))
        ex = u.get("extra_usage") or {}
        if ex.get("is_enabled"):
            used, cap = ex.get("used_credits"), ex.get("monthly_limit")
            limits.append({"label": "Usage credits", "pct": ex.get("utilization") or 0, "reset": "%s of %s" % (usd(used), usd(cap)) if cap else usd(used) + " used", "sev": "normal", "note": ""})
    snap = scan.rate_limits.get("codex")
    if snap:
        rl = snap[1]
        for key, label in (("primary", "Codex primary"), ("secondary", "Codex secondary")):
            w = rl.get(key)
            if isinstance(w, dict) and isinstance(w.get("used_percent"), (int, float)):
                mins = w.get("window_minutes")
                span = "%dh" % (mins // 60) if mins and mins < 2880 else "%dd" % (mins // 1440) if mins else ""
                limits.append({"label": "%s%s" % (label, " · " + span if span else ""), "pct": w["used_percent"],
                               "reset": until(datetime.fromtimestamp(w["resets_at"], timezone.utc).isoformat()) if w.get("resets_at") else "",
                               "sev": "normal", "note": "as of " + local_time(snap[0])})
        if rl.get("plan_type") and not plan_name:
            plan_name = "ChatGPT " + str(rl["plan_type"]).title()
    # Cost note under the hero number
    reported = [r for r in recs if r.reported is not None]
    if reported and len(reported) == len(recs):
        note = "as reported by " + " and ".join(sorted({PROVIDER_NAMES.get(r.prov, r.prov) for r in reported}))
    else:
        note = "API-equivalent at list prices"
        if reported:
            note += "; %s as reported" % " and ".join(sorted({PROVIDER_NAMES.get(r.prov, r.prov) for r in reported}))
    if plan_name and any(r.prov == "claude" for r in recs):
        note += " · on your %s plan" % plan_name
    if pricer.unpriced:
        note += " · unpriced: " + ", ".join(sorted(pretty_model(m) for m in pricer.unpriced))
    srcs = []
    used = {id(r.src) for r in recs}
    for s in sources:
        if id(s) in used or s.role == "main":
            srcs.append([PROVIDER_NAMES.get(s.prov, s.prov), s.label, s.sid[:13]])
    warn = None
    unsynced = [s for s in sources if s.prov == "cursor" and not any(r.src is s for r in recs)]
    if unsynced:
        _, synced = cursor_rows("")
        warn = ("Cursor hasn't reported billing for %s yet%s. Open T3 Code's Usage view to sync it, then run the usage report again."
                % ("this thread" if target["kind"] == "thread" else "this session",
                   " (T3 Code last synced Cursor usage " + local_time(synced) + ")" if synced else ""))
    elif not recs:
        warn = "No billed requests found in this %s's transcripts on this machine. They may have been deleted, or it ran on another machine." % (
            "thread" if target["kind"] == "thread" else "session")
    foot = ["Prices: LiteLLM model table, %s." % (datetime.fromtimestamp(rates_at / 1000).strftime("%b %-d, %Y") if rates_at else "unavailable")]
    if any(s.prov == "cursor" for s in sources):
        _, cu = cursor_rows("")
        foot.append("Cursor usage comes from T3 Code's account cache%s." % (", synced " + local_time(cu) if cu else ""))
    if others:
        foot.append("Other costs are detected from tool calls; edit extras.json to price more of them.")
    return {
        "title": title, "meta": meta, "cost": round(total, 4), "costNote": note, "tiles": tiles, "cats": cats,
        "t0": round(t0), "tl": tl, "lab": lab, "tabs": tabs, "limits": limits, "planName": (plan_name + " · now") if plan_name and limits else plan_name, "planNote": plan_note,
        "other": others, "srcs": srcs, "foot": " ".join(foot), "warn": warn,
    }


def fmt_pct(v):
    return ("%.1f" % v).rstrip("0").rstrip(".") if v < 10 else "%d" % round(v)


RENDERER = os.path.realpath(os.path.join(SKILL_DIR, "assets", "renderer.svg"))
FAILED = "The report renderer did not load (\"+e.message+\"). Run the usage report again with --inline."


def cdata(text):
    """Body of the first CDATA section, as the page's loader reads it."""
    return text[text.index("<![CDATA[") + 9:text.rindex("]]>")]


def write_data_svg(data, path):
    """The report data wrapped in an SVG so T3 Code will inline it like an image (see render)."""
    blob = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("]]>", "]]\\u003e")
    with open(path, "w") as fh:
        fh.write('<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1"><desc>Data for a usage report page.</desc>'
                 "<metadata><![CDATA[%s]]></metadata></svg>\n" % blob)


def render(data, data_svg=None):
    """The report page.

    T3 Code's html_render replaces local image paths written in a page, JS strings included, with
    data URIs, and SVG counts as an image. So by default the page is a ~600-byte loader that names
    two local SVGs, the renderer and this report's data, and the agent never has to copy either.
    Without `data_svg` the page embeds both, for browsers and hosts that don't inline local files."""
    head = ('<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            '</head><body><div id="a"></div><script>')
    if data_svg is None:
        blob = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/").replace("<!--", "<\\!--")
        code = cdata(open(RENDERER).read()).replace("</", "<\\/")
        return head + "(function(D){%s})(%s)</script></body></html>" % (code, blob)
    return head + ('const g=p=>fetch(p).then(r=>r.text()),x=t=>t.slice(t.indexOf("<![CDATA[")+9,t.lastIndexOf("]]>"));'
                   'Promise.all([g(%s),g(%s)]).then(([r,d])=>Function("D",x(r))(JSON.parse(x(d))))'
                   '.catch(e=>{document.getElementById("a").textContent="%s"})</script></body></html>'
                   ) % (json.dumps(RENDERER), json.dumps(os.path.realpath(data_svg)), FAILED)


def estimate_height(d):
    h = 70 + 96  # header, hero
    h += 64 * ((len(d["tiles"]) + 2) // 3) + 20
    h += 84 if d["cats"] else 0
    h += 236 if len(d["tl"]["s"]) > 1 else 0
    if d["tabs"]:
        h += 70 + 31 * min(12, max(len(t["rows"]) for t in d["tabs"][:1]))
    if d["limits"] or d.get("planNote"):
        h += 46 + 50 * len(d["limits"])
    h += 44 + 30 * len(d["other"]) if d["other"] else 0
    h += 90
    # T3 Code measures the page and fits the frame; this is only the cap, so leave room for phones.
    return max(240, min(2000, int(h * 1.25)))


def main():
    # "$ARGUMENTS" arrives as one word even when the user typed several.
    args = [w for a in sys.argv[1:] for w in a.split()]
    flags = {a for a in args if a.startswith("--") and a != "--out"}
    out_dir = os.path.join(CACHE_DIR, "reports")
    if "--out" in args:
        i = args.index("--out")
        out_dir = args[i + 1]
        del args[i:i + 2]
    pos = [a for a in args if not a.startswith("--")]
    db = t3_connect()
    target, sources = resolve(pos[0] if pos else "", db)
    if not sources:
        die("found %s %s but no usage data for it on this machine." % (target["kind"], target["id"]))
    want_plan = "--no-plan" not in flags and any(s.prov == "claude" for s in sources)
    plan_box = {}
    th = None
    if want_plan:
        th = threading.Thread(target=lambda: plan_box.update(claude_plan()), daemon=True)
        th.start()
    table, rates_at, overrides = load_rates()
    pricer = Pricer(table, overrides)
    scan = Scan()
    for s in sources:
        if s.prov == "cursor":
            rows, _ = cursor_rows(s.sid)
            for r, model in rows:
                scan.add(Rec(r[0], "cursor", model, s, key="u:" + str(r[8]), inp=n(r[3]), cr=n(r[4]), cw=n(r[5]), out=n(r[6]),
                             reported=r[7] if isinstance(r[7], (int, float)) else None))
            continue
        for p in s.files:
            try:
                PARSERS[s.prov](p, s, scan, s.role != "subagent")
            except OSError:
                pass
    if th:
        th.join(10)
    data = build(target, sources, scan, pricer, rates_at, plan_box if want_plan else None)
    os.makedirs(out_dir, exist_ok=True)
    # Rendered pages keep their own copy of the data, so old report files can go.
    for f in os.listdir(out_dir):
        p = os.path.join(out_dir, f)
        try:
            if f.startswith("usage-") and time.time() - os.path.getmtime(p) > 14 * 86400:
                os.remove(p)
        except OSError:
            pass
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    base = os.path.join(out_dir, "usage-%s-%s" % (target["id"][:8], stamp))
    write_data_svg(data, base + ".svg")
    full = render(data)
    with open(base + ".html", "w") as fh:
        fh.write(full)
    html = full if "--inline" in flags else render(data, base + ".svg")
    if "--json" in flags:
        print(json.dumps(data, ensure_ascii=False, indent=1))
        return
    if "--open" in flags:
        subprocess.run(["open", base + ".html"])
    tiles = {t[0]: t[1] for t in data["tiles"]}
    print("title: Usage · %s" % data["title"][:60])
    print("height: %d" % estimate_height(data))
    print("file: %s.html" % base)
    print("summary: %s total (%s) · %s tokens · %s requests · %s" % (
        usd(data["cost"]), data["costNote"].split(" · ")[0], tiles.get("Tokens"), tiles.get("Requests"), tiles.get("Duration")))
    if data.get("planNote"):
        print("plan: " + data["planNote"])
    if data.get("warn"):
        print("note: " + data["warn"])
    if "--quiet" not in flags:
        print("--- html ---")
        print(html)


if __name__ == "__main__":
    main()
