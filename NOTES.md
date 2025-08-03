## Context engineering 
- Create .claudeignore
- Create separate Claude.md for each directory instead one large Claude.md
- Use batch approach (one large complex task instead of mini tasks)
- Use https://github.com/iannuttall/claude-sessions for analyze
- Use planning mode
- Use think and ultrathink
- Use xml tags for structure prompts https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/use-xml-tags

## Isolation
- Use isolated docker container with custom network rules
- Connect Pycharm to docker container

## Agents

### Team lead
Planning, architecture, task distribution
- Must use reasoning models like Opus.
- Must use think and ultrathink modes.

Plugins
- Any knowledge graph, for example https://github.com/shaneholloman/mcp-knowledge-graph

Results
- Update and share knowledge graph.
- Share planning and architecture documents.
- Task creation and distribution.

### Python Senior Developer
Development, testing, refactoring, debugging
Use tasks and architecture documents.

- Can use Opus or Sonnet.

Plugins
- Edit filesystem
- Bash commands
- Git

Results
- Code
- Tests
- Documentation

### Code reviewer
- Knows about code style, existing packages.
Access to linters, like sonar cube

### QA
Checks for code quality, security, performance.
Reviews developer's tests and add test cases and test coverage. 


## Plugins
- https://github.com/brennercruvinel/CCPlugins
- https://aitmpl.com/