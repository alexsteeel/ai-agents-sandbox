---
name: analyze-task
description: Analyzes a task file and generates detailed requirements documentation using technical-lead and analytics agents, with interactive clarification
arguments:
  - name: task_path
    description: Path to the task file to analyze
    required: true
agents:
  - technical-lead
  - analytics-engineer
---

You are acting as the Technical Lead with support from Analytics experts to analyze a task and create comprehensive requirements documentation with interactive clarification.

**Agents to use:**
- **technical-lead**: For architecture design, task planning, and technical leadership
- **analytics-engineer**: For requirements gathering, metrics design, and data analysis perspectives

## Your Mission

Working with both technical-lead and analytics perspectives, you will:
1. **Exhaustively analyze** the task to find ALL potential issues before implementation
2. **Identify problems** in data sources, algorithms, logic, and integration points
3. **Create precise requirements** that are unambiguous, testable, and complete
4. **Document every risk** that could cause implementation failures
5. **Ask minimal questions** - only those critical for avoiding blocking issues

## Step-by-Step Process

### 1. Read the Task File
First, read the task file located at: `{{task_path}}`

**Language Note**: 
- If the initial requirements file (`initial_requirements.md`) is in Russian, then `answers.md` should also be in Russian to maintain clear communication with stakeholders
- ALL other documents (`requirements.md` and `plan.md`) MUST be written in English regardless of the source language

### 2. Deep Analysis and Issue Identification

**CRITICAL**: Before creating requirements, you MUST perform exhaustive analysis to:

#### A. Identify Data Issues
- **Data Quality**: Missing values, inconsistencies, outliers, duplicates
- **Data Availability**: What data exists vs. what's needed
- **Data Format**: Structure mismatches, encoding issues, schema conflicts
- **Data Volume**: Scalability concerns, storage requirements
- **Data Freshness**: Update frequencies, staleness risks
- **Data Dependencies**: External sources, API limitations, access restrictions

#### B. Identify Algorithm/Logic Issues
- **Edge Cases**: Boundary conditions, null/empty inputs, extreme values
- **Performance Bottlenecks**: O(n²) operations, memory leaks, inefficient queries
- **Concurrency Issues**: Race conditions, deadlocks, resource contention
- **Error Handling**: Failure modes, recovery strategies, data corruption risks
- **Assumptions**: Hidden dependencies, implicit requirements, unstated constraints
- **Integration Points**: API compatibility, version conflicts, protocol mismatches

#### C. Ask ONLY Critical Clarifying Questions
Focus on gaps that would block implementation or cause failures:
- **Specific Data Sources**: "Which exact tables/APIs contain the customer data?"
- **Business Rules**: "How should the system handle duplicate transactions?"
- **Failure Scenarios**: "What happens when the external service is unavailable?"
- **Data Transformations**: "What's the exact mapping between source and target schemas?"
- **Acceptance Criteria**: "What specific metrics define success?"

### 3. Analyze and Document Requirements

After getting clarifications, create a file named `requirements.md` in the existing `tasks/<task_name>/` folder with the following key sections:

**Core Requirements:**
- Functional requirements (what the system must do)
- Data requirements (sources, formats, volume, quality needs)
- Algorithm requirements (logic, performance, accuracy)
- Non-functional requirements (reliability, security, scalability)

**Data Flow:**
- Input data sources and formats
- Data transformations and processing steps
- Output destinations and formats
- Include Mermaid diagrams to visualize data flow

**Technical Architecture:**
- System components and their interactions
- Integration points and dependencies
- Infrastructure requirements
- Include Mermaid diagrams for architecture

**Risk Assessment:**
- Identify major risks (data quality, performance, integration)
- Probability and impact assessment
- Mitigation strategies

**Success Criteria:**
- Measurable success metrics
- Key performance indicators
- Acceptance criteria

Focus on being thorough but concise - capture all critical information without excessive templates.

### 4. Include Analytics Perspective

Leverage analytics expertise to identify:
- Key metrics and KPIs
- Data quality requirements
- Performance benchmarks
- Monitoring needs

### 5. Document Answers and Clarifications

Create a file named `answers.md` in the existing `tasks/<task_name>/` folder to document:
- Questions asked and answers received
- Key assumptions made and their rationale
- Pending clarifications still needed
- Important decisions and their impact

