#!/usr/bin/env python3
"""
Complete the agent workspace setup
"""
import os
import json
from pathlib import Path
from datetime import datetime

# Base directory
BASE_DIR = Path(__file__).parent.parent

# Define all agents
AGENTS = [
    "orchestrator",
    "business-analyst", 
    "context-researcher",
    "implementation-specialist",
    "validation-engineer",
    "integration-architect",
    "documentation-curator",
    "security-auditor",
    "performance-optimizer",
    "devops-engineer"
]

def create_directories():
    """Create all necessary directories"""
    
    # Agent directories
    for agent in AGENTS:
        agent_dir = BASE_DIR / ".agent-system" / "agents" / agent
        agent_dir.mkdir(parents=True, exist_ok=True)
        print(f"✓ Created agent directory: {agent}")
    
    # Sync directory
    sync_dir = BASE_DIR / ".agent-system" / "sync"
    sync_dir.mkdir(parents=True, exist_ok=True)
    
    # PRPs cache directories
    prps_cache = BASE_DIR / "PRPs" / ".cache"
    (prps_cache / "agent-views").mkdir(parents=True, exist_ok=True)
    (prps_cache / "task-briefs").mkdir(parents=True, exist_ok=True)
    
    # PRPs subdirectories
    prps_dirs = [
        "planning",
        "architecture", 
        "contracts",
        "security",
        "implementation"
    ]
    for dir_name in prps_dirs:
        (BASE_DIR / "PRPs" / dir_name).mkdir(parents=True, exist_ok=True)
    
    # Workspace directories
    workspace_dirs = [
        "workspace/features",
        "workspace/fixes",
        "workspace/shared/libraries",
        "workspace/shared/utils",
        "workspace/shared/contracts"
    ]
    for dir_path in workspace_dirs:
        (BASE_DIR / dir_path).mkdir(parents=True, exist_ok=True)
    
    # Stack directories
    stacks = ["python", "java", "javascript", "typescript"]
    for stack in stacks:
        (BASE_DIR / "stacks" / stack).mkdir(parents=True, exist_ok=True)
    
    # Integration directories
    integration_dirs = [
        "integration/environments/local",
        "integration/environments/staging",
        "integration/environments/production",
        "integration/ci-cd/.github/workflows",
        "integration/ci-cd/jenkins",
        "integration/monitoring/dashboards"
    ]
    for dir_path in integration_dirs:
        (BASE_DIR / dir_path).mkdir(parents=True, exist_ok=True)
    
    # Reports directories
    reports_dirs = [
        "reports/daily",
        "reports/phase-completions",
        "reports/metrics"
    ]
    for dir_path in reports_dirs:
        (BASE_DIR / dir_path).mkdir(parents=True, exist_ok=True)
    
    print("✓ All directories created successfully")

