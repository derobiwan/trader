#!/usr/bin/env python3
"""
BMAD-PRPs Integration Manager
Bridges BMAD-METHOD with PRPs framework
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import argparse

# Base directory
BASE_DIR = Path(__file__).parent.parent


class BMADIntegration:
    """Manages integration between BMAD-METHOD and PRPs framework"""

    def __init__(self):
        self.bmad_docs = BASE_DIR / "docs"
        self.prps_dir = BASE_DIR / "PRPs"
        self.agent_system = BASE_DIR / ".agent-system"

        # Ensure directories exist
        self.bmad_docs.mkdir(exist_ok=True)
        (self.bmad_docs / "epics").mkdir(exist_ok=True)
        (self.bmad_docs / "stories").mkdir(exist_ok=True)
        (self.bmad_docs / "qa" / "assessments").mkdir(parents=True, exist_ok=True)
        (self.bmad_docs / "qa" / "gates").mkdir(parents=True, exist_ok=True)

    def import_prd(self, output_name: Optional[str] = None):
        """Import BMAD PRD to PRPs planning"""
        prd_file = self.bmad_docs / "prd.md"

        if not prd_file.exists():
            print(f"❌ Error: PRD not found at {prd_file}")
            print("   Create docs/prd.md first using BMAD planning phase")
            return False

        print("📋 Importing BMAD PRD to PRPs...")

        prd_content = prd_file.read_text()

        # Convert to PRPs format
        prp_content = self._convert_prd_to_prp(prd_content)

        # Determine output filename
        if not output_name:
            output_name = "project-requirements.md"

        # Save to PRPs
        output_path = self.prps_dir / "planning" / "completed" / output_name
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(prp_content)

        print(f"✅ PRD imported to {output_path}")

        # Update sync status
        self._update_sync_status("prd_imported", True)

        return True

    def import_architecture(self, output_name: Optional[str] = None):
        """Import BMAD architecture to PRPs architecture"""
        arch_file = self.bmad_docs / "architecture.md"

        if not arch_file.exists():
            print(f"❌ Error: Architecture not found at {arch_file}")
            print("   Create docs/architecture.md first using BMAD planning phase")
            return False

        print("🏗️  Importing BMAD architecture to PRPs...")

        arch_content = arch_file.read_text()

        # Determine output filename base
        if not output_name:
            output_name = "project-architecture"

        # Split into components
        architecture_prp = self._extract_architecture(arch_content)
        contracts_prp = self._extract_api_contracts(arch_content)
        security_prp = self._extract_security(arch_content)

        # Save to PRPs
        arch_path = self.prps_dir / "architecture" / f"{output_name}.md"
        arch_path.parent.mkdir(parents=True, exist_ok=True)
        arch_path.write_text(architecture_prp)
        print(f"✅ Architecture imported to {arch_path}")

        if contracts_prp:
            contracts_path = self.prps_dir / "contracts" / f"{output_name}-api-contracts.md"
            contracts_path.parent.mkdir(parents=True, exist_ok=True)
            contracts_path.write_text(contracts_prp)
            print(f"✅ API contracts extracted to {contracts_path}")

        if security_prp:
            security_path = self.prps_dir / "security" / f"{output_name}-security.md"
            security_path.parent.mkdir(parents=True, exist_ok=True)
            security_path.write_text(security_prp)
            print(f"✅ Security requirements extracted to {security_path}")

        # Update sync status
        self._update_sync_status("architecture_imported", True)

        return True

    def sync_stories_to_tasks(self):
        """Convert BMAD stories to PRP tasks"""
        stories_dir = self.bmad_docs / "stories"

        if not stories_dir.exists() or not list(stories_dir.glob("STORY-*.md")):
            print("❌ No stories found in docs/stories/")
            print("   Generate stories first using Scrum Master or BMAD workflow")
            return False

        print("🔄 Syncing BMAD stories to PRP tasks...")

        # Load existing registries
        tasks_file = self.agent_system / "registry" / "tasks.json"
        stories_file = self.agent_system / "registry" / "stories.json"

        with open(tasks_file, 'r') as f:
            task_registry = json.load(f)

        with open(stories_file, 'r') as f:
            story_registry = json.load(f)

        synced = 0
        errors = 0

        # Process each story
        for story_file in sorted(stories_dir.glob("STORY-*.md")):
            try:
                story = self._parse_story(story_file)
                story_id = f"STORY-{story['number']:03d}"

                # Check if already synced
                if story_id in story_registry['stories'] and story_id != "STORY-EXAMPLE":
                    print(f"  ⏭️  {story_id} already synced")
                    continue

                # Create corresponding task
                task_num = task_registry['statistics']['total'] + 1
                task_id = f"TASK-{task_num:03d}"

                task_registry['tasks'][task_id] = {
                    "title": f"Story-{story['number']}: {story['title']}",
                    "description": story['description'],
                    "story_reference": str(story_file.relative_to(BASE_DIR)),
                    "bmad_epic": story.get('epic'),
                    "status": "pending",
                    "priority": story.get('priority', 'medium'),
                    "estimated_hours": story.get('estimate', 8),
                    "created_at": datetime.now().isoformat(),
                    "dependencies": [],
                    "files": [],
                    "acceptance_criteria": story.get('acceptance_criteria', [])
                }

                # Update task statistics
                task_registry['statistics']['total'] += 1
                task_registry['statistics']['pending'] += 1

                # Add to story registry
                story_registry['stories'][story_id] = {
                    "file": str(story_file.relative_to(BASE_DIR)),
                    "task_id": task_id,
                    "epic_id": story.get('epic'),
                    "title": story['title'],
                    "status": "pending",
                    "created_at": datetime.now().isoformat()
                }

                # Update story statistics
                story_registry['statistics']['total'] += 1
                story_registry['statistics']['pending'] += 1

                print(f"  ✅ {story_id} → {task_id}: {story['title']}")
                synced += 1

            except Exception as e:
                print(f"  ❌ Error processing {story_file.name}: {e}")
                errors += 1

        # Save updated registries
        task_registry['updated'] = datetime.now().isoformat()
        story_registry['updated'] = datetime.now().isoformat()

        with open(tasks_file, 'w') as f:
            json.dump(task_registry, f, indent=2)

        with open(stories_file, 'w') as f:
            json.dump(story_registry, f, indent=2)

        print(f"\n📊 Synced: {synced}, Errors: {errors}")
        return True

    def generate_story_views(self):
        """Generate agent-specific views from BMAD stories"""
        print("🔍 Generating agent views from stories...")

        stories_dir = self.bmad_docs / "stories"
        views_dir = self.prps_dir / ".cache" / "story-views"
        views_dir.mkdir(parents=True, exist_ok=True)

        generated = 0

        for story_file in sorted(stories_dir.glob("STORY-*.md")):
            story = self._parse_story(story_file)
            story_id = f"STORY-{story['number']:03d}"

            # Generate view for implementation specialist
            impl_view = self._generate_implementation_view(story)
            impl_path = views_dir / f"{story_id}-implementation.md"
            impl_path.write_text(impl_view)

            # Generate view for validation engineer
            val_view = self._generate_validation_view(story)
            val_path = views_dir / f"{story_id}-validation.md"
            val_path.write_text(val_view)

            print(f"  ✅ {story_id}: Generated implementation and validation views")
            generated += 1

        print(f"\n📊 Generated views for {generated} stories")
        return True

    def status(self):
        """Show BMAD integration status"""
        sync_file = self.agent_system / "sync" / "bmad-sync.json"

        with open(sync_file, 'r') as f:
            sync_status = json.load(f)

        print("\n📊 BMAD Integration Status")
        print("=" * 50)
        print(f"Enabled: {sync_status['bmad_integration']['enabled']}")
        print(f"Last Sync: {sync_status['bmad_integration'].get('last_sync', 'Never')}")
        print()
        print("Import Status:")
        print(f"  PRD:          {'✅' if sync_status['bmad_integration']['prd_imported'] else '⏸️'}")
        print(f"  Architecture: {'✅' if sync_status['bmad_integration']['architecture_imported'] else '⏸️'}")
        print(f"  Epics:        {'✅' if sync_status['bmad_integration']['epics_generated'] else '⏸️'}")
        print(f"  Stories:      {'✅' if sync_status['bmad_integration']['stories_generated'] else '⏸️'}")

        # Check file existence
        print()
        print("Files:")
        prd = self.bmad_docs / "prd.md"
        arch = self.bmad_docs / "architecture.md"
        print(f"  docs/prd.md:          {'✅ Exists' if prd.exists() else '❌ Missing'}")
        print(f"  docs/architecture.md: {'✅ Exists' if arch.exists() else '❌ Missing'}")

        # Count stories and epics
        stories_count = len(list((self.bmad_docs / "stories").glob("STORY-*.md"))) if (self.bmad_docs / "stories").exists() else 0
        epics_count = len(list((self.bmad_docs / "epics").glob("EPIC-*.md"))) if (self.bmad_docs / "epics").exists() else 0

        print()
        print(f"Epics:   {epics_count}")
        print(f"Stories: {stories_count}")

    def import_all(self, project_name: str = "project"):
        """Import all BMAD artifacts at once"""
        print("🚀 Importing all BMAD artifacts to PRPs...\n")

        success = True

        # Import PRD
        if (self.bmad_docs / "prd.md").exists():
            if not self.import_prd(f"{project_name}-requirements.md"):
                success = False
        else:
            print("⚠️  Skipping PRD (not found)")

        print()

        # Import Architecture
        if (self.bmad_docs / "architecture.md").exists():
            if not self.import_architecture(project_name):
                success = False
        else:
            print("⚠️  Skipping Architecture (not found)")

        print()

        # Sync stories
        if (self.bmad_docs / "stories").exists():
            if not self.sync_stories_to_tasks():
                success = False
        else:
            print("⚠️  Skipping Stories (not found)")

        print()

        # Generate views
        if (self.bmad_docs / "stories").exists() and list((self.bmad_docs / "stories").glob("STORY-*.md")):
            self.generate_story_views()

        if success:
            print("\n✅ Import complete!")
        else:
            print("\n⚠️  Import completed with some errors")

        return success

    # Helper methods

    def _convert_prd_to_prp(self, prd_content: str) -> str:
        """Convert BMAD PRD format to PRP requirements format"""
        prp = f"""# Product Requirements - PRP Format

