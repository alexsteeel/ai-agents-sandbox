# Code Review: Migration from Shell Scripts to Python CLI

Scope: Review and validation of the new Python implementation replacing host shell scripts. No code changes made — this document records test results, potential issues, and recommendations.

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

### 2) Image variant naming mismatches

- Enum includes `dotnet`, `golang`, `rust`, `java` but repository directories are:
  - `images/devcontainer-dotnet`, `images/devcontainer-golang` (no `images/dotnet`/`images/golang`).
  - No `images/rust` or `images/java` present.
- Build code uses `images/{variant}` and compose uses `ai-agents-sandbox/{variant}:latest`.
- Impact: Building/using these variants will fail or pull non-existent images.
- Recommendation: Align variant names and paths (either rename dirs/images or map enum→path/tag).

### 3) Container name computation mismatch

- `docker exec` builds container name as `{project_root.name}-{service}`.
- Compose sets `container_name: {config.name}-devcontainer`.
- Impact: If `config.name` ≠ project directory name, `exec` can’t find the container.
- Recommendation: Load `ProjectConfig` and derive names from config consistently across commands.

### 4) `notify stop` command not exposed

- `commands/notify.py` defines a `@click.command()` `stop`, but it’s not registered to the CLI.
- Impact: Users can’t call `ai-sbx notify stop` or `ai-sbx stop` from the current CLI wiring.
- Recommendation: Make `notify` a group and add `notify stop`, or register `stop` on the root group.

### 5) Hardcoded host path in devcontainer override

- Change in `.devcontainer/override.user.yaml` adds a host-specific absolute path mount:
  - `/media/bas/repo/github/ai-agents-sandbox/.git:...`
- Impact: Breaks portability and leaks a developer’s local path into the repo.
- Recommendation: Remove this from versioned config; prefer relative paths or documented local-only overrides.

### 6) Cross-platform and privilege edge-cases

- `os.fork()` used in `notify --daemon` is POSIX-only; won’t work on Windows.
- Group/user management (`groupadd`, `usermod`) assumes Linux; fail gracefully with guidance on non-Linux.
- `get_user_home()` builds `/home/{username}` for non-root; doesn’t handle macOS/custom home dirs.
- Recommendation: Platform guards and more portable home resolution (use `pwd` db on Unix; `Path.home()` fallback).

### 7) Shell calls and injection safety

- `init.py` uses `os.system("chgrp -R {group} ...")` and `chmod` string commands.
- Recommendation: Use `subprocess` with argv lists to avoid shell injection and to capture errors.

### 8) Default shell assumptions

- `docker exec`/worktree connect default to `/bin/zsh`.
- Impact: Fails on images without zsh or when using minimal variants.
- Recommendation: Fallback to `/bin/bash` or `/bin/sh` if zsh is missing.

### 9) Notify permissions: observed failure

- `ai-sbx notify --test` failed here due to notifications dir owned by a different user/group.
- Recommendation: In `init --global`, ensure ownership and group perms for `$HOME/.ai_agents_sandbox/notifications`.

## Lint & Type-Check Improvements

- Ruff highlights (examples):
  - Unused imports/vars in `cli.py` (`Path`, `Optional`, `Settings`, `title`, `subtitle`).
  - Unused imports and unsorted imports in `docker.py`, `doctor.py`.
  - F-string without placeholders in `docker.py` summary line.
- Mypy highlights:
  - Add `-> None` for Click group functions; annotate tuple parameter (`tuple[str, ...]`).
  - Use `CompletedProcess[str]` for `run_command` return type; fix `format_size` int/float variable type.
  - Install stubs: `types-PyYAML`; consider `# type: ignore[...]/py.typed` strategy for `inquirer`.

## Documentation Gaps

- README mixes legacy shell scripts (e.g., `images/build.sh`) and new Python CLI (`ai-sbx docker build`).
  - Action: Clarify authoritative path (Python CLI), keep script references as optional/advanced.
- Document variant availability vs. repo images; note any variants not yet provided.
- Document Docker JSON formatting expectations for `docker ps`.

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

1) Fix `docker ps` formatter to `--format '{{json .}}'` and add tests.
2) Align `ImageVariant` mapping to actual image directories/tags (dotnet/golang/rust/java).
3) Unify container name derivation via `ProjectConfig` across commands.
4) Expose `notify stop` as a subcommand (`notify stop`) and document it.
5) Replace `os.system` usages with `run_command([...])` for chgrp/chmod.
6) Improve cross-platform behavior (`os.fork` guard, `get_user_home` using `pwd`).
7) Resolve Ruff/Mypy findings; add `types-PyYAML` as dev dep and annotate functions.
8) Remove developer-specific path from `.devcontainer/override.user.yaml`.

