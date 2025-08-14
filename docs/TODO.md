- fix persistence of zshhistory
- add golang, dotnet and python containers based on devcontainer base
- add timings and statistics for tasks
- add host script for create git worktree in current directory, go in this worktree, create task folder and open pycharm
- get docker image cache storage (may be custom) add mount it to the devcontainer
first:
❯ docker info | grep 'Storage Driver'

Storage Driver: overlay2

❯ cat /etc/docker/daemon.json
  {
  "data-root": "/media/bas/data/docker"
  }
- update reviewer - only claude opus
- add script for review requirement for codex
- add images diagram to readme base > base_ai > python, golang, dotnet
- move all claude install and settings and codex cli to separate image
- add to the @run-codex logging of calls
- code reviewer must remember to put review to the task folder. IT IS also very imporatant for him to check existing code, look for inconsistence.
- add new agent requirements_reviewer, which must review requirements for inconsistence, mistake, add questions etc. use codex cli in the same way as code reviewer and put them in separate codex_answers. Very important: the agent-analytics MUST check his answers first and update his own answers or ask requirements_reviewer if something is unclear.
- add hook to the log all workflow with timestamps: which agent and when was called.
- add to the pycharm docs that if wants to connect from pycharm use tcp with https://docker:2376 and /certs/client
- add to software engineer and qa ALWAYS run all tests suite after finish of task