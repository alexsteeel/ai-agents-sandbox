# Code Review: Migration from Shell Scripts to Python CLI

Scope: Review and validation of the new Python implementation replacing host shell scripts. This document records test results, identified issues, and the fixes that were applied as part of this review.

## Summary

- Python CLI (`ai-sbx`) is functional: help/version work; unit/integration tests all pass.
- Template rendering generates expected devcontainer artifacts.
- Docker/Worktree/Notify commands exist and generally align with the shell workflow, but there are correctness gaps and cross-platform pitfalls to address.
- Linting and type checks reveal actionable improvements (unused imports, annotations, minor logic bugs).

## What I Tested

- Pytest: 50 tests passed. Coverage ~45% overall; core modules have high gaps (commands modules 20–50%).
- CLI smoke tests: `ai-sbx --help`, `ai-sbx --version`, `ai-sbx worktree list -v` executed successfully.
- TemplateManager: verified project scaffolding to a temp directory produced 6 expected files.
- Lint: Ruff found 117 issues (mostly import/unused/format); many auto-fixable.
- Types: mypy found 15 errors (missing generics, return types, missing stubs).

## Test Output (abridged)

- Pytest: 50 passed, coverage 45% — commands/{docker,init,notify,worktree} have low coverage.
- Ruff: 117 issues (49 fixable with `--fix`), including unused imports/variables and unsorted imports.
- Mypy: 15 errors; highlights:
  - `subprocess.CompletedProcess` missing type param; functions missing return types; Any leaks.
  - Third-party stubs missing: `types-PyYAML`, `inquirer` (missing py.typed).

## Functional Findings

### 1) Docker PS JSON output likely incorrect

- Code: `docker ps --format json` in `commands/docker.py`.
- Reality: Docker’s `--format` expects a Go template; to emit JSON lines use `--format '{{json .}}'`.
- Impact: `ai-sbx docker ps` will fail to parse real output unless mocked; tests bypass with stubs.
- Recommendation: Use `--format '{{json .}}'` and parse each line as JSON.
- Status: Fixed. `ai-sbx docker ps` now uses `--format '{{json .}}'` and parses JSON lines.

### 2) Image variant naming mismatches

- Enum includes `dotnet`, `golang`, `rust`, `java` but repository directories are:
  - `images/devcontainer-dotnet`, `images/devcontainer-golang` (no `images/dotnet`/`images/golang`).
  - No `images/rust` or `images/java` present.
- Build code uses `images/{variant}` and compose uses `ai-agents-sandbox/{variant}:latest`.
- Impact: Building/using these variants will fail or pull non-existent images.
- Recommendation: Align variant names and paths (either rename dirs/images or map enum→path/tag).
- Status: Fixed (partial). Added explicit mapping in build logic and templates:
  - dotnet → `images/devcontainer-dotnet` / `ai-agents-sandbox/devcontainer-dotnet`
  - golang → `images/devcontainer-golang` / `ai-agents-sandbox/devcontainer-golang`
  - rust/java currently unsupported in this repo (skipped with warning).

### 3) Container name computation mismatch

- `docker exec` builds container name as `{project_root.name}-{service}`.
- Compose sets `container_name: {config.name}-devcontainer`.
- Impact: If `config.name` ≠ project directory name, `exec` can’t find the container.
- Recommendation: Load `ProjectConfig` and derive names from config consistently across commands.
- Status: Fixed. `ai-sbx docker exec` now reads `ProjectConfig` and uses `{config.name}-{service}`.

### 4) `notify stop` command not exposed

- `commands/notify.py` defines a `@click.command()` `stop`, but it’s not registered to the CLI.
- Impact: Users can’t call `ai-sbx notify stop` or `ai-sbx stop` from the current CLI wiring.
- Recommendation: Make `notify` a group and add `notify stop`, or register `stop` on the root group.
- Status: Fixed. `notify` is now a Click group; `ai-sbx notify stop` is available. README updated.

### 5) Hardcoded host path in devcontainer override

- Change in `.devcontainer/override.user.yaml` adds a host-specific absolute path mount:
  - `/media/bas/repo/github/ai-agents-sandbox/.git:...`
- Impact: Breaks portability and leaks a developer’s local path into the repo.
- Recommendation: Remove this from versioned config; prefer relative paths or documented local-only overrides.
- Status: Fixed. Removed developer-specific absolute mount; replaced with a comment.

### 6) Cross-platform and privilege edge-cases

- `os.fork()` used in `notify --daemon` is POSIX-only; won’t work on Windows.
- Group/user management (`groupadd`, `usermod`) assumes Linux; fail gracefully with guidance on non-Linux.
- `get_user_home()` builds `/home/{username}` for non-root; doesn’t handle macOS/custom home dirs.
- Recommendation: Platform guards and more portable home resolution (use `pwd` db on Unix; `Path.home()` fallback).
- Status: Partially fixed. `get_user_home()` now uses the system user database (`pwd`) when available, with fallback. `notify --daemon` still uses `os.fork()` (POSIX-only) — document/guard as future work.

### 7) Shell calls and injection safety

- `init.py` uses `os.system("chgrp -R {group} ...")` and `chmod` string commands.
- Recommendation: Use `subprocess` with argv lists to avoid shell injection and to capture errors.
- Status: Fixed. Replaced `os.system` in `init.py` with safe `run_command([...])` calls for `chgrp`/`chmod`.

### 8) Default shell assumptions

- `docker exec`/worktree connect default to `/bin/zsh`.
- Impact: Fails on images without zsh or when using minimal variants.
- Recommendation: Fallback to `/bin/bash` or `/bin/sh` if zsh is missing.
- Status: Fixed. `docker exec` now falls back: zsh → bash → sh.

### 9) Notify permissions: observed failure

- `ai-sbx notify --test` failed here due to notifications dir owned by a different user/group.
- Recommendation: In `init --global`, ensure ownership and group perms for `$HOME/.ai_agents_sandbox/notifications`.
- Status: Open. Current behavior warns gracefully; future improvement could fix ownership during global init.

## Lint & Type-Check Improvements

- Ruff highlights (examples):
  - Unused imports/vars in `cli.py` (`Path`, `Optional`, `Settings`, `title`, `subtitle`).
  - Unused imports and unsorted imports in `docker.py`, `doctor.py`.
  - F-string without placeholders in `docker.py` summary line.
- Mypy highlights:
  - Add `-> None` for Click group functions; annotate tuple parameter (`tuple[str, ...]`).
  - Use `CompletedProcess[str]` for `run_command` return type; fix `format_size` int/float variable type.
  - Install stubs: `types-PyYAML`; consider `# type: ignore[...]/py.typed` strategy for `inquirer`.

Status: Partially fixed.
- Typing: `run_command` now returns `CompletedProcess[str]`; `format_size` handles floats; click types improved; several list/tuple types moved to PEP 585 built-ins.
- Lint: Removed unused imports/vars in CLI; many Ruff warnings remain (89 issues), mostly auto-fixable import/order/formatting.

## Documentation Gaps

- README mixes legacy shell scripts (e.g., `images/build.sh`) and new Python CLI (`ai-sbx docker build`).
  - Action: Clarify authoritative path (Python CLI), keep script references as optional/advanced.
- Document variant availability vs. repo images; note any variants not yet provided.
- Document Docker JSON formatting expectations for `docker ps`.

Status: Partially fixed. README updated to document `notify stop` and `doctor --verbose`. Template now selects correct image repo for dotnet/golang. Additional doc updates still recommended for variant availability and Docker ps formatting rationale.

## Test Coverage Recommendations

- Add tests for:
  - `docker ps` parsing using real `--format '{{json .}}'` output samples.
  - `TemplateManager.generate_project_files` contents and idempotency (`force=True/False`).
  - Container name resolution when `config.name` differs from dir name.
  - `notify` watcher paths: inotify and polling modes (with fake files), and `notify stop` wiring once exposed.

## Security Considerations

- Replace `os.system` string shells with `subprocess.run([...], check=...)` for safer execution.
- Validate or sanitize config-derived strings used in shell contexts (group names, paths).
- Ensure no secrets are written to world-readable files in `.devcontainer` by default; set appropriate file modes.

## Overall Assessment

The migration significantly improves maintainability, UX, and modularity. The CLI structure, config models, and templating are solid foundations. Addressing the identified issues — especially Docker JSON format, image variant mapping, container naming consistency, CLI wiring for notify stop, cross-platform guards, and lint/type hygiene — will close most functional and quality gaps.

## Actionable Next Steps

1) Add tests for real `docker ps` JSON-line parsing and image mapping logic.
2) Decide on support or clear documentation for rust/java variants; currently skipped during build.
3) Add platform guards for `notify --daemon` (Windows), and optionally a PID file for robust stop.
4) Implement ownership/perms fix for notifications dir in `init --global` (best-effort).
5) Run `ruff --fix` and resolve remaining lint; add `types-PyYAML` and annotate modules to reduce mypy warnings.
6) Expand README docs for variant availability and Docker JSON formatting.

## Post-Fix Verification

- Tests: 50 passed; coverage unchanged (~45%).
- Docker detection: `is_docker_running()` now correctly returns False in restricted environments (treats `ServerErrors`/missing `ServerVersion` as not running).
- CLI:
  - `ai-sbx doctor --verbose` works (subcommand-level flag added; also inherited from root `-v`).
  - `ai-sbx docker ps` uses JSON lines format and error-handles properly.
  - `ai-sbx notify stop` is exposed and documented.
  - Templates drop the obsolete top-level `version:` and pick correct image repos for dotnet/golang.
