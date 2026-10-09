"""Local PDF/DOCX ingestion through Docling, with source/output provenance."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


def _position(obj, label: str):
    value = getattr(obj, label, None)
    if value is None:
        return None
    if hasattr(value, "page_no"):
        return value.page_no
    if isinstance(value, int):
        return value
    return None


def _provenance(document, markdown: str) -> list[dict]:
    lines = markdown.splitlines()
    sections: dict[int, str | None] = {}
    current_section = None
    for number, line in enumerate(lines, 1):
        if line.lstrip().startswith("#"):
            current_section = line.lstrip("# ").strip() or None
        sections[number] = current_section
    records = []
    for item, level in document.iterate_items():
        prov_list = getattr(item, "prov", None) or []
        page = _position(prov_list[0], "page_no") if prov_list else None
        text = getattr(item, "text", None)
        if not text:
            continue
        value = str(text).strip()
        needle = value.splitlines()[0]
        match = next((i for i, line in enumerate(lines, 1) if needle and needle in line), None)
        records.append({"text": value, "level": level, "page": page, "section": sections.get(match) if match else None, "markdown_line": match})
    return records


def ingest(source_dir: str | Path, output_dir: str | Path, recursive: bool = False) -> dict:
    source = Path(source_dir).resolve(strict=True)
    output = Path(output_dir).resolve()
    if not source.is_dir():
        raise ValueError(f"Input is not a directory: {source}")
    if output == source or source in output.parents or output in source.parents:
        raise ValueError("Ingest output directory must be separate from the source directory")
    candidates = sorted(p for p in (source.rglob("*") if recursive else source.iterdir()) if p.is_file() and not p.is_symlink() and p.suffix.casefold() in {".pdf", ".docx"})
    if not candidates:
        raise ValueError(f"No PDF or DOCX files found in {source}")
    try:
        from docling_core.types.doc import ImageRefMode
        from docling.document_converter import DocumentConverter
    except ImportError as exc:
        raise RuntimeError(f"Docling import failed ({exc}); install with `pip install -e '.[ingest]'`.") from exc
    converter = DocumentConverter()
    entries = []
    output.mkdir(parents=True, exist_ok=True)
    used_targets: set[Path] = set()
    for original in candidates:
        relative = original.relative_to(source)
        target_base = (output / relative).with_suffix("")
        if target_base in used_targets:
            target_base = target_base.with_name(f"{target_base.name}-{relative.suffix[1:].casefold()}")
        used_targets.add(target_base)
        target_base.parent.mkdir(parents=True, exist_ok=True)
        if not target_base.parent.resolve().is_relative_to(output.resolve()):
            raise ValueError(f"Generated document path escapes output directory: {relative}")
        markdown_path = target_base.with_suffix(".md")
        assets_dir = target_base.parent / f"{target_base.name}_assets"
        assets_dir.mkdir(parents=True, exist_ok=True)
        try:
            result = converter.convert(original)
            doc = result.document
            # Docling's referenced image mode writes extracted pictures beside the Markdown file.
            image_prefix = assets_dir.relative_to(markdown_path.parent).as_posix() + "/"
            markdown = doc.export_to_markdown(image_mode=ImageRefMode.REFERENCED, image_dir=assets_dir, image_uri_prefix=image_prefix)
        except Exception as exc:
            raise RuntimeError(f"Docling failed to convert {relative}: {exc}") from exc
        markdown_path.write_text(markdown, encoding="utf-8")
        asset_refs = sorted(p.relative_to(output).as_posix() for p in assets_dir.rglob("*") if p.is_file())
        input_hash = hashlib.sha256(original.read_bytes()).hexdigest()
        entries.append({
            "source": relative.as_posix(),
            "markdown": markdown_path.relative_to(output).as_posix(),
            "sha256": input_hash,
            "assets": asset_refs,
            "provenance": _provenance(doc, markdown),
        })
    metadata_dir = output / ".link-doctor"
    metadata_dir.mkdir(exist_ok=True)
    manifest = {"schema_version": 1, "documents": entries}
    (metadata_dir / "provenance.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest
