# PRPs Agentic Engineering Starter Guide

Welcome to the **PRPs Agentic Engineering** workspace. This repository packages everything you need to run a distributed, multi-agent development process where specialized AI roles collaborate through lightweight context, structured prompts, and a shared task registry. Use this guide when you spin up a brand-new project, deliver a feature, patch a production bug, or just need a refresher on where things live.

## Core Ideas at a Glance
- **Product Requirement Prompts (PRPs)** break work into clear phases: discovery, architecture, planning, implementation, validation, deployment, and optimization.
- **Ten specialized agents** (orchestrator, business analyst, context researcher, implementation specialist, validation engineer, integration architect, documentation curator, security auditor, performance optimizer, devops engineer) each work from focused context slices stored in `.agent-system/` and `PRPs/.cache/`.
- **Task registry & sessions** in `.agent-system/registry/` keep everyone synchronized while avoiding lock contention; lock files in `.agent-system/sessions/active/` show who holds what.
- **Workspace layout** under `workspace/` keeps features, hotfixes, and reusable libraries isolated so you can ship in parallel without stepping on toes.
- **Helper scripts** (inside `scripts/`) automate routine chores: bootstrapping the folder structure, generating agent-ready briefs, and managing task lifecycles.

## Prerequisites
- Python **3.12+** (see `pyproject.toml`)
- A shell environment that can execute bash/zsh scripts
- Claude Code (or another agent-friendly IDE) if you plan to run the orchestration workflow end-to-end

## First-Time Setup (15 minutes)
1. **Clone the repo and review scripts**
   ```bash
   git clone <this-repo-url>
   cd PRPs-agentic-eng
   ls scripts
   ```
2. **Bootstrap the agent workspace** (creates directories, registries, and defaults)
   ```bash
   chmod +x ./init-agent-workspace.sh
   ./init-agent-workspace.sh
   ```
   The script lays down `.agent-system/`, `PRPs/`, `workspace/`, `integration/`, and `reports/` scaffolding plus sensible `.gitignore` entries.
3. **Optional: rebuild from Python** (mirrors the shell script; handy when containers or CI restrict shell access)
   ```bash
   python scripts/setup-workspace.py
   ```
4. **Prime Claude Code**
   - In Claude Code run `/prime-core`.
   - Say: `Load AGENT-ORCHESTRATION.md and initialize all agents for project: <project name>`.
   - The orchestrator will pull context from `.claude/context-loader.yaml` and announce which phase you are in.
5. **Confirm the registry is ready**
   ```bash
   python scripts/agent-task-manager.py status
   ls .agent-system/agents
   ls PRPs/.cache/agent-views
   ```

## Repository Map
```
.agent-system/        # Task registry, agent contexts, session locks, sync files
PRPs/                 # Planning assets, architecture notes, contracts, security, cached briefs
workspace/
  features/           # Feature-scoped implementation areas
  fixes/              # Hotfixes and patches
  shared/             # Reusable libraries, utilities, and contracts
scripts/              # Automation helpers (setup, task manager, agent views)
integration/          # Deployment targets, CI/CD wiring, monitoring hooks
reports/              # Daily notes, phase summaries, metrics (gitignored by default)
.claude/              # Agent personas, commands, context loading rules
```

## Starting a Fresh Project
Follow this sequence whenever you launch a net-new initiative.

1. **Kickoff in Phase 0 (Initialization)**
   - `/prime-core`
   - `PRP Orchestrator, initiate standard workflow for: <project description>`
   - The orchestrator enlists the Business Analyst and Context Researcher; they populate `PRPs/planning/` and `PRPs/.cache/task-briefs/`.
2. **Capture vision and constraints**
   - Business Analyst drafts: `PRPs/planning/<project>-requirements.md`, `.../user-stories.md`, `.../success-metrics.md`.
   - Context Researcher logs findings in `PRPs/planning/context-notes.md` or `PRPs/architecture/research.md`.
