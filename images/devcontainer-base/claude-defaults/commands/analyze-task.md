---
name: analyze-task
description: Analyzes a task file and creates requirements documents through questions and planning
arguments:
  - name: task_path
    description: Path to the task file to analyze
    required: true
agents:
  - technical-lead
  - analytics-engineer
---

You analyze tasks using technical-lead planning and analytics-engineer questions to create clear requirements documentation.

**Agents to use:**
- **technical-lead**: For creating implementation plans and breaking down tasks
- **analytics-engineer**: For asking clarifying questions about requirements

## Process

### 1. Read the Task File
Read the task file located at: `{{task_path}}`

### 2. Ask Questions (using analytics-engineer agent)
Use the question template to gather missing information:
```
Question: [Your question here]
Suggested options:
1. [First option]
2. [Second option]
Answer: [Wait for user input]
```

### 3. Create Documents (using technical-lead agent)
Create implementation plan and requirements documents.

## Documents to Create

Create these files in the existing `tasks/<task_name>/` folder:

### requirements.md
- Functional requirements (what needs to be built)
- Technical specifications 
- Success criteria

### answers.md  
- Questions asked and answers received
- Key decisions and assumptions

### plan.md
- Implementation phases with specific tasks
- Clear completion criteria for each task

## Language Rules

- **answers.md**: Same language as initial_requirements.md 
- **requirements.md and plan.md**: Always in English
- **Questions**: Can be in user's preferred language

## Important Notes

- Ask only essential clarifying questions
- Create clear, actionable documents
- All files must be in the existing `tasks/<task_name>/` folder
- Do NOT start implementation until documents are approved