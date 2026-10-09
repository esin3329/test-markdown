# Link Doctor expansion contract

Implementation interface for AGY documentation. Update this file if the CLI or generated formats change.

## Package and runtime

- Python distribution: `link-doctor` (project remains private; no project-wide license declaration).
- Import package: `link_doctor`, Python `>=3.12,<3.14` (verified compatible runtimes only).
- Entry point: `link-doctor-py`; equivalent `python -m link_doctor`.
- Existing Node 24 ESM CLI remains `node src/cli.js <directory> [--format text|json|html] [--output file]`; no model dependencies are needed for it.

## Python commands

- `link-doctor-py ingest <source-dir> --output <dir> [--recursive]`: converts local PDF/DOCX into `<output>/<relative-source-without-extension>.md`, associated exported assets, and `.link-doctor/provenance.json`. Markdown links resolve against generated output files. Source files are read only. Docling is loaded only for this command.
- `link-doctor-py compile <root> [--output <dir>] [--format text|json|html]`: adapts Markdown into the vendored `wiki-compiler` graph/rewriter pipeline; fenced and inline code is excluded from lexical relationships, and link diagnostics classify errors separately from orphan warnings. Output defaults to stdout; optional output directory receives compiled Markdown/graph artifacts.
- `link-doctor-py search <root> <query> [--top-k N] [--index-dir DIR] [--dimension 256] [--device DEVICE]`: semantic search using `google/embeddinggemma-2` at revision `914f7f89142e33e77833254d9c9b90c3cef7303b`, asymmetric SearchQuery + title-formatted SearchDocument embeddings, and symmetric SentenceSimilarity relation candidates (cosine ≥0.55 among top-k query hits). Embeddings are truncated and L2-normalized; candidates are never written back as links.
- `link-doctor-py check <root> [--format text|json|html] [--output FILE]`: checks ordinary Markdown and `[[wiki links]]`; text/JSON to stdout, HTML can be written with `--output`. Exit status 0 when no targets are missing (including reports with skipped external/out-of-root links), 1 for missing or ambiguous targets, 2 for usage, I/O, or dependency failures. Orphan diagnostics are warnings and do not fail the command. HTML output refuses to overwrite a Markdown input.

## Layout and formats

- Python sources: `src/link_doctor/`; tests: `python_tests/`.
- Ingest provenance JSON schema version `1`: top-level `schema_version`, `documents`; each entry has source-relative path, output-relative Markdown path, SHA-256 input hash, assets, and page/section/Markdown-line provenance records. `page` is source PDF/DOCX page numbering when Docling supplies it; `markdown_line` is generated Markdown line numbering. Unknown source position is `null`.
- Compile output contains deterministic `graph.json`, diagnostics JSON, and rewritten Markdown under `--output` when requested; `--format` controls diagnostic report format.
- Search cache defaults to `.link-doctor/index`; entries are keyed by content SHA-256 plus model ID/revision, dimension, task, and chunk settings. Changes force a cache miss/new entry; stale generations are ignored, not automatically deleted. Remove the cache directory to reclaim old generations. Do not commit cache or weights.

## Optional dependencies

- `pip install -e '.[ingest]'` installs Docling >=2.136 (tested with 2.136.0).
- `pip install -e '.[search]'` installs Sentence Transformers >=6.1, Transformers >=5.19, and PyTorch.
- `pip install -e '.[all]'` installs Docling plus both embedding packages.
- Core checks/compilation use lightweight Python dependencies; model/Docling extras are lazy imports.

## Verification

- Existing Node regression suite: `npm test` on Node 24.
- Python core suite: `python -m unittest discover -s python_tests -v`.
- CLI smoke: `python -m link_doctor check docs`, `python -m link_doctor compile docs`.
- Full installed extras and real model/document conversion evidence are recorded in `.handoff/EXPANSION_READY.md` and `.handoff/evidence/` separately from mock/unit tests.