3. **Define architecture & contracts (Phase 2)**
   - Integration Architect and Security Auditor collaborate on `PRPs/architecture/<project>-architecture.md` and `PRPs/contracts/<system>-api-contract.md`.
   - Performance targets land in `PRPs/architecture/performance-targets.md`.
4. **Plan executable work (Phase 3)**
   - Create tasks per feature:
     ```bash
     python scripts/agent-task-manager.py create \
       --title "Implement user authentication" \
       --priority high \
       --hours 8
     ```
   - Run `python scripts/generate-agent-views.py --all` to produce lightweight briefs for each agent.
5. **Spin up feature workspaces**
   - For each task, create `workspace/features/<feature-name>/` with `src/`, `tests/`, `docs/`, and `.meta/` as needed.
   - Drop API stubs, config samples, or scaffolding before handing off to the Implementation Specialist.
6. **Record milestones**
   - Update `.agent-system/registry/milestones.md` as gates close.
   - Daily updates belong in `reports/daily/<date>.md` (the orchestrator references `reports/daily/latest.md`).

## Onboarding an Existing Codebase
When you inherit or revisit an established repository, treat the first hour as a structured migration into the agent framework.

1. **Mirror the current code layout**
   - Map each major capability to `workspace/features/<feature>/` and drop shared utilities into `workspace/shared/`.
   - Preserve legacy documentation by parking it in `workspace/features/<feature>/docs/` so agents can surface it.
2. **Rebuild coordination scaffolding**
   - Run `python scripts/complete-setup.py` to regenerate registry JSON, stack detection rules, and blank changelogs without touching code.
   - Back up any existing `.agent-system/registry/tasks.json` before you overwrite it; re-import tasks afterward.
3. **Seed the task registry from the backlog**
   - For each outstanding work item, execute:
     ```bash
     python scripts/agent-task-manager.py create \
       --title "Refactor payment webhook" \
       --description "Clean up retry logic" \
       --priority medium \
       --hours 5
     ```
   - Optionally add dependencies directly in `.agent-system/registry/tasks.json` once the initial IDs exist.
4. **Brief Claude or Codex on the migration plan**
   - Prompt example:
     > `/prime-core`
     >
     > "PRP Orchestrator, adopt the existing codebase that now lives under `workspace/features/` and sync the backlog into the task registry. Announce each TASK-* you log and hand off refactors to the relevant agents."
   - Ask the Implementation Specialist to inspect high-risk areas and the Validation Engineer to note missing tests.
5. **Refresh agent-specific context**
   - Run `python scripts/generate-agent-views.py --clean --all` so every agent receives lightweight slices that reflect the imported code.
   - Verify `.claude/context-loader.yaml` includes the new feature directories and adjust `priority_files` in each agent’s `context.json` if certain modules should always load.

## Delivering a New Feature (Phase 4 onwards)
Follow these steps for each feature folder you open under `workspace/features/`.

1. **Claim the task**
   ```bash
   python scripts/agent-task-manager.py claim \
     --agent implementation-specialist \
     --task TASK-001
   ```
   A lock file appears in `.agent-system/sessions/active/` showing who owns the work.
2. **Build inside the feature sandbox**
   - Place code in `workspace/features/<feature>/src/`.
   - Write acceptance tests in `workspace/features/<feature>/tests/` (pick tooling that matches the detected stack—see `stacks/.stack-detection.yaml`).
   - Capture design choices or usage notes in `workspace/features/<feature>/docs/`.
3. **Run validations**
   - Execute automated tests locally (add language-specific tooling in `stacks/<language>/`).
   - If security-sensitive, ping the Security Auditor: `python scripts/agent-task-manager.py handoff --task TASK-001 --to-agent security-auditor --notes "Please run security checklist"`.
4. **Complete or hand off**
   - When done, `python scripts/agent-task-manager.py complete --task TASK-001 --notes "Key outcomes"`.
   - Or, hand off to Validation Engineer or Documentation Curator with detailed notes so they can finish their gate.
5. **Document outcomes**
   - Update the relevant PRP section (typically `PRPs/implementation/<feature>-summary.md`).
   - Append highlights to `reports/phase-completions/<phase>-<date>.md` if this feature closes a milestone.

