# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 🎯 Repository Overview

This repository contains a **Distributed Agent Coordination Framework** used to build an **LLM-Powered Cryptocurrency Trading System**. The framework enables 10 specialized AI agents to collaborate on building production-ready code with minimal context loading.

**Current Project**: Automated cryptocurrency trading system that leverages Large Language Models to analyze market data every 3 minutes and execute trades based on technical analysis.

## 📁 Repository Structure

```
.agent-system/              # Agent coordination layer (task registry, sessions, sync)
PRPs/                       # Product Requirement Prompts (planning, architecture, contracts)
PRD/                        # Product Requirements Documents
  └── llm_crypto_trading_prd.md  # Main PRD for trading system
workspace/
  ├── features/             # Feature-scoped implementation areas
  ├── fixes/                # Hotfixes and patches
  └── shared/               # Reusable libraries, utilities, and contracts
scripts/                    # Automation helpers (setup, task manager, agent views)
integration/                # Deployment targets, CI/CD wiring, monitoring hooks
reports/                    # Daily notes, phase summaries, metrics (gitignored)
.claude/                    # Agent personas, commands, context loading rules
```

## 🚀 Quick Start

### First-Time Setup

```bash
# Bootstrap the agent workspace structure
./init-agent-workspace.sh

# Verify setup
python scripts/agent-task-manager.py status
ls .agent-system/agents
ls PRPs/.cache/agent-views
```

### Starting Work on the Trading System

```bash
# In Claude Code, initialize agents
/prime-core
"Load AGENT-ORCHESTRATION.md and initialize all agents for: LLM Crypto Trading System"

# Orchestrator coordinates workflow
"PRP Orchestrator, initiate standard workflow for the trading system"
```

## 🛠️ Development Commands

### Agent Task Management

**Create and Manage Tasks**:
```bash
# Create new task
python scripts/agent-task-manager.py create \
  --title "Implement feature X" \
  --priority high \
  --hours 8

# Claim task
python scripts/agent-task-manager.py claim \
  --agent implementation-specialist \
  --task TASK-001

# Complete task
python scripts/agent-task-manager.py complete \
  --task TASK-001 \
  --notes "Implementation complete, tests passing"

# Check status
python scripts/agent-task-manager.py status
python scripts/agent-task-manager.py list --status in-progress
```

### Context Generation (Critical)

```bash
# ALWAYS regenerate agent views after PRP changes
python scripts/generate-agent-views.py --all

# Generate specific agent view
python scripts/generate-agent-views.py --agent implementation-specialist

# Generate task brief
python scripts/generate-agent-views.py --task TASK-001

# Clean stale cache
python scripts/generate-agent-views.py --clean --all
```

### PRP Execution

```bash
# Orchestrator coordinates PRP execution
/prp-planning-create [feature description]
/prp-base-execute PRPs/[feature].md

# Interactive mode with agent
uv run PRPs/scripts/prp_runner.py --prp [name] --interactive
```

### Monitoring Progress

```bash
# View PRP status
ls PRPs/planning/active/          # Currently being planned
ls PRPs/implementation/in-progress/  # Currently being built

# View task status
python scripts/agent-task-manager.py status

# View agent activity
ls .agent-system/sessions/active/    # Active agent sessions
tail .agent-system/agents/*/changelog.md  # Recent changes
```

## 🤖 The 10 Specialized Agents

1. **PRP Orchestrator** - Workflow coordination, phase management, quality gates
2. **Business Analyst** - Requirements, user stories, success metrics, ROI analysis
3. **Context Researcher** - Codebase investigation, documentation research, gotcha identification
4. **Implementation Specialist** - Core development, code implementation, feature building
5. **Validation Engineer** - Testing, quality assurance, acceptance criteria validation
6. **Integration Architect** - System design, API contracts, service integration
7. **Documentation Curator** - Documentation generation, user guides, API docs
8. **Security Auditor** - Security assessment, compliance verification, threat modeling
9. **Performance Optimizer** - Performance tuning, optimization, scalability planning
10. **DevOps Engineer** - Deployment, infrastructure, CI/CD, monitoring

### Agent Coordination Principles

```yaml
coordination:
  task_assignment: "Lock-free claiming via session files"
  context_loading: "Agent-specific views (2-5KB vs 50KB+)"
  communication: "JSON-based registry and sync files"
  handoffs: "Structured protocol with notes and file tracking"
  parallel_work: "Multiple agents on different features simultaneously"
```

## 🔄 Workflow Phases

The framework follows a 7-phase workflow:

```
P0: Init → P1: Discovery → P2: Architecture → P3: Planning →
P4: Implementation → P5: Deployment Prep → P6: Go-Live → P7: Optimization
```

### Workflow Types

