#!/usr/bin/env python3
"""
Generate lightweight agent-specific views from PRP documents
Reduces context loading from ~50KB to ~2-5KB per agent
"""

import json
from pathlib import Path
import argparse

# Base directory
BASE_DIR = Path(__file__).parent.parent

# Agent section mappings
AGENT_SECTIONS = {
    "orchestrator": [
        "## Overview",
        "## Project Goals",
        "## Phase Status",
        "## Risk Register",
        "## Timeline",
    ],
    "business-analyst": [
        "## Business Requirements",
        "## User Stories",
        "## Success Metrics",
        "## Stakeholder Analysis",
        "## ROI Analysis",
    ],
    "context-researcher": [
        "## Technical Context",
        "## Similar Implementations",
        "## Known Issues",
        "## Research Findings",
        "## External Dependencies",
    ],
    "implementation-specialist": [
        "## Technical Requirements",
        "## API Contracts",
        "## Implementation Guidelines",
        "## Code Structure",
        "## Dependencies",
    ],
    "validation-engineer": [
        "## Acceptance Criteria",
        "## Test Requirements",
        "## Performance Targets",
        "## Test Strategy",
        "## Coverage Goals",
    ],
    "integration-architect": [
        "## System Architecture",
        "## Integration Points",
        "## API Design",
        "## Data Flow",
        "## Service Contracts",
    ],
    "documentation-curator": [
        "## Documentation Requirements",
        "## User Guide Structure",
        "## API Documentation",
        "## Deployment Guide",
        "## Troubleshooting",
    ],
    "security-auditor": [
        "## Security Requirements",
        "## Threat Model",
        "## Compliance Checklist",
        "## Data Protection",
        "## Authentication Design",
    ],
    "performance-optimizer": [
        "## Performance Targets",
        "## Optimization Opportunities",
        "## Scalability Requirements",
        "## Resource Limits",
        "## Benchmarks",
    ],
    "devops-engineer": [
        "## Deployment Strategy",
        "## Infrastructure Requirements",
        "## CI/CD Pipeline",
        "## Monitoring Setup",
        "## Rollback Procedures",
    ],
}


