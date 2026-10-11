#!/usr/bin/env python3
"""
scan_ui_text.py - Recon pass for the deslop-writing skill.

Finds candidate user-facing strings across a project and maintains an
incremental manifest (.deslop-writing/inventory.json) so repeat runs only
re-scan files that changed, while still surfacing anything left over from a
prior run that was never reviewed.

This is a heuristic, regex-based scanner. It is meant to narrow a codebase
down to a candidate list for a human or agent to read in context, not to be an
exhaustive or perfectly precise source of truth. Expect some false positives
(code fragments that happen to sit between `>` and `<`) and some misses
(unusual frameworks, strings built by concatenation). See
references/file-patterns.md in the skill for what it doesn't cover.

Usage:
    python scan_ui_text.py <project_root> [--manifest PATH] [--full]

Output: a JSON summary printed to stdout. The manifest on disk is the
persistent record; the stdout summary is what to read this run.
"""

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

SKIP_DIRS = {
    "node_modules", ".git", "dist", "build", "out", ".next", "vendor",
    "__pycache__", ".venv", "venv", "target", "coverage", ".turbo",
    ".cache", "public/build",
}
SKIP_FILES = {"package-lock.json", "yarn.lock", "pnpm-lock.yaml", "composer.lock"}
MAX_FILE_BYTES = 500_000

CODE_EXTS = {".jsx", ".tsx", ".js", ".ts", ".vue", ".svelte", ".html", ".htm"}
LOCALE_EXTS = {".json", ".yml", ".yaml"}
LOCALE_DIR_HINTS = ("locale", "locales", "i18n", "lang", "translations", "messages")

# --- Candidate-finding patterns for code files -----------------------------

TAG_TEXT_RE = re.compile(r">([^<>{}\n]{2,}?)<")
ATTR_RE = re.compile(r'\b(?:aria-label|placeholder|alt|title)=["\']([^"\']{2,})["\']')
CALL_RE = re.compile(
    r'\b(?:toast|alert|confirm|showNotification|showToast|notify)\s*\(\s*["\']([^"\']{2,})["\']'
)
I18N_DEFAULT_RE = re.compile(
    r't\(\s*["\'][\w.\-]+["\']\s*,\s*["\']([^"\']{2,})["\']\s*\)'
)
VAR_RE = re.compile(
    r'\b(?:const|let|var)\s+\w*(?:[Mm]essage|[Ee]rror|[Ll]abel|[Tt]ext|[Tt]itle)\w*\s*=\s*'
    r'["\']([^"\']{4,})["\']'
)

CODE_PATTERNS = [TAG_TEXT_RE, ATTR_RE, CALL_RE, I18N_DEFAULT_RE, VAR_RE]

# --- Prose the line-by-line patterns above structurally cannot see ----------
#
# Component prose is normally a multi-line text node containing interpolations:
#
#     <p>
#       Another tab saved this{" "}
#       {ago(meta.updatedAt)}. Nothing has been overwritten.
#     </p>
#
# TAG_TEXT_RE rejects that three times over - it forbids newlines, forbids
# `{}`, and is applied one line at a time. Tour/onboarding copy has the same
# problem in a different shape: `body: () => "..."` is a plain object value,
# matched by none of the patterns above.
#
# This matters more than precision does. Measured against one real Next.js
# app, the line-based patterns found 231 candidates and missed every single
# one of the thirteen strings that turned out to carry the most slop.

BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", re.S)
LINE_COMMENT_RE = re.compile(r"^\s*//.*$", re.M)
JSX_TEXT_RE = re.compile(r">([^<>]{3,}?)<", re.S)
INTERP_RE = re.compile(r"\{[^{}]*\}")
PROSE_KEYS = (
    "body|line|message|description|label|hint|title|subtitle|note|caption|"
    "placeholder|emptyMessage|closeLabel|actionLabel|summary|nudge|legend"
)
PROSE_VALUE_RE = re.compile(
    r"\b(?:" + PROSE_KEYS + r")\s*:\s*(?:\([^)]*\)\s*=>\s*)?[\"`]([^\"`]{4,})[\"`]"
)
ARROW_STRING_RE = re.compile(r"=>\s*[\"`]([^\"`]{8,})[\"`]")
THROWN_RE = re.compile(
    r"(?:new Error|setError|setMessage|fail)\s*\([^)\"'`]*[\"`]([^\"`]{8,})[\"`]"
)
SENTENCE_RE = re.compile(r"[a-z]{3}\s+\w")


