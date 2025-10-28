# Documentation Index

Complete guide to all documentation in this framework. Start here to find what you need.

## 🚀 Getting Started

**New to the framework?** Follow this path:

1. **[README.md](README.md)** - Start here for overview and quick orientation
2. **[QUICK-START.md](QUICK-START.md)** - 15-minute setup guide
3. **[FRAMEWORK-USAGE-GUIDE.md](FRAMEWORK-USAGE-GUIDE.md)** - Comprehensive usage guide with examples
4. **[VISUAL-REFERENCE.md](VISUAL-REFERENCE.md)** - Quick visual reference while working

## 📚 Core Documentation

### Framework Overview
- **[README.md](README.md)** - Repository overview, structure, prerequisites
- **[QUICK-START.md](QUICK-START.md)** - Fast setup and first project guide
- **[CLAUDE.md](CLAUDE.md)** - Framework architecture, agent system, patterns
- **[ARCHON-INTEGRATION.md](ARCHON-INTEGRATION.md)** - Optional MCP server for enhanced features
- **[BMAD-INTEGRATION-PLAN.md](BMAD-INTEGRATION-PLAN.md)** - BMAD story-driven development integration

### Usage Guides
- **[FRAMEWORK-USAGE-GUIDE.md](FRAMEWORK-USAGE-GUIDE.md)** - Complete usage guide
  - Quick start (5 min)
  - PRP lifecycle (detailed)
  - Task management (full reference)
  - Context optimization (3 layers)
  - Progress tracking (monitoring)
  - Common workflows (examples)
  - Troubleshooting (solutions)

### Visual References
- **[VISUAL-REFERENCE.md](VISUAL-REFERENCE.md)** - Quick visual reference
  - Directory structure tree
  - Flow diagrams
  - Command quick reference
  - Status indicators
  - Agent matrix

### Agent Coordination
- **[AGENT-ORCHESTRATION.md](AGENT-ORCHESTRATION.md)** - Master orchestration process
  - Phase-based execution (7 phases)
  - Agent interaction patterns
  - Workflow variations (standard, hotfix, research)
  - Command integration matrix

## 📋 PRP Documentation

### PRP Methodology
- **[PRPs/README.md](PRPs/README.md)** - PRP methodology overview
  - What is a PRP
  - Structure and components
  - Agent assignments
  - Best practices

### PRP Lifecycle
- **[PRPs/PRP-LIFECYCLE.md](PRPs/PRP-LIFECYCLE.md)** - Lifecycle management
  - Directory structure
  - 4 lifecycle stages
  - Stage transitions
  - Progress tracking
  - Context optimization per stage

### PRP Templates
Located in `PRPs/templates/`:
- **prp_planning.md** - Planning-focused template (Business Analyst)
- **prp_base.md** - Standard implementation template
- **prp_base_typescript.md** - TypeScript-specific template
- **prp_spec.md** - Technical specification template
- **prp_task.md** - Single task template
- **bmad_story.md** - BMAD story template with acceptance criteria
- **bmad_epic.md** - BMAD epic template with story breakdown

## 🤖 Agent System

### Agent Configuration
- **[.claude/context-loader.yaml](.claude/context-loader.yaml)** - Context loading rules
  - Per-agent token limits
  - Conditional loading rules
  - Never-load exclusions

### Agent Definitions
Located in `.claude/agents/`:
- Business Analyst
- Context Researcher
- Implementation Specialist
- Validation Engineer
- Integration Architect
- Documentation Curator
- Security Auditor
- Performance Optimizer
- DevOps Engineer
- PRP Orchestrator
- Scrum Master (BMAD integration)

## 🔧 Technical References

### Scripts
- **[scripts/agent-task-manager.py](scripts/agent-task-manager.py)** - Task lifecycle CLI
- **[scripts/generate-agent-views.py](scripts/generate-agent-views.py)** - Context optimization
- **[scripts/archon-sync.py](scripts/archon-sync.py)** - Archon MCP synchronization (optional)
- **[scripts/bmad-integration.py](scripts/bmad-integration.py)** - BMAD-PRPs integration manager
- **[scripts/bmad-orchestrator.py](scripts/bmad-orchestrator.py)** - BMAD workflow coordinator
- **[scripts/story-dev.py](scripts/story-dev.py)** - Story-based development workflow
- **[scripts/setup-workspace.py](scripts/setup-workspace.py)** - Initial setup
- **[scripts/complete-setup.py](scripts/complete-setup.py)** - Workspace refresh

### Setup Scripts
- **[init-agent-workspace.sh](init-agent-workspace.sh)** - Bash setup script

