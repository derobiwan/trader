#!/bin/bash
# Agent Workspace Initialization Script
# This script sets up the complete agent orchestration structure

echo "🚀 Initializing Agent Workspace Structure..."

# Base directory
BASE_DIR="$(pwd)"

# Create .agent-system directories
echo "📁 Creating agent system directories..."
mkdir -p .agent-system/{registry,sessions/{active,history},agents,sync}

# Create agent-specific directories
AGENTS=(
  "orchestrator"
  "business-analyst"
  "context-researcher"
  "implementation-specialist"
  "validation-engineer"
  "integration-architect"
  "documentation-curator"
  "security-auditor"
  "performance-optimizer"
  "devops-engineer"
)

for agent in "${AGENTS[@]}"; do
  mkdir -p ".agent-system/agents/$agent"
done

# Create PRPs cache structure
echo "📁 Creating PRPs cache structure..."
mkdir -p PRPs/.cache/{agent-views,task-briefs}
mkdir -p PRPs/{planning,architecture,contracts,security}

# Create workspace directories
echo "📁 Creating workspace directories..."
mkdir -p workspace/{features,fixes,shared/{libraries,utils,contracts}}

# Create stacks directories for multi-language support
echo "📁 Creating technology stack directories..."
mkdir -p stacks/{python,java,javascript,typescript}

# Create integration directories
echo "📁 Creating integration directories..."
mkdir -p integration/{environments/{local,staging,production},ci-cd/{github-actions,jenkins},monitoring/dashboards}

# Create reports directories
echo "📁 Creating reports directories..."
mkdir -p reports/{daily,phase-completions,metrics}

# Initialize registry files
echo "📄 Initializing registry files..."

# Initialize tasks registry
cat > .agent-system/registry/tasks.json << 'EOF'
{
  "version": "1.0.0",
  "updated": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "next_task_id": 1,
  "tasks": {},
  "statistics": {
    "total": 0,
    "completed": 0,
    "in_progress": 0,
    "blocked": 0,
    "pending": 0
  }
}
EOF

# Initialize milestones
cat > .agent-system/registry/milestones.md << 'EOF'
# Project Milestones

## Active Milestones

### Phase 0: Initialization
- [ ] Project context loaded
- [ ] Agents initialized
- [ ] Task registry created
- [ ] Dependencies mapped

---

## Completed Milestones

<!-- Completed milestones will be moved here -->

---

## Upcoming Milestones

<!-- Future milestones will be listed here -->
EOF

# Initialize dependencies
cat > .agent-system/registry/dependencies.json << 'EOF'
{
  "version": "1.0.0",
  "task_dependencies": {},
  "feature_dependencies": {},
  "agent_dependencies": {}
}
EOF

# Initialize sync files
echo "📄 Initializing synchronization files..."

cat > .agent-system/sync/broadcasts.json << 'EOF'
{
  "broadcasts": [],
  "last_broadcast_id": 0
}
EOF

cat > .agent-system/sync/handoffs.json << 'EOF'
{
  "handoffs": [],
  "pending": [],
  "completed": []
}
EOF

cat > .agent-system/sync/conflicts.json << 'EOF'
{
  "active_conflicts": [],
  "resolved_conflicts": []
}
EOF

# Initialize agent context files
echo "📄 Initializing agent contexts..."

for agent in "${AGENTS[@]}"; do
  cat > ".agent-system/agents/$agent/context.json" << EOF
{
  "agent": "$agent",
  "initialized": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "capabilities": [],
  "current_tasks": [],
  "completed_tasks": [],
  "preferences": {},
  "knowledge_base": []
}
EOF

  cat > ".agent-system/agents/$agent/tasks.json" << EOF
{
  "assigned": [],
  "in_progress": [],
  "completed": [],
  "blocked": []
}
EOF

  cat > ".agent-system/agents/$agent/changelog.md" << EOF
# $agent Changelog

## Active Session

### Date: $(date +%Y-%m-%d)

#### Tasks
<!-- Task changes will be logged here -->

#### Files Modified
<!-- File modifications will be logged here -->

---

## Previous Sessions
<!-- Previous session logs will be archived here -->
EOF
done

# Create feature index
cat > workspace/features/.index.json << 'EOF'
{
  "features": {},
  "total_features": 0,
  "active_features": 0,
  "completed_features": 0
}
EOF

# Create stack detection configuration
cat > stacks/.stack-detection.yaml << 'EOF'
# Stack Detection Rules
# Automatically detect and configure technology stacks

rules:
  - pattern: "**/*.py"
    stack: "python"
    config: "stacks/python"
    tools:
      - pytest
      - black
      - pylint
      
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

features:
  # Feature-specific stack configurations will be added here
  example:
    primary_stack: "python"
    secondary: ["typescript"]
    
defaults:
  test_coverage_threshold: 80
  linting_enabled: true
  auto_format: true
EOF

# Create context loader configuration
cat > .claude/context-loader.yaml << 'EOF'
# Context Loading Configuration
# Defines what each agent should load to minimize context consumption