## Fixing Bugs and Shipping Hotfixes
Use the accelerated “hotfix workflow” when production issues strike.

1. **Initiate a hotfix session** `PRP Orchestrator, initiate hotfix workflow for: <incident>`.
2. **Create a fix task**
   ```bash
   python scripts/agent-task-manager.py create \
     --title "Hotfix: <issue>" \
     --priority critical \
     --hours 2
   ```
3. **Work inside `workspace/fixes/<issue>/`**
   - Mirror the feature structure (`src/`, `tests/`, `docs/`).
   - Log reproduction steps and verification evidence in `docs/verification.md`.
4. **Run emergency validations**
   - Validation Engineer confirms tests and metrics.
   - DevOps Engineer preps rollback notes in `integration/environments/<env>/` or `reports/metrics/` if needed.
5. **Close the loop**
   - Mark the task complete, publish a quick report in `reports/daily/<date>.md`, and backfill a long-term fix task in the main backlog if the root cause deserves more work.

## Reusing and Sharing Code
- Keep cross-cutting utilities in `workspace/shared/` (e.g., `workspace/shared/libraries/logger/` or `workspace/shared/contracts/payment-gateway.md`).
- Update `.agent-system/registry/dependencies.json` when shared components become prerequisites for features so the orchestrator respects ordering.
- Document integration points in `integration/` to keep the DevOps Engineer and Performance Optimizer in sync.

## Monitoring Progress
- `python scripts/agent-task-manager.py status` — quick health snapshot.
- `python scripts/agent-task-manager.py list --status in-progress` — active workload.
- `ls -la .agent-system/sessions/active/` — who currently holds locks.
- `tail -n 20 .agent-system/agents/*/changelog.md` — recent agent activity.
- `cat .agent-system/sync/handoffs.json` — pending handoffs between agents.

## Task Registry & Agent Instructions
- **Initialize or reset**: `python scripts/complete-setup.py` safely recreates registry scaffolding; run it when onboarding a new team or clearing corrupted data.
- **Capture tasks with the CLI**: rely on `python scripts/agent-task-manager.py create|claim|handoff|complete ...` as the single source of truth that updates `.agent-system/registry/tasks.json` and session locks.
- **Capture tasks with Claude/Codex**: ask the orchestrator to execute the same CLI commands and read back the results, e.g.
  > "/prime-core"
  >
  > "PRP Orchestrator, register the backlog item 'Improve webhook retries' with priority high and estimate 6 hours. Assign it to the Implementation Specialist and confirm the TASK ID in the registry."
- **Check work in/out**: after a claim, expect Claude to mention the generated session lock under `.agent-system/sessions/active/`. When closing work, insist on `--notes` that summarize code changes, tests, and handoffs so downstream agents inherit context.
- **Prepare agent contexts**: whenever PRP documents or feature folders change materially, regenerate caches with `python scripts/generate-agent-views.py --all` and confirm `.claude/context-loader.yaml` names any new directories you introduced.

## Script Reference
| Script | Purpose |
| --- | --- |
| `init-agent-workspace.sh` | Shell-friendly bootstrapper for the entire directory layout and seed files |
| `scripts/setup-workspace.py` | Python alternative to bootstrap (useful in CI) |
| `scripts/agent-task-manager.py` | Create, claim, hand off, complete, and inspect tasks |
| `scripts/generate-agent-views.py` | Produce lightweight PRP extracts so each agent loads only the context it needs |
| `scripts/complete-setup.py` | Idempotent helper to refresh JSON registries and stack detection files |

## Staying in Flow
- Keep PRP documents terse and structured—agent views depend on consistent headings (see `scripts/generate-agent-views.py`).
- When you add new file types or stacks, extend `stacks/.stack-detection.yaml` so the orchestrator picks the right tools.
- Treat `reports/` as disposable analytics: add `.gitkeep` files to persist structure, but the contents are ignored by Git for privacy.
- If you introduce custom agents, mirror the format in `.claude/agents/` and update `.claude/context-loader.yaml`.

