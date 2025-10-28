# PRP Lifecycle Management

This document explains how PRPs move through different stages and how to track progress.

## Directory Structure

```
PRPs/
├── planning/
│   ├── backlog/          # 📋 Planned PRPs (not started)
│   ├── active/           # 🔄 Currently being refined/approved
│   └── completed/        # ✅ Planning complete, ready for implementation
├── implementation/
│   ├── in-progress/      # 👷 Active implementation by agents
│   └── completed/        # ✅ Fully implemented and deployed
├── architecture/         # 🏗️  Architecture decisions and designs
├── contracts/            # 📜 API contracts and specifications
├── security/             # 🔒 Security requirements and audits
└── .cache/
    ├── agent-views/      # 🤖 Per-agent lightweight context (2-5KB)
    └── task-briefs/      # 📝 Task-specific briefs
```

## Lifecycle Stages

### Stage 1: Backlog → Active Planning

```bash
# When starting a new project/feature
# 1. Create initial PRP in backlog
cp PRPs/templates/prp_planning.md PRPs/planning/backlog/my-feature.md

# 2. Business Analyst refines requirements
# 3. Move to active when work begins
mv PRPs/planning/backlog/my-feature.md PRPs/planning/active/my-feature.md
```

**Responsible Agents**: Business Analyst, Context Researcher, PRP Orchestrator

**Exit Criteria**:
- [ ] Requirements documented
- [ ] User stories complete
- [ ] Success metrics defined
- [ ] Stakeholder approval

### Stage 2: Active Planning → Completed Planning

```bash
# Once planning is complete and approved
mv PRPs/planning/active/my-feature.md PRPs/planning/completed/my-feature.md

# Generate architecture documents
# Integration Architect creates PRPs/architecture/my-feature-arch.md
# Security Auditor creates PRPs/security/my-feature-security.md
```

**Responsible Agents**: Integration Architect, Security Auditor, Performance Optimizer

**Exit Criteria**:
- [ ] Architecture designed
- [ ] API contracts defined
- [ ] Security requirements integrated
- [ ] Performance targets set

### Stage 3: Planning Complete → In-Progress Implementation

```bash
# Create implementation PRP
cp PRPs/templates/prp_base.md PRPs/implementation/in-progress/my-feature-impl.md

# Create tasks in registry
python scripts/agent-task-manager.py create \
  --title "Implement my-feature backend" \
  --priority high \
  --hours 8

# Generate agent views for efficient context loading
python scripts/generate-agent-views.py --all
```

**Responsible Agents**: Implementation Specialist, Validation Engineer

**Exit Criteria**:
- [ ] Code complete
- [ ] Tests passing (>80% coverage)
- [ ] Security scan clean
- [ ] Performance validated

### Stage 4: In-Progress → Completed Implementation

```bash
# Once implementation is done and deployed
mv PRPs/implementation/in-progress/my-feature-impl.md \
   PRPs/implementation/completed/my-feature-impl.md

# Mark all related tasks as complete
python scripts/agent-task-manager.py complete \
  --task TASK-001 \
  --notes "Feature deployed to production"
```

**Responsible Agents**: DevOps Engineer, Documentation Curator

**Exit Criteria**:
- [ ] Deployed to production
- [ ] Monitoring active
- [ ] Documentation complete
- [ ] Stakeholders notified

## Quick Status Check

### View All Active Work

```bash
# List PRPs by stage
echo "=== ACTIVE PLANNING ==="
ls -1 PRPs/planning/active/

echo "=== IN PROGRESS IMPLEMENTATION ==="
ls -1 PRPs/implementation/in-progress/

echo "=== TASK REGISTRY STATUS ==="
python scripts/agent-task-manager.py status
```

### View Agent Workload

```bash
# Check which agents are busy
python scripts/agent-task-manager.py list --status in-progress

# Check session locks
ls -la .agent-system/sessions/active/
```

### View Context Size

```bash
# See how much context each agent loads
ls -lh PRPs/.cache/agent-views/
```

## Task-to-PRP Mapping

Tasks in `.agent-system/registry/tasks.json` should reference PRPs:

```json
{
  "TASK-001": {
    "title": "Implement payment gateway",
    "prp_source": "PRPs/implementation/in-progress/payment-feature.md",
    "prp_section": "## Implementation Blueprint",
    "context_refs": [
      "PRPs/contracts/payment-api-contract.md",
      "PRPs/security/payment-security.md"
    ]
  }
}
```

