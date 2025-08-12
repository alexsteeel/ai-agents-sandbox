# Simplified .devcontainer Example

This directory shows how simple the new devcontainer system is for users.

## What's Here

- **.env** - Just 2 required settings (PROJECT_NAME and PROJECT_DIR)
- **docker-compose.yaml** - 3 lines! Just extends the base template
- **whitelist.txt** - Your project-specific allowed domains
- **dind-whitelist.txt** - Docker registries for your project
- **Dockerfile** - Optional, only if you need customization

## That's It!

Compare this to the original `.devcontainer` with 125+ lines of docker-compose.yaml!

The complexity is now:
1. **System-installed** in `/usr/local/share/claude-devcontainer/`
2. **Managed by commands** like `claude-devcontainer start`
3. **Reusable** across all your projects

## Usage

```bash
# After system installation
claude-devcontainer init /path/to/project
claude-devcontainer start
claude-devcontainer shell
```

## Benefits

✅ **5 files instead of 10+**  
✅ **~20 lines of config instead of 200+**  
✅ **Standardized across all projects**  
✅ **Easy to update (just update system installation)**  
✅ **Still fully customizable when needed**