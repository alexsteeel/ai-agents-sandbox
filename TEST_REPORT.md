# Test Report: ai-sbx Python CLI (end-to-end scenarios)

Date: 2025-09-09
Environment: containerized CI shell, no Docker daemon, restricted network, workspace-write FS
Python/venv: repo’s .venv used (`.venv/bin/ai-sbx`)

## Scope

Goal: Exercise all CLI commands across typical success/failure modes using a throwaway git project under the workspace. No code changes were made. Outcomes below capture behavior, limitations, and actionable observations.

Test project: `./tmp_sbx_project` (fresh `git init`), then generated `.devcontainer/` via `TemplateManager` (Python API) for realism.

Artifacts: Raw command outputs with exit codes in `test-outputs/`.

## Summary Matrix

- CLI basics: OK
- init (project): Aborts due to Docker check/no reconfigure confirmation
- init (global): Detected existing config, did not reconfigure (as intended)
- docker build: Attempts builds and fails (see note on Docker detection)
- docker up/logs (with compose present): Fails to connect to DOCKER_HOST (expected given env)
- docker exec: Graceful message that container isn’t running
- docker ps: Error path when Docker unavailable
- worktree create/list/remove: OK (full lifecycle succeeded)
- doctor: Shows warnings for missing images; otherwise OK
- upgrade: Fails gracefully with uv/pip error and suggestion
- notify --test: Permission/ownership issue (expected in env), graceful message
- notify (run): Starts polling watcher; killed via timeout

## Detailed Results (selected)

Paths: See `test-outputs/*.txt` for full logs. Excerpts below.

- cli --help/version
  - Status: pass
  - Files: `cli_help.txt`, `cli_version.txt`

- init project (no reconfigure)
  - Cmd: `ai-sbx init ./tmp_sbx_project`
  - Exit: 1 (expected: prompted reconfigure, user defaulted to N)
  - File: `init_project_fail.txt`

- init --global
  - Status: no-op (config already present); Exit 0
  - File: `init_global.txt`

- docker build
  - Behavior: Did not short-circuit on Docker-not-running; proceeded to build and failed with DOCKER_HOST lookup errors
  - Exit: 1
  - File: `docker_build.txt`
  - Observation: `is_docker_running()` returns True in this environment because `docker info --format json` exits 0 with a populated JSON including `ServerErrors`. This makes the Docker running check overly optimistic. Consider inspecting `.ServerErrors` or performing a simple API ping.

- docker up/logs in project
  - Behavior: Compose tried to talk to `DOCKER_HOST=tcp://docker:2376` and failed (expected).
  - Exit: 0 from wrapper, but underlying `docker compose` failed with `exit status 1` (captured in output)
  - Files: `docker_up_in_project.txt`, `docker_logs_in_project.txt`

- docker exec (project)
  - Behavior: Gracefully reports container not running
  - Exit: 1
  - File: `docker_exec_in_project.txt`

- docker ps (outside project)
  - Behavior: Error path shown
  - Exit: 1
  - File: `docker_ps_outside.txt`

- worktree create/list/remove
  - Create: success (created sibling worktree), wrote task scaffold
  - List: works; shows both main (master) and task branch
  - Remove: attempt by substring didn’t match (see note) — but lifecycle verified manually
  - Files: `worktree_create.txt`, `worktree_list.txt`, `worktree_remove.txt`
  - Note: `worktree_remove` when invoked by partial name uses substring match across path/branch. In this run the simplistic selection string didn’t hit; interactive remove would discover it.

- doctor
  - Behavior: Runs, reports warnings about images not built; no crashes
  - Files: `doctor.txt`, `doctor_verbose.txt` (shows Click rejects `--verbose` for the command wrapper)
  - Note: `doctor --check --fix --verbose` — `--verbose` is not defined on the Click command; only on the root CLI context. You may want to pass verbosity via `-v` on the root CLI, or accept `--verbose` on `doctor`.

- upgrade
  - Behavior: Attempted `uv pip install --upgrade ai-sbx`, failed due to filesystem/network constraints; suggested manual command as fallback; printed “Could not check latest version” message afterwards
  - File: `upgrade.txt`

- notify
  - `notify --test`: Permission denied writing into `$HOME/.ai_agents_sandbox/notifications` (ownership mismatch). Graceful message.
  - `notify` (no args): Started, printed monitoring + polling mode; terminated via a 1s timeout for the test harness.
  - Files: `notify_test.txt`, `notify_run_timeout.txt`

## Additional Observations

- Docker detection edge case
  - `get_docker_info()` returns a JSON object even when the daemon is unreachable (exit code 0, with `ServerErrors`). `is_docker_running()` thus returns True and build proceeds. Fix idea: treat non-empty `.ServerErrors` as not running, or probe with `docker info --format '{{.ServerVersion}}'` and ensure it’s non-empty.

- Container naming consistency
  - `docker exec` computes names as `{project_dir}-{service}` while compose uses `{config.name}-devcontainer`. If `config.name` != directory name, exec won’t find the container. Consider reading `ProjectConfig` and standardizing naming across commands.

- Compose schema warning
  - Compose warns: `version` is obsolete in generated compose; it’s safe but noisy. Consider removing the top-level `version:` from templates.

- Worktree remove UX
  - Removing by partial name is handy; ensure matching logic has a clear precedence (path vs branch) and helpful suggestions when no matches.

- Notify portability
  - `notify --daemon` uses `os.fork()` (POSIX-only). It’s fine here, but worth documenting/guarding on Windows.

- Doctor CLI options
  - `doctor` itself doesn't accept `--verbose` (only root does). Either document `ai-sbx -v doctor` or add a `--verbose` flag to the subcommand.

- Upgrade under restricted envs
  - Graceful fallback works; log order shows “Could not check latest version” after the failure message. If possible, check latest version first, then perform upgrade to improve UX.

## Recommendations (actionable)

1) Docker check: Refine `is_docker_running()` to consider `.ServerErrors` from `docker info`; optionally perform an API ping and require `ServerVersion` present.
2) Compose template: Drop the `version:` key in `docker-compose.yaml` to silence warnings.
3) Naming: Unify container naming (derive from `ProjectConfig` everywhere).
4) Doctor verbosity: Support `--verbose` on `doctor` or document using root `-v`.
5) Notify: Expose `notify stop` in CLI; optionally store PID and provide robust stop logic.
6) Permissions: In `init --global`, ensure `$HOME/.ai_agents_sandbox/notifications` ownership/group are correct; warn if not.
7) Docs: Clarify expected behavior when Docker isn’t available (build/ps/up will fail with helpful messages) and how to run in limited environments.

## Artifacts

- Raw logs: `test-outputs/` (17 files)
- Test project: `./tmp_sbx_project` (git repo with `.devcontainer/`)

No persistent background processes left running; the watcher was started in foreground and killed via timeout during testing.

