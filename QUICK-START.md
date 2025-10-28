# 🚀 Quick Start: Agent-Orchestrated Development

## First Time Setup (Already Complete ✅)

Your workspace is configured with:
- 10 specialized AI agents
- Distributed task coordination
- Minimal context loading (2-5KB per agent)
- Multi-technology support

## Starting a New Project

### 1️⃣ Initialize in Claude Code
```
/prime-core
"Load AGENT-ORCHESTRATION.md and initialize all agents for project: [your project name]"
```

### 2️⃣ Choose Workflow Type
```
"PRP Orchestrator, initiate [workflow type] for [project description]"
```

**Workflow Types:**
- `standard workflow` - Full 7 phases (1-2 weeks)
- `hotfix workflow` - Emergency fix (2-4 hours)
- `small feature workflow` - Simple addition (<1 day)
- `research workflow` - Technical investigation (variable)

### 3️⃣ The System Takes Over
The orchestrator will:
1. Create initial tasks in registry
2. Assign to appropriate agents
3. Generate lightweight views
4. Coordinate execution
5. Validate at each phase
6. Report progress

## Manual Task Management (Optional)

### Create Task
```bash
python scripts/agent-task-manager.py create \
  --title "Implement user authentication" \
  --priority high \
  --hours 8
```

### View Tasks
```bash
python scripts/agent-task-manager.py list
```

### Claim Task for Agent
```bash
python scripts/agent-task-manager.py claim \
  --agent implementation-specialist \
  --task TASK-001
```

### Complete Task
```bash
python scripts/agent-task-manager.py complete \
  --task TASK-001 \
  --notes "Authentication implemented with JWT"
```

### Handoff to Next Agent
```bash
python scripts/agent-task-manager.py handoff \
  --task TASK-001 \
  --to-agent validation-engineer \
  --notes "Ready for testing"
```

## Context Optimization

### Generate Agent Views (Automatic)
```bash
# Reduces context from 50KB to 2-5KB per agent
python scripts/generate-agent-views.py --all
```

### Check Context Usage
```bash
# View what each agent loads
cat .claude/context-loader.yaml | grep -A5 "implementation-specialist"
```

## Monitoring Progress

### Overall Status
```bash
python scripts/agent-task-manager.py status
```

### Phase Progress
```bash
cat .agent-system/registry/milestones.md
```

### Active Agents
```bash
ls -la .agent-system/sessions/active/
```

### Recent Changes
```bash
tail -n 20 .agent-system/agents/*/changelog.md
```

## Common Commands

### PRP Commands
```
/prp-planning-create     # Create planning PRP
/prp-base-execute       # Execute PRP
/api-contract-define    # Define API contracts
/user-story-rapid       # Create user stories
```

### Review Commands
```
/review-general         # General code review
/review-staged-unstaged # Review git changes
/refactor-simple        # Simple refactoring
```

### Git Commands
```
/smart-commit           # Intelligent commit
/create-pr             # Create pull request
/conflict-resolver-general # Resolve conflicts
```

## The 10 Agents Quick Reference

| # | Agent | Primary Role | Key Commands |
|---|-------|--------------|--------------|
| 1 | **PRP Orchestrator** | Coordinate all agents | `/prime-core`, `/prp-planning-create` |
| 2 | **Business Analyst** | Requirements & metrics | `/user-story-rapid`, `/task-list-init` |
| 3 | **Context Researcher** | Research & investigation | `/review-general`, `/debug-RCA` |
| 4 | **Implementation Specialist** | Code development | `/prp-base-execute`, `/prp-task-execute` |
| 5 | **Validation Engineer** | Testing & QA | `/review-staged-unstaged` |
| 6 | **Integration Architect** | System design | `/api-contract-define`, `/prp-spec-create` |
| 7 | **Documentation Curator** | Documentation | `/onboarding`, `/create-pr` |
| 8 | **Security Auditor** | Security & compliance | `/review-general` |
| 9 | **Performance Optimizer** | Performance tuning | `/refactor-simple` |
| 10 | **DevOps Engineer** | Deployment & infra | `/smart-commit`, `/create-pr` |

## Phase Validation Gates

### ✅ Phase 0: Initialization
```
□ Context loaded
□ Agents activated
□ Project scope defined
```

### ✅ Phase 1: Discovery
```
□ Requirements documented
□ User stories created
□ Success metrics defined
```

### ✅ Phase 2: Architecture
```
□ System design complete
□ API contracts defined
□ Security requirements set
```

### ✅ Phase 3: Planning
```
□ Implementation PRP created
□ Tasks estimated
□ Dependencies mapped
```

### ✅ Phase 4: Implementation
```
□ Code complete
□ Tests passing (>80% coverage)
□ Security scan clean
```

### ✅ Phase 5: Deployment Prep
```
□ Documentation complete
□ Infrastructure ready
□ Monitoring configured
```

### ✅ Phase 6: Go-Live
```
□ Deployed to production
□ Health checks passing
□ Metrics tracking
```

### ✅ Phase 7: Optimization
```
□ Performance analyzed
□ Optimizations applied
□ Lessons documented
```

## Emergency Procedures

### 🚨 Hotfix
```
"PRP Orchestrator, initiate hotfix workflow for: [critical issue]"
```

### 🔴 All Hands
```
"All agents, emergency collaboration on: [crisis description]"
```

### ↩️ Rollback
```
"DevOps Engineer, emergency rollback to: [version]"
```

### 🔍 Root Cause Analysis
```
"Context Researcher, perform root cause analysis on: [incident]"
```

## File Locations

### Core System
- Task Registry: `.agent-system/registry/tasks.json`
- Agent Contexts: `.agent-system/agents/*/context.json`
- Session Locks: `.agent-system/sessions/active/*.lock`
- Handoffs: `.agent-system/sync/handoffs.json`

### Documentation
- PRPs: `PRPs/planning/*.md`, `PRPs/architecture/*.md`
- Agent Views: `PRPs/.cache/agent-views/*.md`
- Task Briefs: `PRPs/.cache/task-briefs/*.md`

### Code
- Features: `workspace/features/*/`
- Shared: `workspace/shared/`
- Tests: `workspace/features/*/tests/`

### Reports
- Daily: `reports/daily/*.md`
- Metrics: `reports/metrics/*.json`
- Phase Reports: `reports/phase-completions/*.md`

## Tips for Success

1. **Always start with Phase 0** - Proper initialization prevents problems
2. **Trust the orchestrator** - It knows the optimal agent sequence
3. **Use lightweight views** - Never load full PRPs for agents
4. **Clear handoffs** - Include notes and next actions
5. **Monitor sync files** - Check for broadcasts and conflicts
6. **Validate at gates** - Don't skip phase validations
7. **Document decisions** - Update reports and changelogs

## Need Help?

- **Documentation**: See `AGENT-ORCHESTRATION.md`
- **Commands**: Check `.claude/commands/**/*.md`
- **Agent Roles**: Review `.claude/agents/*.md`
- **Troubleshooting**: See `WORKSPACE-SETUP-SUMMARY.md`

---

**Remember:** Let the orchestrator coordinate. Focus agents on their specialties. Keep context minimal. Validate at every phase.

**Ready?** Start with `/prime-core` in Claude Code! 🚀