| Type | Duration | Agents | Use Case |
|------|----------|--------|----------|
| **Standard** | 1-2 weeks | All 10 | Complex features |
| **Hotfix** | 2-4 hours | 3-4 | Emergency fixes |
| **Small Feature** | <1 day | 4-5 | Simple additions |
| **Research** | Variable | 2-3 | Technical investigation |

## 🎯 LLM Crypto Trading System - Project Specifics

### System Architecture

The trading system uses:
- **Event-driven architecture** with 3-minute decision intervals
- **OpenRouter API** for multi-LLM support
- **Exchange APIs** (Binance, Bybit, etc.) via ccxt
- **FastAPI** for REST endpoints
- **Celery + Redis** for task scheduling
- **PostgreSQL** for data persistence
- **WebSocket** for real-time market data

### Key Components

```python
# Core modules (to be implemented in workspace/features/)
market_data/        # Data fetching and preprocessing
llm_engine/         # LLM provider abstraction and prompt management
decision_engine/    # Trading signal generation
trade_executor/     # Order execution and position management
risk_manager/       # Position sizing and stop-loss logic
monitoring/         # Performance tracking and alerting
```

### Trading System Requirements

From PRD/llm_crypto_trading_prd.md:
- **Decision Latency**: < 2 seconds per trading cycle
- **System Uptime**: > 99.5% availability
- **Risk Compliance**: 100% adherence to stop-loss rules
- **Profitability**: Positive Sharpe Ratio > 0.5
- **LLM Cost**: < $100/month for continuous operation
- **Assets**: 6 cryptocurrencies on perpetual futures
- **Execution Interval**: Every 3 minutes

### Development Workflow for Trading System

1. **Requirements are in**: PRD/llm_crypto_trading_prd.md
2. **PRPs will be created in**: PRPs/planning/ and PRPs/implementation/
3. **Code will be implemented in**: workspace/features/
4. **Tests go in**: workspace/features/{feature}/tests/
5. **API contracts in**: PRPs/contracts/
6. **Architecture docs in**: PRPs/architecture/

## 🔑 Context Minimization Strategy

The framework uses 3 layers to minimize context loading:

### Layer 1: Agent-Specific Views (PRPs/.cache/agent-views/)
```bash
# Generate lightweight views (2-5KB each from 50KB+ PRPs)
python scripts/generate-agent-views.py --all

# Result: 90-95% context reduction per agent
```

### Layer 2: Context Loader Configuration (.claude/context-loader.yaml)
Each agent has specific files they always/conditionally/never load:
- **Implementation Specialist**: Code, contracts, task briefs (no planning docs)
- **Business Analyst**: Requirements, user stories (no architecture)
- **Validation Engineer**: Test requirements (no architecture/planning)

### Layer 3: Task-Specific Briefs (PRPs/.cache/task-briefs/)
Contains only relevant context for a specific task.

**Context Budget**: Maximum 50,000 tokens total across all agents per session
**Per-Agent Budget**: 6,000-12,000 tokens depending on role complexity
**Actual Usage**: 2,000-5,000 tokens after optimization

## 📋 Critical Success Patterns

### When Starting a Project

1. **Always start with Phase 0**:
   ```
   /prime-core
   "Load AGENT-ORCHESTRATION.md and initialize all agents"
   ```

2. **Let Orchestrator coordinate**:
   ```
   "PRP Orchestrator, initiate standard workflow for [project]"
   ```

3. **Follow phase progression**:
   - Complete validation gates before proceeding
   - Move PRPs through lifecycle: backlog → active → completed

### When an Agent Works on a Task

1. **Claim the task** (creates session lock, updates registry)
2. **Load minimal context** (agent-specific view + task brief)
3. **Execute work** (follow task brief, update changelog, modify files)
4. **Handoff or complete** (with detailed notes for downstream agents)

### Critical Rule: Context Regeneration

**ALWAYS regenerate agent views after PRP changes**:
```bash
python scripts/generate-agent-views.py --all
```

This is not optional - stale views cause agents to miss critical updates.

## 🚫 Anti-Patterns to Avoid

### Agent Coordination Anti-Patterns
- ❌ Don't load full PRPs for every agent (wastes context)
- ❌ Don't skip handoff protocols (causes confusion)
- ❌ Don't bypass validation gates (quality suffers)
- ❌ Don't let agents work without session locks (conflicts)
- ❌ Don't ignore the orchestrator (chaos ensues)

### Context Loading Anti-Patterns
- ❌ Don't load other agents' changelogs
- ❌ Don't load full documentation when brief suffices
- ❌ Don't keep stale context in memory
- ❌ Don't load files outside agent's scope

### Trading System Anti-Patterns
- ❌ Don't implement trading logic outside the decision_engine
- ❌ Don't bypass risk management checks
- ❌ Don't hard-code API keys or secrets
- ❌ Don't skip position validation before execution
- ❌ Don't ignore exchange rate limits

## 🔧 Configuration Files