*Imported from BMAD PRD on {datetime.now().strftime('%Y-%m-%d')}*

---

## 📋 Goal

{self._extract_section(prd_content, ['Goal', 'Overview', 'Introduction'])}

## 💡 Why

### Business Value
{self._extract_section(prd_content, ['Business Value', 'Why', 'Rationale'])}

### User Impact
{self._extract_section(prd_content, ['User Impact', 'User Benefits', 'Value Proposition'])}

## ✅ What (Success Criteria)

### Functional Requirements
{self._extract_section(prd_content, ['Functional Requirements', 'Features', 'Requirements'])}

### Success Metrics
{self._extract_section(prd_content, ['Success Metrics', 'KPIs', 'Metrics'])}

## 📚 Context

### Market Context
{self._extract_section(prd_content, ['Market', 'Context', 'Background'])}

### Technical Context
{self._extract_section(prd_content, ['Technical', 'Technology', 'Platform'])}

## 🎯 User Stories

{self._extract_section(prd_content, ['User Stories', 'Stories', 'Scenarios'])}

## 📝 Notes

*Original BMAD PRD*: docs/prd.md

---

**Source**: BMAD-METHOD PRD
**Imported**: {datetime.now().isoformat()}
"""
        return prp

    def _extract_architecture(self, arch_content: str) -> str:
        """Extract main architecture content"""
        return f"""# System Architecture

