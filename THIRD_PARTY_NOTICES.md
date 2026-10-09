# Third Party Notices

This project (`link-doctor`) uses several third-party libraries and models. We gratefully acknowledge their authors and contributors. 

## Node.js Dependencies

- **mdast-util-from-markdown**: Used to parse Markdown documents for link resolution. Distributed under the MIT License.

## Python Dependencies

- **wiki-compiler**: Vendored integration for compiling Markdown documents and wiki links into graph representations.
- **docling**: Used for ingesting PDF and DOCX files when installed with `pip install -e '.[ingest]'`. Distributed under the MIT License.
- **sentence-transformers**: Used for semantic search when installed with `pip install -e '.[search]'`. Distributed under the Apache 2.0 License.
- **PyTorch**: Deep learning framework required for embeddings. Distributed under the BSD License.

## Models

- **google/embeddinggemma-2**: Text embedding model used for semantic search.

Please refer to the respective documentation and source repositories of these libraries and models for full license texts and terms of use.