### Configuration
- **[.gitignore](.gitignore)** - Git exclusions (protects cache, sessions)
- **[stacks/.stack-detection.yaml](stacks/.stack-detection.yaml)** - Technology detection

## 📖 Framework-Specific CLAUDE.md Files

Located in `claude_md_files/`:
- **CLAUDE-PYTHON-BASIC.md** - Python project guidance
- **CLAUDE-NODE.md** - Node.js project guidance
- **CLAUDE-REACT.md** - React project guidance
- **CLAUDE-NEXTJS-15.md** - Next.js 15 project guidance
- **CLAUDE-ASTRO.md** - Astro project guidance
- **CLAUDE-JAVA-MAVEN.md** - Java Maven project guidance
- **CLAUDE-JAVA-GRADLE.md** - Java Gradle project guidance

## 📊 Session Summaries

Located in `docs/`:
- **SESSION_SUMMARY_2025-10-01-00-00.md** - Framework documentation & PRP lifecycle enhancement

## 🎯 By Task/Goal

### I want to...

#### Start a new project
→ [QUICK-START.md](QUICK-START.md) → [FRAMEWORK-USAGE-GUIDE.md](FRAMEWORK-USAGE-GUIDE.md) → Section "Starting a Fresh Project"

#### Understand the PRP methodology
→ [PRPs/README.md](PRPs/README.md) → [PRPs/PRP-LIFECYCLE.md](PRPs/PRP-LIFECYCLE.md)

#### Track progress on PRPs
→ [PRPs/PRP-LIFECYCLE.md](PRPs/PRP-LIFECYCLE.md) → Section "Monitoring Progress"

#### Optimize context loading
→ [CLAUDE.md](CLAUDE.md) → Section "Context Minimization Strategy"
→ [FRAMEWORK-USAGE-GUIDE.md](FRAMEWORK-USAGE-GUIDE.md) → Section "Context Optimization"

#### Manage tasks
→ [FRAMEWORK-USAGE-GUIDE.md](FRAMEWORK-USAGE-GUIDE.md) → Section "Task Management"

#### Understand agent coordination
→ [AGENT-ORCHESTRATION.md](AGENT-ORCHESTRATION.md)
→ [CLAUDE.md](CLAUDE.md) → Section "Agent System Overview"

#### Find a specific command
→ [VISUAL-REFERENCE.md](VISUAL-REFERENCE.md) → Section "Command Quick Reference"

#### Troubleshoot an issue
→ [FRAMEWORK-USAGE-GUIDE.md](FRAMEWORK-USAGE-GUIDE.md) → Section "Troubleshooting"

#### Follow a workflow example
→ [FRAMEWORK-USAGE-GUIDE.md](FRAMEWORK-USAGE-GUIDE.md) → Section "Common Workflows"

#### See visual diagrams
→ [VISUAL-REFERENCE.md](VISUAL-REFERENCE.md)

#### Set up Archon MCP (optional)
→ [ARCHON-INTEGRATION.md](ARCHON-INTEGRATION.md) → Installation & Setup

#### Use knowledge base search
→ [ARCHON-INTEGRATION.md](ARCHON-INTEGRATION.md) → Knowledge Base Integration

#### Use BMAD story-driven development
→ [BMAD-INTEGRATION-PLAN.md](BMAD-INTEGRATION-PLAN.md) → Integration Architecture

#### Create BMAD stories from PRD
→ [.claude/agents/scrum-master.md](.claude/agents/scrum-master.md) → Scrum Master Agent

#### Work on BMAD stories
→ [scripts/story-dev.py](scripts/story-dev.py) → Story Development Workflow

## 📁 Directory Documentation

### PRPs/
```
PRPs/
├── README.md                    # PRP methodology
├── PRP-LIFECYCLE.md            # Lifecycle management
├── planning/
│   ├── backlog/                # Planned PRPs
│   ├── active/                 # Being refined
│   └── completed/              # Ready for implementation
├── implementation/
│   ├── in-progress/            # Active coding
│   └── completed/              # Deployed
├── architecture/               # System designs
├── contracts/                  # API specifications
├── security/                   # Security requirements
├── templates/                  # PRP templates
│   ├── prp_planning.md
│   ├── prp_base.md
│   ├── prp_base_typescript.md
│   ├── prp_spec.md
│   ├── prp_task.md
│   ├── bmad_story.md          # BMAD story template
│   └── bmad_epic.md           # BMAD epic template
└── .cache/                     # Generated context
    ├── agent-views/            # Per-agent views (2-5KB)
    ├── task-briefs/            # Task-specific context
    └── story-views/            # BMAD story views (3KB)
```