*Imported from BMAD Architecture on {datetime.now().strftime('%Y-%m-%d')}*

---

{arch_content}

---

**Source**: BMAD-METHOD Architecture
**Imported**: {datetime.now().isoformat()}
"""

    def _extract_api_contracts(self, arch_content: str) -> str:
        """Extract API contracts from architecture"""
        api_section = self._extract_section(arch_content, ['API', 'APIs', 'Endpoints', 'Contracts'])

        if api_section and api_section.strip():
            return f"""# API Contracts

*Extracted from BMAD Architecture on {datetime.now().strftime('%Y-%m-%d')}*

---

{api_section}

---

**Source**: BMAD-METHOD Architecture
**Imported**: {datetime.now().isoformat()}
"""
        return ""

    def _extract_security(self, arch_content: str) -> str:
        """Extract security requirements from architecture"""
        security_section = self._extract_section(arch_content, ['Security', 'Authentication', 'Authorization', 'Compliance'])

        if security_section and security_section.strip():
            return f"""# Security Requirements

*Extracted from BMAD Architecture on {datetime.now().strftime('%Y-%m-%d')}*

---

{security_section}

---

**Source**: BMAD-METHOD Architecture
**Imported**: {datetime.now().isoformat()}
"""
        return ""

    def _extract_section(self, content: str, headers: List[str]) -> str:
        """Extract content under specific headers"""
        for header in headers:
            # Try different header levels
            for level in ['##', '###', '####']:
                pattern = f"{level}\\s+{header}\\s*\\n(.*?)(?=\\n#{2,}|$)"
                match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
                if match:
                    return match.group(1).strip()
        return ""

    def _parse_story(self, story_file: Path) -> Dict:
        """Parse BMAD story file"""
        content = story_file.read_text()

        # Extract story number from filename
        number_match = re.search(r'STORY-(\d+)', story_file.name)
        number = int(number_match.group(1)) if number_match else 0

        # Extract title (first # heading)
        title_match = re.search(r'^#\s+Story\s+\d+:?\s*(.+)$', content, re.MULTILINE | re.IGNORECASE)
        title = title_match.group(1).strip() if title_match else "Untitled Story"

        # Extract description
        desc_match = re.search(r'##\s+Description\s*\n(.*?)(?=\n##|$)', content, re.DOTALL | re.IGNORECASE)
        description = desc_match.group(1).strip() if desc_match else ""

        # Extract epic reference
        epic_match = re.search(r'(?:Epic|EPIC)[:\s]+([A-Z]+-\d+)', content, re.IGNORECASE)
        epic = epic_match.group(1) if epic_match else None

        # Extract priority
        priority_match = re.search(r'(?:Priority|PRIORITY)[:\s]+(\w+)', content, re.IGNORECASE)
        priority = priority_match.group(1).lower() if priority_match else "medium"

        # Extract estimate
        estimate_match = re.search(r'(?:Estimate|ESTIMATE)[:\s]+(\d+)', content, re.IGNORECASE)
        estimate = int(estimate_match.group(1)) if estimate_match else 8

        # Extract acceptance criteria
        criteria = []
        criteria_section = re.search(r'##\s+Acceptance Criteria\s*\n(.*?)(?=\n##|$)', content, re.DOTALL | re.IGNORECASE)
        if criteria_section:
            criteria_text = criteria_section.group(1)
            criteria = [line.strip('- [ ] ').strip() for line in criteria_text.split('\n') if line.strip().startswith('- [')]

        return {
            "number": number,
            "title": title,
            "description": description,
            "epic": epic,
            "priority": priority,
            "estimate": estimate,
            "acceptance_criteria": criteria
        }

    def _generate_implementation_view(self, story: Dict) -> str:
        """Generate implementation specialist view of story"""
        return f"""# Story {story['number']:03d}: {story['title']} - Implementation View

