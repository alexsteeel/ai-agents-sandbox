# Update Memory - Summarize Changes and Update Context

Analyze the recent changes in our conversation and update the appropriate CLAUDE.md files throughout the project structure. Follow this systematic approach:

## 1. Summarize Recent Changes
First, provide a concise summary of what was accomplished in this session:
- What files were modified/created
- What features were implemented/changed
- What decisions were made
- What patterns or conventions were established

## 2. Determine Context-Specific Updates
Based on the changes, identify which CLAUDE.md files need updates and what type of information should go where:

### Root CLAUDE.md (`./CLAUDE.md`)
Update ONLY for:
- Overall project architecture changes
- Main technology stack modifications
- Core development principles
- Project-wide conventions
- High-level folder structure changes

### Directory-Specific CLAUDE.md Files
Create or update CLAUDE.md files in relevant subdirectories based on the actual project structure. The following are **examples only** - adapt to your specific project organization:

**Integration Testing Directory** (e.g., `/tests/integration/`, `/e2e/`, `/integration-tests/`):
- Integration test patterns and conventions
- Test environment setup
- Database seeding strategies
- API testing approaches
- Mock/stub patterns

**Business Logic Directory** (e.g., `/src/business/`, `/domain/`, `/services/`, `/core/`):
- Domain models and entities
- Business rule implementations
- Validation patterns
- Business process flows

**UI/Component Directory** (e.g., `/src/components/`, `/ui/`, `/views/`, `/pages/`):
- Component architecture patterns
- Styling conventions
- Component composition rules
- Props and state management patterns

**API Layer Directory** (e.g., `/src/api/`, `/routes/`, `/controllers/`, `/endpoints/`):
- API design patterns
- Error handling conventions
- Authentication/authorization patterns
- Request/response schemas

**Documentation Directory** (e.g., `/docs/`, `/documentation/`, `/guides/`):
- Documentation standards
- Writing guidelines
- Code comment patterns

**Build/Scripts Directory** (e.g., `/scripts/`, `/build/`, `/tools/`, `/config/`):
- Build process specifics
- Deployment procedures
- Script conventions
- Environment configurations

**Note**: These directory names are examples only. Analyze the actual project structure and create CLAUDE.md files in directories that exist and are relevant to the changes made.

## 3. Update Process
For each identified CLAUDE.md file:

1. **Check if file exists**: Use file system tools to see if CLAUDE.md already exists in the target directory
2. **Read existing content**: If it exists, read the current content to avoid duplication
3. **Merge information**: Add new information while preserving existing relevant content
4. **Write updated file**: Create or update the CLAUDE.md file with the new information
5. **Verify update**: Confirm the file was written correctly

## 4. Update Guidelines

### Content Organization
- Keep information specific to the directory's purpose
- Avoid duplicating information that belongs in parent directories
- Cross-reference related CLAUDE.md files when appropriate
- Use clear headings and bullet points for readability

### Writing Style
- Be concise but comprehensive
- Focus on decisions made and patterns established
- Include examples where helpful
- Explain the "why" behind conventions, not just the "what"

### Maintenance
- Remove outdated information
- Update changed patterns or conventions
- Ensure consistency across related files

## 5. Execution Steps

Execute this process step by step:

1. Summarize the recent session changes
2. List all directories that need CLAUDE.md updates based on the changes and the actual project structure
3. For each relevant directory that exists in the project:
   - Check if CLAUDE.md exists
   - Read existing content (if any)
   - Determine what new information to add
   - Write/update the file
   - Confirm the update was successful
4. Provide a final summary of all CLAUDE.md files that were updated

## Example Directory Structure After Updates
**Note**: This is just one example structure. Your project may have completely different directory names and organization. Adapt the CLAUDE.md placement to match your actual project structure.

```
project-root/
├── CLAUDE.md                           # Main project guide
├── src/
│   ├── components/                     # Could be /ui/, /views/, etc.
│   │   ├── CLAUDE.md                   # Component patterns
│   │   └── Button/
│   ├── business/                       # Could be /domain/, /services/, etc.
│   │   ├── CLAUDE.md                   # Business rules
│   │   └── models/
│   └── api/                           # Could be /routes/, /controllers/, etc.
│       ├── CLAUDE.md                   # API conventions
│       └── routes/
├── tests/                             # Could be /test/, /__tests__/, etc.
│   ├── integration/                   # Could be /e2e/, /integration-tests/, etc.
│   │   ├── CLAUDE.md                   # Integration test guide
│   │   └── user-flows/
│   └── unit/
├── docs/                              # Could be /documentation/, /guides/, etc.
│   ├── CLAUDE.md                       # Documentation standards
│   └── api/
└── scripts/                           # Could be /build/, /tools/, /config/, etc.
    ├── CLAUDE.md                       # Build/deployment guide
    └── build/
```

**Important**: Always examine the actual project structure first and place CLAUDE.md files in directories that exist and are relevant to the work being done.

Remember: Each CLAUDE.md should be a focused, actionable guide for working in that specific part of the codebase.