def initialize_json_files():
    """Initialize all JSON configuration files"""
    
    # Task registry
    tasks_json = {
        "version": "1.0.0",
        "updated": datetime.now().isoformat(),
        "tasks": {},
        "statistics": {
            "total": 0,
            "completed": 0,
            "in_progress": 0,
            "blocked": 0,
            "pending": 0
        }
    }
    
    tasks_path = BASE_DIR / ".agent-system" / "registry" / "tasks.json"
    with open(tasks_path, 'w') as f:
        json.dump(tasks_json, f, indent=2)
    print(f"✓ Created: {tasks_path}")
    
    # Dependencies registry
    deps_json = {
        "version": "1.0.0",
        "updated": datetime.now().isoformat(),
        "dependencies": {},
        "graph": {}
    }
    
    deps_path = BASE_DIR / ".agent-system" / "registry" / "dependencies.json"
    with open(deps_path, 'w') as f:
        json.dump(deps_json, f, indent=2)
    print(f"✓ Created: {deps_path}")
    
    # Sync files
    sync_files = {
        "broadcasts.json": {
            "version": "1.0.0",
            "broadcasts": []
        },
        "handoffs.json": {
            "version": "1.0.0",
            "handoffs": []
        },
        "conflicts.json": {
            "version": "1.0.0",
            "conflicts": []
        }
    }
    
    for filename, content in sync_files.items():
        sync_path = BASE_DIR / ".agent-system" / "sync" / filename
        with open(sync_path, 'w') as f:
            json.dump(content, f, indent=2)
        print(f"✓ Created: {sync_path}")
    
    # Agent context files
    for agent in AGENTS:
        agent_context = {
            "agent": agent,
            "context": {
                "role": f"Specialized {agent.replace('-', ' ').title()}",
                "capabilities": [],
                "current_focus": None
            },
            "preferences": {
                "max_context_tokens": 8000 if agent != "orchestrator" else 12000,
                "priority_files": [],
                "excluded_patterns": []
            }
        }
        
        context_path = BASE_DIR / ".agent-system" / "agents" / agent / "context.json"
        with open(context_path, 'w') as f:
            json.dump(agent_context, f, indent=2)
        
        # Agent tasks file
        agent_tasks = {
            "assigned": [],
            "completed": [],
            "in_progress": []
        }
        
        tasks_path = BASE_DIR / ".agent-system" / "agents" / agent / "tasks.json"
        with open(tasks_path, 'w') as f:
            json.dump(agent_tasks, f, indent=2)
        
        # Agent changelog
        changelog_path = BASE_DIR / ".agent-system" / "agents" / agent / "changelog.md"
        with open(changelog_path, 'w') as f:
            f.write(f"# {agent.replace('-', ' ').title()} Changelog\n\n")
            f.write(f"## Session History\n\n")
            f.write(f"*No sessions yet*\n")
        
        print(f"✓ Initialized agent files: {agent}")
    
    # Workspace feature index
    feature_index = {
        "version": "1.0.0",
        "features": {},
        "shared_components": []
    }
    
    feature_index_path = BASE_DIR / "workspace" / "features" / ".index.json"
    with open(feature_index_path, 'w') as f:
        json.dump(feature_index, f, indent=2)
    print(f"✓ Created: {feature_index_path}")

def create_stack_detection():
    """Create stack detection configuration"""
    
    stack_detection = """# Stack Detection Configuration
# Automatically detects technology stack for features

rules:
  - pattern: "**/*.py"
    stack: "python"
    config: "stacks/python"
    tools:
      - pytest
      - black
      - mypy
      - ruff
  
  - pattern: "**/*.java"
    stack: "java"
    config: "stacks/java"
    tools:
      - junit
      - maven
      - gradle
  
  - pattern: "**/*.ts"
    stack: "typescript"
    config: "stacks/javascript"
    tools:
      - jest
      - eslint
      - prettier
  
  - pattern: "**/*.js"
    stack: "javascript"
    config: "stacks/javascript"
    tools:
      - jest
      - eslint
      - prettier
  
  - pattern: "**/*.go"
    stack: "golang"
    config: "stacks/golang"
    tools:
      - go test
      - golangci-lint

# Feature-specific overrides
features:
  # Example configurations - will be populated as features are added
  example_payment:
    primary_stack: "python"
    secondary: ["typescript"]
    description: "Payment processing feature"
  
  example_auth:
    primary_stack: "java"
    secondary: ["typescript"]
    description: "Authentication service"
"""
    
    stack_path = BASE_DIR / "stacks" / ".stack-detection.yaml"
    with open(stack_path, 'w') as f:
        f.write(stack_detection)
    print(f"✓ Created: {stack_path}")

