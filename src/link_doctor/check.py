"""Safe Markdown and wiki-link checker with name and anchor resolution."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

from .markdown import index_markdown


def _inside(root: Path, candidate: Path) -> bool:
    try:
        candidate.relative_to(root)
        return True
    except ValueError:
        return False


def _files(root: Path) -> list[Path]:
    found = []
    for current, dirs, names in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in {".git", "node_modules", ".venv", ".link-doctor"} and not (Path(current) / d).is_symlink())
        for name in sorted(names):
            path = Path(current) / name
            if path.is_file() and path.suffix.casefold() == ".md" and not path.is_symlink():
                found.append(path)
    return sorted(found, key=lambda p: p.relative_to(root).as_posix())


def _key(value: str) -> str:
    return " ".join(value.casefold().replace("_", " ").split())

def _decode_component(value: str) -> str:
    if re.search(r"%(?![0-9A-Fa-f]{2})", value):
        raise ValueError("invalid percent escape")
    return unquote(value, errors="strict")



def _safe_target(root: Path, source: Path, raw: str) -> tuple[Path | None, str | None, str | None]:
    raw = raw.strip()
    if not raw:
        return None, None, "empty link target"
    parsed = urlsplit(raw)
    if parsed.scheme or raw.startswith("//"):
        return None, None, "external URL"
    try:
        path_text = _decode_component(parsed.path)
        fragment = _decode_component(parsed.fragment) or None
    except (UnicodeDecodeError, ValueError):
        return None, None, "invalid URL encoding"
    if not path_text:
        return None, fragment, "anchor-only link" if parsed.fragment else "empty link path"
    candidate = (root / path_text.lstrip("/")) if path_text.startswith("/") else (source.parent / path_text)
    candidate = Path(os.path.abspath(candidate))
    if not _inside(root, candidate):
        return None, fragment, "outside scan root"
    # Check nearest existing ancestor to reject symlink escapes even for missing targets.
    ancestor = candidate
    while not ancestor.exists() and ancestor != ancestor.parent:
        ancestor = ancestor.parent
    try:
        resolved = ancestor.resolve(strict=True)
    except OSError:
        resolved = ancestor
    if not _inside(root, resolved):
        return None, fragment, "symlink escapes scan root"
    return candidate, fragment, None


def check(root_path: str | Path) -> dict:
    root = Path(root_path).resolve(strict=True)
    if not root.is_dir():
        raise ValueError(f"Check root is not a directory: {root_path}")
    files = _files(root)
    docs: dict[Path, MarkdownIndex] = {}
    names: dict[str, list[Path]] = {}
    for path in files:
        rel = path.relative_to(root)
        doc = index_markdown(path.read_text(encoding="utf-8"), path.stem)
        docs[path] = doc
        for value in (doc.title, path.stem, rel.as_posix(), rel.with_suffix("").as_posix(), *doc.aliases):
            names.setdefault(_key(value), []).append(path)
    results: list[dict] = []
    for source, doc in docs.items():
        source_rel = source.relative_to(root).as_posix()
        for link in doc.links:
            result = {"source": source_rel, "line": link.line, "target": link.target, "kind": link.kind, "status": "ok", "reason": "file exists"}
            if link.kind == "wiki":
                target_part, sep, raw_anchor = link.target.partition("#")
                try:
                    decoded = _decode_component(target_part.strip())
                    anchor = _decode_component(raw_anchor) if sep else ""
                except (UnicodeDecodeError, ValueError):
                    decoded, anchor = "", ""
                    result.update(status="skipped", reason="invalid URL encoding")
                direct, _, unsafe = _safe_target(root, source, decoded) if ("/" in decoded or decoded.casefold().endswith(".md")) else (None, None, None)
                candidates: list[Path] = []
                if result["status"] != "ok":
                    pass
                elif unsafe:
                    result.update(status="skipped", reason=unsafe)
                elif direct is not None:
                    direct_file = direct if direct.suffix.casefold() == ".md" else direct.with_suffix(".md")
                    if direct_file in docs:
                        candidates = [direct_file]
                else:
                    candidates = [source] if not decoded and sep else list(dict.fromkeys(names.get(_key(decoded), [])))
                if result["status"] == "ok":
                    if not candidates:
                        result.update(status="missing", reason="wiki target does not exist")
                    elif len(candidates) > 1:
                        result.update(status="missing", reason="ambiguous wiki target: " + ", ".join(sorted(p.relative_to(root).as_posix() for p in candidates)))
                    else:
                        target = candidates[0]
                        if sep and anchor:
                            anchors = {heading.anchor for heading in docs[target].headings}
                            if anchor not in anchors:
                                result.update(status="missing", reason="wiki anchor does not exist")
                            else:
                                result["reason"] = "wiki target and anchor exist"
                        else:
                            result["reason"] = "wiki target exists"
            else:
                candidate, anchor, unsafe = _safe_target(root, source, link.target)
                if unsafe:
                    result.update(status="skipped", reason=unsafe)
                else:
                    try:
                        resolved = candidate.resolve(strict=True)
                    except (FileNotFoundError, NotADirectoryError):
                        result.update(status="missing", reason="file does not exist")
                    else:
                        if not _inside(root, resolved):
                            result.update(status="skipped", reason="symlink escapes scan root")
                        elif not resolved.is_file():
                            result.update(status="missing", reason="target is not a file")
                        elif anchor and resolved.suffix.casefold() == ".md":
                            target_doc = docs.get(resolved)
                            valid = target_doc and anchor in {heading.anchor for heading in target_doc.headings}
                            result.update(status="ok" if valid else "missing", reason="anchor exists" if valid else "Markdown anchor does not exist")
            results.append(result)
    warnings = []
    incoming = {p: 0 for p in files}
    for item in results:
        if item["kind"] == "wiki" and item["status"] == "ok":
            source_path = root / item["source"]
            raw = item["target"].partition("#")[0]
            if not raw and "#" in item["target"]:
                candidates = [source_path]
            else:
                target_path, _, err = _safe_target(root, source_path, raw) if ("/" in raw or raw.casefold().endswith(".md")) else (None, None, None)
                candidates = [target_path] if target_path and target_path.suffix.casefold() == ".md" else [target_path.with_suffix(".md")] if target_path else list(dict.fromkeys(names.get(_key(raw), [])))
            if len(candidates) == 1 and candidates[0] in incoming:
                incoming[candidates[0]] += 1
    for path, count in incoming.items():
        if count == 0:
            warnings.append({"source": path.relative_to(root).as_posix(), "kind": "orphan", "status": "warning", "reason": "no incoming wiki links"})
    results.sort(key=lambda r: (r["source"], r["line"]))
    return {"filesScanned": len(files), "counts": {status: sum(r["status"] == status for r in results) for status in ("ok", "missing", "skipped")}, "results": results, "warnings": warnings}


def render(report: dict, fmt: str = "text") -> str:
    if fmt == "json":
        return json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if fmt == "html":
        from html import escape
        rows = "\n".join(f"<tr><td>{escape(r['status'])}</td><td>{escape(r['source'])}:{r['line']}</td><td>{escape(r['kind'])}</td><td>{escape(r['target'])}</td><td>{escape(r['reason'])}</td></tr>" for r in report["results"])
        warnings = "\n".join(f"<li>{escape(w['source'])}: {escape(w['reason'])}</li>" for w in report["warnings"])
        return f'<!doctype html><meta charset="utf-8"><title>Link Doctor report</title><h1>Link Doctor report</h1><table><thead><tr><th>Status</th><th>Location</th><th>Kind</th><th>Target</th><th>Reason</th></tr></thead><tbody>{rows}</tbody></table><h2>Warnings</h2><ul>{warnings}</ul>\n'
    if fmt != "text":
        raise ValueError(f"Invalid format: {fmt}")
    lines = [f"Files scanned: {report['filesScanned']}", f"Links: {sum(report['counts'].values())} (ok {report['counts']['ok']}, missing {report['counts']['missing']}, skipped {report['counts']['skipped']})"]
    lines.extend(f"{r['status'].upper()} {r['source']}:{r['line']} [{r['kind']}] {json.dumps(r['target'], ensure_ascii=False)} — {r['reason']}" for r in report["results"])
    lines.extend(f"WARNING {w['source']} — {w['reason']}" for w in report["warnings"])
    return "\n".join(lines) + "\n"
