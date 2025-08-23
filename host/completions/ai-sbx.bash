#!/bin/bash
# Bash completion for ai-sbx command
#
# Installation:
#   1. Copy to system location (requires sudo):
#      sudo cp ai-sbx.bash /etc/bash_completion.d/ai-sbx
#   
#   2. Or source in your ~/.bashrc:
#      source /path/to/ai-sbx.bash
#   
#   3. Reload your shell or run:
#      source ~/.bashrc

_ai_sbx_completion() {
    local cur prev words cword
    _init_completion || return

    local commands="worktree init notify help version"
    local worktree_subcommands="create connect remove list help"

    # Complete main command
    if [[ $cword -eq 1 ]]; then
        # Main commands and options
        COMPREPLY=($(compgen -W "$commands --help -h --version -v" -- "$cur"))
        return
    fi

    # Complete based on the main command
    case "${words[1]}" in
        worktree|wt)
            if [[ $cword -eq 2 ]]; then
                # Worktree subcommands
                COMPREPLY=($(compgen -W "$worktree_subcommands" -- "$cur"))
            elif [[ $cword -eq 3 ]]; then
                # Complete based on worktree subcommand
                case "${words[2]}" in
                    create)
                        # Suggest common task prefixes
                        local prefixes="feature bugfix hotfix refactor test docs chore experiment"
                        COMPREPLY=($(compgen -W "$prefixes" -- "$cur"))
                        ;;
                    remove|rm|delete)
                        # Complete with worktree branches
                        if command -v git >/dev/null 2>&1; then
                            local branches=$(git worktree list --porcelain 2>/dev/null | awk '/^branch/ {gsub(/.*\//, "", $2); print $2}')
                            COMPREPLY=($(compgen -W "$branches" -- "$cur"))
                        fi
                        ;;
                    *)
                        # No completion for other subcommands
                        ;;
                esac
            fi
            ;;
        
        init|initialize)
            # Complete with directory paths
            _filedir -d
            ;;
        
        notify|notifications|watch)
            # No additional arguments
            ;;
        
        help|-h|--help)
            # No additional arguments
            ;;
        
        version|-v|--version)
            # No additional arguments
            ;;
    esac
}

# Register the completion function for ai-sbx command
complete -F _ai_sbx_completion ai-sbx