def update_context_loader():
    """Update the context loader configuration"""
    
    context_loader = """# Context Loading Configuration for Agents
# Defines what each agent loads to minimize token usage

version: "1.0.0"

# Global settings
global:
  max_file_size_kb: 100
  exclude_patterns:
    - "*.pyc"
    - "__pycache__"
    - "node_modules"
    - ".git"
    - "*.log"
    - "*.tmp"

# Agent-specific configurations
agents:
  orchestrator:
    always_load:
      - ".agent-system/registry/tasks.json"
      - ".agent-system/sync/broadcasts.json"
      - "reports/daily/latest.md"
      - "PRPs/planning/*-prd.md"  # High-level planning docs
    
    conditional_load:
      when_phase_active:
        phase_1:
          - "PRPs/planning/*.md"
        phase_2:
          - "PRPs/architecture/*.md"
        phase_3:
          - "PRPs/implementation/*.md"
    
    max_context_tokens: 12000
    priority: "high"
  
  business-analyst:
    always_load:
      - ".agent-system/agents/business-analyst/context.json"
      - ".agent-system/agents/business-analyst/tasks.json"
    
    conditional_load:
      when_task_requires:
        - "PRPs/.cache/task-briefs/TASK-{current}.md"
        - "PRPs/planning/user-stories.md"
        - "PRPs/planning/success-metrics.md"
    
    never_load:
      - "workspace/features/*/src/**"  # Don't need source code
      - "integration/**"
    
    max_context_tokens: 8000
  
  context-researcher:
    always_load:
      - ".agent-system/agents/context-researcher/context.json"
      - "workspace/shared/**/*.md"  # Shared documentation
    
    conditional_load:
      when_researching:
        - "**/*README.md"
        - "**/*NOTES.md"
        - "docs/**/*.md"
    
    max_context_tokens: 10000
  
  implementation-specialist:
    always_load:
      - ".agent-system/agents/implementation-specialist/context.json"
      - ".agent-system/agents/implementation-specialist/tasks.json"
    
    conditional_load:
      when_task_requires:
        - "PRPs/.cache/task-briefs/TASK-{current}.md"
        - "workspace/features/{feature}/.meta/*.json"
        - "PRPs/contracts/*-api-contract.md"
        - "workspace/shared/libraries/**"
    
    never_load:
      - "PRPs/planning/*.md"  # Full planning documents
      - "reports/**"
      - ".agent-system/agents/*/changelog.md"  # Other agents' logs
    
    max_context_tokens: 8000
  
  validation-engineer:
    always_load:
      - ".agent-system/agents/validation-engineer/context.json"
      - ".agent-system/agents/validation-engineer/tasks.json"
    
    conditional_load:
      when_task_requires:
        - "PRPs/.cache/agent-views/validation-engineer.md"
        - "workspace/features/{feature}/tests/**"
        - "PRPs/planning/user-stories.md"  # For acceptance criteria
    
    max_context_tokens: 8000
  
  integration-architect:
    always_load:
      - ".agent-system/agents/integration-architect/context.json"
      - "PRPs/architecture/*.md"
      - "PRPs/contracts/*.md"
    
    conditional_load:
      when_designing:
        - "workspace/shared/contracts/**"
        - "integration/environments/**/*.yaml"
    
    max_context_tokens: 10000
  
  documentation-curator:
    always_load:
      - ".agent-system/agents/documentation-curator/context.json"
      - "workspace/features/*/docs/*.md"
    
    conditional_load:
      when_documenting:
        - "workspace/features/{feature}/README.md"
        - "PRPs/.cache/agent-views/documentation-curator.md"
    
    max_context_tokens: 8000
  
  security-auditor:
    always_load:
      - ".agent-system/agents/security-auditor/context.json"
      - "PRPs/security/*.md"
    
    conditional_load:
      when_auditing:
        - "workspace/features/{feature}/src/**"
        - "integration/environments/*/secrets.yaml"
    
    max_context_tokens: 8000
  
  performance-optimizer:
    always_load:
      - ".agent-system/agents/performance-optimizer/context.json"
      - "reports/metrics/*.json"
    
    conditional_load:
      when_optimizing:
        - "workspace/features/{feature}/benchmarks/**"
        - "integration/monitoring/dashboards/*.json"
    
    max_context_tokens: 8000
  
  devops-engineer:
    always_load:
      - ".agent-system/agents/devops-engineer/context.json"
      - "integration/ci-cd/**/*.yaml"
    
    conditional_load:
      when_deploying:
        - "integration/environments/{environment}/**"
        - "workspace/features/{feature}/Dockerfile"
    
    max_context_tokens: 8000

# Dynamic loading rules
dynamic_rules:
  - condition: "task.priority == 'critical'"
    action: "increase_max_tokens"
    value: 2000
  
  - condition: "phase == 'hotfix'"
    action: "load_minimal"
    agents: ["all"]
  
  - condition: "multi_agent_collaboration"
    action: "share_context"
    scope: "task_specific"
"""
    
    loader_path = BASE_DIR / ".claude" / "context-loader.yaml"
    with open(loader_path, 'w') as f:
        f.write(context_loader)
    print(f"✓ Updated: {loader_path}")