### .agent-system/
```
.agent-system/
├── registry/
│   ├── tasks.json              # Central task registry
│   ├── dependencies.json       # Task dependencies
│   ├── milestones.md          # Project milestones
│   ├── stories.json           # BMAD story registry
│   └── epics.json             # BMAD epic registry
├── sessions/
│   ├── active/                 # Current sessions (*.lock)
│   └── history/                # Completed sessions
├── agents/                     # 11 agent directories (includes scrum-master)
│   └── [agent-name]/
│       ├── context.json        # Agent config
│       ├── tasks.json          # Assigned tasks
│       └── changelog.md        # Activity log
└── sync/
    ├── broadcasts.json         # System-wide updates
    ├── handoffs.json           # Agent-to-agent transfers
    ├── conflicts.json          # Merge tracking
    └── bmad-sync.json         # BMAD integration status
```

### workspace/
```
workspace/
├── features/                   # Feature development
│   └── [feature]/
│       ├── src/
│       ├── tests/
│       ├── docs/
│       └── .meta/
├── fixes/                      # Hotfixes
└── shared/                     # Reusable components
```

### docs/ (BMAD Integration)
```
docs/
├── prd.md                      # Product Requirements Document
├── architecture.md             # System architecture
├── epics/                      # BMAD epics
│   └── EPIC-*.md
├── stories/                    # BMAD stories
│   └── STORY-*.md
├── story-notes/                # Story development notes
└── qa/
    ├── assessments/            # Quality assessments
    └── gates/                  # Quality gates
```

## 🔍 Search Index

### Key Concepts
- **PRP**: [PRPs/README.md](PRPs/README.md), [PRPs/PRP-LIFECYCLE.md](PRPs/PRP-LIFECYCLE.md)
- **Agent**: [CLAUDE.md](CLAUDE.md), [AGENT-ORCHESTRATION.md](AGENT-ORCHESTRATION.md)
- **Context Optimization**: [CLAUDE.md](CLAUDE.md), [FRAMEWORK-USAGE-GUIDE.md](FRAMEWORK-USAGE-GUIDE.md)
- **Task Management**: [FRAMEWORK-USAGE-GUIDE.md](FRAMEWORK-USAGE-GUIDE.md)
- **Lifecycle**: [PRPs/PRP-LIFECYCLE.md](PRPs/PRP-LIFECYCLE.md)
- **BMAD Integration**: [BMAD-INTEGRATION-PLAN.md](BMAD-INTEGRATION-PLAN.md), [scripts/bmad-orchestrator.py](scripts/bmad-orchestrator.py)
- **Story Development**: [scripts/story-dev.py](scripts/story-dev.py), [.claude/agents/scrum-master.md](.claude/agents/scrum-master.md)

### Commands
- **create task**: [FRAMEWORK-USAGE-GUIDE.md](FRAMEWORK-USAGE-GUIDE.md) → "Task Management"
- **claim task**: [FRAMEWORK-USAGE-GUIDE.md](FRAMEWORK-USAGE-GUIDE.md) → "Claiming Tasks"
- **generate views**: [FRAMEWORK-USAGE-GUIDE.md](FRAMEWORK-USAGE-GUIDE.md) → "Context Optimization"
- **check status**: [VISUAL-REFERENCE.md](VISUAL-REFERENCE.md) → "Command Quick Reference"
- **import BMAD planning**: [scripts/bmad-orchestrator.py](scripts/bmad-orchestrator.py) → import-planning
- **sync stories**: [scripts/bmad-integration.py](scripts/bmad-integration.py) → sync-stories
- **work on story**: [scripts/story-dev.py](scripts/story-dev.py) → work-on-story

### Workflows
- **Standard Feature**: [FRAMEWORK-USAGE-GUIDE.md](FRAMEWORK-USAGE-GUIDE.md) → "Common Workflows"
- **Hotfix**: [FRAMEWORK-USAGE-GUIDE.md](FRAMEWORK-USAGE-GUIDE.md) → "Common Workflows"
- **Research**: [FRAMEWORK-USAGE-GUIDE.md](FRAMEWORK-USAGE-GUIDE.md) → "Common Workflows"
- **BMAD Story-Driven**: [BMAD-INTEGRATION-PLAN.md](BMAD-INTEGRATION-PLAN.md) → "Unified Workflow"

