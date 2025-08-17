- add timings and statistics for tasks
- get docker image cache storage (may be custom) add mount it to the devcontainer
first:
❯ docker info | grep 'Storage Driver'

Storage Driver: overlay2

❯ cat /etc/docker/daemon.json
  {
  "data-root": "/media/bas/data/docker"
  }
- update reviewer - only claude opus
- simplify analytics and tech lead agent prompts. now they are overcomplicated
- add script for review requirements for codex
- add images diagram to readme base > base_ai > python, golang, dotnet
- move all claude install and settings and codex cli to separate image
- add to the @run-codex logging of calls
- code reviewer must remember to put review to the task folder. IT IS also very imporatant for him to check existing code, look for inconsistence.
- add new agent requirements_reviewer, which must review requirements for inconsistence, mistake, add questions etc. use codex cli in the same way as code reviewer and put them in separate codex_answers. Very important: the agent-analytics MUST check his answers first and update his own answers or ask requirements_reviewer if something is unclear.
- add hook to the log all workflow with timestamps: which agent and when was called.
- add to the pycharm docs that if wants to connect from pycharm use tcp with https://docker:2376 and /certs/client
- add to software engineer and qa ALWAYS run all tests suite after finish of task
- hooks:  Invalid Settings
  /home/claude/.ai_agents_sandbox/settings.json
  └ hooks
  ├ Error: "Error" is not valid. Expected one of: "PreToolUse", "PostToolUse", "Notification", "UserPromptSubmit", "SessionStart", "Stop", "SubagentStop",
  "PreCompact"
  └ ToolUse: "ToolUse" is not valid. Expected one of: "PreToolUse", "PostToolUse", "Notification", "UserPromptSubmit", "SessionStart", "Stop", "SubagentStop",
  "PreCompact"

Valid values: "PreToolUse", "PostToolUse", "Notification", "UserPromptSubmit", "SessionStart", "Stop", "SubagentStop", "PreCompact"
Learn more: https://docs.anthropic.com/en/docs/claude-code/hooks

- add command review current changes for redundant code