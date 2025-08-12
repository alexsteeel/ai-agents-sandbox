# common_settings/CLAUDE.md

This directory contains shared configuration files used across the project.

## Purpose

Provides common settings that are shared between the base image build and runtime configuration.

## Files

### `default-whitelist.txt`

Central whitelist of allowed domains for proxy filtering. This file is:
- Copied into the tinyproxy image at build time
- Merged with project-specific whitelists at runtime
- Maintained as the single source of truth for default allowed domains

**Categories of whitelisted domains**:

1. **Source Control**:
   - GitHub: `github.com`, `raw.githubusercontent.com`, `github.githubassets.com`
   - GitLab: `gitlab.com`
   - Bitbucket: `bitbucket.org`

2. **Package Registries**:
   - Python: `pypi.org`, `files.pythonhosted.org`
   - Node.js: `registry.npmjs.org`, `nodejs.org`
   - Rust: `crates.io`, `static.crates.io`
   - Go: `proxy.golang.org`, `go.dev`

3. **Container Registries**:
   - Docker Hub: `hub.docker.com`, `registry-1.docker.io`
   - GitHub Container Registry: `ghcr.io`

4. **Development Tools**:
   - VS Code: `marketplace.visualstudio.com`
   - Package managers: `install.python-poetry.org`
   - Documentation: `docs.python.org`, `docs.npmjs.com`

5. **AI/Claude Tools**:
   - Anthropic: `anthropic.com`, `claude.ai`
   - Documentation: `docs.anthropic.com`

## Maintenance

### Adding New Default Domains

When adding domains that should be available in ALL devcontainer instances:

1. Edit `common_settings/default-whitelist.txt`
2. Add domain(s) - one per line
3. Rebuild images: `./images/build.sh`
4. Document the addition and reason

### Domain Format

- Use exact domain names: `example.com`
- Include subdomains explicitly: `api.example.com`
- Wildcards supported: `*.example.com`
- No protocols: Just domain, not `https://example.com`
- No paths: Just domain, not `example.com/path`

### Security Considerations

Before adding a default domain, consider:
- Is this needed by most/all projects?
- What's the security impact?
- Can it be project-specific instead?
- Is the domain trustworthy?

Project-specific domains should go in `.devcontainer/whitelist.txt` instead.

## Integration

The whitelist is used at multiple stages:

1. **Build time**: Copied into tinyproxy image at `/default-whitelist.txt`
2. **Runtime**: Merged with other whitelists by `get-whitelist.sh`
3. **Final filter**: Combined list used by tinyproxy for filtering

Merge order (later overrides earlier):
1. `devcontainer_base/default-whitelist.txt` (built into base image)
2. `common_settings/default-whitelist.txt` (this file)
3. `.devcontainer/whitelist.txt` (project-specific)

## Best Practices

- **Minimize defaults**: Only truly common domains
- **Document additions**: Explain why each domain is needed
- **Regular review**: Remove unused domains periodically
- **Test changes**: Verify filtering still works after changes
- **Version control**: Track all changes with clear commit messages