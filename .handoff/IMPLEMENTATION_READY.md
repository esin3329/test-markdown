# Link Doctor implementation ready — independent review addressed

## Implementation scope

Implemented Node.js 24 ESM CLI, `mdast-util-from-markdown` scanner, and text/JSON/static HTML renderers. The scanner handles ordinary, image, full/collapsed reference links and their use-line numbers; ignores inline and block code; resolves nested and root-relative links plus URL-encoded names; skips external URLs, anchor-only links, out-of-root paths, and out-of-root symlinks; excludes `.git`, `node_modules`, and symlink entries. Reports have deterministic source/line ordering and `ok | missing | skipped` statuses. CLI status is 0/1/2 for clean/missing/argument-or-I/O failure. HTML escapes report content. Output is refused if it resolves to a Markdown file under the scan root, preserving inputs.

## Changed files

- `.gitignore` — ignores the installed `node_modules/` tree.
- `package.json`, `package-lock.json` — ESM package, Node 24 local runtime, parser dependency, scripts.
- `src/scan.js`, `src/report.js`, `src/cli.js` — scanner, renderers, CLI.
- `test/scan.test.js`, `test/report-cli.test.js`, `test/fixtures/scan/**` — scanner, CLI, escaping, symlink, and exit-code coverage.
- `README.md`, `docs/index.md`, `docs/guide.md` — usage and clean docs smoke target.
- `EXPERIMENTS.md` — only observed Orca/Herdr results; unavailable experiments explicitly marked not performed.
- `.handoff/evidence/**` — captured test, CLI, docs, and read-error evidence.

`PLAN.md` was not modified. The independent review report is recorded in `.handoff/REVIEW.md`.

## Reproduction and evidence

Runtime: `./node_modules/.bin/node --version` → `v24.21.0`.

- Full suite: `npm test` → 12 tests, 12 passed, 0 failed, 0 skipped; captured at `.handoff/evidence/tests-after-review.txt`. Explicit Node 24 run `./node_modules/.bin/node --test` also passed 12/12; captured at `.handoff/evidence/tests-node24-final.txt`.
- Real docs folder: `npm run check` → 2 files, 1 link, 1 ok, 0 missing, 0 skipped. Explicit Node 24 `./node_modules/.bin/node src/cli.js ./docs` produced the same clean report; captured at `.handoff/evidence/docs-check-node24-final.txt`.
- Text/JSON/HTML examples: `./node_modules/.bin/node src/cli.js test/fixtures/scan`, add `--format json`, or add `--format html --output .handoff/evidence/cli-report.html`. All three produced output and returned 1 because the fixture intentionally contains one missing link. Captured outputs: `.handoff/evidence/cli-text.txt`, `cli-json.json`, `cli-report.html`, `cli-status.txt` (`text=1`, `json=1`, `html=1`).
- Unreadable Markdown input: chmod-000 file produced `EACCES` and exit 2; captured at `.handoff/evidence/read-error.txt` and `read-error-status.txt`. Automated permission test now covers this path on non-root POSIX test runs.
- `npm test` exercises exit 0, expected broken-link exit 1, argument/input/output errors exit 2, refusal to overwrite a Markdown input directly or through a symlink, and anchor-unverified reasons in text/JSON/HTML.

The fixture's `assets/missing.md` result is an intentional test input, not a product defect. The real `docs/` scan has no broken or skipped links.

## Independent review disposition and constraints

The independent review in `.handoff/REVIEW.md` identified one plan defect (F1) and refinements F2–F4, then one test-quality issue (G1). F1: successful file links with fragments say `file exists; anchor not verified`; missing targets with fragments remain `missing` / `file does not exist`. Scanner and text/JSON/HTML CLI regressions cover both. F2: empty and query-only links have distinct skip reasons. F3: stable sorting preserves source occurrence for same-line links. F4: source paths use locale-independent UTF-16 code-unit ordering (not Unicode scalar-value ordering). G1: path-order regression includes `B/z.md` and `Z.md`, which makes it fail under locale sorting. The final review marks G1 resolved with no remaining findings. Additional regression coverage includes Hangul and encoded spaces, reference images, directory targets, uppercase `.MD`, and unreadable input. Local Node 24.21.0 test suite passes 12/12; real docs scan is clean.

The working directory started without a Git repository; none was initialized. Orca runtime was ready, but this path is registered as folder-kind, so the plan's parallel Git-worktree worker experiment was not performed. Herdr 0.9.3 was running and protocol-compatible, but this shell lacks `HERDR_ENV=1`; its skill disallows session control here. Herdr split/detach/reattach experiments were not performed. Details: `EXPERIMENTS.md`.

Known scope limits match the plan: no HTTP checks, fragment/heading-anchor validation, or automatic link repair; file fragments are explicitly reported as unverified. Output parents must exist. Absolute `/...` links are scan-root relative. No timing or interaction-count metrics were collected.
