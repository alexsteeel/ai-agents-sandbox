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