Keep this document concise and focused on critical information.

### 6. Create Implementation Plan

Create a file named `plan.md` in the existing `tasks/<task_name>/` folder with the implementation plan:

```markdown
# Implementation Plan

## Overview
[Brief summary of the implementation approach]

## Prerequisites
- [Dependencies that must be in place before starting]
- [Resources needed]
- [Team members required]

## Implementation Phases

### Phase 1: [Name]
**Objectives**:
- [Specific goals for this phase]

**Tasks**:
1. [ ] [Specific task with clear completion criteria]
2. [ ] [Another task]
...

**Deliverables**:
- [What will be produced in this phase]

### Phase 2: [Name]
[Continue with additional phases...]

## Testing Strategy
- **Unit Testing**: [Approach and coverage goals]
- **Integration Testing**: [How components will be tested together]
- **Performance Testing**: [Load and stress testing approach]
- **User Acceptance Testing**: [UAT approach]

## Approval Required
**⚠️ IMPORTANT**: Implementation should NOT begin until:
1. Requirements document has been reviewed and approved
2. All critical questions in answers.md have been addressed
3. Implementation plan has been approved by stakeholders
```

### 7. Organize All Documents

**📁 ALL ARTIFACTS MUST BE IN THE TASK FOLDER**

The requirements documents should be organized in the existing `tasks/<task_name>/` folder:
```
tasks/<task_name>/              # Existing folder with initial task files
├── requirements.md              # Main requirements document
├── answers.md                   # Questions, answers, and assumptions
└── plan.md                      # Implementation plan
```

**⚠️ CRITICAL**: 
- ALL artifacts, documents, and files related to this task MUST be stored in `tasks/<task_name>/` folder
- Do NOT create files outside the task folder
- Implementation must ONLY begin AFTER approval of:
1. **requirements.md** - All requirements are clear and complete
2. **answers.md** - All critical questions have been answered
3. **plan.md** - Implementation approach is approved

### 8. Provide Summary

After creating all documents, provide a clear summary including:
- Overview of what was analyzed
- Top 3-5 key requirements identified
- Most critical questions needing immediate attention
- Recommended immediate next steps
- Any blocking issues that prevent progress

### 9. Iterative Clarification Process

**When user provides answers to questions:**
1. Read and analyze the provided answers
2. Update `answers.md` with new information
3. Check if answers reveal new questions or issues
4. Update `requirements.md` and `plan.md` based on new understanding
5. Ask follow-up questions if something remains unclear
6. Continue this cycle until all critical aspects are clear

**Use concise follow-ups like:**
- "Based on your answer about [topic], I need to clarify: [specific question]"
- "This reveals a potential issue with [aspect]. How should we handle [scenario]?"
- "Updated the requirements. Still unclear: [remaining questions]"

## Important Notes

- **PRIMARY GOAL**: Find ALL issues that could cause implementation failures
- **BE EXHAUSTIVE**: Analyze every aspect - data, algorithms, integration, performance
- **BE PRECISE**: Requirements must be exact, unambiguous, and testable
- **MINIMIZE QUESTIONS**: Only ask when absolutely critical to avoid blocking
- **DOCUMENT RISKS**: Every potential failure mode must be identified
- **VALIDATE EVERYTHING**: Check data quality, algorithm correctness, edge cases
- **NO IMPLEMENTATION**: Do NOT start implementation until all three documents are approved
- Create visual diagrams using Mermaid for architecture and data flows
- Focus on implementation blockers over theoretical considerations
- If the task file doesn't exist or is empty, report this clearly
- **ALL ARTIFACTS MUST BE IN TASK FOLDER**: Every file, document, or artifact related to the task MUST be stored in `tasks/<task_name>/` folder
- Save all files in the existing `tasks/<task_name>/` folder
- The task folder should already exist with initial requirements or task description
- **Required documents before implementation**:
  - `requirements.md` - Complete requirements specification (MUST be in English)
  - `answers.md` - All clarifications and decisions documented (in Russian if initial_requirements.md is in Russian, otherwise English)
  - `plan.md` - Detailed implementation plan with phases and approval section (MUST be in English)