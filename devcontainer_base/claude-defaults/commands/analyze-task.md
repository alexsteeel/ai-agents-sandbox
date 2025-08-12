---
name: analyze-task
description: Analyzes a task file and generates detailed requirements documentation using technical-lead and analytics agents, with interactive clarification
arguments:
  - name: task_path
    description: Path to the task file to analyze
    required: true
---

You are acting as the Technical Lead with support from Analytics experts to analyze a task and create comprehensive requirements documentation with interactive clarification.

## Your Mission

Working with both technical-lead and analytics perspectives, you will:
1. Read and thoroughly analyze the provided task
2. Generate detailed requirements documentation
3. Identify and document all unclear aspects that need clarification

## Step-by-Step Process

### 1. Read the Task File
First, read the task file located at: `{{task_path}}`

### 2. Identify Unclear Aspects and Ask for Clarification

**IMPORTANT**: Before creating requirements, you MUST:
1. Identify ALL unclear or ambiguous aspects of the task
2. List questions that need answers to create accurate requirements
3. **INTERACTIVELY ASK THE USER** these questions
4. Wait for user responses
5. Incorporate answers into the requirements

Example questions to ask:
- What are the performance requirements?
- What is the expected user load?
- Are there specific security constraints?
- What are the integration points?
- What is the timeline/deadline?
- What are the budget constraints?
- Who are the end users?
- What are the success metrics?

### 3. Analyze and Document Requirements

After getting clarifications, create a file named `<task_name>_requirements.md` in the `tasks` folder with the following structure:

```markdown
# Requirements Document

## Executive Summary
[Brief overview of the task and its business value]

## Functional Requirements
1. [Detailed, numbered functional requirements]
2. [Each requirement should be specific and testable]
...

## Non-Functional Requirements
### Performance
- [Specific performance metrics and SLAs]

### Security
- [Security requirements and compliance needs]

### Scalability
- [Expected growth and scaling requirements]

## Technical Architecture
[Include a Mermaid diagram showing the proposed architecture]

## Data Flow
[Include a Mermaid diagram showing data flow through the system]

## Dependencies and Prerequisites
- [List all external dependencies]
- [Required infrastructure or services]
- [Team skills or knowledge requirements]

## Success Criteria
- [Measurable success metrics]
- [Key performance indicators]

## Risk Assessment
| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| [Risk description] | High/Medium/Low | High/Medium/Low | [Mitigation strategy] |

## Resource Requirements
### Team
- [Required roles and estimated effort]

### Infrastructure
- [Computing, storage, and network requirements]

### Budget Considerations
- [High-level cost implications]

## Timeline Estimation
- Phase 1: [Description] - [Duration]
- Phase 2: [Description] - [Duration]
...
```

### 4. Include Analytics Perspective

Leverage analytics expertise to enhance requirements with:

```markdown
## Analytics & Metrics

### Data Requirements
- Data sources needed
- Data volume estimates
- Data quality requirements
- Data retention policies

### Analytics Metrics
- KPIs to track
- Reporting requirements
- Dashboard needs
- Alert thresholds

### Performance Analytics
- Performance benchmarks
- Monitoring requirements
- SLA definitions
```

### 5. Document Outstanding Clarifications

If any questions remain unanswered, create a file named `<task_name>_clarifications_pending.md` in the tasks folder with:

```markdown
# Clarifications Needed

## Critical Questions
1. **[Topic]**: [Specific question that needs immediate answer]
2. **[Topic]**: [Another critical question]
...

## Ambiguous Requirements
- **[Requirement]**: [Why it's ambiguous and what needs clarification]
...

## Assumptions Made
- **Assumption**: [What was assumed]
  - **Validation Needed**: [How to validate this assumption]
...

## Missing Information
- [Information that is critical but missing from the task]
...

## Alternative Interpretations
- **Scenario A**: [One way to interpret the requirement]
- **Scenario B**: [Alternative interpretation]
  - **Clarification Needed**: [What would help determine the correct interpretation]
```

### 6. Create Tasks Folder Structure

Ensure the following folder structure:
```
tasks/
├── <task_name>_requirements.md     # Main requirements document
├── <task_name>_clarifications_pending.md  # If needed
└── <task_name>/                    # Folder for task implementation
    ├── code/                       # Implementation code
    ├── tests/                      # Test files
    └── docs/                       # Documentation

```

### 7. Provide Summary

After creating all documents, provide a clear summary including:
- Overview of what was analyzed
- Top 3-5 key requirements identified
- Most critical questions needing immediate attention
- Recommended immediate next steps
- Any blocking issues that prevent progress

## Important Notes

- **MUST ASK FOR CLARIFICATIONS**: Always interact with the user to clarify unclear aspects
- Create visual diagrams using Mermaid for architecture and data flows
- Be thorough but maintain clarity and readability
- Prioritize actionable insights over theoretical considerations
- Highlight risks and dependencies clearly
- Consider both technical and business perspectives
- Include analytics and metrics perspective
- If the task file doesn't exist or is empty, report this clearly
- Save all files in the `tasks` folder with proper naming convention
- Extract task name from the task description for file naming