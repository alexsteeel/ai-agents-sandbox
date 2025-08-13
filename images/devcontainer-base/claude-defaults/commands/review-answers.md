---
name: review-answers
description: Reviews user-provided answers, updates task artifacts, and iterates with new questions if needed
arguments:
  - name: task_path
    description: Path to the task folder containing answers.md
    required: true
agents:
  - analytics-engineer
  - technical-lead
---

You are reviewing answers provided by the user and updating task documentation accordingly. You will work iteratively until all requirements are clear and ready for approval.

**Agents to use:**
- **analytics-engineer**: For data requirements and metrics clarification
- **technical-lead**: For technical architecture and implementation details

## Your Mission

1. **Review provided answers** in the task folder
2. **Update all task artifacts** based on new information
3. **Identify any remaining unclear points**
4. **Ask concise follow-up questions** or **request approval** to proceed

## Step-by-Step Process

### 1. Read Current Task State

Check what needs to be read from the task folder: `{{task_path}}`

**If continuing from analyze-task in same chat:**
- Only read `answers.md` to see new/updated answers
- You already have context from previous analysis

**If starting fresh or in new chat:**
- Read all relevant files to understand current state
- `initial_requirements.md` or task description
- `answers.md` - User's answers to previous questions
- `requirements.md` - Current requirements document
- `plan.md` - Implementation plan

### 2. Analyze New Information

Review the answers provided and determine:
- Which requirements can now be clarified
- What new risks or issues are revealed
- Whether any assumptions can be validated
- If new questions arise from the answers

### 3. Update Task Artifacts

Based on the new information, update:

**requirements.md:**
- Refine functional requirements with specific details
- Update data sources and formats
- Clarify performance criteria
- Adjust risk assessments

**plan.md:**
- **When all requirements are clear**: Analytics engineer passes refined requirements to technical lead
- Technical lead updates implementation plan based on complete understanding
- Update implementation phases if needed
- Refine task breakdowns
- Adjust testing strategies
- Update prerequisites

**answers.md:**
- Mark questions as answered
- Add new questions if discovered
- Update assumptions and decisions
- Document any remaining uncertainties

### 4. Determine Next Action

After updating artifacts, either:

**A. Ask Follow-up Questions (if still unclear):**
```
Based on your answers, I've updated the requirements. I still need clarification on:

1. **[Topic]**: [Specific question]
   - Why this matters: [Impact on implementation]

2. **[Topic]**: [Another question]
   - Context: [Why this arose from previous answer]

Please provide answers so I can finalize the requirements.
```

**B. Request Approval (if everything is clear):**

Before requesting approval:
1. Analytics engineer finalizes all data and metrics requirements
2. Technical lead receives the complete requirements
3. Technical lead updates the implementation plan with final details

```
✅ All requirements are now clear and documented.

**Analytics engineer has finalized:**
- Data requirements and sources
- Metrics and KPIs
- Performance criteria

**Technical lead has updated:**
- Implementation plan based on complete requirements
- Task breakdown and sequencing
- Resource allocation

**Ready for approval:**
- requirements.md - Complete specification
- plan.md - Implementation roadmap (updated by technical lead)
- answers.md - All clarifications documented

Please review and confirm we can proceed with implementation.
```

### 5. Iteration Guidelines

**Keep iterations concise:**
- Only ask questions that block implementation
- Group related questions together
- Provide context for why each question matters
- Reference specific parts of answers that need clarification

**Language consistency:**
- If initial_requirements.md is in Russian, keep answers.md updates in Russian
- Keep requirements.md and plan.md in English
- Use clear, technical language

## Example Interaction Flow

```
User: "The data comes from our PostgreSQL database, tables: orders, customers, products"

You: "Updated requirements with data sources. Need to clarify:
1. **Data Volume**: How many records in orders table daily?
2. **Update Frequency**: Real-time or batch updates needed?
3. **Historical Data**: How far back should we process?"

User: "About 10K orders/day, batch updates every hour, last 2 years"

You: "✅ Requirements complete. Updated:
- Data volume: 10K records/day
- Processing: Hourly batch
- Retention: 2 years history

Ready for approval to begin implementation."
```

## Important Notes

- **Be concise**: Don't repeat information already documented
- **Focus on blockers**: Only ask questions that prevent implementation
- **Update incrementally**: Modify only sections affected by new answers
- **Maintain consistency**: Keep all documents synchronized
- **ALL ARTIFACTS MUST BE IN TASK FOLDER**: Never create files outside `tasks/<task_name>/`

## Success Criteria

The review is complete when:
1. All critical questions have clear answers
2. Requirements are unambiguous and testable
3. Implementation plan is realistic and complete
4. No blocking uncertainties remain
5. User approves the final documents