def create_project_template():
    """Create an enhanced project template"""
    
    template = """# Project: [PROJECT_NAME]
# Generated: {timestamp}

## Project Configuration

### Workflow Type
- [ ] Standard (Full 7-phase process)
- [ ] Hotfix (Emergency 2-4 hour fix)
- [ ] Small Feature (< 1 day effort)
- [ ] Research (Technical investigation)

### Active Agents
| Agent | Status | Assigned Tasks | Session |
|-------|--------|----------------|---------|
| PRP Orchestrator | ✅ Active | - | - |
| Business Analyst | ⏸️ Standby | - | - |
| Context Researcher | ⏸️ Standby | - | - |
| Implementation Specialist | ⏸️ Standby | - | - |
| Validation Engineer | ⏸️ Standby | - | - |
| Integration Architect | ⏸️ Standby | - | - |
| Documentation Curator | ⏸️ Standby | - | - |
| Security Auditor | ⏸️ Standby | - | - |
| Performance Optimizer | ⏸️ Standby | - | - |
| DevOps Engineer | ⏸️ Standby | - | - |

### Current Phase
```mermaid
graph LR
    P0[Phase 0: Init] --> P1[Phase 1: Discovery]
    P1 --> P2[Phase 2: Architecture]
    P2 --> P3[Phase 3: Planning]
    P3 --> P4[Phase 4: Implementation]
    P4 --> P5[Phase 5: Deployment Prep]
    P5 --> P6[Phase 6: Go-Live]
    P6 --> P7[Phase 7: Optimization]
    
    style P0 fill:#90EE90
```

- [x] Phase 0: Initialization
- [ ] Phase 1: Discovery & Requirements
- [ ] Phase 2: Architecture & Security
- [ ] Phase 3: Implementation Planning
- [ ] Phase 4: Implementation Execution
- [ ] Phase 5: Deployment Preparation
- [ ] Phase 6: Deployment & Go-Live
- [ ] Phase 7: Post-Launch Optimization

## Key Files & Locations

### Planning Documents
- Requirements: `PRPs/planning/[project]-requirements.md`
- User Stories: `PRPs/planning/[project]-user-stories.md`
- Architecture: `PRPs/architecture/[project]-architecture.md`
- API Contracts: `PRPs/contracts/[project]-api-contract.md`

### Implementation
- Feature Code: `workspace/features/[project]/`
- Tests: `workspace/features/[project]/tests/`
- Documentation: `workspace/features/[project]/docs/`

### Deployment
- CI/CD Pipeline: `integration/ci-cd/.github/workflows/[project].yaml`
- Environments: `integration/environments/*/[project]/`
- Monitoring: `integration/monitoring/dashboards/[project].json`

## Success Metrics

| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| Code Coverage | >80% | 0% | 🔴 |
| Performance (P95) | <200ms | - | ⏸️ |
| Security Score | A | - | ⏸️ |
| Documentation | 100% | 0% | 🔴 |

## Task Registry Summary

| Priority | Status | Count |
|----------|--------|-------|
| 🔴 Critical | Pending | 0 |
| 🟠 High | Pending | 0 |
| 🟡 Medium | Pending | 0 |
| 🟢 Low | Pending | 0 |

## Next Actions

### Immediate (Today)
1. [ ] Initialize project context with orchestrator
2. [ ] Conduct stakeholder discovery
3. [ ] Document initial requirements

### Short-term (This Week)
1. [ ] Complete Phase 1: Discovery
2. [ ] Begin Phase 2: Architecture
3. [ ] Identify security requirements

### Long-term (This Sprint)
1. [ ] Complete implementation
2. [ ] Deploy to staging
3. [ ] Production release

## Risk Register

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| [Example] | Low/Med/High | Low/Med/High | [Strategy] |

## Communication Channels

- **Sync Broadcasts**: `.agent-system/sync/broadcasts.json`
- **Handoffs**: `.agent-system/sync/handoffs.json`
- **Conflicts**: `.agent-system/sync/conflicts.json`

## Session History

| Session ID | Agent | Start | End | Tasks Completed |
|------------|-------|-------|-----|-----------------|
| - | - | - | - | - |

## Notes & Decisions

### Architectural Decisions
- 

### Technical Debt
- 

### Lessons Learned
- 

---
*Template Version: 1.0.0 | Framework: PRPs Agentic Engineering*
""".format(timestamp=datetime.now().isoformat())
    
    template_path = BASE_DIR / ".claude" / "PROJECT-TEMPLATE.md"
    with open(template_path, 'w') as f:
        f.write(template)
    print(f"✓ Created: {template_path}")

