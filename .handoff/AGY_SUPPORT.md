# AGY Support Expansion

This document outlines the support added to Link Doctor for AGY documentation workflows. The original Node.js CLI provided standard Markdown link validation. The Python CLI expansion adds specific capabilities required for the AGY documentation pipeline.

## Capabilities

- **Wiki Link Compilation**: Resolves `[[wiki links]]` and compiles Markdown documents into an integrated graph.
- **Document Ingestion**: Converts local PDF and DOCX files into Markdown, extracting necessary assets for integration into the documentation site. Uses `docling` under the hood.
- **Semantic Search**: Provides a semantic search CLI (`link-doctor-py search`) over documentation using normalized embeddings (`google/embeddinggemma-2`).
- **Comprehensive Validation**: Continues to support standard validation and diagnostic reporting for broken links or orphaned documents.

## Integration Details

- The CLI uses a modular installation structure allowing environments to install only necessary dependencies (e.g. `[ingest]` or `[search]`).
- The semantic search index is generated locally and cached in `.link-doctor/index`.
- Output artifacts include `graph.json` and transformed Markdown files tailored for the AGY system.
- Full interface specifications can be found in `.handoff/EXPANSION_CONTRACT.md`.
