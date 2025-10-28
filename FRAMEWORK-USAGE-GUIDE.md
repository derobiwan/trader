# Framework Usage Guide

Complete guide for using the distributed agent coordination framework with PRP methodology.

## Table of Contents
- [Quick Start](#quick-start)
- [PRP Lifecycle](#prp-lifecycle)
- [Task Management](#task-management)
- [Context Optimization](#context-optimization)
- [Progress Tracking](#progress-tracking)
- [Common Workflows](#common-workflows)
- [Troubleshooting](#troubleshooting)

## Quick Start

### Initial Setup (5 minutes)

```bash
# 1. Bootstrap workspace
./init-agent-workspace.sh

# 2. Verify structure
ls .agent-system/agents          # Should show 10 agent directories
ls PRPs/.cache/agent-views       # Should exist
python scripts/agent-task-manager.py status  # Should show task registry

# 3. Generate initial agent views
python scripts/generate-agent-views.py --all
```

### First Project (15 minutes)

```bash
# 1. Initialize in Claude Code
/prime-core
"Load AGENT-ORCHESTRATION.md and initialize all agents"

# 2. Start project
"PRP Orchestrator, initiate standard workflow for: [your project description]"

# 3. Follow orchestrator guidance through phases
```

## PRP Lifecycle

### Understanding the Flow

```
Backlog → Active Planning → Completed Planning
                ↓
        Architecture & Design
                ↓
        Implementation (In-Progress) → Completed
                ↓
        Deployment & Optimization
```

### Creating a New PRP

```bash
# 1. Start from template
cp PRPs/templates/prp_planning.md PRPs/planning/backlog/my-feature.md

# 2. Edit with your requirements
vim PRPs/planning/backlog/my-feature.md

# 3. When ready to start, move to active
mv PRPs/planning/backlog/my-feature.md PRPs/planning/active/my-feature.md

# 4. Trigger Business Analyst
# In Claude Code:
"Business Analyst, refine requirements for my-feature PRP in planning/active/"
```

### Moving PRPs Through Stages

#### Stage 1: Backlog → Active (Planning Phase)

**When**: Starting requirements gathering
**Responsible**: Business Analyst, Context Researcher

```bash
# Move to active
mv PRPs/planning/backlog/feature.md PRPs/planning/active/feature.md

# Generate agent views
python scripts/generate-agent-views.py --all

# In Claude Code:
"Business Analyst, work on PRPs/planning/active/feature.md"
```

**Exit Criteria**:
- [ ] Requirements documented
- [ ] User stories complete
- [ ] Success metrics defined
- [ ] Stakeholder signoff

#### Stage 2: Active → Completed Planning

**When**: Planning approved, ready for architecture
**Responsible**: Integration Architect, Security Auditor

```bash
# Move to completed planning
mv PRPs/planning/active/feature.md PRPs/planning/completed/feature.md

# Create architecture documents
# In Claude Code:
"Integration Architect, design architecture for feature based on PRPs/planning/completed/feature.md"

# Result: PRPs/architecture/feature-arch.md
# Result: PRPs/contracts/feature-api-contract.md
# Result: PRPs/security/feature-security.md
```

**Exit Criteria**:
- [ ] Architecture designed
- [ ] API contracts defined
- [ ] Security requirements integrated
- [ ] Performance targets set

#### Stage 3: Planning Complete → In-Progress Implementation

**When**: Ready to write code
**Responsible**: Implementation Specialist, Validation Engineer

```bash
# Create implementation PRP
cp PRPs/templates/prp_base.md PRPs/implementation/in-progress/feature-impl.md

# Create tasks
python scripts/agent-task-manager.py create \
  --title "Implement feature backend" \
  --description "See PRPs/implementation/in-progress/feature-impl.md" \
  --priority high \
  --hours 8

# Generate views with new PRP
python scripts/generate-agent-views.py --all

# In Claude Code:
"Implementation Specialist, execute PRPs/implementation/in-progress/feature-impl.md"
```

**Exit Criteria**:
- [ ] Code complete
- [ ] Tests passing (>80% coverage)
- [ ] Security scan clean
- [ ] Performance validated

#### Stage 4: In-Progress → Completed Implementation

**When**: Deployed to production
**Responsible**: DevOps Engineer, Documentation Curator

```bash
# Move to completed
mv PRPs/implementation/in-progress/feature-impl.md \
   PRPs/implementation/completed/feature-impl.md

# Complete all tasks
python scripts/agent-task-manager.py complete \
  --task TASK-001 \
  --notes "Deployed to production, monitoring active"

# In Claude Code:
"DevOps Engineer, deploy feature to production"
"Documentation Curator, finalize documentation"
```

**Exit Criteria**:
- [ ] Production deployment successful
- [ ] Monitoring configured
- [ ] Documentation complete
- [ ] Stakeholders notified

## Task Management

### Creating Tasks

```bash
# Basic task creation
python scripts/agent-task-manager.py create \
  --title "Implement user authentication" \
  --description "Add JWT-based auth with refresh tokens" \
  --priority high \
  --hours 8

# Returns: TASK-001
```

### Claiming Tasks (Agent Takes Ownership)

```bash
# Agent claims task
python scripts/agent-task-manager.py claim \
  --agent implementation-specialist \
  --task TASK-001

# Creates session lock in .agent-system/sessions/active/
# Updates task status to "in-progress"
```

### Completing Tasks

```bash
# Mark task complete with notes
python scripts/agent-task-manager.py complete \
  --task TASK-001 \
  --notes "Authentication implemented, tests passing, security scan clean"

# Moves session lock to history
# Updates statistics
```

### Handing Off Tasks

```bash
# Hand off to another agent
python scripts/agent-task-manager.py handoff \
  --task TASK-001 \
  --to-agent validation-engineer \
  --notes "Implementation complete, ready for testing"

# Creates handoff record in .agent-system/sync/handoffs.json
# Updates task agent assignment
```

### Listing Tasks

```bash
# All tasks
python scripts/agent-task-manager.py list

# By status
python scripts/agent-task-manager.py list --status in-progress
python scripts/agent-task-manager.py list --status pending

# By agent
python scripts/agent-task-manager.py list --agent implementation-specialist
```

### Task Status

```bash
# Overall statistics
python scripts/agent-task-manager.py status

# Specific task
python scripts/agent-task-manager.py status --task TASK-001
```

## Context Optimization

### Why Context Matters

**Problem**: Full PRPs are 50KB+, agents hit token limits
**Solution**: 3-layer context optimization

### Layer 1: Agent Views

```bash
# Generate lightweight views (2-5KB each)
python scripts/generate-agent-views.py --all

# Result:
# PRPs/.cache/agent-views/business-analyst.md        (~2KB)
# PRPs/.cache/agent-views/implementation-specialist.md (~4KB)
# PRPs/.cache/agent-views/validation-engineer.md      (~2KB)
# ... etc for all 10 agents

# Each agent loads ONLY their view, not full PRPs
```

### Layer 2: Task Briefs

```bash
# Generate brief for specific task
python scripts/generate-agent-views.py --task TASK-001

# Result: PRPs/.cache/task-briefs/TASK-001.md
# Contains:
# - Task metadata
# - Referenced PRP sections only
# - Relevant file paths
# - Acceptance criteria
```

### Layer 3: Context Loader Config

Edit `.claude/context-loader.yaml` to control what each agent loads:

```yaml
agents:
  implementation-specialist:
    always_load:
      - ".agent-system/agents/implementation-specialist/context.json"
      - ".agent-system/agents/implementation-specialist/tasks.json"
    conditional_load:
      when_task_requires:
        - "PRPs/.cache/task-briefs/TASK-{current}.md"
        - "PRPs/contracts/{feature}-api-contract.md"
    never_load:
      - "PRPs/planning/*.md"  # Full planning docs
      - ".agent-system/agents/*/changelog.md"  # Other agents' logs
    max_context_tokens: 8000
```

### When to Regenerate Views

**ALWAYS** regenerate after:
- Creating new PRPs
- Updating existing PRPs
- Moving PRPs between directories
- Changing PRP structure

```bash
# Clean and regenerate
python scripts/generate-agent-views.py --clean --all

# Check sizes
ls -lh PRPs/.cache/agent-views/
```

### Checking Context Usage

```bash
# View agent view sizes
ls -lh PRPs/.cache/agent-views/

# View task brief sizes
ls -lh PRPs/.cache/task-briefs/

# Expected: 2-5KB per file
# If larger: review PRP structure, extract less content
```

## Progress Tracking

### Quick Status Dashboard

```bash
#!/bin/bash
# status-dashboard.sh

echo "=== PRP LIFECYCLE ==="
echo "Backlog:     $(ls PRPs/planning/backlog/ 2>/dev/null | wc -l)"
echo "Active:      $(ls PRPs/planning/active/ 2>/dev/null | wc -l)"
echo "In Progress: $(ls PRPs/implementation/in-progress/ 2>/dev/null | wc -l)"
echo "Completed:   $(ls PRPs/implementation/completed/ 2>/dev/null | wc -l)"

echo ""
echo "=== TASK REGISTRY ==="
python scripts/agent-task-manager.py status

echo ""
echo "=== ACTIVE AGENTS ==="
ls .agent-system/sessions/active/ 2>/dev/null | wc -l
```

### Viewing Agent Activity

```bash
# Recent changes by all agents
for agent in .agent-system/agents/*/; do
  echo "=== $(basename $agent) ==="
  tail -n 5 "$agent/changelog.md"
  echo ""
done

# Active sessions
ls -la .agent-system/sessions/active/

# Session details
cat .agent-system/sessions/active/claude-*.lock
```

### Viewing Handoffs

```bash
# View handoff queue
cat .agent-system/sync/handoffs.json

# Recent handoffs
tail -n 20 .agent-system/sync/handoffs.json
```

### Daily Reports

```bash
# Generate daily report
cat > reports/daily/$(date +%Y-%m-%d).md <<EOF
# Daily Report - $(date +%Y-%m-%d)

## Active PRPs
$(ls PRPs/implementation/in-progress/)

## Completed Today
$(find PRPs/implementation/completed/ -mtime -1)

## Task Statistics
$(python scripts/agent-task-manager.py status)

## Active Agents
$(ls .agent-system/sessions/active/)
EOF
```

## Common Workflows

### Standard Feature Workflow

```bash
# 1. Create planning PRP
cp PRPs/templates/prp_planning.md PRPs/planning/backlog/my-feature.md
vim PRPs/planning/backlog/my-feature.md

# 2. Activate planning
mv PRPs/planning/backlog/my-feature.md PRPs/planning/active/my-feature.md

# 3. In Claude Code - Planning
"Business Analyst, refine requirements for PRPs/planning/active/my-feature.md"
# Wait for completion, then:
mv PRPs/planning/active/my-feature.md PRPs/planning/completed/my-feature.md

# 4. In Claude Code - Architecture
"Integration Architect, design architecture for my-feature based on PRPs/planning/completed/my-feature.md"

# 5. Create implementation PRP
cp PRPs/templates/prp_base.md PRPs/implementation/in-progress/my-feature-impl.md
vim PRPs/implementation/in-progress/my-feature-impl.md

# 6. Generate views
python scripts/generate-agent-views.py --all

# 7. Create task
python scripts/agent-task-manager.py create \
  --title "Implement my-feature" \
  --priority high \
  --hours 8

# 8. In Claude Code - Implementation
"Implementation Specialist, execute PRPs/implementation/in-progress/my-feature-impl.md"

# 9. Complete
mv PRPs/implementation/in-progress/my-feature-impl.md PRPs/implementation/completed/
python scripts/agent-task-manager.py complete --task TASK-001 --notes "Feature complete"
```

### Hotfix Workflow

```bash
# 1. In Claude Code - Emergency
"PRP Orchestrator, initiate hotfix workflow for: [issue description]"

# 2. Create fix in workspace/fixes/
mkdir workspace/fixes/issue-123
cd workspace/fixes/issue-123

# 3. Create task
python scripts/agent-task-manager.py create \
  --title "Hotfix: [issue]" \
  --priority critical \
  --hours 2

# 4. Claim and fix
python scripts/agent-task-manager.py claim --agent implementation-specialist --task TASK-XXX
# Fix the issue

# 5. Test and deploy
python scripts/agent-task-manager.py handoff --task TASK-XXX --to-agent validation-engineer
# After validation:
python scripts/agent-task-manager.py handoff --task TASK-XXX --to-agent devops-engineer
# After deployment:
python scripts/agent-task-manager.py complete --task TASK-XXX --notes "Hotfix deployed"
```

### Research Workflow

```bash
# 1. In Claude Code
"Context Researcher, investigate: [topic]"

# 2. Research results go in
# PRPs/architecture/research-[topic].md

# 3. Create summary task
python scripts/agent-task-manager.py create \
  --title "Research: [topic]" \
  --priority medium \
  --hours 4

# 4. Share findings
# Context Researcher adds to PRPs/architecture/
# Other agents reference in their work
```

## Troubleshooting

### Problem: Agent Context Too Large

**Symptoms**: Agent loading >10KB context, hitting token limits

**Solution**:
```bash
# 1. Clean and regenerate
python scripts/generate-agent-views.py --clean --all

# 2. Check sizes
ls -lh PRPs/.cache/agent-views/

# 3. If still large, review PRPs
# Ensure proper section headers for extraction
# Move verbose content to separate docs

# 4. Adjust context-loader.yaml
vim .claude/context-loader.yaml
# Reduce conditional_load rules for agent
```

### Problem: PRP Stuck in Active

**Symptoms**: PRP in `planning/active/` for >1 week

**Solution**:
```bash
# 1. Review with orchestrator
# In Claude Code:
"PRP Orchestrator, review status of PRPs/planning/active/stuck-feature.md"

# 2. Either complete or move back
# If requirements clear:
mv PRPs/planning/active/stuck-feature.md PRPs/planning/completed/

# If blocked:
mv PRPs/planning/active/stuck-feature.md PRPs/planning/backlog/
# Add notes about blockers
```

### Problem: Too Many In-Progress Tasks

**Symptoms**: >10 tasks in `in-progress` status

**Solution**:
```bash
# 1. Review task list
python scripts/agent-task-manager.py list --status in-progress

# 2. Complete finished tasks
python scripts/agent-task-manager.py complete --task TASK-XXX --notes "..."

# 3. Prioritize remaining
# In Claude Code:
"PRP Orchestrator, prioritize in-progress tasks and recommend focus"

# 4. Move non-critical back to pending
# Manually edit .agent-system/registry/tasks.json if needed
```

### Problem: Agent Views Not Loading

**Symptoms**: Agent loads full PRPs instead of views

**Solution**:
```bash
# 1. Check views exist
ls PRPs/.cache/agent-views/

# 2. If empty, regenerate
python scripts/generate-agent-views.py --all

# 3. Check context-loader.yaml
cat .claude/context-loader.yaml
# Ensure agent configured to load views

# 4. Check PRP structure
# Views depend on section headers matching AGENT_SECTIONS in generate-agent-views.py
```

### Problem: Session Lock Conflicts

**Symptoms**: Can't claim task, lock file exists

**Solution**:
```bash
# 1. Check active sessions
ls -la .agent-system/sessions/active/

# 2. Check if session is actually active
cat .agent-system/sessions/active/claude-*.lock

# 3. If stale (old timestamp), remove
rm .agent-system/sessions/active/claude-XXXXXX-XXXXXX.lock

# 4. Try claiming again
python scripts/agent-task-manager.py claim --agent [agent] --task TASK-XXX
```

## Best Practices

### DO:
✅ Regenerate agent views after PRP changes
✅ Keep one active PRP per agent
✅ Complete tasks before starting new ones
✅ Archive completed PRPs for reference
✅ Link tasks to source PRPs
✅ Check context sizes regularly
✅ Use orchestrator for coordination

### DON'T:
❌ Load full PRPs for every agent
❌ Skip handoff protocols
❌ Work on multiple PRPs simultaneously
❌ Delete completed PRPs
❌ Create tasks without PRP context
❌ Bypass validation gates
❌ Ignore the orchestrator

## Summary

This framework enables:
- ✅ **Clear progress visibility**: Know what's planned, active, and done
- ✅ **Context optimization**: Agents load 2-5KB instead of 50KB+
- ✅ **Task coordination**: Lock-free claiming, structured handoffs
- ✅ **Parallel execution**: Multiple agents work simultaneously
- ✅ **Production quality**: Phase-based validation gates

**Key Commands**:
```bash
# Setup
./init-agent-workspace.sh

# PRP Management
mv PRPs/planning/backlog/X.md PRPs/planning/active/X.md

# Task Management
python scripts/agent-task-manager.py create/claim/handoff/complete

# Context Optimization
python scripts/generate-agent-views.py --all

# Progress Tracking
python scripts/agent-task-manager.py status
```

**Remember**: The framework is your orchestrator. Let it coordinate, optimize context, and ensure quality.