### Key Configuration Files
- `.claude/context-loader.yaml` - Agent context loading rules
- `.agent-system/registry/tasks.json` - Central task registry
- `stacks/.stack-detection.yaml` - Stack and tool detection
- `PRD/llm_crypto_trading_prd.md` - Product requirements
- `pyproject.toml` - Python project configuration

## 📊 Validation Gates (Per Phase)

```bash
# Phase 1: Requirements Complete
[ ] User stories documented
[ ] Success metrics defined
[ ] Stakeholder approval

# Phase 2: Architecture Approved
[ ] API contracts defined
[ ] Security requirements integrated
[ ] Performance targets set

# Phase 4: Implementation Complete
[ ] Code coverage >80%
[ ] All tests passing
[ ] Security scan clean

# Phase 6: Deployment Ready
[ ] Infrastructure configured
[ ] Monitoring active
[ ] Rollback tested
```

## 🔗 Optional Enhancements

### Archon MCP Server Integration (Optional)

The framework supports optional integration with [Archon MCP Server](https://github.com/coleam00/Archon):
- 🧠 **Knowledge Base**: RAG-powered search across PRPs, docs, and code
- 📊 **Visual Dashboard**: Web UI for project and task management
- 👥 **Team Collaboration**: Real-time sync across multiple developers

```bash
# With Archon installed (optional)
python scripts/archon-sync.py sync-to      # Upload to Archon
python scripts/archon-sync.py search --query "auth patterns"  # RAG search
open http://localhost:3000                 # Web UI dashboard
```

**See [ARCHON-INTEGRATION.md](ARCHON-INTEGRATION.md) for setup.**

File-based system works perfectly without Archon.

## 📚 Essential Documentation

- **[README.md](README.md)** - Complete framework guide with examples
- **[PRD/llm_crypto_trading_prd.md](PRD/llm_crypto_trading_prd.md)** - Trading system requirements
- **[AGENT-ORCHESTRATION.md](AGENT-ORCHESTRATION.md)** - Agent coordination process
- **[PRPs/PRP-LIFECYCLE.md](PRPs/PRP-LIFECYCLE.md)** - PRP lifecycle stages
- **[FRAMEWORK-USAGE-GUIDE.md](FRAMEWORK-USAGE-GUIDE.md)** - Usage guide with examples
- **[QUICK-START.md](QUICK-START.md)** - Quick setup instructions
- **[ARCHON-INTEGRATION.md](ARCHON-INTEGRATION.md)** - Optional Archon MCP integration
- **[BMAD-INTEGRATION-PLAN.md](BMAD-INTEGRATION-PLAN.md)** - BMAD Method integration

## 🚀 Quick Reference Commands

```bash
# System initialization
/prime-core
"PRP Orchestrator, initiate standard workflow for [project]"

# Task management
python scripts/agent-task-manager.py create --title "Task" --priority high --hours 8
python scripts/agent-task-manager.py claim --agent [agent-name] --task TASK-001
python scripts/agent-task-manager.py complete --task TASK-001 --notes "Notes"
python scripts/agent-task-manager.py status

# Context generation (do this after PRP changes!)
python scripts/generate-agent-views.py --all

# Monitoring
ls PRPs/planning/active/
ls PRPs/implementation/in-progress/
ls .agent-system/sessions/active/
tail .agent-system/agents/*/changelog.md

# Emergency response
"All agents, emergency collaboration on [critical issue]"
```

## 💡 Best Practices

### For Optimal Agent Coordination

1. **Minimize Context**: Always use agent views, not full documents
2. **Clear Handoffs**: Use structured handoff protocol with notes
3. **Respect Gates**: Don't proceed until validation passes
4. **Track Changes**: Maintain detailed changelogs per agent
5. **Parallel Work**: Leverage multi-agent capabilities
6. **Session Management**: One task per session, clear locks
7. **Progressive Enhancement**: Start simple, validate, enhance

### For PRP Success

1. **Context is King**: Include all necessary documentation
2. **Validation Loops**: Provide executable tests
3. **Information Dense**: Use codebase patterns
4. **Structured Format**: Follow PRP templates

### For Trading System Development

1. **Risk First**: Implement risk management before execution logic
2. **Test with Paper Trading**: Use exchange testnet/sandbox first
3. **Monitor API Limits**: Track and respect exchange rate limits
4. **Fail Safe**: Default to hold/close on errors, never execute on uncertainty
5. **Log Everything**: Comprehensive logging of decisions and executions
6. **Backtest First**: Validate strategies before live deployment

---

**Remember**: This framework enables **parallel agent coordination with minimal context loading**. The goal is **one-pass implementation success** through **comprehensive orchestration** and **intelligent task distribution**.

**Current Project**: LLM-Powered Cryptocurrency Trading System
**Framework Version**: 2.0.0
**Python Version**: 3.12+
