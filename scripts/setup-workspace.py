#!/usr/bin/env python3
"""
Quick setup script to create all necessary directories and files
"""

import json
from pathlib import Path
from datetime import datetime

# Base directory
base_dir = Path("/Users/tobiprivat/Documents/GitProjects/work/PRPs-agentic-eng")

# Define all directories to create
directories = [
    ".agent-system/sessions/active",
    ".agent-system/sessions/history",
    ".agent-system/agents/orchestrator",
    ".agent-system/agents/business-analyst",
    ".agent-system/agents/context-researcher",
    ".agent-system/agents/implementation-specialist",
    ".agent-system/agents/validation-engineer",
    ".agent-system/agents/integration-architect",
    ".agent-system/agents/documentation-curator",
    ".agent-system/agents/security-auditor",
    ".agent-system/agents/performance-optimizer",
    ".agent-system/agents/devops-engineer",
    ".agent-system/sync",
    "PRPs/.cache/agent-views",
    "PRPs/.cache/task-briefs",
    "PRPs/planning",
    "PRPs/architecture",
    "PRPs/contracts",
    "PRPs/security",
    "workspace/features",
    "workspace/fixes",
    "workspace/shared/libraries",
    "workspace/shared/utils",
    "workspace/shared/contracts",
    "stacks/python",
    "stacks/java",
    "stacks/javascript",
    "stacks/typescript",
    "integration/environments/local",
    "integration/environments/staging",
    "integration/environments/production",
    "integration/ci-cd/github-actions",
    "integration/ci-cd/jenkins",
    "integration/monitoring/dashboards",
    "reports/daily",
    "reports/phase-completions",
    "reports/metrics",
]

# Create all directories
for dir_path in directories:
    full_path = base_dir / dir_path
    full_path.mkdir(parents=True, exist_ok=True)
    print(f"Created: {dir_path}")

# Initialize JSON files
json_files = {
    ".agent-system/registry/tasks.json": {
        "version": "1.0.0",
        "updated": datetime.now().isoformat(),
        "next_task_id": 1,
        "tasks": {},
        "statistics": {
            "total": 0,
            "completed": 0,
            "in_progress": 0,
            "blocked": 0,
            "pending": 0,
        },
    },
    ".agent-system/registry/dependencies.json": {
        "version": "1.0.0",
        "task_dependencies": {},
        "feature_dependencies": {},
        "agent_dependencies": {},
    },
    ".agent-system/sync/broadcasts.json": {"broadcasts": [], "last_broadcast_id": 0},
    ".agent-system/sync/handoffs.json": {
        "handoffs": [],
        "pending": [],
        "completed": [],
    },
    ".agent-system/sync/conflicts.json": {
        "active_conflicts": [],
        "resolved_conflicts": [],
    },
    "workspace/features/.index.json": {
        "features": {},
        "total_features": 0,
        "active_features": 0,
        "completed_features": 0,
    },
}

# Create JSON files
for file_path, content in json_files.items():
    full_path = base_dir / file_path
    with open(full_path, "w") as f:
        json.dump(content, f, indent=2, default=str)
    print(f"Created JSON: {file_path}")

# Create agent-specific files
agents = [
    "orchestrator",
    "business-analyst",
    "context-researcher",
    "implementation-specialist",
    "validation-engineer",
    "integration-architect",
    "documentation-curator",
    "security-auditor",
    "performance-optimizer",
    "devops-engineer",
]

for agent in agents:
    # Context file
    context_file = base_dir / f".agent-system/agents/{agent}/context.json"
    context_data = {
        "agent": agent,
        "initialized": datetime.now().isoformat(),
        "capabilities": [],
        "current_tasks": [],
        "completed_tasks": [],
        "preferences": {},
        "knowledge_base": [],
    }
    with open(context_file, "w") as f:
        json.dump(context_data, f, indent=2)

    # Tasks file
    tasks_file = base_dir / f".agent-system/agents/{agent}/tasks.json"
    tasks_data = {"assigned": [], "in_progress": [], "completed": [], "blocked": []}
    with open(tasks_file, "w") as f:
        json.dump(tasks_data, f, indent=2)

    # Changelog file
    changelog_file = base_dir / f".agent-system/agents/{agent}/changelog.md"
    with open(changelog_file, "w") as f:
        f.write(f"# {agent} Changelog\n\n")
        f.write("## Active Session\n\n")
        f.write(f"### Date: {datetime.now().strftime('%Y-%m-%d')}\n\n")
        f.write("#### Tasks\n<!-- Task changes will be logged here -->\n\n")
        f.write(
            "#### Files Modified\n<!-- File modifications will be logged here -->\n\n"
        )
        f.write(
            "---\n\n## Previous Sessions\n<!-- Previous session logs will be archived here -->\n"
        )

    print(f"Created agent files for: {agent}")

print("\n✅ All directories and files created successfully!")
