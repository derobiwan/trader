# Visual Reference Guide

Quick visual reference for the framework's structure, flow, and commands.

## Directory Structure at a Glance

```
PRPs-agentic-eng/
│
├── 📚 Core Documentation
│   ├── README.md                    # Repository overview
│   ├── FRAMEWORK-USAGE-GUIDE.md     # Complete usage guide ⭐
│   ├── QUICK-START.md               # Fast setup
│   ├── CLAUDE.md                    # Framework architecture
│   └── AGENT-ORCHESTRATION.md       # Agent coordination
│
├── 📋 PRPs/ (Product Requirement Prompts)
│   ├── planning/
│   │   ├── backlog/      📦 Planned (not started)
│   │   ├── active/       🔄 Being refined
│   │   └── completed/    ✅ Ready for implementation
│   │
│   ├── implementation/
│   │   ├── in-progress/  👷 Active coding
│   │   └── completed/    ✅ Deployed
│   │
│   ├── architecture/     🏗️  System designs
│   ├── contracts/        📜 API specifications
│   ├── security/         🔒 Security requirements
│   ├── templates/        📝 PRP templates
│   │
│   ├── .cache/           🗂️  Context optimization
│   │   ├── agent-views/     # 2-5KB per agent (vs 50KB+ full)
│   │   └── task-briefs/     # Task-specific context
│   │
│   ├── PRP-LIFECYCLE.md  📖 Lifecycle documentation
│   └── README.md         📖 PRP methodology
│
├── 🤖 .agent-system/ (Coordination)
│   ├── registry/
│   │   ├── tasks.json       # Central task registry
│   │   ├── dependencies.json # Task dependencies
│   │   └── milestones.md    # Project milestones
│   │
│   ├── sessions/
│   │   ├── active/          # Current agent sessions (*.lock)
│   │   └── history/         # Completed sessions
│   │
│   ├── agents/              # One directory per agent (10 total)
│   │   ├── business-analyst/
│   │   ├── context-researcher/
│   │   ├── implementation-specialist/
│   │   ├── validation-engineer/
│   │   ├── integration-architect/
│   │   ├── documentation-curator/
│   │   ├── security-auditor/
│   │   ├── performance-optimizer/
│   │   ├── devops-engineer/
│   │   └── orchestrator/
│   │       ├── context.json     # Agent config
│   │       ├── tasks.json       # Assigned tasks
│   │       └── changelog.md     # Activity log
│   │
│   └── sync/
│       ├── broadcasts.json  # System-wide updates
│       ├── handoffs.json    # Agent-to-agent transfers
│       └── conflicts.json   # Merge tracking (gitignored)
│
├── 💼 workspace/ (Implementation)
│   ├── features/        # Feature development
│   │   └── [feature]/
│   │       ├── src/
│   │       ├── tests/
│   │       ├── docs/
│   │       └── .meta/
│   │
│   ├── fixes/           # Hotfixes and patches
│   └── shared/          # Reusable components
│       ├── libraries/
│       └── contracts/
│
├── 🔧 scripts/
│   ├── agent-task-manager.py      # Task lifecycle CLI
│   ├── generate-agent-views.py    # Context optimization
│   ├── setup-workspace.py         # Initialization
│   └── complete-setup.py          # Workspace refresh
│
├── 🚀 integration/
│   ├── ci-cd/           # Pipeline configs
│   └── environments/    # Deployment targets
│
├── 📊 reports/
│   ├── daily/           # Daily status
│   ├── phase-completions/  # Milestone reports
│   └── metrics/         # Performance data
│
├── 🎛️ .claude/
│   ├── context-loader.yaml  # Per-agent context rules
│   └── agents/              # Agent definitions
│
└── 📚 stacks/
    └── .stack-detection.yaml  # Technology detection
```

## PRP Lifecycle Flow

```
┌─────────────┐
│   Backlog   │  📦 Planned features
│             │     - Not yet started
└──────┬──────┘     - Waiting for capacity
       │
       │ Move when starting
       ↓
┌─────────────┐
│   Active    │  🔄 Requirements gathering
│  Planning   │     - Business Analyst refines
└──────┬──────┘     - Context Researcher investigates
       │
       │ Exit: Requirements complete
       ↓
┌─────────────┐
│  Completed  │  ✅ Ready for architecture
│  Planning   │     - Integration Architect designs
└──────┬──────┘     - Security Auditor reviews
       │
       │ Architecture designed
       ↓
┌─────────────┐
│In-Progress  │  👷 Active implementation
│    Impl     │     - Implementation Specialist codes
└──────┬──────┘     - Validation Engineer tests
       │
       │ Exit: Code complete, deployed
       ↓
┌─────────────┐
│  Completed  │  ✅ Archived for reference
│    Impl     │     - Documentation complete
└─────────────┘     - Monitoring active
```