def scan_prose(text: str, raw_lines):
    """Multi-line JSX text nodes, and message-shaped object values.

    Comments are stripped first: a repo that explains itself in block comments
    (the kind most likely to need this skill) otherwise floods the manifest
    with prose no user will ever read.
    """
    stripped = LINE_COMMENT_RE.sub("", BLOCK_COMMENT_RE.sub("", text))
    out = []
    for m in JSX_TEXT_RE.finditer(stripped):
        chunk = " ".join(INTERP_RE.sub(" ", m.group(1)).split())
        if is_noise(chunk) or len(chunk.split()) < 3 or not SENTENCE_RE.search(chunk):
            continue
        out.append({"line": find_line_of_value(raw_lines, chunk.split()[0]), "text": chunk})
    for rx in (PROSE_VALUE_RE, ARROW_STRING_RE, THROWN_RE):
        for m in rx.finditer(stripped):
            value = m.group(1).strip()
            if is_noise(value) or len(value.split()) < 2:
                continue
            out.append({"line": find_line_of_value(raw_lines, value[:40]), "text": value})
    return out

NOISE_RE = re.compile(r'=>|&&|\|\||===|!==|;\s*$')
ALPHA_RE = re.compile(r"[A-Za-z]")
NUMERIC_PUNCT_ONLY_RE = re.compile(r"^[\d\s.,:;/\-]+$")


def is_noise(text: str) -> bool:
    text = text.strip()
    if len(text) < 2:
        return True
    if not ALPHA_RE.search(text):
        return True
    if NUMERIC_PUNCT_ONLY_RE.match(text):
        return True
    if NOISE_RE.search(text):
        return True
    return False


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def should_skip_dir(name: str) -> bool:
    return name in SKIP_DIRS or name.startswith(".")


def is_locale_file(path: Path) -> bool:
    if path.suffix.lower() not in LOCALE_EXTS:
        return False
    parts_lower = {p.lower() for p in path.parts}
    return any(hint in parts_lower or any(hint in p for p in parts_lower) for hint in LOCALE_DIR_HINTS)


def find_line_of_value(raw_lines, value: str) -> int:
    """Best-effort: find the 1-indexed line where a quoted value appears."""
    needle = value
    for i, line in enumerate(raw_lines, start=1):
        if needle in line:
            return i
    return 0