**Priority**: {story['priority']}
**Estimate**: {story['estimate']} hours

## What to Build

{story['description']}

## Acceptance Criteria

{chr(10).join(f"- [ ] {criterion}" for criterion in story['acceptance_criteria'])}

## Next Actions

1. Review technical context in full story: docs/stories/STORY-{story['number']:03d}.md
2. Claim task: python scripts/agent-task-manager.py claim --agent implementation-specialist --task TASK-{story['number']:03d}
3. Implement with tests
4. Run validations

---

*Optimized view for Implementation Specialist*
*Full story*: docs/stories/STORY-{story['number']:03d}.md
"""

    def _generate_validation_view(self, story: Dict) -> str:
        """Generate validation engineer view of story"""
        return f"""# Story {story['number']:03d}: {story['title']} - Validation View

**Priority**: {story['priority']}

## Test Requirements

### Acceptance Criteria to Validate

{chr(10).join(f"{i+1}. {criterion}" for i, criterion in enumerate(story['acceptance_criteria']))}

### Required Test Types

- [ ] Unit tests (coverage >80%)
- [ ] Integration tests
- [ ] Security scan
- [ ] Performance check

## Validation Commands

```bash
# Unit tests
pytest tests/ -v

# Coverage
pytest tests/ --cov=. --cov-report=term-missing

# Security
bandit -r src/

# Lint
ruff check src/
```

