# Link Doctor

[English](README.md) | [한국어](README.ko.md)

Link Doctor provides tools to validate links, compile markdown with wiki links, ingest office documents into markdown, and semantically search documentation. It has two CLIs: a standalone Node.js scanner and a comprehensive Python CLI for compilation and search.

## Node.js CLI

The Node.js CLI recursively checks local file and image links in Markdown documents. It does not modify input files and makes no network requests.

### Requirements

- Node.js 24.x
- npm

Install dependencies and run the Node test suite:

```sh
npm install
npm test
```

### Usage

```sh
node src/cli.js ./docs
node src/cli.js ./docs --format json
node src/cli.js ./docs --format html --output ./outputs/report.html
```

Formats are `text` (default), `json`, and `html`. HTML is a self-contained static report; `--output` is supported only with HTML. The output parent directory must already exist.

Exit status is `0` when no missing targets are found, `1` when at least one target is missing or is not a file, and `2` for argument, input, read, or output errors.

## Python CLI

The Python CLI expands capabilities to document ingestion, wiki link compilation, and semantic search. 

### Requirements

- Python >= 3.12, < 3.14 (Verified with Python 3.12.15)

Install core capabilities and run tests:

```sh
pip install -e .
python -m unittest discover -s python_tests -v
```

Optional capabilities require additional dependencies (lazy-loaded):
- `pip install -e '.[ingest]'` installs Docling (verified with 2.136.0) for document conversion.
- `pip install -e '.[search]'` installs Sentence Transformers (>= 6.1, verified with 6.1.0), Transformers (>= 5.19, verified with 5.19.0), and PyTorch (verified with 2.14.1).
- `pip install -e '.[all]'` installs both extras.

### Commands

The entry point is `link-doctor-py` (equivalent to `python -m link_doctor`).

- **Check**: Validates regular and `[[wiki links]]`.
  ```sh
  link-doctor-py check <root> [--format text|json|html] [--output FILE]
  ```
  Exit status is `0` when no targets are missing (external and unsafe/out-of-root symlink links are skipped). It returns `1` for missing or ambiguous targets, and `2` for usage/I/O failures. HTML output will be rejected with `2` if it attempts to overwrite a Markdown input.
- **Compile**: Compiles Markdown and wiki links, generating a graph and rewriting links. Fenced and inline code spans are masked and excluded from lexical matching.
  ```sh
  link-doctor-py compile <root> [--output <dir>] [--format text|json|html]
  ```
- **Ingest**: Converts local PDF/DOCX into Markdown and extracts assets.
  ```sh
  link-doctor-py ingest <source-dir> --output <dir> [--recursive]
  ```
  *Note*: Conversion supports native text documents. Scanned image OCR requires an external OCR engine to be installed; it is not currently exercised or claimed by default.
- **Search**: Semantic search using a reusable local index.
  ```sh
  link-doctor-py search <root> <query> [--top-k N] [--index-dir DIR] [--dimension 256] [--device DEVICE]
  ```
  The search command uses `google/embeddinggemma-2` (exact revision `914f7f89142e33e77833254d9c9b90c3cef7303b`) with asymmetric `SearchQuery` + title-formatted `SearchDocument` embeddings, and symmetric `SentenceSimilarity` relation candidates (cosine >= 0.55 among top-k query hits). Candidates remain unverified and are never auto-linked. Embeddings are truncated to the target dimension and L2-normalized. Cache entries use a content-hash identity (including source/chunk content, model ID/revision, dimension, task, and chunk configuration). Stale generations are ignored but kept until the user manually removes `.link-doctor/index`.

## Reports

- Text: stable, line-oriented summary for terminals.
- JSON: structured diagnostics and metrics.
- HTML: self-contained static report for viewing in a browser.

The sample documentation under [`docs/`](docs/index.md) is used for CLI smoke checks. Test fixtures live under [`test/fixtures/scan/`](test/fixtures/scan/index.md).