## Essential Documentation

- **[FRAMEWORK-USAGE-GUIDE.md](FRAMEWORK-USAGE-GUIDE.md)** - Complete usage guide with examples
- **[PRPs/PRP-LIFECYCLE.md](PRPs/PRP-LIFECYCLE.md)** - PRP lifecycle stages and tracking
- **[AGENT-ORCHESTRATION.md](AGENT-ORCHESTRATION.md)** - Agent coordination process
- **[CLAUDE.md](CLAUDE.md)** - Framework overview and architecture
- **[QUICK-START.md](QUICK-START.md)** - Quick setup instructions
- **[ARCHON-INTEGRATION.md](ARCHON-INTEGRATION.md)** - Optional Archon MCP server integration
- **[BMAD-INTEGRATION-PLAN.md](BMAD-INTEGRATION-PLAN.md)** - BMAD Method integration (story-driven development)

## Key Concepts

### PRP Lifecycle Tracking

PRPs now move through clear stages with dedicated directories:

```
PRPs/
├── planning/
│   ├── backlog/          # 📋 Planned (not started)
│   ├── active/           # 🔄 Currently being refined
│   └── completed/        # ✅ Ready for implementation
├── implementation/
│   ├── in-progress/      # 👷 Active implementation
│   └── completed/        # ✅ Deployed to production
```

**Progress Tracking**:
```bash
# See what's being worked on
ls PRPs/planning/active/          # Planning phase
ls PRPs/implementation/in-progress/  # Implementation phase

# Check task status
python scripts/agent-task-manager.py status
```

### Context Optimization

The framework minimizes context loading through 3 layers:

1. **Agent Views** (PRPs/.cache/agent-views/): 2-5KB per agent vs 50KB+ full PRPs
2. **Context Loader** (.claude/context-loader.yaml): Per-agent token limits (6-12K)
3. **Task Briefs** (PRPs/.cache/task-briefs/): Task-specific context only

```bash
# Regenerate after PRP changes (IMPORTANT!)
python scripts/generate-agent-views.py --all

# Check context sizes
ls -lh PRPs/.cache/agent-views/
```

**Result**: 90-95% context reduction per agent

### Optional: Archon MCP Server

The framework supports optional integration with [Archon](https://github.com/coleam00/Archon) for enhanced capabilities:

- 🧠 **Knowledge Base**: RAG-powered search across all PRPs and docs
- 📊 **Web Dashboard**: Visual project and task management UI
- 👥 **Team Collaboration**: Real-time sync across multiple developers
- 🤖 **AI-Enhanced**: Smart task suggestions and context retrieval

```bash
# With Archon installed (optional)
python scripts/archon-sync.py sync-to      # Upload tasks to Archon
python scripts/archon-sync.py search --query "auth patterns"  # RAG search
open http://localhost:3000                 # Web UI dashboard
```

**See [ARCHON-INTEGRATION.md](ARCHON-INTEGRATION.md) for setup.**

**Note**: File-based system works perfectly without Archon. It's purely optional enhancement.

## Next Steps

1. **Read the guides**:
   - Start with [FRAMEWORK-USAGE-GUIDE.md](FRAMEWORK-USAGE-GUIDE.md) for complete workflow examples
   - Review [PRPs/PRP-LIFECYCLE.md](PRPs/PRP-LIFECYCLE.md) for PRP management

2. **Initialize your first project**:
   ```bash
   /prime-core
   "PRP Orchestrator, initiate standard workflow for: [your project]"
   ```

3. **Practice the lifecycle**:
   - Create a test PRP in `PRPs/planning/backlog/`
   - Move it through stages: backlog → active → completed
   - Generate agent views after each change
   - Track with task registry

4. **Monitor progress**:
   ```bash
   # Quick status
   python scripts/agent-task-manager.py status

   # PRP locations
   ls PRPs/planning/active/
   ls PRPs/implementation/in-progress/
   ```

Happy building—and let the orchestrator do the heavy lifting while keeping context minimal! 🚀