agents:
  orchestrator:
    always_load:
      - ".agent-system/registry/tasks.json"
      - ".agent-system/sync/broadcasts.json"
      - ".agent-system/registry/milestones.md"
      - "reports/daily/latest.md"
    conditional_load:
      when_coordinating:
        - ".agent-system/agents/*/tasks.json"
    max_context_tokens: 12000

  business-analyst:
    always_load:
      - ".agent-system/agents/business-analyst/context.json"
      - ".agent-system/agents/business-analyst/tasks.json"
    conditional_load:
      when_task_requires:
        - "PRPs/.cache/task-briefs/TASK-{current}.md"
        - "PRPs/planning/requirements.md"
        - "PRPs/planning/user-stories.md"
    max_context_tokens: 8000

  context-researcher:
    always_load:
      - ".agent-system/agents/context-researcher/context.json"
      - "workspace/shared/**/*.md"
    conditional_load:
      when_researching:
        - "workspace/features/{feature}/**/*.md"
        - "PRPs/architecture/*.md"
    max_context_tokens: 10000

  implementation-specialist:
    always_load:
      - ".agent-system/agents/implementation-specialist/context.json"
      - ".agent-system/agents/implementation-specialist/tasks.json"
    conditional_load:
      when_task_requires:
        - "PRPs/.cache/task-briefs/TASK-{current}.md"
        - "PRPs/contracts/{feature}-api-contract.md"
        - "workspace/features/{feature}/.meta/"
    never_load:
      - "PRPs/planning/*.md"  # Full planning documents
      - ".agent-system/agents/*/changelog.md"  # Other agents' logs
    max_context_tokens: 8000

  validation-engineer:
    always_load:
      - ".agent-system/agents/validation-engineer/context.json"
      - ".agent-system/agents/validation-engineer/tasks.json"
    conditional_load:
      when_testing:
        - "workspace/features/{feature}/tests/"
        - "PRPs/.cache/agent-views/validation-engineer.md"
    max_context_tokens: 8000

  integration-architect:
    always_load:
      - ".agent-system/agents/integration-architect/context.json"
      - "PRPs/architecture/integration-map.md"
    conditional_load:
      when_designing:
        - "PRPs/contracts/*.md"
        - "workspace/shared/contracts/*.md"
    max_context_tokens: 10000

  documentation-curator:
    always_load:
      - ".agent-system/agents/documentation-curator/context.json"
    conditional_load:
      when_documenting:
        - "workspace/features/{feature}/docs/"
    max_context_tokens: 6000

  security-auditor:
    always_load:
      - ".agent-system/agents/security-auditor/context.json"
      - "PRPs/security/*.md"
    conditional_load:
      when_auditing:
        - "workspace/features/{feature}/**/*.{py,java,js,ts}"
    max_context_tokens: 8000

  performance-optimizer:
    always_load:
      - ".agent-system/agents/performance-optimizer/context.json"
      - "PRPs/architecture/performance-targets.md"
    conditional_load:
      when_optimizing:
        - "reports/metrics/*.json"
    max_context_tokens: 8000

  devops-engineer:
    always_load:
      - ".agent-system/agents/devops-engineer/context.json"
      - "integration/ci-cd/**/*.yaml"
    conditional_load:
      when_deploying:
        - "integration/environments/{environment}/*.yaml"
    max_context_tokens: 8000

global:
  max_total_context: 50000
  compression_enabled: true
  cache_duration_minutes: 30
EOF

# Create PROJECT-TEMPLATE update
cat > .claude/PROJECT-TEMPLATE.md << 'EOF'
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
EOF

# Update .gitignore
echo "📄 Updating .gitignore..."
cat >> .gitignore << 'EOF'

# Agent System
.agent-system/sessions/active/*.lock
.agent-system/sync/conflicts.json
.agent-system/agents/*/context.json.backup
*.tmp
*.cache

# IDE
.vscode/
.idea/
*.swp
*.swo

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
.env

# Java
*.class
*.jar
*.war
target/
build/

# JavaScript/TypeScript
node_modules/
dist/
*.log
.npm
.next/
out/

# Reports (keep structure but not content)
reports/daily/*.md
reports/metrics/*.json
!reports/daily/.gitkeep
!reports/metrics/.gitkeep

# Workspace temporary files
workspace/**/.meta/*.tmp
workspace/**/.meta/*.backup
EOF

# Create .gitkeep files for empty directories
touch reports/daily/.gitkeep
touch reports/metrics/.gitkeep
touch reports/phase-completions/.gitkeep
touch integration/monitoring/dashboards/.gitkeep
touch .agent-system/sessions/active/.gitkeep
touch .agent-system/sessions/history/.gitkeep

echo "✅ Agent Workspace Structure Initialized Successfully!"
echo ""
echo "📊 Structure Summary:"
echo "  - ${#AGENTS[@]} agent directories created"
echo "  - Registry system initialized"
echo "  - Workspace structure ready"
echo "  - Stack detection configured"
echo "  - Context loading rules defined"
echo ""
echo "🚀 Next Steps:"
echo "  1. Run: chmod +x init-agent-workspace.sh"
echo "  2. Review .claude/context-loader.yaml for agent-specific settings"
echo "  3. Start with: /prime-core to load AGENT-ORCHESTRATION.md"
echo "  4. Initialize agents with their specific prompts from .claude/agents/"
EOF

# Make script executable
chmod +x "$BASE_DIR/init-agent-workspace.sh"