class AgentViewGenerator:
    def __init__(self):
        self.prps_dir = BASE_DIR / "PRPs"
        self.cache_dir = BASE_DIR / "PRPs" / ".cache"
        self.agent_views_dir = self.cache_dir / "agent-views"
        self.task_briefs_dir = self.cache_dir / "task-briefs"

        # Ensure directories exist
        self.agent_views_dir.mkdir(parents=True, exist_ok=True)
        self.task_briefs_dir.mkdir(parents=True, exist_ok=True)

    def extract_sections(self, content, sections):
        """Extract specific sections from markdown content"""
        extracted = []
        lines = content.split("\n")

        current_section = None
        section_content = []

        for line in lines:
            # Check if this is a section header
            if line.startswith("##"):
                # Save previous section if it was one we wanted
                if current_section in sections and section_content:
                    extracted.append("\n".join(section_content))

                # Start new section
                current_section = line.strip()
                section_content = [line]
            elif current_section in sections:
                section_content.append(line)

        # Don't forget the last section
        if current_section in sections and section_content:
            extracted.append("\n".join(section_content))

        return "\n\n".join(extracted) if extracted else None

    def generate_agent_view(self, agent_name):
        """Generate a lightweight view for a specific agent"""
        if agent_name not in AGENT_SECTIONS:
            print(f"❌ Unknown agent: {agent_name}")
            return False

        sections_to_extract = AGENT_SECTIONS[agent_name]
        agent_view = [f"# Agent View: {agent_name.replace('-', ' ').title()}"]
        agent_view.append("*Generated for minimal context loading*\n")

        # Process all PRP documents
        prp_files = []
        for subdir in [
            "planning",
            "architecture",
            "contracts",
            "security",
            "implementation",
        ]:
            subdir_path = self.prps_dir / subdir
            if subdir_path.exists():
                prp_files.extend(subdir_path.glob("*.md"))

        if not prp_files:
            print("⚠️  No PRP documents found")
            # Create a placeholder
            agent_view.append("## No Active Projects\n")
            agent_view.append(
                "No PRP documents available yet. Waiting for project initialization."
            )
        else:
            for prp_file in prp_files:
                try:
                    content = prp_file.read_text()
                    extracted = self.extract_sections(content, sections_to_extract)

                    if extracted:
                        agent_view.append(f"\n## From: {prp_file.name}")
                        agent_view.append(extracted)
                except Exception as e:
                    print(f"⚠️  Error processing {prp_file}: {e}")

        # Write agent view
        output_path = self.agent_views_dir / f"{agent_name}.md"
        output_content = "\n".join(agent_view)
        output_path.write_text(output_content)

        # Calculate size reduction
        original_size = sum(f.stat().st_size for f in prp_files) if prp_files else 0
        new_size = len(output_content.encode("utf-8"))

        if original_size > 0:
            reduction = (1 - new_size / original_size) * 100
            print(
                f"✅ Generated view for {agent_name}: "
                f"{new_size / 1024:.1f}KB (reduced by {reduction:.1f}%)"
            )
        else:
            print(
                f"✅ Generated placeholder view for {agent_name}: {new_size / 1024:.1f}KB"
            )

        return True

    def generate_task_brief(self, task_id):
        """Generate a task-specific brief from registry and PRPs"""
        # Load task registry
        registry_path = BASE_DIR / ".agent-system" / "registry" / "tasks.json"

        try:
            with open(registry_path, "r") as f:
                registry = json.load(f)
        except FileNotFoundError:
            print("❌ Task registry not found")
            return False

        if task_id not in registry.get("tasks", {}):
            print(f"❌ Task {task_id} not found")
            return False

        task = registry["tasks"][task_id]

        # Create task brief
        brief = [f"# Task Brief: {task_id}"]
        brief.append(f"**Title:** {task.get('title', 'Untitled')}")
        brief.append(f"**Status:** {task.get('status', 'unknown')}")
        brief.append(f"**Priority:** {task.get('priority', 'medium')}")
        brief.append(f"**Agent:** {task.get('agent', 'unassigned')}")
        brief.append(f"**Estimated Hours:** {task.get('estimated_hours', 'unknown')}")

        if task.get("description"):
            brief.append(f"\n## Description\n{task['description']}")

        if task.get("dependencies"):
            brief.append("\n## Dependencies")
            for dep in task["dependencies"]:
                brief.append(f"- {dep}")

        if task.get("context_refs"):
            brief.append("\n## Context References")
            for ref in task["context_refs"]:
                brief.append(f"- {ref}")
                # Try to extract the referenced section
                if "#" in ref:
                    file_path, section = ref.split("#")
                    try:
                        full_path = BASE_DIR / file_path
                        if full_path.exists():
                            content = full_path.read_text()
                            # Simple extraction of referenced section
                            section_title = f"## {section.replace('-', ' ').title()}"
                            if section_title in content:
                                start = content.index(section_title)
                                end = content.find("\n##", start + 1)
                                if end == -1:
                                    end = len(content)
                                extracted = content[start:end].strip()
                                brief.append(f"\n### Referenced: {section}")
                                brief.append(
                                    extracted[:500] + "..."
                                    if len(extracted) > 500
                                    else extracted
                                )
                    except Exception as e:
                        print(f"⚠️  Could not extract reference: {e}")

        # Write task brief
        output_path = self.task_briefs_dir / f"{task_id}.md"
        output_content = "\n".join(brief)
        output_path.write_text(output_content)

        print(
            f"✅ Generated task brief for {task_id}: {len(output_content) / 1024:.1f}KB"
        )
        return True

    def generate_all_views(self):
        """Generate views for all agents"""
        print("🔄 Generating agent views...")

        for agent_name in AGENT_SECTIONS.keys():
            self.generate_agent_view(agent_name)

        # Also generate task briefs for active tasks
        registry_path = BASE_DIR / ".agent-system" / "registry" / "tasks.json"
        if registry_path.exists():
            with open(registry_path, "r") as f:
                registry = json.load(f)

            active_tasks = [
                task_id
                for task_id, task in registry.get("tasks", {}).items()
                if task.get("status") in ["in-progress", "pending"]
            ]

            if active_tasks:
                print(
                    f"\n🔄 Generating task briefs for {len(active_tasks)} active tasks..."
                )
                for task_id in active_tasks:
                    self.generate_task_brief(task_id)

        print("\n✅ All views generated successfully!")

    def clean_cache(self):
        """Clean the cache directory"""
        print("🧹 Cleaning cache...")

        for view_file in self.agent_views_dir.glob("*.md"):
            view_file.unlink()

        for brief_file in self.task_briefs_dir.glob("*.md"):
            brief_file.unlink()

        print("✅ Cache cleaned")


def main():
    parser = argparse.ArgumentParser(description="Generate Agent Views from PRPs")
    parser.add_argument("--agent", help="Generate view for specific agent")
    parser.add_argument("--task", help="Generate brief for specific task")
    parser.add_argument("--all", action="store_true", help="Generate all views")
    parser.add_argument(
        "--clean", action="store_true", help="Clean cache before generating"
    )

    args = parser.parse_args()

    generator = AgentViewGenerator()

    if args.clean:
        generator.clean_cache()

    if args.all:
        generator.generate_all_views()
    elif args.agent:
        generator.generate_agent_view(args.agent)
    elif args.task:
        generator.generate_task_brief(args.task)
    else:
        # Default: generate all
        generator.generate_all_views()


if __name__ == "__main__":
    main()