def create_agent_quickref():
    """Create quick reference for agents"""
    
    quickref = """# Agent System Quick Reference

## 🚀 Quick Start Commands

### Initialize System
```bash
# Load everything
/prime-core
"Load AGENT-ORCHESTRATION.md and initialize all agents"

# Start new project
"PRP Orchestrator, initiate standard workflow for [project]"

# Emergency fix
"PRP Orchestrator, initiate hotfix workflow for [issue]"

# Research task
"Context Researcher, lead research workflow for [topic]"
```

## 🤖 Agent Activation Phrases

```python
agents = {
    "orchestrator": "PRP Orchestrator, coordinate: ",
    "business": "Business Analyst, analyze requirements for: ",
    "context": "Context Researcher, investigate: ",
    "implementation": "Implementation Specialist, implement: ",
    "validation": "Validation Engineer, validate: ",
    "integration": "Integration Architect, design integration for: ",
    "documentation": "Documentation Curator, document: ",
    "security": "Security Auditor, audit: ",
    "performance": "Performance Optimizer, optimize: ",
    "devops": "DevOps Engineer, deploy: "
}
```

## 📋 Phase Checkpoints

| Phase | Status Check | Validation Command |
|-------|--------------|-------------------|
| 0 | Initialized | `cat .agent-system/registry/tasks.json` |
| 1 | Requirements | `ls PRPs/planning/` |
| 2 | Architecture | `ls PRPs/architecture/` |
| 3 | Planning | `grep "TASK-" .agent-system/registry/tasks.json` |
| 4 | Implementation | `find workspace/features -name "*.py"` |
| 5 | Deployment Ready | `ls integration/ci-cd/` |
| 6 | Live | `cat reports/daily/latest.md` |
| 7 | Optimized | `ls reports/metrics/` |

## 🔧 Task Management

### Claim a Task
```python
python scripts/agent-task-manager.py claim --agent "implementation-specialist" --task "TASK-001"
```

### Check Task Status
```python
python scripts/agent-task-manager.py status --task "TASK-001"
```

### Complete Task
```python
python scripts/agent-task-manager.py complete --task "TASK-001" --notes "Implemented payment gateway"
```

## 🔄 Multi-Session Coordination

### Start New Session
```bash
# Agent creates session automatically when claiming task
# Session ID format: claude-YYYYMMDD-XXXXXX
```

### Check Active Sessions
```bash
ls -la .agent-system/sessions/active/
```

### Handoff Between Sessions
```python
python scripts/agent-task-manager.py handoff --from-session "abc123" --to-agent "validation-engineer"
```

## 🚨 Emergency Commands

### All Hands Emergency
```
"All agents, emergency collaboration on [critical issue]"
```

### Security Incident
```
"Security Auditor, immediate security assessment for [component]"
```

### Performance Crisis
```
"Performance Optimizer, system experiencing degradation in [area]"
```

### Rollback
```
"DevOps Engineer, emergency rollback to [version]"
```

## 📊 Status Commands

### Overall Project Status
```bash
cat .agent-system/registry/milestones.md
```

### Task Statistics
```bash
jq '.statistics' .agent-system/registry/tasks.json
```

### Agent Activity
```bash
find .agent-system/agents -name "changelog.md" -exec tail -n 5 {} \\;
```

## 🔍 Context Management

### Minimize Context Loading
```yaml
# Check agent's context configuration
cat .claude/context-loader.yaml | grep -A 10 "implementation-specialist:"
```

### Generate Agent Views
```python
python scripts/generate-agent-views.py --agent "validation-engineer"
```

### Clear Cache
```bash
rm -rf PRPs/.cache/agent-views/*
python scripts/generate-agent-views.py --all
```

## 📈 Workflow Patterns

### Standard Workflow (7 phases)
```
Phase 0 → 1 → 2 → 3 → 4 → 5 → 6 → 7
Duration: 1-2 weeks
All agents involved
```

### Hotfix Workflow
```
Context Research → Implementation → Validation → Deployment
Duration: 2-4 hours
Minimal agents
```

### Small Feature
```
Planning → Implementation → Testing → Deployment
Duration: < 1 day
3-4 agents
```

### Research Task
```
Context Research → Analysis → Documentation
Duration: Variable
Research-focused agents
```

## 🎯 Best Practices

1. **Always start with Phase 0** - Never skip initialization
2. **Respect validation gates** - Don't proceed until green
3. **Use parallel patterns** - Some work can happen simultaneously
4. **Document decisions** - Every significant choice should be captured
5. **Maintain changelogs** - Each agent tracks their changes
6. **Minimize context** - Agents only load what they need
7. **Clear handoffs** - Use structured handoff protocol

## 🛠️ Utility Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| `agent-task-manager.py` | Manage tasks | `python scripts/agent-task-manager.py [command]` |
| `generate-agent-views.py` | Create views | `python scripts/generate-agent-views.py` |
| `complete-setup.py` | Setup workspace | `python scripts/complete-setup.py` |
| `impact-analyzer.py` | Analyze changes | `python scripts/impact-analyzer.py [files]` |

## 📞 Help & Support

- **Documentation**: `PRPs/README.md`
- **Agent Library**: `.claude/agents/*.md`
- **Commands**: `.claude/commands/**/*.md`
- **Troubleshooting**: `PRPs/ai_docs/cc_troubleshoot.md`

---
*Quick Reference v1.0.0 | Framework: PRPs Agentic Engineering*
"""
    
    quickref_path = BASE_DIR / ".claude" / "AGENT-QUICKREF.md"
    with open(quickref_path, 'w') as f:
        f.write(quickref)
    print(f"✓ Created: {quickref_path}")

