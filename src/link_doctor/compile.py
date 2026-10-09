"""Markdown-to-entity adapter around the pinned upstream compiler stages."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, replace
from pathlib import Path

from .check import check
from .markdown import index_markdown, slugify, text_without_code
from ._vendor.wiki_compiler.graph import build_graph, orphan_ids
from ._vendor.wiki_compiler.rewriter import compile_pages

UPSTREAM_REVISION = "b2b2b0ecf5f32d69e1cf6d9254216ab902f3d188"


@dataclass
class Entity:
    entity_id: str
    name: str
    aliases: list[str] = field(default_factory=list)
    created: str = ""
    body: str = ""
    source_path: str = ""


def _entities(root: Path) -> dict[str, Entity]:
    entities = {}
    used: set[str] = set()
    for path in sorted(p for p in root.rglob("*") if p.is_file() and p.suffix.casefold() == ".md" and not any(part in {".git", ".link-doctor", "node_modules", ".venv"} for part in p.parts) and not p.is_symlink()):
        rel = path.relative_to(root).as_posix()
        document = index_markdown(path.read_text(encoding="utf-8"), path.stem)
        base = slugify(Path(rel).with_suffix("").as_posix().replace("/", " "))
        entity_id = base
        if entity_id in used:
            entity_id = f"{base}-{hashlib.sha256(rel.encode()).hexdigest()[:8]}"
        used.add(entity_id)
        entities[entity_id] = Entity(entity_id, document.title, list(document.aliases), "", document.body, rel)
    return entities


def compile_wiki(root_path: str | Path, output_dir: str | Path | None = None) -> dict:
    root = Path(root_path).resolve(strict=True)
    if not root.is_dir():
        raise ValueError(f"Compile root is not a directory: {root_path}")
    entities = _entities(root)
    graph_entities = {entity_id: replace(entity, body=text_without_code(entity.body)) for entity_id, entity in entities.items()}
    graph = build_graph(graph_entities)
    diagnostics = check(root)
    written = []
    if output_dir:
        dest = Path(output_dir).resolve()
        if dest == root or root in dest.parents:
            raise ValueError("Compile output must not be inside the Markdown input root")
        dest.mkdir(parents=True, exist_ok=True)
        written = compile_pages(entities, graph, str(dest))
        (dest / "diagnostics.json").write_text(json.dumps(diagnostics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        graph_data = {key: {edge: sorted(values) for edge, values in edges.items()} for key, edges in sorted(graph.items())}
        (dest / "graph.json").write_text(json.dumps({"upstream_revision": UPSTREAM_REVISION, "entities": graph_data, "orphans": orphan_ids(graph)}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"diagnostics": diagnostics, "entities": len(entities), "graph": graph, "orphans": orphan_ids(graph), "written_paths": written, "upstream_revision": UPSTREAM_REVISION}