## Context Optimization Flow

```
┌──────────────────────────────────────┐
│  Full PRP: payment-feature.md       │
│  Size: 50KB                          │
│  Contains: All sections, all agents  │
└────────────┬─────────────────────────┘
             │
             │ generate-agent-views.py --all
             ↓
    ┌────────┴────────┐
    │  Agent Views    │
    │  (Extracted)    │
    └────────┬────────┘
             │
    ┌────────┴──────────────────────────────────┐
    │                                            │
    ↓                                            ↓
┌─────────────────────┐              ┌────────────────────────┐
│ business-analyst.md │              │ implementation-spec.md │
│ Size: 2KB           │              │ Size: 4KB              │
│                     │              │                        │
│ Sections:           │              │ Sections:              │
│ - Goal              │              │ - Tech Requirements    │
│ - Why               │              │ - API Contracts        │
│ - Success Criteria  │              │ - Implementation       │
└─────────────────────┘              └────────────────────────┘
             │                                    │
             │ context-loader.yaml                │
             │ max_context_tokens: 8000           │
             ↓                                    ↓
    ┌────────────────┐              ┌────────────────────┐
    │ Business       │              │ Implementation     │
    │ Analyst Agent  │              │ Specialist Agent   │
    │                │              │                    │
    │ Loads: 2KB     │              │ Loads: 4KB         │
    └────────────────┘              └────────────────────┘

Result: 90-95% context reduction per agent
```

## Task Management Flow

```
┌─────────────┐
│   Create    │  python scripts/agent-task-manager.py create
│    Task     │  --title "Feature X" --priority high
└──────┬──────┘
       │  Returns: TASK-001
       │  Status: pending
       ↓
┌─────────────┐
│    Claim    │  python scripts/agent-task-manager.py claim
│    Task     │  --agent implementation-specialist --task TASK-001
└──────┬──────┘
       │  Creates: .agent-system/sessions/active/claude-*.lock
       │  Status: in-progress
       ↓
┌─────────────┐
│    Work     │  Agent implements feature
│   On Task   │  Updates: workspace/features/feature-x/
└──────┬──────┘
       │
       ├─────────────────┐
       │                 │
       ↓                 ↓
┌─────────────┐   ┌─────────────┐
│   Handoff   │   │  Complete   │
└──────┬──────┘   └──────┬──────┘
       │                 │
       │  To: validation-engineer   │  Status: completed
       │  Notes: "Ready for testing"│  Moves lock to history/
       ↓                 ↓
┌─────────────┐   ┌─────────────┐
│Next Agent   │   │   Archived  │
│  Claims     │   │             │
└─────────────┘   └─────────────┘
```

## Agent Specialization Matrix

```
┌──────────────────────┬──────────────────┬────────────────────┬─────────────┐
│ Agent                │ Primary Role     │ PRP Sections       │ Context Size│
├──────────────────────┼──────────────────┼────────────────────┼─────────────┤
│ 🎯 Orchestrator      │ Coordination     │ All (overview)     │ 12KB        │
│ 📊 Business Analyst  │ Requirements     │ Goal, Why, Success │ 2KB         │
│ 🔍 Context Researcher│ Investigation    │ Context, Research  │ 10KB        │
│ 💻 Implementation    │ Coding           │ Tech, API, Impl    │ 8KB         │
│ ✅ Validation        │ Testing          │ Tests, Acceptance  │ 8KB         │
│ 🏗️  Integration Arch │ Design           │ Architecture, APIs │ 10KB        │
│ 📝 Documentation     │ Docs             │ Doc Requirements   │ 6KB         │
│ 🔒 Security Auditor  │ Security         │ Security, Threats  │ 8KB         │
│ ⚡ Performance Opt   │ Optimization     │ Performance, Scale │ 8KB         │
│ 🚀 DevOps Engineer   │ Deployment       │ Deploy, Infra      │ 8KB         │
└──────────────────────┴──────────────────┴────────────────────┴─────────────┘
```

## Command Quick Reference

### Setup & Initialization
```bash
# First time setup
./init-agent-workspace.sh

# Verify setup
python scripts/agent-task-manager.py status
ls .agent-system/agents

# In Claude Code
/prime-core
"Load AGENT-ORCHESTRATION.md and initialize all agents"
```

### PRP Management
```bash
# Create new PRP
cp PRPs/templates/prp_planning.md PRPs/planning/backlog/feature.md

# Move through lifecycle
mv PRPs/planning/backlog/feature.md PRPs/planning/active/feature.md
mv PRPs/planning/active/feature.md PRPs/planning/completed/feature.md
mv PRPs/implementation/in-progress/feature.md PRPs/implementation/completed/feature.md

# View status
ls PRPs/planning/active/
ls PRPs/implementation/in-progress/
```

