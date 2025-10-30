#!/usr/bin/env python3
"""
BMAD-Enhanced PRP Orchestrator
Coordinates BMAD planning → PRPs development workflow
"""

import argparse
import sys
from pathlib import Path

# Add parent directory to path for imports
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR / "scripts"))

try:
    from bmad_integration import BMADIntegration
except ImportError:
    print("❌ Error: Could not import BMADIntegration")
    print("   Make sure bmad-integration.py is in scripts/")
    sys.exit(1)


class BMADOrchestrator:
    """Coordinates BMAD + PRPs workflow"""

    def __init__(self):
        self.bmad = BMADIntegration()
        self.base_dir = BASE_DIR

    def start_project(self, project_name: str, workflow_type: str = "standard"):
        """Initialize BMAD + PRPs project"""
        print(f"🚀 Starting BMAD-PRPs project: {project_name}")
        print(f"Workflow: {workflow_type}")
        print("=" * 60)

        if workflow_type == "standard":
            self._run_standard_workflow(project_name)
        elif workflow_type == "quick":
            self._run_quick_workflow(project_name)
        else:
            print(f"❌ Unknown workflow type: {workflow_type}")
            return False

        return True

    def continue_project(self):
        """Continue existing BMAD project"""
        print("🔄 Continuing BMAD-PRPs project")
        print("=" * 60)

        # Check what's already done
        self.bmad.status()

        print()
        print("📋 Next Steps:")
        print("1. If PRD not imported: python scripts/bmad-integration.py import-prd")
        print(
            "2. If Architecture not imported: python scripts/bmad-integration.py import-architecture"
        )
        print(
            "3. If Stories not synced: python scripts/bmad-integration.py sync-stories"
        )
        print(
            "4. Start development: python scripts/story-dev.py work-on-story STORY-001"
        )

    def _run_standard_workflow(self, project_name: str):
        """Execute standard BMAD-PRPs workflow"""

        # Phase 1: BMAD Planning
        print("\n📋 Phase 1: BMAD Planning")
        print("-" * 60)
        print(
            """
This phase creates comprehensive specifications:

1. **Analyst Research** (Optional)
   - Market analysis
   - Competitive research
   - User research

2. **Product Manager Creates PRD**
   - Product vision
   - User stories
   - Success metrics
   - Requirements

3. **Architect Designs System**
   - System architecture
   - API contracts
   - Data models
   - Integration points

You can do this in:
- BMAD Web UI (if you have BMAD-METHOD installed)
- Directly in Claude Code with Business Analyst + Integration Architect
- Manually by creating docs/prd.md and docs/architecture.md

When ready, run:
  python scripts/bmad-orchestrator.py import-planning --project {project_name}
        """
        )

    def _run_quick_workflow(self, project_name: str):
        """Execute quick workflow for small projects"""
        print("\n⚡ Quick Workflow (Small Projects)")
        print("-" * 60)
        print(
            """
For small projects, skip full BMAD planning:

1. Create minimal docs/prd.md with:
   - Goal
   - Key features
   - Success criteria

2. Skip architecture doc (or keep it minimal)

3. Import directly:
   python scripts/bmad-integration.py import-prd

4. Create stories manually or with Scrum Master

5. Start development:
   python scripts/story-dev.py work-on-story STORY-001
        """
        )

    def import_planning(self, project_name: str):
        """Import BMAD planning artifacts to PRPs"""
        print(f"\n🔄 Importing BMAD planning to PRPs for: {project_name}")
        print("=" * 60)

        # Check if planning docs exist
        prd_exists = (self.base_dir / "docs" / "prd.md").exists()
        arch_exists = (self.base_dir / "docs" / "architecture.md").exists()

        if not prd_exists and not arch_exists:
            print("❌ Error: No planning documents found")
            print("   Create docs/prd.md and/or docs/architecture.md first")
            return False

        # Import all
        success = self.bmad.import_all(project_name)

        if success:
            print("\n✅ Planning imported successfully!")
            print("\n📖 Phase 3: Story Generation")
            print("-" * 60)
            print(
                """
Next: Generate development stories

Option 1: Use Scrum Master agent in Claude Code
  "Scrum Master, analyze PRD and Architecture and create detailed stories"

Option 2: Use BMAD-METHOD story generation
  (If you have BMAD installed)

Option 3: Create stories manually using template:
  cp PRPs/templates/bmad_story.md docs/stories/STORY-001.md

After creating stories, sync them:
  python scripts/bmad-integration.py sync-stories
            """
            )
        else:
            print("\n⚠️  Import had errors. Check output above.")

        return success

    def generate_stories(self):
        """Guide user through story generation"""
        print("\n📖 Story Generation Guide")
        print("=" * 60)
        print(
            """
BMAD stories are detailed development units that include:
- Clear description
- Technical context
- Acceptance criteria
- Implementation notes
- Testing strategy

**Recommended Approach**:

1. **Use Scrum Master Agent** (Easiest)
   In Claude Code:
   "Scrum Master, create stories for [feature] based on:
    - PRD: docs/prd.md
    - Architecture: docs/architecture.md
    Output to: docs/stories/"

2. **Use Template** (Manual)
   For each story:
   ```bash
   cp PRPs/templates/bmad_story.md docs/stories/STORY-001.md
   # Edit with your story details
   ```

3. **Import from BMAD-METHOD** (If installed)
   Use BMAD Web UI or CLI

**After creating stories**:
```bash
# Sync stories to PRP tasks
python scripts/bmad-integration.py sync-stories

# Generate agent views
python scripts/bmad-integration.py generate-views

# Check status
python scripts/bmad-integration.py status

# Start development
python scripts/story-dev.py work-on-story STORY-001
```
        """
        )

    def show_workflow_diagram(self):
        """Show visual workflow diagram"""
        print("\n🎯 BMAD-PRPs Unified Workflow")
        print("=" * 60)
        print(
            """
┌─────────────────────────────────────────────────────────┐
│ PHASE 0: INITIALIZATION                                 │
│ • Run: bmad-orchestrator.py start-project               │
└──────────────┬──────────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────────┐
│ PHASE 1-2: BMAD PLANNING (Analyst, PM, Architect)      │
│ • Create: docs/prd.md                                   │
│ • Create: docs/architecture.md                          │
│ • Run: bmad-orchestrator.py import-planning            │
└──────────────┬──────────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────────┐
│ PHASE 3: STORY GENERATION (Scrum Master)               │
│ • Create: docs/stories/STORY-*.md                       │
│ • Run: bmad-integration.py sync-stories                │
└──────────────┬──────────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────────┐
│ PHASE 4: DEVELOPMENT (Implementation + Validation)      │
│ • Work on stories with: story-dev.py                    │
│ • Agents use optimized views (2-5KB)                    │
│ • Tasks tracked in .agent-system/registry/              │
└──────────────┬──────────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────────┐
│ PHASE 5-6: QA + DEPLOYMENT (QA, DevOps)                │
│ • BMAD QA gates + PRPs validation gates                 │
│ • Deploy with DevOps Engineer                           │
└──────────────┬──────────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────────┐
│ PHASE 7: OPTIMIZATION (Performance Optimizer)           │
│ • Monitor and optimize                                   │
└─────────────────────────────────────────────────────────┘

**Key Commands**:
  Start:    bmad-orchestrator.py start-project my-project
  Import:   bmad-orchestrator.py import-planning --project my-project
  Stories:  bmad-orchestrator.py generate-stories
  Develop:  story-dev.py work-on-story STORY-001
  Status:   bmad-integration.py status
        """
        )

    def check_integration(self):
        """Check if BMAD integration is properly set up"""
        print("\n🔍 BMAD Integration Check")
        print("=" * 60)

        issues = []
        warnings = []

        # Check directories
        required_dirs = [
            "docs",
            "docs/epics",
            "docs/stories",
            "docs/qa/assessments",
            "docs/qa/gates",
            "PRPs/.cache/story-views",
            ".agent-system/registry",
        ]

        for dir_path in required_dirs:
            full_path = self.base_dir / dir_path
            if not full_path.exists():
                issues.append(f"Missing directory: {dir_path}")
            else:
                print(f"✅ {dir_path}")

        # Check registry files
        registry_files = [
            ".agent-system/registry/stories.json",
            ".agent-system/registry/epics.json",
            ".agent-system/sync/bmad-sync.json",
        ]

        for file_path in registry_files:
            full_path = self.base_dir / file_path
            if not full_path.exists():
                issues.append(f"Missing file: {file_path}")
            else:
                print(f"✅ {file_path}")

        # Check templates
        template_files = ["PRPs/templates/bmad_story.md", "PRPs/templates/bmad_epic.md"]

        for file_path in template_files:
            full_path = self.base_dir / file_path
            if not full_path.exists():
                warnings.append(f"Missing template: {file_path}")
            else:
                print(f"✅ {file_path}")

        # Check scripts
        script_files = [
            "scripts/bmad-integration.py",
            "scripts/bmad-orchestrator.py",
            "scripts/story-dev.py",
        ]

        for file_path in script_files:
            full_path = self.base_dir / file_path
            if not full_path.exists():
                issues.append(f"Missing script: {file_path}")
            else:
                print(f"✅ {file_path}")

        # Summary
        print()
        if issues:
            print("❌ Issues Found:")
            for issue in issues:
                print(f"   - {issue}")
        else:
            print("✅ All required files and directories present")

        if warnings:
            print("\n⚠️  Warnings:")
            for warning in warnings:
                print(f"   - {warning}")

        return len(issues) == 0


