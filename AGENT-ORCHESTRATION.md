Standardized Agent Orchestration Process for Claude Code
I'll provide you with a comprehensive process framework that integrates all agents with the PRP methodology. This can be injected into your Claude Code environment as a master orchestration document.
The Master Process Document: AGENT-ORCHESTRATION.md
Create this file in your project root alongside CLAUDE.md:
markdown# AGENT-ORCHESTRATION.md - Systematic Agent Collaboration Framework

This document defines the standardized process for utilizing all specialized agents in coordination with the PRP framework. When working on any feature or project, Claude should follow this systematic approach to ensure comprehensive, high-quality delivery.

## Core Principle: Progressive Enhancement Through Specialist Collaboration

Every project follows a predictable flow where each agent contributes their expertise at the optimal moment. This is not a waterfall - agents collaborate continuously, but there's a logical sequence that maximizes value.

## Master Orchestration Process

### PHASE 0: Project Initialization (Always Start Here)

```yaml
trigger: "New project/feature request received"
primary_agent: "PRP Orchestrator"
duration: "30 minutes"

activation_sequence:
  1. ALWAYS_FIRST:
     command: "/prime-core"
     purpose: "Load project context from CLAUDE.md"

  2. ORCHESTRATOR_ACTIVATION:
     prompt: |
       "PRP Orchestrator, we have a new [project/feature/fix]: [description].
       Initialize the standard orchestration process and coordinate all agents."

  3. CONTEXT_GATHERING:
     prompt: |
       "Context Researcher, investigate existing codebase for relevant patterns,
       similar implementations, and potential gotchas related to [project]."

checklist:
  - [ ] Project context loaded
  - [ ] Orchestrator activated and briefed
  - [ ] Initial context research complete
  - [ ] All agents aware of project scope
PHASE 1: Business Discovery & Requirements
yamltrigger: "Project initialized"
primary_agents: ["Business Analyst", "Context Researcher"]
duration: "1-3 days"
prp_commands: ["/prp-planning-create", "/user-story-rapid"]

workflow:
  1. BUSINESS_ANALYSIS:
     agent: "Business Analyst"
     prompt: |
       "Business Analyst, conduct discovery for [project]:
       - Identify all stakeholders and their needs
       - Define success metrics and ROI
       - Create user stories with acceptance criteria
       - Prioritize features using MoSCoW"
     outputs:
       - requirements.md
       - user-stories.md
       - success-metrics.md

  2. DEEP_CONTEXT_RESEARCH:
     agent: "Context Researcher"
     prompt: |
       "Context Researcher, investigate:
       - Similar implementations in codebase
       - External service documentation
       - Known issues and gotchas
       - Reusable components"
     outputs:
       - context-report.md
       - gotchas.md
       - reusable-components.md

  3. PRP_PLANNING_CREATION:
     command: "/prp-planning-create"
     inputs: "[business requirements + context research]"
     outputs: "PRPs/[project]-prd.md"

validation_gates:
  - [ ] Stakeholder requirements documented
  - [ ] Success metrics defined
  - [ ] Technical context researched
  - [ ] Initial PRP created

decision_point: "PROCEED if requirements clear, else ITERATE with stakeholders"
PHASE 2: Technical Architecture & Security
yamltrigger: "Requirements approved"
primary_agents: ["Integration Architect", "Security Auditor", "Performance Optimizer"]
duration: "2-3 days"
prp_commands: ["/api-contract-define", "/prp-spec-create"]

workflow:
  1. ARCHITECTURE_DESIGN:
     agent: "Integration Architect"
     prompt: |
       "Integration Architect, design technical architecture for [project]:
       - Define integration patterns
       - Specify API contracts
       - Design data flows
       - Plan service interactions"
     command: "/api-contract-define"
     outputs:
       - architecture.md
       - PRPs/contracts/[project]-api-contract.md
       - integration-map.md

  2. SECURITY_ASSESSMENT:
     agent: "Security & Compliance Auditor"
     prompt: |
       "Security Auditor, assess requirements for:
       - Security vulnerabilities
       - Compliance requirements (GDPR, etc.)
       - Data protection needs
       - Authentication/authorization design"
     outputs:
       - security-requirements.md
       - compliance-checklist.md
       - threat-model.md

  3. PERFORMANCE_PLANNING:
     agent: "Performance Optimizer"
     prompt: |
       "Performance Optimizer, establish:
       - Performance targets and SLAs
       - Scalability requirements
       - Optimization opportunities
       - Capacity planning"
     outputs:
       - performance-targets.md
       - scalability-plan.md

validation_gates:
  - [ ] Architecture documented and reviewed
  - [ ] Security requirements integrated
  - [ ] Performance targets established
  - [ ] API contracts defined

decision_point: "PROCEED if architecture approved, else REFINE design"
PHASE 3: Implementation Planning
yamltrigger: "Architecture approved"
primary_agent: "PRP Orchestrator"
duration: "1 day"
prp_commands: ["/prp-base-create", "/prp-task-create"]

workflow:
  1. COMPREHENSIVE_PRP_CREATION:
     command: "/prp-base-create"
     inputs: |
       "Create implementation PRP using:
       - PRPs/[project]-prd.md (from Phase 1)
       - PRPs/contracts/[project]-api-contract.md (from Phase 2)
       - Security requirements
       - Performance targets"
     outputs: "PRPs/[project]-implementation.md"

  2. TASK_BREAKDOWN:
     command: "/prp-task-create"
     parallel_agents:
       - Implementation Specialist: "Review implementation approach"
       - Validation Engineer: "Define test strategy"
       - DevOps Engineer: "Plan deployment pipeline"
     outputs:
       - implementation-tasks.md
       - test-strategy.md
       - deployment-plan.md

  3. DOCUMENTATION_PLANNING:
     agent: "Documentation Curator"
     prompt: |
       "Documentation Curator, prepare:
       - Documentation structure
       - Auto-generation setup
       - User guide templates
       - API documentation plan"
     outputs:
       - documentation-plan.md

validation_gates:
  - [ ] Implementation PRP complete with all context
  - [ ] Task breakdown reviewed by specialists
  - [ ] Test strategy defined
  - [ ] Documentation plan ready

decision_point: "PROCEED to implementation, else CLARIFY requirements"
PHASE 4: Implementation Execution
yamltrigger: "Implementation plan approved"
primary_agents: ["Implementation Specialist", "Validation Engineer"]
duration: "1-2 weeks"
prp_commands: ["/prp-base-execute", "/smart-commit"]

workflow:
  1. IMPLEMENTATION_EXECUTION:
     agent: "Implementation Specialist"
     command: "/prp-base-execute PRPs/[project]-implementation.md"
     continuous_validation:
       - After each component: "Run unit tests"
       - After integration: "Run integration tests"
       - After feature: "Run e2e tests"
     outputs:
       - Source code
       - Unit tests
       - Integration tests

  2. CONTINUOUS_VALIDATION:
     agent: "Validation Engineer"
     parallel: true
     prompt: |
       "Validation Engineer, continuously:
       - Review code quality
       - Run test suites
       - Check coverage
       - Validate acceptance criteria"
     gates:
       - Level 1: "Syntax and linting"
       - Level 2: "Unit test coverage >80%"
       - Level 3: "Integration tests passing"
       - Level 4: "E2E tests passing"

  3. SECURITY_VALIDATION:
     agent: "Security Auditor"
     trigger: "Each commit"
     prompt: |
       "Security Auditor, scan for:
       - Security vulnerabilities
       - Compliance violations
       - Data leaks
       - Authentication issues"

  4. PERFORMANCE_MONITORING:
     agent: "Performance Optimizer"
     trigger: "Feature complete"
     prompt: |
       "Performance Optimizer, validate:
       - Response times meet SLA
       - Resource usage acceptable
       - Scalability targets met"

continuous_integration:
  - command: "/review-staged-unstaged"  # Before each commit
  - command: "/smart-commit"             # For each commit
  - command: "/review-general"           # Daily comprehensive review

validation_gates:
  - [ ] All 4 validation levels passing
  - [ ] Security scan clean
  - [ ] Performance targets met
  - [ ] Code review completed

decision_point: "PROCEED to deployment prep, else FIX issues"
PHASE 5: Deployment Preparation
yamltrigger: "Implementation complete and validated"
primary_agents: ["DevOps Engineer", "Documentation Curator"]
duration: "2-3 days"
prp_commands: ["/create-pr", "/onboarding"]

workflow:
  1. INFRASTRUCTURE_SETUP:
     agent: "DevOps Engineer"
     prompt: |
       "DevOps Engineer, prepare production:
       - Configure infrastructure
       - Set up monitoring
       - Create deployment pipeline
       - Prepare rollback procedures"
     outputs:
       - infrastructure-as-code/
       - monitoring-config.yaml
       - deployment-pipeline.yaml
       - rollback-plan.md

  2. DOCUMENTATION_FINALIZATION:
     agent: "Documentation Curator"
     prompt: |
       "Documentation Curator, complete:
       - API documentation
       - User guides
       - Deployment guides
       - Troubleshooting guides"
     command: "/onboarding"  # Generate onboarding docs
     outputs:
       - docs/api/
       - docs/user-guide/
       - docs/deployment/
       - TROUBLESHOOTING.md

  3. FINAL_INTEGRATION_CHECK:
     agent: "Integration Architect"
     prompt: |
       "Integration Architect, verify:
       - All integrations working
       - Error handling complete
       - Retry logic implemented
       - Monitoring hooks in place"

  4. PULL_REQUEST_CREATION:
     command: "/create-pr"
     includes:
       - Implementation code
       - Tests
       - Documentation
       - Deployment configuration

validation_gates:
  - [ ] Infrastructure ready
  - [ ] Monitoring configured
  - [ ] Documentation complete
  - [ ] PR created and reviewed

decision_point: "PROCEED to deployment, else ADDRESS concerns"
PHASE 6: Deployment & Go-Live
yamltrigger: "PR approved"
primary_agents: ["DevOps Engineer", "All Agents on standby"]
duration: "1 day"

workflow:
  1. STAGING_DEPLOYMENT:
     agent: "DevOps Engineer"
     prompt: |
       "DevOps Engineer, deploy to staging:
       - Execute deployment pipeline
       - Run smoke tests
       - Verify monitoring
       - Test rollback procedure"
     validation:
       - Validation Engineer: "Run staging tests"
       - Security Auditor: "Security scan staging"
       - Performance Optimizer: "Load test staging"

  2. PRODUCTION_DEPLOYMENT:
     agent: "DevOps Engineer"
     strategy: "Blue-green with canary"
     prompt: |
       "DevOps Engineer, deploy to production:
       - 10% canary deployment
       - Monitor metrics for 30 minutes
       - If healthy, proceed to 50%
       - If healthy, proceed to 100%"
     rollback_trigger: "Error rate >1% or latency >SLA"

  3. POST_DEPLOYMENT_VALIDATION:
     parallel_agents:
       - Validation Engineer: "Run production smoke tests"
       - Performance Optimizer: "Monitor performance metrics"
       - Security Auditor: "Check security alerts"
       - Integration Architect: "Verify all integrations"

  4. BUSINESS_VALIDATION:
     agent: "Business Analyst"
     prompt: |
       "Business Analyst, validate:
       - Success metrics being tracked
       - User feedback channels active
       - Stakeholders notified
       - ROI measurement in place"

validation_gates:
  - [ ] Staging validation complete
  - [ ] Production deployment successful
  - [ ] All systems healthy
  - [ ] Business metrics tracking

decision_point: "If issues, ROLLBACK, else COMPLETE"
PHASE 7: Post-Launch Optimization
yamltrigger: "System live for 24 hours"
primary_agents: ["Performance Optimizer", "Business Analyst"]
duration: "Ongoing"

workflow:
  1. PERFORMANCE_ANALYSIS:
     agent: "Performance Optimizer"
     schedule: "Daily for first week"
     prompt: |
       "Performance Optimizer, analyze:
       - Real-world performance data
       - Optimization opportunities
       - Capacity planning updates
       - Cost optimization potential"

  2. BUSINESS_METRICS_REVIEW:
     agent: "Business Analyst"
     schedule: "Daily for first week, then weekly"
     prompt: |
       "Business Analyst, report on:
       - Success metrics achievement
       - User adoption rates
       - ROI tracking
       - Stakeholder feedback"

  3. CONTINUOUS_IMPROVEMENT:
     agent: "PRP Orchestrator"
     prompt: |
       "PRP Orchestrator, based on metrics:
       - Identify improvement opportunities
       - Create optimization PRPs
       - Plan next iterations"

outputs:
  - performance-report.md
  - business-metrics.md
  - improvement-backlog.md
Contextual Workflow Variations
HOTFIX WORKFLOW (Emergency)
yamltrigger: "Production issue detected"
compressed_timeline: "2-4 hours"

rapid_sequence:
  1. Context Researcher: "Investigate issue history"
  2. Security Auditor: "Assess security impact"
  3. Implementation Specialist: "Implement fix"
  4. Validation Engineer: "Emergency testing"
  5. DevOps Engineer: "Express deployment"
  6. All Agents: "Monitor resolution"

command_sequence:
  - "/debug-RCA"                    # Root cause analysis
  - "/prp-task-create"              # Quick fix task
  - "/prp-task-execute"             # Execute fix
  - "/conflict-resolver-general"    # If merge conflicts
  - "/smart-commit"                 # Commit fix
SMALL FEATURE WORKFLOW
yamltrigger: "Feature <1 day effort"
compressed_phases: true

simplified_sequence:
  1. Business Analyst: "Quick requirements"
  2. Implementation Specialist: "Direct implementation"
  3. Validation Engineer: "Test suite"
  4. DevOps Engineer: "Standard deployment"

command_sequence:
  - "/prp-task-create"              # Simple task PRP
  - "/prp-task-execute"             # Execute
  - "/review-staged-unstaged"       # Review
  - "/create-pr"                    # Submit
RESEARCH WORKFLOW
yamltrigger: "Technical investigation needed"
primary_agent: "Context Researcher"

research_sequence:
  1. Context Researcher: "Deep investigation"
  2. Integration Architect: "Integration feasibility"
  3. Security Auditor: "Security implications"
  4. Performance Optimizer: "Performance impact"
  5. Business Analyst: "Business value assessment"

output: "Research report with recommendations"
Agent Interaction Patterns
PARALLEL COLLABORATION PATTERN
yamlwhen: "Multiple aspects need simultaneous work"
example: "Payment processing implementation"

parallel_execution:
  track_1:
    - Integration Architect: "Payment gateway integration"
    - Security Auditor: "PCI compliance"
  track_2:
    - Implementation Specialist: "Payment UI"
    - Validation Engineer: "Test scenarios"
  track_3:
    - DevOps Engineer: "Infrastructure setup"
    - Documentation Curator: "Payment docs"

synchronization_points:
  - "After design complete"
  - "Before integration testing"
  - "Before deployment"
ITERATIVE REFINEMENT PATTERN
yamlwhen: "Requirements unclear or evolving"
example: "UI/UX improvements"

iteration_cycle:
  1. Business Analyst: "Gather feedback"
  2. Implementation Specialist: "Prototype"
  3. Validation Engineer: "User testing"
  4. Business Analyst: "Analyze results"
  5. REPEAT until satisfaction threshold met
ESCALATION PATTERN
yamlwhen: "Blocker or critical issue encountered"

escalation_chain:
  level_1: "Implementing agent attempts resolution"
  level_2: "Integration Architect consulted"
  level_3: "PRP Orchestrator coordinates response"
  level_4: "All relevant agents collaborate"
  level_5: "Human intervention requested"
Command Integration Matrix
This matrix shows which PRP commands each agent typically uses:
AgentPrimary CommandsSecondary CommandsPRP Orchestrator/prime-core, /prp-planning-createAll commandsBusiness Analyst/user-story-rapid, /task-list-init/prp-planning-createContext Researcher/review-general, /debug-RCA/prime-coreImplementation Specialist/prp-base-execute, /prp-task-execute/refactor-simpleValidation Engineer/review-staged-unstaged, /review-general/debug-RCAIntegration Architect/api-contract-define, /prp-spec-create/prp-base-createDocumentation Curator/onboarding, /create-pr/review-generalSecurity Auditor/review-general/prp-spec-createPerformance Optimizer/refactor-simple, /review-general/debug-RCADevOps Engineer/smart-commit, /create-pr/conflict-resolver-general
Success Metrics for Each Phase
Phase 1: Discovery

 100% stakeholders interviewed
 All requirements documented
 Success metrics defined
 Context research complete

Phase 2: Architecture

 Architecture diagram created
 Security requirements integrated
 Performance targets set
 API contracts defined

Phase 3: Planning

 Implementation PRP created
 Tasks estimated
 Dependencies identified
 Risks documented

Phase 4: Implementation

 Code coverage >80%
 All tests passing
 Security scan clean
 Performance targets met

Phase 5: Deployment Prep

 Infrastructure ready
 Documentation complete
 Monitoring configured
 Rollback tested

Phase 6: Go-Live

 Zero deployment errors
 All systems healthy
 Metrics tracking
 Stakeholders notified

Phase 7: Optimization

 Performance improved
 ROI demonstrated
 Users satisfied
 Lessons documented

Activation Instructions for Claude
When a new project or feature request is received, Claude should:

Load this document alongside CLAUDE.md
Identify the workflow type (Standard, Hotfix, Small Feature, Research)
Initialize Phase 0 with the PRP Orchestrator
Follow the phase progression systematically
Use the validation gates to ensure quality
Make decisions at each decision point
Document progress throughout
Escalate when blocked using the escalation pattern

Default Agent Prompts for Quick Activation
python# Copy these into your Claude conversation for quick agent activation

agents = {
    "orchestrator": "PRP Orchestrator, initialize standard workflow for: ",
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

# Quick team activation
all_agents_briefing = """
All agents, we have a new project: [PROJECT_NAME]
PRP Orchestrator, please coordinate the standard workflow.
All agents, report your readiness and initial observations.
"""
Continuous Improvement Protocol
Every project completion should trigger:

Retrospective Analysis

What went well?
What could improve?
What was missing?


Process Updates

Update this document with lessons learned
Refine agent interactions
Optimize phase durations


Knowledge Capture

Update CLAUDE.md with new patterns
Document new gotchas
Save reusable components



Remember
This is a living document. Each project makes it better. The goal is not rigid process but intelligent orchestration that ensures comprehensive, high-quality delivery every time.

## How to Inject This Into Your Claude Code Environment

### Step 1: Create the Core Files

Place these files in your project root:

1. **AGENT-ORCHESTRATION.md** (the complete document above)
2. **AGENT-LIBRARY.md** (all 10 agent creation prompts)
3. **CLAUDE.md** (your project-specific context)
4. **PRP-METHODOLOGY.md** (link to the framework)

### Step 2: Create an Initialization Prompt

Save this as `INIT-AGENTS.md`:

```markdown
# Agent System Initialization