def flatten_json_like(obj, prefix=""):
    """Yield (key_path, value) for every leaf string in a nested dict/list."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            new_prefix = f"{prefix}.{k}" if prefix else str(k)
            yield from flatten_json_like(v, new_prefix)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from flatten_json_like(v, f"{prefix}[{i}]")
    elif isinstance(obj, str):
        yield prefix, obj


def scan_code_file(path: Path):
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []
    lines = text.splitlines()
    candidates = []
    seen = set()
    for lineno, line in enumerate(lines, start=1):
        for pattern in CODE_PATTERNS:
            for m in pattern.finditer(line):
                value = m.group(1).strip()
                if is_noise(value):
                    continue
                key = (lineno, value)
                if key in seen:
                    continue
                seen.add(key)
                candidates.append({"line": lineno, "text": value})
    for c in scan_prose(text, lines):
        key = (c["line"], c["text"])
        if key in seen:
            continue
        seen.add(key)
        candidates.append(c)
    return candidates


def scan_locale_file(path: Path):
    try:
        raw_text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []
    raw_lines = raw_text.splitlines()
    data = None
    if path.suffix.lower() == ".json":
        try:
            data = json.loads(raw_text)
        except Exception:
            data = None
    else:  # .yml / .yaml
        try:
            import yaml  # type: ignore
            data = yaml.safe_load(raw_text)
        except Exception:
            data = None

    candidates = []
    if data is not None:
        for key_path, value in flatten_json_like(data):
            value = value.strip()
            if is_noise(value):
                continue
            lineno = find_line_of_value(raw_lines, value)
            candidates.append({"line": lineno, "text": value, "key": key_path})
    else:
        # Fallback for YAML without pyyaml, or unparsable JSON: grab quoted
        # values after a colon, line by line.
        line_re = re.compile(r':\s*["\']([^"\']{2,})["\']\s*$')
        for lineno, line in enumerate(raw_lines, start=1):
            m = line_re.search(line)
            if not m:
                continue
            value = m.group(1).strip()
            if is_noise(value):
                continue
            candidates.append({"line": lineno, "text": value})
    return candidates


def iter_target_files(root: Path):
    for dirpath, dirnames, filenames in __import__("os").walk(root):
        dirnames[:] = [d for d in dirnames if not should_skip_dir(d)]
        for fname in filenames:
            if fname in SKIP_FILES:
                continue
            fpath = Path(dirpath) / fname
            if fpath.stat().st_size > MAX_FILE_BYTES:
                continue
            suffix = fpath.suffix.lower()
            if suffix in CODE_EXTS or is_locale_file(fpath):
                yield fpath


def load_manifest(manifest_path: Path):
    if manifest_path.exists():
        try:
            return json.loads(manifest_path.read_text())
        except Exception:
            pass
    return {"version": 1, "files": {}}


def save_manifest(manifest_path: Path, manifest: dict):
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("project_root")
    parser.add_argument("--manifest", default=None)
    parser.add_argument("--full", action="store_true", help="Ignore cached hashes; rescan every file.")
    args = parser.parse_args()

    root = Path(args.project_root).resolve()
    manifest_path = Path(args.manifest) if args.manifest else root / ".deslop-writing" / "inventory.json"
    manifest = load_manifest(manifest_path)
    files = manifest.setdefault("files", {})

    seen_relpaths = set()
    rescanned = []

    for fpath in iter_target_files(root):
        relpath = str(fpath.relative_to(root))
        seen_relpaths.add(relpath)
        try:
            file_hash = sha256_of(fpath)
        except Exception:
            continue

        existing = files.get(relpath)
        if existing and existing.get("hash") == file_hash and not args.full:
            continue  # unchanged since last scan; keep existing entries as-is

        locale = is_locale_file(fpath)
        candidates = scan_locale_file(fpath) if locale else scan_code_file(fpath)

        # When a file changed, its candidate list is rebuilt from scratch --
        # but carry over status/note for any (line, text) pair that's
        # identical to what it was before, so lines that didn't actually
        # change don't get reset to "unreviewed" just because something
        # else in the same file did. Skip this carry-over on --full, which
        # is meant to be a genuinely fresh look.
        prev_status = {}
        if existing and not args.full:
            for s in existing.get("strings", []):
                prev_status[(s["line"], s["text"])] = (s.get("status", "unreviewed"), s.get("note", ""))

        new_strings = []
        for c in candidates:
            status, note = prev_status.get((c["line"], c["text"]), ("unreviewed", ""))
            new_strings.append({
                "line": c["line"], "text": c["text"], "key": c.get("key"),
                "status": status, "note": note,
            })

        files[relpath] = {
            "hash": file_hash,
            "kind": "locale" if locale else "code",
            "strings": new_strings,
        }
        rescanned.append(relpath)

    # Drop files that no longer exist on disk.
    for stale in [rp for rp in files if rp not in seen_relpaths]:
        del files[stale]

    save_manifest(manifest_path, manifest)

    unreviewed = []
    kept = 0
    rewritten = 0
    total_candidates = 0
    for relpath, entry in files.items():
        for s in entry["strings"]:
            total_candidates += 1
            if s["status"] == "unreviewed":
                unreviewed.append({
                    "file": relpath, "line": s["line"], "text": s["text"],
                    "key": s.get("key"),
                })
            elif s["status"] == "kept":
                kept += 1
            elif s["status"] == "rewritten":
                rewritten += 1

    summary = {
        "manifest_path": str(manifest_path),
        "files_tracked_total": len(files),
        "files_rescanned_this_run": len(rescanned),
        "rescanned_files": rescanned,
        "candidates_total": total_candidates,
        "unreviewed_total": len(unreviewed),
        "kept_total": kept,
        "rewritten_total": rewritten,
        "unreviewed_candidates": unreviewed,
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