def main():
    parser = argparse.ArgumentParser(
        description="BMAD-PRPs Orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start new project
  python scripts/bmad-orchestrator.py start-project my-project

  # Start with quick workflow (small projects)
  python scripts/bmad-orchestrator.py start-project my-project --workflow quick

  # Continue existing project
  python scripts/bmad-orchestrator.py continue-project

  # Import planning artifacts
  python scripts/bmad-orchestrator.py import-planning --project my-project

  # Story generation guidance
  python scripts/bmad-orchestrator.py generate-stories

  # Show workflow diagram
  python scripts/bmad-orchestrator.py show-workflow

  # Check integration setup
  python scripts/bmad-orchestrator.py check-integration
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Start project
    start_parser = subparsers.add_parser(
        "start-project", help="Start new BMAD-PRPs project"
    )
    start_parser.add_argument("project_name", help="Project name")
    start_parser.add_argument(
        "--workflow",
        choices=["standard", "quick"],
        default="standard",
        help="Workflow type (default: standard)",
    )

    # Continue project
    subparsers.add_parser("continue-project", help="Continue existing project")

    # Import planning
    import_parser = subparsers.add_parser(
        "import-planning", help="Import BMAD planning to PRPs"
    )
    import_parser.add_argument("--project", required=True, help="Project name")

    # Generate stories
    subparsers.add_parser("generate-stories", help="Guide for story generation")

    # Show workflow
    subparsers.add_parser("show-workflow", help="Show workflow diagram")

    # Check integration
    subparsers.add_parser("check-integration", help="Check integration setup")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    orchestrator = BMADOrchestrator()

    if args.command == "start-project":
        success = orchestrator.start_project(args.project_name, args.workflow)
    elif args.command == "continue-project":
        orchestrator.continue_project()
        success = True
    elif args.command == "import-planning":
        success = orchestrator.import_planning(args.project)
    elif args.command == "generate-stories":
        orchestrator.generate_stories()
        success = True
    elif args.command == "show-workflow":
        orchestrator.show_workflow_diagram()
        success = True
    elif args.command == "check-integration":
        success = orchestrator.check_integration()
    else:
        parser.print_help()
        sys.exit(1)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
