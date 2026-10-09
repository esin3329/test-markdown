# Link Doctor expansion implementation readiness

## Implemented interfaces

- Python package `link-doctor`, import module `link_doctor`, entry point `link-doctor-py` / `python -m link_doctor`, Python `>=3.12,<3.14`.
- Commands: `ingest`, `compile`, `search`, `check`. Exact options, paths, report policy, and extras are in `.handoff/EXPANSION_CONTRACT.md`.
- Existing Node 24 ESM CLI and its text/JSON/HTML reports remain unchanged.
- Optional extras are lazy-imported: `.[ingest]` (Docling), `.[search]` (Sentence Transformers, Transformers, PyTorch), `.[all]`.

## Implementation facts

- Docling API used: `DocumentConverter.convert` and `DoclingDocument.export_to_markdown(ImageRefMode.REFERENCED, image_dir=..., image_uri_prefix=...)`. Source and output directories are required to be disjoint. Generated `.md` links/assets are relative to the output tree. `.link-doctor/provenance.json` v1 records original source hash, assets, page (if available), section, and Markdown line separately.
- Wiki compiler integration vendors upstream `graph.py` and `rewriter.py` from MIT project `Emmimal/wiki-compiler`, pinned at `b2b2b0ecf5f32d69e1cf6d9254216ab902f3d188`. The upstream graph stage is adapted for Unicode whole-word tokens and aliases; Markdown documents are adapted into upstream entities, and `build_graph`, `orphan_ids`, and `compile_pages` are used. Code spans are masked before lexical relation matching and the rewriter preserves original source code. Names use hierarchical source-path slugs with stable hash suffixes on slug collision. Markdown/wiki diagnostics handle aliases, anchors, duplicate names, path traversal, URL decoding, and code exclusion. Orphans are warnings only.
- Semantic model is exactly `google/embeddinggemma-2@914f7f89142e33e77833254d9c9b90c3cef7303b`. Search uses SearchQuery + model-card-formatted title/text SearchDocument embeddings; relation candidates use symmetric SentenceSimilarity embeddings and are explicitly marked unverified, never inserted as links. Text-only model config sets `config_kwargs={"vision_config": None, "audio_config": None}`. Outputs are float32, truncated to requested supported MRL dimension and re-normalized after truncation.
- Cache identity hashes source/chunk content and model ID/revision, dimension, task, and chunk size. Any identity change causes a cache miss; previous generations are retained until removed by the user. Default cache is `.link-doctor/index`.

## Verification actually run

Runtime: project `.venv`, CPython 3.12.15; Docling 2.136.0; PyTorch 2.14.1+cu130; Transformers 5.19.0; Sentence Transformers 6.1.0. Device: NVIDIA GeForce RTX 3060; CUDA BF16 support reported true.

- `npm test`: 12 passed, 0 failed, 0 skipped. Evidence: `.handoff/evidence/node-tests-final.txt`.
- `.venv/bin/python -m unittest discover -s python_tests -v`: 13 passed, 0 failed. Evidence: `.handoff/evidence/python-tests-final.txt`. Mock-based search/index tests are isolated from real model evidence.
- `npm run check`: 2 Markdown files, 1 link, 0 missing/skipped. Evidence: `.handoff/evidence/node-docs-check-final.txt`.
- Real model vector inference through the implementation returned shape `[1,256]`, all finite values, L2 norm `1.0`. Evidence: `.handoff/evidence/embeddinggemma-real-vector.txt`.
- Real `link-doctor-py search` over the Docling corpus ran EmbeddingGemma2 and returned ranked chunks plus explicitly unverified semantic candidates; the repeated run returned `cache_reused: true`. Evidence: `.handoff/evidence/embeddinggemma-real-search.json`.
- Real Docling converted one text PDF, two DOCX files, including a DOCX with an embedded image, to Markdown. It wrote a referenced image under `image_assets/`; PDF provenance reports source page 1 and Markdown line 1. Evidence: `.handoff/evidence/docling-real-ingest.json`.
- End-to-end real corpus check: 3 converted Markdown files, 3 valid links (two wiki links and the generated image link), 0 missing/skipped, 1 orphan warning. The warning does not affect exit status. Evidence: `.handoff/evidence/end-to-end-check.json`.
- End-to-end real corpus compile produced three upstream-rewriter pages, deterministic graph and diagnostics; evidence `.handoff/evidence/end-to-end-compile.txt`.
- `link-doctor-py compile ... --format html` also emitted a valid HTML document to stdout; the compile summary went to stderr. The CLI regression test covers this separation.
- `uv build --wheel` succeeded; an isolated Python 3.12 venv installed the final wheel and ran `link-doctor-py compile docs --output /tmp/link-doctor-wheel-compiled --format json` successfully: 2 pages compiled, `graph.json` emitted, 1 valid Markdown link, 0 missing/skipped. The wheel contains the vendored graph/rewriter and MIT license. Evidence: `.handoff/evidence/python-wheel-smoke.txt`.

## Limits observed

- Docling emitted `No OCR engine found. Please review the install details.` during the text-native PDF/DOCX/image conversion; all conversions succeeded, but scanned-image OCR was not exercised and is not claimed.
- This is local extraction and embedding inference; no generation/summarization model is added. Semantic candidates are not assertions and are not written back as links.
- HF Hub emitted the unauthenticated-request rate-limit warning; the pinned weights downloaded and inference succeeded.
- No project-wide LICENSE is declared. The vendored upstream MIT notice is preserved at `src/link_doctor/_vendor/wiki_compiler/LICENSE`.