When starting a new Claude Code session, use this prompt:

"Initialize the complete agent system by:
1. Loading AGENT-ORCHESTRATION.md for the process
2. Loading AGENT-LIBRARY.md for agent definitions
3. Creating all 10 specialist agents
4. Activating the PRP Orchestrator to coordinate

I need all agents ready to collaborate on [describe your project]."
Step 3: Create Quick Reference Card
Save this as AGENT-QUICKREF.md:
markdown# Agent System Quick Reference

## Quick Start Commands
```bash
# Initialize everything
/prime-core
"Load AGENT-ORCHESTRATION.md and initialize all agents"

# Start new project
"PRP Orchestrator, initiate standard workflow for [project]"

# Emergency fix
"PRP Orchestrator, initiate hotfix workflow for [issue]"

# Research task
"Context Researcher, lead research workflow for [topic]"
Standard Activation Sequence

Prime core context
Load orchestration process
Initialize agents
Start appropriate workflow

Phase Checkpoints

 Phase 0: Initialized
 Phase 1: Requirements complete
 Phase 2: Architecture designed
 Phase 3: Implementation planned
 Phase 4: Code complete
 Phase 5: Deployment ready
 Phase 6: Live in production
 Phase 7: Optimized

Emergency Commands

"All agents, emergency collaboration on [issue]"
"Security Auditor, immediate security assessment"
"DevOps Engineer, emergency rollback"
"Performance Optimizer, system is slow, help!"


### Step 4: Create a Project Template

Save this as `.claude/PROJECT-TEMPLATE.md`:

```markdown
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
- Requirements: `PRPs/[project]-requirements.md`
- Architecture: `PRPs/[project]-architecture.md`
- Implementation: `PRPs/[project]-implementation.md`
- Tests: `tests/[project]/`
- Docs: `docs/[project]/`

