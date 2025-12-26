if [[ -r "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh" ]]; then
  source "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh"
fi

# Set umask to allow group write permissions
umask 0002

# Path to your oh-my-zsh installation.
export ZSH="$HOME/.oh-my-zsh"

ZSH_THEME="powerlevel10k/powerlevel10k"
POWERLEVEL9K_DISABLE_GITSTATUS=true

plugins=(
  aliases
  colorize
  docker
  docker-compose
  git
  history
  zsh-autosuggestions
  zsh-syntax-highlighting
)

source $ZSH/oh-my-zsh.sh

[[ ! -f ~/.p10k.zsh ]] || source ~/.p10k.zsh

# Aliases for Claude and Codex
# Disable auto-update to preserve pinned version (proxy regression in 2.0.48+)
alias claude='CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1 claude --dangerously-skip-permissions'
alias codex='codex'
