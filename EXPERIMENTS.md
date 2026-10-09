# Orca and Herdr experiment record

## Environment observations

- The directory initially had no `.git` repository; `git rev-parse --show-toplevel` failed with `fatal: not a git repository`. No Git repository was initialized.
- The first `node --version` was `v22.22.1`, below the planned Node 24 runtime. The project-local `node@24.21.0` package was installed; `./node_modules/.bin/node --version` reports `v24.21.0`. Tests run with that local binary.
- Orca CLI `orca-ide` is available. `orca-ide status --json` reported app version `1.4.223`, runtime ready/reachable, and graph ready. `orca-ide repo list --json` reports this directory as a `folder` repo, not a Git repo.
- Herdr client/server `0.9.3` reported running and protocol-compatible. This shell has no `HERDR_ENV=1`; Herdr's installed skill prohibits controlling the current session outside a Herdr-managed pane. No workspace, split, agent, detach, or reattach experiment was performed.

## Planned workflow results

| Experiment | Evidence | Result |
|---|---|---|
| Parallel Orca worktree implementation | No Git repository; Orca repo is folder-kind | Not performed. No Git initialization or worker dispatch was made. |
| Herdr review/test/manual panes | Herdr `status` succeeded; `HERDR_ENV` check returned “not 1” | Not performed; session control is disallowed from this shell. The requested independent review is handed to `agy` separately. |
| Herdr detach/reattach continuity | No Herdr-managed caller session | Not performed. |

Task durations, post-instruction human intervention counts, and reassignment counts were not instrumented; no values are claimed. No tool-speed comparison is made.