## Best Practices

### 1. Always Move PRPs Forward

❌ **Don't:** Leave PRPs in backlog indefinitely
✅ **Do:** Regularly review backlog and activate or archive

### 2. One Active PRP per Agent

❌ **Don't:** Agents working on multiple PRPs simultaneously
✅ **Do:** Complete current PRP before starting next

### 3. Archive Completed Work

❌ **Don't:** Delete completed PRPs
✅ **Do:** Move to completed/ for reference and learning

### 4. Link Tasks to PRPs

❌ **Don't:** Create tasks without PRP context
✅ **Do:** Always reference source PRP in task metadata

### 5. Generate Views Regularly

❌ **Don't:** Load full PRPs for every agent
✅ **Do:** Run `python scripts/generate-agent-views.py --all` after PRP changes

## Monitoring Progress

### Daily Standup Script

```bash
#!/bin/bash
# daily-status.sh

echo "📊 Daily Status Report - $(date)"
echo ""

echo "🔄 Active Planning:"
ls PRPs/planning/active/ | wc -l

echo "👷 In Progress Implementation:"
ls PRPs/implementation/in-progress/ | wc -l

echo "✅ Completed This Week:"
find PRPs/implementation/completed/ -mtime -7 | wc -l

echo ""
echo "📋 Task Registry:"
python scripts/agent-task-manager.py status

echo ""
echo "🔗 Active Sessions:"
ls .agent-system/sessions/active/ | wc -l
```

### Phase Completion Report

```bash
# Generate phase completion report
cat > reports/phase-completions/phase-$(date +%Y-%m-%d).md <<EOF
# Phase Completion Report - $(date +%Y-%m-%d)

## Completed PRPs
$(ls PRPs/implementation/completed/)

## Active Work
$(ls PRPs/implementation/in-progress/)

## Backlog
$(ls PRPs/planning/backlog/ | wc -l) items

## Metrics
- Total tasks: $(python scripts/agent-task-manager.py status | grep "Total Tasks")
- Active agents: $(ls .agent-system/sessions/active/ | wc -l)
EOF
```

## Context Optimization

### Agent View Generation

The system automatically extracts relevant sections for each agent:

| Agent | Loads From | Typical Size |
|-------|-----------|--------------|
| **Business Analyst** | Goal, Why, Success Criteria | ~2KB |
| **Implementation Specialist** | Implementation Blueprint, API Contracts | ~3-4KB |
| **Validation Engineer** | Validation Loop, Test Requirements | ~2KB |
| **Security Auditor** | Security Requirements, Threat Model | ~2KB |
| **DevOps Engineer** | Deployment Strategy, Infrastructure | ~2KB |

**Total context per agent**: 2-5KB (vs 50KB+ full PRP)
**Reduction**: 90-95%

### Regenerate Views After Changes

```bash
# Clean old views and regenerate
python scripts/generate-agent-views.py --clean --all

# Generate for specific agent
python scripts/generate-agent-views.py --agent implementation-specialist

# Generate brief for specific task
python scripts/generate-agent-views.py --task TASK-001
```

## Troubleshooting

### PRP Stuck in Planning

**Symptom**: PRP in `planning/active/` for >1 week

**Solution**:
1. Check if Business Analyst has blockers
2. Review with PRP Orchestrator
3. Either complete planning or move back to backlog

### Too Many In-Progress Implementations

**Symptom**: >5 PRPs in `implementation/in-progress/`

**Solution**:
1. Review with PRP Orchestrator
2. Prioritize critical PRPs
3. Move non-critical to backlog
4. Complete current work before starting new

### Agent Context Too Large

**Symptom**: Agent loading >10KB context

**Solution**:
1. Run `python scripts/generate-agent-views.py --clean --all`
2. Review `.claude/context-loader.yaml` for agent
3. Reduce `conditional_load` rules
4. Archive old PRPs

## Summary

The PRP lifecycle provides:
- ✅ **Clear visibility**: Know what's planned, active, and done
- ✅ **Progress tracking**: See movement through stages
- ✅ **Context optimization**: Agents load only what they need
- ✅ **Task linkage**: Tasks explicitly reference PRPs
- ✅ **Historical reference**: Completed PRPs archived for learning

**Remember**: Move PRPs forward, generate views after changes, and keep one active PRP per agent.
