#!/usr/bin/env python3
"""
apply_rewrites.py - Apply approved rewrites for the deslop-writing skill.

Takes a JSON file of approved rows (see references/file-patterns.md for the
schema) and, for each one:
  - action "rewrite": replaces the exact `old` text with `new` on the given
    file+line (not a global find-and-replace), then marks that manifest
    entry "rewritten". If `old` spans several lines - the normal shape of
    JSX/template prose - the line is treated as a hint and the match is made
    against the whole file, but only when it occurs exactly once.
  - action "keep": makes no file change, marks the manifest entry "kept" so
    it won't be re-flagged by a future scan.

If the current file content on that line doesn't contain `old` anymore
(drift since recon), the row is skipped and reported so it can be
re-located and fixed by hand.

Usage:
    python apply_rewrites.py <manifest_path> <approved_json_path>
"""

import json
import sys
from pathlib import Path


def load_json(path: Path):
    return json.loads(Path(path).read_text())


def apply_one(root: Path, manifest: dict, row: dict):
    relpath = row["file"]
    line_no = row.get("line")
    old = row.get("old", "")
    new = row.get("new", old)
    action = row.get("action", "rewrite")

    file_entry = manifest.get("files", {}).get(relpath)
    if file_entry is None:
        return {"file": relpath, "line": line_no, "result": "skipped_missing_manifest_entry"}

    if action == "keep":
        for s in file_entry["strings"]:
            if s["line"] == line_no and s["text"] == old:
                s["status"] = "kept"
                return {"file": relpath, "line": line_no, "result": "kept"}
        return {"file": relpath, "line": line_no, "result": "skipped_missing_manifest_entry"}

    # action == "rewrite"
    fpath = root / relpath
    if not fpath.exists():
        return {"file": relpath, "line": line_no, "result": "skipped_file_not_found"}

    try:
        lines = fpath.read_text(encoding="utf-8").splitlines(keepends=True)
    except Exception as e:
        return {"file": relpath, "line": line_no, "result": f"skipped_read_error: {e}"}

    if not line_no or line_no < 1 or line_no > len(lines):
        return {"file": relpath, "line": line_no, "result": "skipped_line_out_of_range"}

    idx = line_no - 1
    if old in lines[idx]:
        lines[idx] = lines[idx].replace(old, new, 1)
        fpath.write_text("".join(lines), encoding="utf-8")
    else:
        # Multi-line fallback. Most real UI prose in a component framework is a
        # text node spanning several lines, so `old` legitimately will not fit
        # on the recorded line. Fall back to a whole-file exact match, but only
        # when it is unambiguous: two occurrences means the row cannot say
        # which one it meant, and guessing would silently edit the wrong one.
        whole = "".join(lines)
        occurrences = whole.count(old)
        if occurrences == 0:
            return {
                "file": relpath, "line": line_no, "result": "skipped_drift",
                "current_line_content": lines[idx].rstrip("\n"),
            }
        if occurrences > 1:
            return {
                "file": relpath, "line": line_no, "result": "skipped_ambiguous",
                "occurrences": occurrences,
            }
        fpath.write_text(whole.replace(old, new, 1), encoding="utf-8")

    for s in file_entry["strings"]:
        if s["line"] == line_no and s["text"] == old:
            s["status"] = "rewritten"
            s["note"] = new
            break

    return {"file": relpath, "line": line_no, "result": "applied"}


def main():
    if len(sys.argv) != 3:
        print("Usage: python apply_rewrites.py <manifest_path> <approved_json_path>")
        sys.exit(1)

    manifest_path = Path(sys.argv[1])
    approved_path = Path(sys.argv[2])

    manifest = load_json(manifest_path)
    approved_rows = load_json(approved_path)
    root = manifest_path.parent.parent if manifest_path.parent.name == ".deslop-writing" else manifest_path.parent

    results = [apply_one(root, manifest, row) for row in approved_rows]

    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))

    summary = {
        "applied": sum(1 for r in results if r["result"] == "applied"),
        "kept": sum(1 for r in results if r["result"] == "kept"),
        "skipped": [r for r in results if r["result"] not in ("applied", "kept")],
        "results": results,
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()


