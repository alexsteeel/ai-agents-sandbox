## Installation

- https://github.com/anthropics/claude-code/blob/main/README.md - install Claude Code
- Create devcontainer with https://github.com/anthropics/claude-code/tree/main/.devcontainer or update version in
  .devcontainer
  Main differences with original devcontainer
  - Set default editor from nano to vim
  - Copy local settings of zsh
- Connect Pycharm to devcontainer through JetBrains Gateway
- The issue with different users on the host and inside devcontainer is solved with common group dev. 

## Using
Start claude
[Security](https://docs.anthropic.com/en/docs/claude-code/security)
```bash
claude --dangerously-skip-permissions
```

## Context engineering

- Create .claudeignore
- Create separate Claude.md for each directory instead one large Claude.md
- Use batch approach (one large complex task instead of mini tasks)
- Use https://github.com/ryoppippi/ccusage for analyze
- Use planning mode
- Use think and ultrathink
- Use xml tags for structure
  prompts https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/use-xml-tags

## Isolation

- Use isolated docker container with custom network rules
- Connect Pycharm to docker container
- Use git worktree for each task
```bash
git worktree add -b task-name ../project-name-task-name
git worktree list
```
In this way we have isolated git branch and isolated environment for each team of agents. 
One team can merge these changes and solve the issues.

## Plugins

- https://github.com/brennercruvinel/CCPlugins
- https://aitmpl.com/