### Task Management
```bash
# Create task
python scripts/agent-task-manager.py create \
  --title "Implement feature" \
  --priority high \
  --hours 8

# Claim task
python scripts/agent-task-manager.py claim \
  --agent implementation-specialist \
  --task TASK-001

# Handoff task
python scripts/agent-task-manager.py handoff \
  --task TASK-001 \
  --to-agent validation-engineer \
  --notes "Ready for testing"

# Complete task
python scripts/agent-task-manager.py complete \
  --task TASK-001 \
  --notes "Feature deployed"

# List tasks
python scripts/agent-task-manager.py list
python scripts/agent-task-manager.py list --status in-progress
python scripts/agent-task-manager.py list --agent implementation-specialist

# View status
python scripts/agent-task-manager.py status
python scripts/agent-task-manager.py status --task TASK-001
```

### Context Optimization
```bash
# Generate all agent views (DO THIS AFTER PRP CHANGES!)
python scripts/generate-agent-views.py --all

# Generate for specific agent
python scripts/generate-agent-views.py --agent implementation-specialist

# Generate task brief
python scripts/generate-agent-views.py --task TASK-001

# Clean and regenerate
python scripts/generate-agent-views.py --clean --all

# Check sizes
ls -lh PRPs/.cache/agent-views/
ls -lh PRPs/.cache/task-briefs/
```

### Progress Tracking
```bash
# Quick dashboard
echo "Backlog: $(ls PRPs/planning/backlog/ 2>/dev/null | wc -l)"
echo "Active: $(ls PRPs/planning/active/ 2>/dev/null | wc -l)"
echo "In Progress: $(ls PRPs/implementation/in-progress/ 2>/dev/null | wc -l)"

# Task statistics
python scripts/agent-task-manager.py status

# Active agents
ls .agent-system/sessions/active/

# Agent activity
tail .agent-system/agents/*/changelog.md

# Handoff queue
cat .agent-system/sync/handoffs.json
```

## Status Indicators

### PRP Status (by location)
- 📦 **Backlog**: `PRPs/planning/backlog/` - Planned but not started
- 🔄 **Active Planning**: `PRPs/planning/active/` - Requirements being refined
- ✅ **Planning Complete**: `PRPs/planning/completed/` - Ready for architecture
- 👷 **In Progress**: `PRPs/implementation/in-progress/` - Being implemented
- ✅ **Completed**: `PRPs/implementation/completed/` - Deployed and done

### Task Status (from registry)
- ⏸️  **pending**: Not yet claimed
- 🔄 **in-progress**: Agent actively working
- ✅ **completed**: Finished and archived
- 🔴 **blocked**: Waiting on dependency

### Task Priority
- 🔴 **critical**: Emergency/hotfix
- 🟠 **high**: Important feature
- 🟡 **medium**: Standard work
- 🟢 **low**: Nice-to-have

## Validation Gates by Phase

### Phase 1: Planning
```
✓ Requirements documented
✓ User stories complete
✓ Success metrics defined
✓ Stakeholder approval
```

### Phase 2: Architecture
```
✓ Architecture designed
✓ API contracts defined
✓ Security requirements integrated
✓ Performance targets set
```

### Phase 4: Implementation
```
✓ Code complete
✓ Tests passing (>80% coverage)
✓ Security scan clean
✓ Performance validated
```

### Phase 6: Deployment
```
✓ Production deployment successful
✓ Monitoring active
✓ Documentation complete
✓ Stakeholders notified
```

## Common Patterns

### Standard Feature
```
Backlog → Active Planning → Completed Planning
    ↓
Architecture Design
    ↓
In-Progress Implementation → Completed Implementation
```

### Hotfix
```
Emergency Issue → Context Research → Quick Fix → Test → Deploy
(Compressed timeline: 2-4 hours)
```

### Research
```
Investigation Request → Context Researcher → Findings Report → Decision
```

## Key Files to Track

| File | Purpose | Update When |
|------|---------|-------------|
| `.agent-system/registry/tasks.json` | Task registry | Task created/claimed/completed |
| `.agent-system/sessions/active/*.lock` | Active sessions | Agent claims/releases task |
| `PRPs/.cache/agent-views/*.md` | Agent context | PRP created/updated |
| `.agent-system/sync/handoffs.json` | Task handoffs | Task transferred between agents |
| `.agent-system/registry/milestones.md` | Project milestones | Phase completed |

## Remember

- ✅ Move PRPs forward through lifecycle
- ✅ Regenerate agent views after PRP changes
- ✅ Complete tasks before starting new ones
- ✅ Check context sizes regularly
- ✅ One active PRP per agent
- ✅ Link tasks to source PRPs
- ✅ Follow validation gates

**Context is king, but optimized context is emperor!**