## Success Metrics
- [ ] [Metric 1]
- [ ] [Metric 2]
- [ ] [Metric 3]

## Next Actions
1. [Immediate next step]
2. [Following step]
3. [Subsequent step]
Best Practices for Using This Process
1. Always Start with Phase 0
Never skip initialization. It ensures all agents have context and the orchestrator has control.
2. Respect the Validation Gates
Don't proceed to the next phase until validation gates are green. They prevent cascading problems.
3. Use Parallel Patterns When Appropriate
Some work can happen simultaneously. The orchestrator identifies these opportunities.
4. Document Decisions
Every significant decision should be captured for future reference.
5. Iterate When Needed
The process is systematic but not rigid. Iterate phases when requirements change.
6. Maintain the Knowledge Base
Every project should contribute learnings back to the framework.
Example: Starting Your Salon Project
Here's exactly how you'd begin:
markdown# In Claude Code, type:

/prime-core

"Load AGENT-ORCHESTRATION.md and initialize all specialist agents for a comprehensive salon automation project.

Project: Swiss salon booking automation with WhatsApp, Google Calendar, payment processing, and n8n orchestration.

PRP Orchestrator, please initiate the standard workflow. We need all agents collaborating to deliver a production-ready system with Swiss compliance requirements."

# Claude will then:
1. Load the orchestration process
2. Create all 10 agents
3. Start Phase 0 initialization
4. Begin systematic execution through all phases
5. Coordinate agents at each step
6. Ensure quality gates are met
7. Deliver a complete, documented, tested system
This systematic approach ensures that every project benefits from the full expertise of all agents, following proven patterns, and delivering consistent quality. The process becomes a repeatable, reliable way to tackle any software challenge with confidence.