def update_gitignore():
    """Update gitignore with agent-specific patterns"""
    
    gitignore_additions = """
# Agent System
.agent-system/sessions/active/*.lock
.agent-system/sync/conflicts.json
.agent-system/agents/*/changelog-*.bak
PRPs/.cache/

# IDE and temp files
*.pyc
__pycache__/
.pytest_cache/
*.swp
*.swo
*~
.DS_Store

# Environment
.env
.env.local
venv/
env/

# Build artifacts
dist/
build/
*.egg-info/

# Node
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# Java
target/
*.class
*.jar
*.war

# Logs
*.log
logs/

# Secrets
secrets/
*.key
*.pem
*.crt
"""
    
    gitignore_path = BASE_DIR / ".gitignore"
    with open(gitignore_path, 'a') as f:
        f.write(gitignore_additions)
    print(f"✓ Updated: {gitignore_path}")

def main():
    """Run all setup functions"""
    print("🚀 Starting Agent Workspace Setup...")
    print("=" * 50)
    
    create_directories()
    print()
    
    initialize_json_files()
    print()
    
    create_stack_detection()
    print()
    
    update_context_loader()
    print()
    
    create_project_template()
    print()
    
    create_agent_quickref()
    print()
    
    update_gitignore()
    print()
    
    print("=" * 50)
    print("✅ Agent Workspace Setup Complete!")
    print("\nNext steps:")
    print("1. Run: /prime-core")
    print("2. Load AGENT-ORCHESTRATION.md")
    print("3. Initialize your first project with the orchestrator")

if __name__ == "__main__":
    main()