### Troubleshooting
- **Context too large**: [FRAMEWORK-USAGE-GUIDE.md](FRAMEWORK-USAGE-GUIDE.md) → "Troubleshooting"
- **PRP stuck**: [FRAMEWORK-USAGE-GUIDE.md](FRAMEWORK-USAGE-GUIDE.md) → "Troubleshooting"
- **Too many tasks**: [FRAMEWORK-USAGE-GUIDE.md](FRAMEWORK-USAGE-GUIDE.md) → "Troubleshooting"
- **Session locks**: [FRAMEWORK-USAGE-GUIDE.md](FRAMEWORK-USAGE-GUIDE.md) → "Troubleshooting"

## 💡 Documentation Tips

### For Quick Reference
Use [VISUAL-REFERENCE.md](VISUAL-REFERENCE.md) - it has:
- Directory tree with icons
- Flow diagrams
- Command cheat sheet
- Status indicators

### For Deep Understanding
Read in order:
1. [CLAUDE.md](CLAUDE.md) - Architecture
2. [AGENT-ORCHESTRATION.md](AGENT-ORCHESTRATION.md) - Coordination
3. [PRPs/README.md](PRPs/README.md) - PRP methodology
4. [PRPs/PRP-LIFECYCLE.md](PRPs/PRP-LIFECYCLE.md) - Lifecycle

### For Practical Work
Keep open:
- [FRAMEWORK-USAGE-GUIDE.md](FRAMEWORK-USAGE-GUIDE.md) - Step-by-step examples
- [VISUAL-REFERENCE.md](VISUAL-REFERENCE.md) - Quick commands

### For Setup
Follow:
1. [README.md](README.md) → "Prerequisites"
2. [QUICK-START.md](QUICK-START.md) → "First-Time Setup"
3. [FRAMEWORK-USAGE-GUIDE.md](FRAMEWORK-USAGE-GUIDE.md) → "Quick Start"

## 🔄 Documentation Status

| Document | Status | Last Updated | Lines |
|----------|--------|--------------|-------|
| README.md | ✅ Updated | 2025-10-01 | 279 |
| QUICK-START.md | ✅ Complete | 2024-09-10 | 203 |
| CLAUDE.md | ✅ Updated | 2025-10-14 | 412 |
| AGENT-ORCHESTRATION.md | ✅ Complete | 2024-09-10 | 757 |
| FRAMEWORK-USAGE-GUIDE.md | ✅ New | 2025-10-01 | 1,087 |
| VISUAL-REFERENCE.md | ✅ New | 2025-10-01 | 564 |
| PRPs/README.md | ✅ Complete | 2024-09-10 | 438 |
| PRPs/PRP-LIFECYCLE.md | ✅ New | 2025-10-01 | 687 |
| ARCHON-INTEGRATION.md | ✅ New | 2025-10-14 | 1,087 |
| BMAD-INTEGRATION-PLAN.md | ✅ New | 2025-10-14 | 500+ |
| DOCUMENTATION-INDEX.md | ✅ Updated | 2025-10-14 | 360+ |

## 📝 Contributing to Documentation

When adding/updating documentation:

1. **Update this index** if adding new files
2. **Follow existing structure** (markdown, code examples)
3. **Add to appropriate section** in this index
4. **Update "Last Updated"** in status table
5. **Create session summary** in `docs/`

## 🎯 Most Important Documents

For daily work, these are essential:

1. **[FRAMEWORK-USAGE-GUIDE.md](FRAMEWORK-USAGE-GUIDE.md)** - Your main reference
2. **[VISUAL-REFERENCE.md](VISUAL-REFERENCE.md)** - Quick lookups
3. **[PRPs/PRP-LIFECYCLE.md](PRPs/PRP-LIFECYCLE.md)** - PRP management

For understanding the system:

1. **[CLAUDE.md](CLAUDE.md)** - Core concepts
2. **[AGENT-ORCHESTRATION.md](AGENT-ORCHESTRATION.md)** - How agents work together

## 📞 Quick Links

- **Setup**: [QUICK-START.md](QUICK-START.md)
- **Usage**: [FRAMEWORK-USAGE-GUIDE.md](FRAMEWORK-USAGE-GUIDE.md)
- **Commands**: [VISUAL-REFERENCE.md](VISUAL-REFERENCE.md) → "Command Quick Reference"
- **Troubleshooting**: [FRAMEWORK-USAGE-GUIDE.md](FRAMEWORK-USAGE-GUIDE.md) → "Troubleshooting"
- **Agents**: [AGENT-ORCHESTRATION.md](AGENT-ORCHESTRATION.md)
- **PRPs**: [PRPs/PRP-LIFECYCLE.md](PRPs/PRP-LIFECYCLE.md)

---

**Remember**: Start with README.md, use FRAMEWORK-USAGE-GUIDE.md for work, reference VISUAL-REFERENCE.md for quick lookups.

**Context is king, but organized documentation is emperor!** 📚✨
