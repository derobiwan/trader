# BMAD Method Integration Plan

Integration plan for combining the [BMAD-METHOD™](https://github.com/bmad-code-org/BMAD-METHOD) with our distributed agent coordination framework and PRP methodology.

## Executive Summary

This plan merges two powerful methodologies:
- **BMAD-METHOD™**: Story-driven development with planning → development phases
- **PRPs Framework**: Distributed agent coordination with 7-phase lifecycle and context optimization

**Result**: A unified system that combines BMAD's structured planning and story-driven development with PRPs' agent coordination and context efficiency.

## Table of Contents
- [Understanding Both Methods](#understanding-both-methods)
- [Integration Architecture](#integration-architecture)
- [Unified Workflow](#unified-workflow)
- [Agent Mapping](#agent-mapping)
- [Directory Structure](#directory-structure)
- [Implementation Plan](#implementation-plan)
- [Migration Strategy](#migration-strategy)
- [Benefits](#benefits)

## Understanding Both Methods

### BMAD-METHOD™ Overview

**Purpose**: Eliminate planning inconsistency and context loss in AI-assisted development

**Key Phases**:
1. **Agentic Planning** (Web UI): Analyst, PM, Architect create detailed specifications
2. **Context-Engineered Development** (IDE): Scrum Master, Developer, QA work from hyper-detailed stories

**Core Principles**:
- Natural language first (everything is markdown)
- Minimal dependencies
- Human-AI collaboration
- Task-driven workflow with specialized agents
- Story sharding for context management

**Artifacts**:
```
docs/
├── prd.md                    # Product Requirements Document
├── architecture.md           # System architecture
├── epics/                    # High-level feature descriptions
├── stories/                  # Detailed development stories
└── qa/
    ├── assessments/          # Quality assessments
    └── gates/                # Quality gates
```

### PRPs Framework Overview

**Purpose**: Distributed agent coordination with minimal context loading

**Key Phases**:
1. Phase 0: Initialization
2. Phase 1: Discovery (Business Analyst, Context Researcher)
3. Phase 2: Architecture (Integration Architect, Security Auditor)
4. Phase 3: Planning (PRP Orchestrator)
5. Phase 4: Implementation (Implementation Specialist, Validation Engineer)
6. Phase 5: Deployment Prep (DevOps Engineer, Documentation Curator)
7. Phase 6: Go-Live
8. Phase 7: Optimization

**Core Principles**:
- Context optimization (90-95% reduction)
- Agent-specific views (2-5KB vs 50KB+)
- PRP lifecycle tracking (backlog → active → completed)
- Task registry with session management

**Artifacts**:
```
PRPs/
├── planning/
│   ├── backlog/
│   ├── active/
│   └── completed/
├── implementation/
│   ├── in-progress/
│   └── completed/
├── architecture/
├── contracts/
└── security/
```

## Comparison Matrix

| Aspect | BMAD-METHOD™ | PRPs Framework |
|--------|-------------|----------------|
| **Phases** | 2 main (Planning, Development) | 7 detailed phases |
| **Planning Output** | PRD + Architecture | PRPs (planning, implementation) |
| **Development Unit** | Stories (sharded from epics) | Tasks (from PRPs) |
| **Context Management** | Story sharding | Agent views (2-5KB) |
| **Agent Count** | 6 core (Analyst, PM, Architect, Scrum Master, Dev, QA) | 10 specialized |
| **File Structure** | docs/ (flat-ish) | PRPs/ (lifecycle-tracked) |
| **Interface** | Web UI + IDE | CLI + optional Archon MCP |
| **Quality Assurance** | QA Agent + gates | Validation Engineer + gates |
| **Documentation** | Markdown-based | Markdown-based |
| **Collaboration** | Human-in-the-loop | Agent coordination + optional Archon |

## Integration Architecture

### Unified System: BMAD-Enhanced PRPs

```
┌─────────────────────────────────────────────────────────────────┐
│                         PHASE 0: Initialization                  │
│                         PRP Orchestrator                         │
└───────────────┬─────────────────────────────────────────────────┘
                │
    ┌───────────┴───────────┐
    │                       │
    ▼                       ▼
┌─────────────────────┐   ┌─────────────────────┐
│   BMAD Planning     │   │   PRPs Discovery    │
│   Phase (Phase 1-2) │   │   (Phase 1-2)       │
└──────────┬──────────┘   └──────────┬──────────┘
           │                         │
           │  ┌──────────────────────┘
           │  │
           ▼  ▼
┌─────────────────────────────────────────┐
│   Unified Planning Output               │
│   • BMAD: prd.md, architecture.md       │
│   • PRPs: planning/completed/*.md       │
│   • Merged: architecture/, contracts/   │
└──────────┬──────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────┐
│   BMAD Story Generation (Phase 3)       │
│   • Scrum Master creates stories        │
│   • Stories → PRPs/implementation/      │
│   • Epics → Task breakdown              │
└──────────┬──────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────┐
│   Hybrid Development (Phase 4)          │
│   • BMAD: Story-driven development      │
│   • PRPs: Task-based agent coordination │
│   • Context: Agent views + Story shards │
└──────────┬──────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────┐
│   Unified QA & Deployment (Phase 5-6)   │
│   • BMAD: QA gates + assessments        │
│   • PRPs: Validation gates + DevOps     │
└─────────────────────────────────────────┘
```

### Key Integration Points

#### 1. Planning Phase Integration (Phases 1-2)

**BMAD Planning Agents → PRPs Agents**:
- BMAD Analyst → Context Researcher (investigates market/tech)
- BMAD PM → Business Analyst (creates requirements)
- BMAD Architect → Integration Architect (designs system)

**Output Mapping**:
```
BMAD docs/prd.md           → PRPs/planning/completed/[project]-requirements.md
BMAD docs/architecture.md  → PRPs/architecture/[project]-architecture.md
                           → PRPs/contracts/[project]-api-contracts.md
                           → PRPs/security/[project]-security.md
```

#### 2. Story → Task Conversion (Phase 3)

**BMAD Stories → PRP Tasks**:
```python
# BMAD Story Structure
docs/stories/STORY-001.md:
  - Story Description
  - Acceptance Criteria
  - Technical Context
  - Implementation Steps

# Converted to PRP Task
.agent-system/registry/tasks.json:
  TASK-001: {
    "title": "Story-001: [title]",
    "prp_source": "PRPs/implementation/in-progress/[feature].md",
    "story_reference": "docs/stories/STORY-001.md",
    "bmad_epic": "docs/epics/EPIC-001.md"
  }
```

#### 3. Context Management Synergy

**Combined Approach**:
- **BMAD Story Sharding**: Break large epics into focused stories
- **PRPs Agent Views**: Generate 2-5KB views per agent from stories
- **Result**: Double context optimization

```bash
BMAD Epic (50KB)
    ↓ Story sharding
Story 1 (10KB) + Story 2 (10KB) + Story 3 (10KB)
    ↓ Agent view generation
Agent View: Implementation (3KB) + Validation (2KB)
```

#### 4. Quality Assurance Integration

**Unified QA System**:
- BMAD QA Gates + PRPs Validation Gates = Comprehensive quality
- BMAD QA Assessments = Pre-implementation quality checks
- PRPs Phase-based gates = In-progress validation

```
BMAD QA Gate            PRPs Validation Gate
     ↓                         ↓
┌────────────────────────────────────────┐
│  Unified Quality Gate                  │
│  • Code coverage >80%                  │
│  • Security scan clean                 │
│  • BMAD assessment passed              │
│  • PRPs phase requirements met         │
└────────────────────────────────────────┘
```

## Unified Workflow

### Complete Project Lifecycle

```
┌─────────────────────────────────────────────────────────────┐
│ PHASE 0: INITIALIZATION                                     │
│ • PRP Orchestrator activates BMAD + PRPs agents             │
│ • Load BMAD templates and PRPs templates                    │
└────────────┬────────────────────────────────────────────────┘
             │
┌────────────▼────────────────────────────────────────────────┐
│ PHASE 1: BMAD PLANNING + PRPs DISCOVERY (Combined)          │
│                                                              │
│ BMAD Track:                     PRPs Track:                 │
│ • Analyst research              • Context Researcher        │
│ • PM creates PRD                • Business Analyst          │
│                                                              │
│ Output: docs/prd.md + PRPs/planning/active/[project].md    │
└────────────┬────────────────────────────────────────────────┘
             │
┌────────────▼────────────────────────────────────────────────┐
│ PHASE 2: BMAD ARCHITECTURE + PRPs DESIGN (Merged)           │
│                                                              │
│ BMAD Track:                     PRPs Track:                 │
│ • Architect designs system      • Integration Architect     │
│                                 • Security Auditor          │
│                                 • Performance Optimizer     │
│                                                              │
│ Output: docs/architecture.md + PRPs/architecture/          │
│         PRPs/contracts/ + PRPs/security/                   │
└────────────┬────────────────────────────────────────────────┘
             │
             │ Move PRPs to completed/
             ↓
┌─────────────────────────────────────────────────────────────┐
│ PHASE 3: STORY GENERATION + TASK BREAKDOWN                  │
│                                                              │
│ BMAD Scrum Master:              PRP Orchestrator:           │
│ • Shard PRD into epics          • Create implementation PRP │
│ • Create stories from epics     • Break into tasks          │
│                                                              │
│ Output: docs/epics/ + docs/stories/                        │
│         PRPs/implementation/in-progress/[feature].md       │
│         .agent-system/registry/tasks.json                  │
└────────────┬────────────────────────────────────────────────┘
             │
┌────────────▼────────────────────────────────────────────────┐
│ PHASE 4: HYBRID DEVELOPMENT                                 │
│                                                              │
│ BMAD Workflow:                  PRPs Workflow:              │
│ 1. Scrum Master reviews story   1. Agent claims task        │
│ 2. Developer implements         2. Loads agent view         │
│ 3. Mid-dev QA checks           3. Executes with context    │
│ 4. Run validations             4. Updates changelog        │
│                                                              │
│ Context: Story (10KB) → Agent View (3KB)                   │
│                                                              │
│ Output: Implemented features + Updated stories             │
└────────────┬────────────────────────────────────────────────┘
             │
┌────────────▼────────────────────────────────────────────────┐
│ PHASE 5: UNIFIED QA + DEPLOYMENT PREP                       │
│                                                              │
│ BMAD QA:                        PRPs QA:                    │
│ • QA assessments                • Validation Engineer       │
│ • Quality gates check           • Phase 5 gates check       │
│ • Final story validation        • Documentation complete    │
│                                                              │
│ Output: docs/qa/assessments/ + deployment configs          │
└────────────┬────────────────────────────────────────────────┘
             │
┌────────────▼────────────────────────────────────────────────┐
│ PHASE 6-7: DEPLOYMENT + OPTIMIZATION                        │
│ • DevOps Engineer deploys                                   │
│ • Performance Optimizer monitors                            │
│ • Move to PRPs/implementation/completed/                   │
└─────────────────────────────────────────────────────────────┘
```

## Agent Mapping

### Unified Agent Team (13 Total)

| PRPs Agent | BMAD Agent | Unified Role | When Active |
|-----------|-----------|--------------|-------------|
| **PRP Orchestrator** | *N/A* | Master coordinator | All phases |
| **Business Analyst** | **PM** | Requirements & business value | Phase 1 |
| **Context Researcher** | **Analyst** | Market research & tech investigation | Phase 1 |
| **Integration Architect** | **Architect** | System design & architecture | Phase 2 |
| **Security Auditor** | *(QA partial)* | Security requirements & compliance | Phase 2, 4 |
| **Performance Optimizer** | *(Architect partial)* | Performance targets & optimization | Phase 2, 7 |
| *N/A* | **Scrum Master** | Story creation & sprint planning | Phase 3 |
| **Implementation Specialist** | **Developer** | Code implementation | Phase 4 |
| **Validation Engineer** | **QA** | Testing & quality validation | Phase 4-5 |
| **DevOps Engineer** | *(Developer partial)* | Deployment & infrastructure | Phase 5-6 |
| **Documentation Curator** | *(PM partial)* | User guides & API docs | Phase 5 |

**Total**: 10 PRPs agents + 3 BMAD-specific (PM, Architect, Scrum Master merge with PRPs roles)

### Agent Collaboration Matrix

```
Phase 1 (Planning):
  Context Researcher (Analyst) → Business Analyst (PM)
  Output: PRD + Context Report

Phase 2 (Architecture):
  Integration Architect (Architect) → Security Auditor + Performance Optimizer
  Output: Architecture + Security + Performance specs

Phase 3 (Story Generation):
  PRP Orchestrator + Scrum Master → Task breakdown
  Output: Stories + Tasks

Phase 4 (Development):
  Implementation Specialist (Developer) ↔ Validation Engineer (QA)
  Output: Code + Tests

Phase 5-6 (Deployment):
  DevOps Engineer + Documentation Curator + Validation Engineer (QA)
  Output: Deployed system + Docs
```

## Directory Structure

### Unified Project Structure

```
project/
│
├── docs/                          # BMAD artifacts
│   ├── prd.md                     # Product Requirements (from BMAD PM)
│   ├── architecture.md            # System architecture (from BMAD Architect)
│   ├── epics/                     # High-level features
│   │   ├── EPIC-001.md
│   │   └── EPIC-002.md
│   ├── stories/                   # Detailed dev stories (from Scrum Master)
│   │   ├── STORY-001.md
│   │   ├── STORY-002.md
│   │   └── story-notes/           # Implementation notes
│   └── qa/
│       ├── assessments/           # Quality assessments
│       └── gates/                 # Quality gate tracking
│
├── PRPs/                          # PRPs framework artifacts
│   ├── planning/
│   │   ├── backlog/               # Future features
│   │   ├── active/                # Current planning
│   │   └── completed/             # Approved plans
│   │       └── [project]-requirements.md  # Merged from docs/prd.md
│   │
│   ├── implementation/
│   │   ├── in-progress/           # Active development
│   │   │   └── [feature]-impl.md  # Links to docs/stories/
│   │   └── completed/             # Deployed features
│   │
│   ├── architecture/              # Merged from docs/architecture.md
│   │   └── [project]-architecture.md
│   │
│   ├── contracts/                 # API specifications
│   │   └── [feature]-api-contract.md
│   │
│   ├── security/                  # Security requirements
│   │   └── [feature]-security.md
│   │
│   ├── templates/                 # PRP + BMAD templates
│   │   ├── prp_base.md
│   │   ├── prp_planning.md
│   │   ├── bmad_story.md          # NEW: BMAD story template
│   │   └── bmad_epic.md           # NEW: BMAD epic template
│   │
│   └── .cache/
│       ├── agent-views/           # PRPs agent optimization
│       ├── task-briefs/           # Task-specific context
│       └── story-views/           # NEW: Story-based agent views
│
├── .agent-system/                 # PRPs coordination
│   ├── registry/
│   │   ├── tasks.json             # Tasks (linked to stories)
│   │   ├── stories.json           # NEW: Story registry
│   │   └── epics.json             # NEW: Epic tracking
│   ├── sessions/
│   ├── agents/
│   └── sync/
│       └── bmad-sync.json         # NEW: BMAD workflow state
│
├── workspace/
│   ├── features/
│   ├── fixes/
│   └── shared/
│
└── .claude/
    ├── context-loader.yaml        # Updated with BMAD story loading
    ├── mcp-config.yaml
    └── agents/                    # All 13 agent definitions
```

### File Relationship Map

```
docs/prd.md ──────────┐
                      ├──→ PRPs/planning/completed/[project]-requirements.md
docs/architecture.md ─┤
                      └──→ PRPs/architecture/[project]-architecture.md

docs/epics/EPIC-001.md ──→ .agent-system/registry/epics.json
                         ↓
docs/stories/STORY-001.md ──→ .agent-system/registry/stories.json
                            ↓
                            .agent-system/registry/tasks.json (TASK-001)
                            ↓
PRPs/implementation/in-progress/feature-impl.md
```

## Implementation Plan

### Phase 1: Foundation (Week 1)

#### 1.1 Install BMAD-METHOD

```bash
# Clone BMAD
cd ~/Projects
git clone https://github.com/bmad-code-org/BMAD-METHOD.git
cd BMAD-METHOD

# Install dependencies
npm install

# Configure for integration
cp .env.example .env
# Edit .env with settings
```

#### 1.2 Create Integration Scripts

**File**: `scripts/bmad-integration.py`

```python
#!/usr/bin/env python3
"""
BMAD-PRPs Integration Manager
Bridges BMAD-METHOD with PRPs framework
"""

import json
from pathlib import Path
import yaml

class BMADIntegration:
    def __init__(self):
        self.bmad_docs = Path("docs")
        self.prps_dir = Path("PRPs")
        self.agent_system = Path(".agent-system")

    def import_prd(self):
        """Import BMAD PRD to PRPs planning"""
        prd = (self.bmad_docs / "prd.md").read_text()

        # Convert to PRPs format
        prp_requirements = self.convert_prd_to_prp(prd)

        # Save to PRPs
        output = self.prps_dir / "planning" / "completed" / "project-requirements.md"
        output.write_text(prp_requirements)

    def import_architecture(self):
        """Import BMAD architecture to PRPs architecture"""
        arch = (self.bmad_docs / "architecture.md").read_text()

        # Split into components
        architecture_prp = self.extract_architecture(arch)
        contracts_prp = self.extract_api_contracts(arch)
        security_prp = self.extract_security(arch)

        # Save to PRPs
        (self.prps_dir / "architecture" / "project-architecture.md").write_text(architecture_prp)
        (self.prps_dir / "contracts" / "api-contracts.md").write_text(contracts_prp)
        (self.prps_dir / "security" / "security-requirements.md").write_text(security_prp)

    def sync_stories_to_tasks(self):
        """Convert BMAD stories to PRP tasks"""
        stories_dir = self.bmad_docs / "stories"

        # Load existing tasks
        tasks_file = self.agent_system / "registry" / "tasks.json"
        with open(tasks_file) as f:
            registry = json.load(f)

        # Create story registry
        story_registry = {
            "stories": {},
            "epics": {}
        }

        # Process each story
        for story_file in stories_dir.glob("STORY-*.md"):
            story = self.parse_story(story_file)

            # Create corresponding task
            task_id = f"TASK-{story['number']:03d}"
            registry['tasks'][task_id] = {
                "title": f"Story-{story['number']}: {story['title']}",
                "description": story['description'],
                "story_reference": str(story_file.relative_to(Path.cwd())),
                "bmad_epic": story.get('epic'),
                "status": "pending",
                "priority": story.get('priority', 'medium'),
                "estimated_hours": story.get('estimate', 8)
            }

            # Add to story registry
            story_registry['stories'][f"STORY-{story['number']:03d}"] = {
                "file": str(story_file.relative_to(Path.cwd())),
                "task_id": task_id,
                "epic_id": story.get('epic'),
                "status": "pending"
            }

        # Save updated registries
        with open(tasks_file, 'w') as f:
            json.dump(registry, f, indent=2)

        story_reg_file = self.agent_system / "registry" / "stories.json"
        with open(story_reg_file, 'w') as f:
            json.dump(story_registry, f, indent=2)

    def generate_story_views(self):
        """Generate agent views from BMAD stories"""
        # For each story, create agent-specific views
        # Similar to generate-agent-views.py but for stories
        pass

    def convert_prd_to_prp(self, prd_content):
        """Convert BMAD PRD format to PRP format"""
        # Parse PRD and restructure for PRPs
        # Add PRP sections: Goal, Why, What, Context, etc.
        pass

    def parse_story(self, story_file):
        """Parse BMAD story file"""
        content = story_file.read_text()
        # Extract story metadata
        # Return structured story data
        pass
```

#### 1.3 Update Context Loader

**File**: `.claude/context-loader.yaml`

```yaml
global:
  max_total_context: 50000
  bmad_integration:
    enabled: true
    story_loading: true
    epic_tracking: true

agents:
  orchestrator:
    always_load:
      - ".agent-system/registry/tasks.json"
      - ".agent-system/registry/stories.json"    # NEW
      - ".agent-system/registry/epics.json"      # NEW

  business-analyst:
    always_load:
      - ".agent-system/agents/business-analyst/context.json"
      - "docs/prd.md"                            # NEW: BMAD PRD

  implementation-specialist:
    always_load:
      - ".agent-system/agents/implementation-specialist/context.json"
    conditional_load:
      when_task_requires:
        - "docs/stories/STORY-{current}.md"     # NEW: BMAD story
        - "PRPs/.cache/story-views/{story_id}.md"  # NEW: Story view

  validation-engineer:
    always_load:
      - ".agent-system/agents/validation-engineer/context.json"
      - "docs/qa/gates/*.md"                    # NEW: BMAD QA gates
```

### Phase 2: Agent Integration (Week 2)

#### 2.1 Create Unified Agent Definitions

**File**: `.claude/agents/scrum-master.md`

```markdown
# Scrum Master Agent (BMAD Integration)

## Role
Create detailed development stories from epics and architecture documents.

## Responsibilities
- Review PRD and architecture
- Break epics into implementable stories
- Ensure stories have complete context
- Create story acceptance criteria
- Link stories to PRPs tasks

## Workflow
1. Load: docs/prd.md, docs/architecture.md, docs/epics/
2. For each epic:
   - Create 3-5 stories
   - Include technical context
   - Define acceptance criteria
   - Estimate effort
3. Output: docs/stories/STORY-NNN.md
4. Sync: Create corresponding PRP tasks

## Story Template
```
# Story NNN: [Title]

## Epic Reference
EPIC-XXX: [Epic title]

## Description
[What needs to be built]

## Technical Context
[Architecture decisions, dependencies, patterns]

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2

## PRP Task
TASK-NNN (auto-generated)

## Estimate
X hours
```

## Context Budget
10KB max (uses story sharding + PRPs agent views)
```

#### 2.2 Update Existing Agents

Update all agent definitions to understand BMAD artifacts:

```python
# Example: Implementation Specialist update
implementation_specialist = {
    "understands": [
        "PRPs/implementation/in-progress/*.md",
        "docs/stories/STORY-*.md",              # NEW
        "docs/epics/EPIC-*.md"                  # NEW
    ],
    "works_with": [
        "Scrum Master (story context)",        # NEW
        "Validation Engineer (QA gates)"        # UPDATED
    ]
}
```

### Phase 3: Workflow Scripts (Week 3)

#### 3.1 BMAD-Enhanced PRP Orchestrator

**File**: `scripts/bmad-orchestrator.py`

```python
#!/usr/bin/env python3
"""
BMAD-Enhanced PRP Orchestrator
Coordinates BMAD planning → PRPs development workflow
"""

class BMADOrchestrator:
    def __init__(self):
        self.bmad = BMADIntegration()
        self.prp_orchestrator = PRPOrchestrator()

    def start_project(self, project_name):
        """Initialize BMAD + PRPs project"""
        print("🚀 Starting BMAD-PRPs project: {project_name}")

        # Phase 1: BMAD Planning
        print("\n📋 Phase 1: BMAD Planning")
        self.run_bmad_planning()

        # Import to PRPs
        print("\n🔄 Importing to PRPs framework")
        self.bmad.import_prd()
        self.bmad.import_architecture()

        # Phase 3: Story Generation
        print("\n📖 Phase 3: Story Generation")
        self.run_scrum_master()
        self.bmad.sync_stories_to_tasks()

        # Phase 4: Development Ready
        print("\n✅ Ready for development")
        self.show_next_steps()

    def run_bmad_planning(self):
        """Execute BMAD planning phase"""
        # 1. Analyst research
        # 2. PM creates PRD
        # 3. Architect designs system
        pass

    def run_scrum_master(self):
        """Execute Scrum Master story creation"""
        # Load PRD + Architecture
        # Create epics
        # Break into stories
        pass

    def show_next_steps(self):
        """Display next actions"""
        print("""
Next Steps:
1. Review stories in docs/stories/
2. Claim first task: python scripts/agent-task-manager.py claim --agent implementation-specialist --task TASK-001
3. Start development with context:
   - Story: docs/stories/STORY-001.md
   - Agent view: PRPs/.cache/story-views/STORY-001.md
   - Task: TASK-001
        """)
```

#### 3.2 Story-Based Development Script

**File**: `scripts/story-dev.py`

```python
#!/usr/bin/env python3
"""
Story-based development workflow
Combines BMAD stories with PRPs agent coordination
"""

def work_on_story(story_id):
    """Start development on a BMAD story"""
    # 1. Load story
    story = load_story(f"docs/stories/{story_id}.md")

    # 2. Find corresponding task
    task_id = find_task_for_story(story_id)

    # 3. Generate agent view
    generate_story_view(story_id)

    # 4. Claim task
    claim_task(task_id, "implementation-specialist")

    # 5. Show development context
    print(f"""
Development Context:
- Story: docs/stories/{story_id}.md
- Task: {task_id}
- Agent View: PRPs/.cache/story-views/{story_id}.md (3KB optimized)
- Epic: {story['epic']}
- Estimate: {story['estimate']} hours

Start implementation with: /prp-task-execute {task_id}
    """)
```

### Phase 4: Testing & Validation (Week 4)

#### 4.1 Unified QA System

```python
class UnifiedQA:
    def validate_story(self, story_id):
        """Run both BMAD QA gates and PRPs validation gates"""
        # BMAD QA gates
        bmad_gates = self.check_bmad_gates(story_id)

        # PRPs validation gates
        prps_gates = self.check_prps_gates(story_id)

        # Combined result
        return bmad_gates and prps_gates

    def check_bmad_gates(self, story_id):
        """Check BMAD quality gates"""
        gates = self.load_qa_gates(f"docs/qa/gates/{story_id}.md")
        return all(gate['passed'] for gate in gates)

    def check_prps_gates(self, story_id):
        """Check PRPs validation gates"""
        task_id = self.find_task_for_story(story_id)
        # Run PRPs validation (tests, coverage, security, etc.)
        return self.run_prps_validation(task_id)
```

## Migration Strategy

### For Existing PRPs Projects

#### Option 1: Add BMAD to Existing Project

```bash
# 1. Initialize BMAD structure
mkdir -p docs/{epics,stories,qa/{assessments,gates}}

# 2. Convert existing PRPs to BMAD format
python scripts/bmad-integration.py convert-prps-to-bmad \
  --prp PRPs/planning/completed/feature.md \
  --output docs/

# 3. Enable BMAD integration
# Edit .claude/context-loader.yaml:
#   bmad_integration.enabled: true

# 4. Continue with hybrid workflow
python scripts/bmad-orchestrator.py continue-project
```

#### Option 2: Start Fresh with Unified System

```bash
# 1. Initialize unified project
python scripts/bmad-orchestrator.py start-project "my-project"

# 2. Complete BMAD planning (Web UI or agents)
# 3. Import to PRPs
python scripts/bmad-integration.py import-all

# 4. Generate stories
python scripts/bmad-orchestrator.py generate-stories

# 5. Start development
python scripts/story-dev.py work-on-story STORY-001
```

### For Existing BMAD Projects

```bash
# 1. Add PRPs framework to BMAD project
cp -r /path/to/PRPs-agentic-eng/.agent-system .
cp -r /path/to/PRPs-agentic-eng/PRPs .
cp -r /path/to/PRPs-agentic-eng/scripts .

# 2. Import BMAD artifacts
python scripts/bmad-integration.py import-prd
python scripts/bmad-integration.py import-architecture
python scripts/bmad-integration.py sync-stories-to-tasks

# 3. Generate agent views
python scripts/generate-agent-views.py --all

# 4. Ready for PRPs agent coordination
python scripts/agent-task-manager.py list
```

## Benefits

### Combined Strengths

| Capability | BMAD Contribution | PRPs Contribution | Unified Benefit |
|-----------|-------------------|-------------------|-----------------|
| **Planning** | Structured PRD/Architecture | Multi-phase discovery | Comprehensive specs |
| **Context Management** | Story sharding | Agent views (2-5KB) | Double optimization |
| **Development** | Story-driven workflow | Task-based coordination | Clear execution path |
| **Quality** | QA gates & assessments | Phase-based validation | Comprehensive QA |
| **Collaboration** | Human-in-the-loop | Agent coordination | Team + AI synergy |
| **Tracking** | Story progress | PRP lifecycle + tasks | Complete visibility |
| **Documentation** | Markdown artifacts | PRP methodology | Rich documentation |
| **Flexibility** | Expansion packs | 7-phase framework | Adaptable to any project |

### For Teams

- ✅ **Structured Planning**: BMAD's planning phase ensures thorough specs
- ✅ **Efficient Development**: PRPs agent coordination minimizes context
- ✅ **Quality Assurance**: Combined QA from both methodologies
- ✅ **Clear Progress**: Story progress + PRP lifecycle + task tracking
- ✅ **Team Collaboration**: Human-in-the-loop + agent coordination

### For Complex Projects

- ✅ **Manageable Complexity**: Stories + epics + PRPs break down large systems
- ✅ **Context Control**: Story sharding + agent views keep context minimal
- ✅ **Comprehensive Coverage**: 13 specialized agents cover all aspects
- ✅ **Traceable Progress**: Multiple tracking levels (epic → story → task)

### For Solo Developers

- ✅ **Guided Workflow**: BMAD stories provide clear development path
- ✅ **Agent Assistance**: PRPs agents help with all phases
- ✅ **Flexible Adoption**: Use BMAD planning or PRPs directly
- ✅ **Quality Built-in**: QA gates ensure production-ready code

## Summary

The BMAD-PRPs integration creates a unified system that:

1. **Uses BMAD for structured planning**: Analyst, PM, Architect create comprehensive specs
2. **Generates stories with Scrum Master**: Break large features into implementable units
3. **Coordinates with PRPs agents**: 10+ specialized agents execute with minimal context
4. **Tracks progress at multiple levels**: Epic → Story → Task → PRP lifecycle
5. **Validates comprehensively**: BMAD QA gates + PRPs validation gates
6. **Optimizes context twice**: Story sharding + agent views = 2-5KB per agent
7. **Remains flexible**: Use BMAD, PRPs, or both as needed

**Result**: A powerful, unified system that combines the best of structured planning (BMAD) with efficient agent coordination (PRPs) for production-ready software delivery.

---

**Next Steps**:
1. Review this integration plan
2. Decide on adoption strategy (existing project vs fresh start)
3. Follow implementation plan phases
4. Start with Phase 1 (Foundation) to test integration

**The framework evolves from simple file-based coordination to intelligent story-driven development with comprehensive AI agent collaboration. 🚀**
