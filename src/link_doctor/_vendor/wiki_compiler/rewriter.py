"""Upstream wiki-compiler rewriter.py (pinned and adapted as an importable module).

Upstream: https://github.com/Emmimal/wiki-compiler
Revision: b2b2b0ecf5f32d69e1cf6d9254216ab902f3d188
Copyright (c) 2026 Emmimal P Alexander; MIT License.
"""
import os
import re

SECTION_RE = re.compile(r"^##\s+(.+)$", re.MULTILINE)


def _parse_existing_sections(text: str) -> dict:
    sections = {}
    matches = list(SECTION_RE.finditer(text))
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sections[match.group(1).strip()] = text[match.end():end].strip("\n")
    return sections


def render_page(entity, graph_edges: dict, entities: dict, existing_path: str = None) -> str:
    preserved_notes = ""
    if existing_path and os.path.exists(existing_path):
        with open(existing_path, "r", encoding="utf-8") as stream:
            preserved_notes = _parse_existing_sections(stream.read()).get("Notes", "").strip()
    lines = [f"# {entity.name}", "", "## Metadata", f"- created: {entity.created or 'unknown'}", f"- aliases: {', '.join(entity.aliases) if entity.aliases else 'none'}", f"- source: {entity.source_path}", "", "## Related"]
    outgoing = sorted(graph_edges["outgoing"])
    lines.extend((f"- [[{entities[target].name}]]" for target in outgoing) if outgoing else ["- (no outgoing references found)"])
    lines.extend(["", "## Referenced By"])
    incoming = sorted(graph_edges["incoming"])
    lines.extend((f"- [[{entities[source].name}]]" for source in incoming) if incoming else ["- (orphan: no other page links here)"])
    lines.extend(["", "## Body", entity.body, "", "## Notes", preserved_notes or "_(add your own notes here -- preserved on recompile)_", ""])
    return "\n".join(lines)


def compile_pages(entities: dict, graph: dict, output_dir: str) -> list:
    os.makedirs(output_dir, exist_ok=True)
    written = []
    for eid in sorted(entities):
        entity = entities[eid]
        out_path = os.path.join(output_dir, f"{eid}.md")
        with open(out_path, "w", encoding="utf-8") as stream:
            stream.write(render_page(entity, graph[eid], entities, existing_path=out_path))
        written.append(out_path)
    return written
