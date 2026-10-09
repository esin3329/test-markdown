# Third Party Notices

This project uses several third-party libraries and models. We gratefully acknowledge their authors and contributors.

## Node.js Dependencies

- **mdast-util-from-markdown**: Used to parse Markdown documents for link resolution. Distributed under the MIT License.

## Python Dependencies & Extracurriculars

- **docling**: Document processing code is distributed under the MIT License. (Note: External models fetched by Docling may be subject to their own separate licenses).
  - Source: [https://github.com/docling-project/docling](https://github.com/docling-project/docling)
- **wiki-compiler**: Integrated as a dependency for compiling Markdown documents and wiki links. Distributed under the MIT License.
  - Source: [https://github.com/Emmimal/wiki-compiler](https://github.com/Emmimal/wiki-compiler)
- **sentence-transformers**: Used for semantic search when installed with `pip install -e '.[search]'`. Distributed under the Apache 2.0 License.
- **PyTorch**: Deep learning framework required for embeddings. Distributed under the BSD License.

## Models

- **google/embeddinggemma-2**: Text embedding model used for semantic search (specifically 2026-10-06 release, exact revision `914f7f89142e33e77833254d9c9b90c3cef7303b`). Distributed under the Apache 2.0 License.
  - Source: [https://huggingface.co/google/embeddinggemma-2](https://huggingface.co/google/embeddinggemma-2)

Please refer to the respective documentation and source repositories of these libraries and models for full license texts and terms of use.
