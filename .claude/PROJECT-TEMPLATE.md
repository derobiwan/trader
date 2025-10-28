# Project: [PROJECT_NAME]

## Workflow Type
- [ ] Standard (Full process)
- [ ] Hotfix (Emergency)
- [ ] Small Feature (<1 day)
- [ ] Research (Investigation)

## Active Agents
- [ ] PRP Orchestrator (ALWAYS)
- [ ] Business Analyst
- [ ] Context Researcher
- [ ] Implementation Specialist
- [ ] Validation Engineer
- [ ] Integration Architect
- [ ] Documentation Curator
- [ ] Security Auditor
- [ ] Performance Optimizer
- [ ] DevOps Engineer

## Current Phase
- [ ] Phase 0: Initialization
- [ ] Phase 1: Discovery
- [ ] Phase 2: Architecture
- [ ] Phase 3: Planning
- [ ] Phase 4: Implementation
- [ ] Phase 5: Deployment Prep
- [ ] Phase 6: Go-Live
- [ ] Phase 7: Optimization

## Key Files
- Task Registry: `.agent-system/registry/tasks.json`
- Milestones: `.agent-system/registry/milestones.md`
- Requirements: `PRPs/planning/[project]-requirements.md`
- Architecture: `PRPs/architecture/[project]-architecture.md`
- Implementation: `workspace/features/[feature]/`
- Tests: `workspace/features/[feature]/tests/`
- Docs: `workspace/features/[feature]/docs/`

## Active Session
- Session ID: `[session-id]`
- Agent: `[agent-name]`
- Tasks: `[task-ids]`

## Success Metrics
- [ ] [Metric 1]
- [ ] [Metric 2]
- [ ] [Metric 3]

## Next Actions
1. [Immediate next step]
2. [Following step]
3. [Subsequent step]

## Commands Reference
```bash
# Initialize workspace
./init-agent-workspace.sh

# Claim a task
python scripts/agent-task-manager.py claim --agent "implementation-specialist" --task "TASK-001"

# Create handoff
python scripts/agent-task-manager.py handoff --from "implementation-specialist" --to "validation-engineer" --task "TASK-001"

# Generate agent view
python scripts/generate-agent-views.py --agent "implementation-specialist" --prp "payment-prd.md"

# Check task status
python scripts/agent-task-manager.py status --task "TASK-001"
```