---

*Optimized view for Validation Engineer*
*Full story*: docs/stories/STORY-{story['number']:03d}.md
"""

    def _update_sync_status(self, key: str, value):
        """Update BMAD sync status"""
        sync_file = self.agent_system / "sync" / "bmad-sync.json"

        with open(sync_file, 'r') as f:
            sync_status = json.load(f)

        sync_status['bmad_integration'][key] = value
        sync_status['bmad_integration']['last_sync'] = datetime.now().isoformat()
        sync_status['updated'] = datetime.now().isoformat()

        with open(sync_file, 'w') as f:
            json.dump(sync_status, f, indent=2)


def main():
    parser = argparse.ArgumentParser(
        description='BMAD-PRPs Integration Manager',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Import PRD
  python scripts/bmad-integration.py import-prd

  # Import Architecture
  python scripts/bmad-integration.py import-architecture

  # Sync stories to tasks
  python scripts/bmad-integration.py sync-stories

  # Import everything at once
  python scripts/bmad-integration.py import-all --project my-project

  # Generate agent views from stories
  python scripts/bmad-integration.py generate-views

  # Check status
  python scripts/bmad-integration.py status
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Import PRD
    prd_parser = subparsers.add_parser('import-prd', help='Import BMAD PRD to PRPs')
    prd_parser.add_argument('--output', help='Output filename (default: project-requirements.md)')

    # Import Architecture
    arch_parser = subparsers.add_parser('import-architecture', help='Import BMAD architecture to PRPs')
    arch_parser.add_argument('--output', help='Output filename base (default: project-architecture)')

    # Sync stories
    subparsers.add_parser('sync-stories', help='Sync BMAD stories to PRP tasks')

    # Generate views
    subparsers.add_parser('generate-views', help='Generate agent views from stories')

    # Import all
    all_parser = subparsers.add_parser('import-all', help='Import all BMAD artifacts')
    all_parser.add_argument('--project', default='project', help='Project name for output files')

    # Status
    subparsers.add_parser('status', help='Show BMAD integration status')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    integration = BMADIntegration()

    if args.command == 'import-prd':
        success = integration.import_prd(args.output)
    elif args.command == 'import-architecture':
        success = integration.import_architecture(args.output)
    elif args.command == 'sync-stories':
        success = integration.sync_stories_to_tasks()
    elif args.command == 'generate-views':
        success = integration.generate_story_views()
    elif args.command == 'import-all':
        success = integration.import_all(args.project)
    elif args.command == 'status':
        integration.status()
        success = True
    else:
        parser.print_help()
        sys.exit(1)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
