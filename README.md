# Link Doctor

Link Doctor recursively checks local file and image links in Markdown documents. It does not modify input files and does not make network requests.

## Requirements

- Node.js 24.x
- npm

Install dependencies and run the test suite:

```sh
npm install
npm test
```

## Usage

```sh
node src/cli.js ./docs
node src/cli.js ./docs --format json
node src/cli.js ./docs --format html --output ./outputs/report.html
```

Formats are `text` (default), `json`, and `html`. HTML is a self-contained static report; `--output` is supported only with HTML. The output parent directory must already exist. To preserve input documents, the CLI refuses an output path that resolves to a Markdown file under the scan root.

The scanner walks `.md` files recursively and excludes `.git`, `node_modules`, and symlink entries. Relative paths resolve from each Markdown file; paths beginning with `/` resolve from the scan root. URL-encoded filenames are decoded. Local links, images, and reference links are checked; code blocks and inline code are ignored. A target must be a file. External URLs, anchor-only links, paths outside the root, and symlinks that resolve outside the root are skipped. File fragments are not validated; successful file links with fragments say `anchor not verified` in the result reason. Each result includes `source`, `line`, `target`, `kind`, `status` (`ok`, `missing`, or `skipped`), and `reason`.

Exit status is `0` when no missing targets are found, `1` when at least one target is missing or is not a file, and `2` for argument, input, read, or output errors.

## Reports

- Text: stable, line-oriented summary for terminals.
- JSON: `filesScanned`, per-status `counts`, and ordered `results`.
- HTML: one static document with escaped report content; it contains no executable scripts.

The sample documentation under [`docs/`](docs/index.md) is used for the CLI smoke check. Test fixtures live under [`test/fixtures/scan/`](test/fixtures/scan/index.md).
