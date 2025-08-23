# Shell Completions for ai-sbx

This directory contains shell completion scripts for the `ai-sbx` command.

## Supported Shells

- **Zsh** - `_ai-sbx`
- **Bash** - `ai-sbx.bash`

## Features

The completion scripts provide:

- Tab completion for all main commands (worktree, init, notify)
- Tab completion for worktree subcommands (create, connect, remove, list)
- Intelligent suggestions for task types (feature, bugfix, hotfix, etc.)
- Worktree name completion for remove command
- Directory path completion for init command
- Option completion (-h, --help, -v, --version)

## Installation

### Automatic Installation

The completions are automatically installed when you run the main installer:

```bash
sudo ./install.sh
```

This will install completions to the system directories:
- **Zsh**: `/usr/share/zsh/vendor-completions/` or `/usr/local/share/zsh/site-functions/`
- **Bash**: `/etc/bash_completion.d/` or `/usr/local/etc/bash_completion.d/`

### Manual Installation

#### Zsh

1. Copy the completion file to your Zsh completions directory:
   ```bash
   mkdir -p ~/.zsh/completions
   cp _ai-sbx ~/.zsh/completions/
   ```

2. Add to your `~/.zshrc`:
   ```bash
   fpath=(~/.zsh/completions $fpath)
   autoload -U compinit && compinit
   ```

3. Reload your shell:
   ```bash
   source ~/.zshrc
   ```

#### Bash

1. Option A - System-wide installation (requires sudo):
   ```bash
   sudo cp ai-sbx.bash /etc/bash_completion.d/ai-sbx
   ```

2. Option B - User installation:
   ```bash
   # Add to your ~/.bashrc
   source /path/to/ai-sbx.bash
   ```

3. Reload your shell:
   ```bash
   source ~/.bashrc
   ```

## Usage Examples

After installation, you can use tab completion:

```bash
# Complete main commands
ai-sbx <TAB>
# Shows: worktree init notify help version

# Complete worktree subcommands
ai-sbx worktree <TAB>
# Shows: create connect remove list help

# Get task type suggestions
ai-sbx worktree create <TAB>
# Shows: feature bugfix hotfix refactor test docs chore experiment

# Complete worktree names for removal
ai-sbx worktree remove <TAB>
# Shows: list of existing worktree branches

# Complete directory paths
ai-sbx init <TAB>
# Shows: directory completions
```

## Troubleshooting

### Zsh

If completions don't work:

1. Check that the completion file is in your fpath:
   ```bash
   echo $fpath
   ```

2. Ensure compinit is called in your `.zshrc`:
   ```bash
   grep compinit ~/.zshrc
   ```

3. Force rebuild completion cache:
   ```bash
   rm -f ~/.zcompdump
   compinit
   ```

### Bash

If completions don't work:

1. Check that bash-completion is installed:
   ```bash
   # Debian/Ubuntu
   sudo apt-get install bash-completion
   
   # macOS
   brew install bash-completion
   ```

2. Verify the completion is loaded:
   ```bash
   complete -p | grep ai-sbx
   ```

3. Manually source the completion:
   ```bash
   source /etc/bash_completion.d/ai-sbx
   ```

## Development

To test changes to completion scripts:

### Zsh
```bash
# Reload the completion
unfunction _ai-sbx 2>/dev/null
autoload -U _ai-sbx
```

### Bash
```bash
# Reload the completion
source ai-sbx.bash
```