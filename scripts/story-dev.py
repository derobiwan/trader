#!/usr/bin/env python3
"""
Story-based Development Workflow
Combines BMAD stories with PRPs agent coordination
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime

# Base directory
BASE_DIR = Path(__file__).parent.parent


class StoryDev:
    """Story-based development workflow manager"""

    def __init__(self):
        self.base_dir = BASE_DIR
        self.stories_dir = BASE_DIR / "docs" / "stories"
        self.agent_system = BASE_DIR / ".agent-system"

    def work_on_story(self, story_id: str, agent: str = "implementation-specialist"):
        """Start development on a BMAD story"""
        print(f"📖 Starting work on {story_id}")
        print("=" * 60)

        # Validate story exists
        story_file = self.stories_dir / f"{story_id}.md"
        if not story_file.exists():
            print(f"❌ Story not found: {story_file}")
            print(f"   Available stories:")
            for story in sorted(self.stories_dir.glob("STORY-*.md")):
                print(f"   - {story.stem}")
            return False

        # Load story
        story_content = story_file.read_text()

        # Find corresponding task
        task_id = self._find_task_for_story(story_id)
        if not task_id:
            print(f"⚠️  No task found for {story_id}")
            print(f"   Run: python scripts/bmad-integration.py sync-stories")
            return False

        # Check if story view exists, generate if not
        view_file = BASE_DIR / "PRPs" / ".cache" / "story-views" / f"{story_id}-implementation.md"
        if not view_file.exists():
            print(f"🔍 Generating agent view for {story_id}...")
            self._generate_story_view(story_id)

        # Claim task
        print(f"\n📌 Claiming {task_id}...")
        if not self._claim_task(task_id, agent):
            return False

        # Show development context
        self._show_development_context(story_id, task_id, agent)

        return True

    def list_stories(self, status: str = None):
        """List available stories"""
        print("\n📚 Available Stories")
        print("=" * 80)

        # Load story registry
        registry_file = self.agent_system / "registry" / "stories.json"
        if not registry_file.exists():
            print("❌ Story registry not found")
            print("   Run: python scripts/bmad-integration.py sync-stories")
            return False

        with open(registry_file, 'r') as f:
            registry = json.load(f)

        stories = registry.get('stories', {})

        if not stories or (len(stories) == 1 and 'STORY-EXAMPLE' in stories):
            print("No stories found")
            print("Create stories first, then run: python scripts/bmad-integration.py sync-stories")
            return False

        # Filter by status if specified
        if status:
            stories = {k: v for k, v in stories.items() if v.get('status') == status}

        # Display stories
        print(f"\n{'Story ID':<15} {'Status':<12} {'Task':<10} {'Title':<40}")
        print("-" * 80)

        for story_id, story in sorted(stories.items()):
            if story_id == "STORY-EXAMPLE":
                continue

            status_emoji = {
                'pending': '⏸️',
                'in-progress': '🔄',
                'completed': '✅',
                'blocked': '🔴'
            }.get(story.get('status', 'pending'), '❓')

            print(f"{story_id:<15} {status_emoji} {story.get('status', 'pending'):<10} "
                  f"{story.get('task_id', '-'):<10} {story.get('title', 'Untitled')[:40]:<40}")

        print()
        print(f"Total: {len([s for s in stories if s != 'STORY-EXAMPLE'])}")

        return True

    def story_status(self, story_id: str):
        """Show detailed status of a story"""
        print(f"\n📋 Story Status: {story_id}")
        print("=" * 60)

        # Load story registry
        registry_file = self.agent_system / "registry" / "stories.json"
        with open(registry_file, 'r') as f:
            registry = json.load(f)

        if story_id not in registry['stories']:
            print(f"❌ Story not found: {story_id}")
            return False

        story = registry['stories'][story_id]

        # Display story info
        print(f"Title:    {story.get('title', 'Untitled')}")
        print(f"Status:   {story.get('status', 'unknown')}")
        print(f"Epic:     {story.get('epic_id', 'None')}")
        print(f"Task:     {story.get('task_id', 'None')}")
        print(f"File:     {story.get('file', 'unknown')}")
        print(f"Created:  {story.get('created_at', 'unknown')}")

        # Load task details if available
        if story.get('task_id'):
            task_file = self.agent_system / "registry" / "tasks.json"
            with open(task_file, 'r') as f:
                task_registry = json.load(f)

            task = task_registry['tasks'].get(story['task_id'])
            if task:
                print(f"\n📌 Task Details:")
                print(f"  Status:   {task.get('status')}")
                print(f"  Agent:    {task.get('agent', 'unassigned')}")
                print(f"  Priority: {task.get('priority')}")
                print(f"  Estimate: {task.get('estimated_hours')} hours")

        # Check if story file exists
        story_file = self.base_dir / story['file']
        if story_file.exists():
            print(f"\n📄 Story File: {story_file}")
        else:
            print(f"\n⚠️  Story file not found: {story_file}")

        # Check if agent view exists
        view_file = self.base_dir / "PRPs" / ".cache" / "story-views" / f"{story_id}-implementation.md"
        if view_file.exists():
            print(f"✅ Agent view: {view_file}")
        else:
            print(f"⚠️  Agent view not generated yet")

        return True

    def complete_story(self, story_id: str, notes: str = ""):
        """Mark story as complete"""
        print(f"✅ Completing {story_id}")

        # Find task
        task_id = self._find_task_for_story(story_id)
        if not task_id:
            print(f"❌ No task found for {story_id}")
            return False

        # Complete task using agent-task-manager
        cmd = f"python {BASE_DIR}/scripts/agent-task-manager.py complete --task {task_id}"
        if notes:
            cmd += f' --notes "{notes}"'

        print(f"Running: {cmd}")
        import subprocess
        result = subprocess.run(cmd, shell=True)

        if result.returncode == 0:
            # Update story status
            registry_file = self.agent_system / "registry" / "stories.json"
            with open(registry_file, 'r') as f:
                registry = json.load(f)

            if story_id in registry['stories']:
                registry['stories'][story_id]['status'] = 'completed'
                registry['stories'][story_id]['completed_at'] = datetime.now().isoformat()
                registry['statistics']['completed'] += 1
                registry['statistics']['in_progress'] -= 1

                with open(registry_file, 'w') as f:
                    json.dump(registry, f, indent=2)

            print(f"✅ {story_id} marked complete")
            return True
        else:
            print(f"❌ Failed to complete task")
            return False

    def next_story(self):
        """Suggest next story to work on"""
        print("\n🎯 Next Story Suggestion")
        print("=" * 60)

        # Load story registry
        registry_file = self.agent_system / "registry" / "stories.json"
        with open(registry_file, 'r') as f:
            registry = json.load(f)

        stories = registry.get('stories', {})

        # Find pending stories
        pending = [
            (sid, s) for sid, s in stories.items()
            if s.get('status') == 'pending' and sid != 'STORY-EXAMPLE'
        ]

        if not pending:
            print("🎉 No pending stories! All work is complete or in progress.")
            return True

        # Sort by story number
        pending.sort(key=lambda x: x[0])

        # Suggest first pending
        story_id, story = pending[0]
        print(f"Suggested: {story_id}")
        print(f"Title:     {story.get('title', 'Untitled')}")
        print(f"Epic:      {story.get('epic_id', 'None')}")
        print(f"Task:      {story.get('task_id', 'None')}")
        print()
        print(f"Start work with:")
        print(f"  python scripts/story-dev.py work-on-story {story_id}")

        return True

    # Helper methods

    def _find_task_for_story(self, story_id: str) -> str:
        """Find corresponding task ID for a story"""
        registry_file = self.agent_system / "registry" / "stories.json"
        if not registry_file.exists():
            return None

        with open(registry_file, 'r') as f:
            registry = json.load(f)

        story = registry['stories'].get(story_id)
        return story.get('task_id') if story else None

    def _claim_task(self, task_id: str, agent: str) -> bool:
        """Claim task using agent-task-manager"""
        cmd = f"python {BASE_DIR}/scripts/agent-task-manager.py claim --agent {agent} --task {task_id}"
        import subprocess
        result = subprocess.run(cmd, shell=True)
        return result.returncode == 0

    def _generate_story_view(self, story_id: str):
        """Generate agent view for story"""
        cmd = f"python {BASE_DIR}/scripts/bmad-integration.py generate-views"
        import subprocess
        subprocess.run(cmd, shell=True)

    def _show_development_context(self, story_id: str, task_id: str, agent: str):
        """Display development context"""
        print(f"\n🎯 Development Context for {story_id}")
        print("=" * 60)

        story_file = self.stories_dir / f"{story_id}.md"
        view_file = self.base_dir / "PRPs" / ".cache" / "story-views" / f"{story_id}-implementation.md"

        print(f"\n📖 Full Story:")
        print(f"   {story_file}")
        print(f"   Size: {story_file.stat().st_size / 1024:.1f}KB")

        if view_file.exists():
            print(f"\n🔍 Agent View (Optimized):")
            print(f"   {view_file}")
            print(f"   Size: {view_file.stat().st_size / 1024:.1f}KB")

        print(f"\n📌 Task:")
        print(f"   ID: {task_id}")
        print(f"   Agent: {agent}")
        print(f"   Registry: .agent-system/registry/tasks.json")

        print(f"\n💻 Start Implementation:")
        print(f"   1. Review optimized view: cat {view_file}")
        print(f"   2. Read full story for details: cat {story_file}")
        print(f"   3. Implement with tests")
        print(f"   4. Run validations")
        print(f"   5. Complete: python scripts/story-dev.py complete-story {story_id}")

        print(f"\n🤖 With Claude Code:")
        print(f'   "Implementation Specialist, implement {task_id} using {story_id}"')


def main():
    parser = argparse.ArgumentParser(
        description='Story-based Development Workflow',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Work on a story
  python scripts/story-dev.py work-on-story STORY-001

  # List all stories
  python scripts/story-dev.py list-stories

  # List pending stories
  python scripts/story-dev.py list-stories --status pending

  # Show story status
  python scripts/story-dev.py story-status STORY-001

  # Complete story
  python scripts/story-dev.py complete-story STORY-001 --notes "Implementation complete"

  # Get next story suggestion
  python scripts/story-dev.py next-story
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Work on story
    work_parser = subparsers.add_parser('work-on-story', help='Start work on a story')
    work_parser.add_argument('story_id', help='Story ID (e.g., STORY-001)')
    work_parser.add_argument('--agent', default='implementation-specialist',
                            help='Agent to assign (default: implementation-specialist)')

    # List stories
    list_parser = subparsers.add_parser('list-stories', help='List stories')
    list_parser.add_argument('--status', help='Filter by status')

    # Story status
    status_parser = subparsers.add_parser('story-status', help='Show story status')
    status_parser.add_argument('story_id', help='Story ID')

    # Complete story
    complete_parser = subparsers.add_parser('complete-story', help='Complete a story')
    complete_parser.add_argument('story_id', help='Story ID')
    complete_parser.add_argument('--notes', default='', help='Completion notes')

    # Next story
    subparsers.add_parser('next-story', help='Get next story suggestion')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    story_dev = StoryDev()

    if args.command == 'work-on-story':
        success = story_dev.work_on_story(args.story_id, args.agent)
    elif args.command == 'list-stories':
        success = story_dev.list_stories(args.status)
    elif args.command == 'story-status':
        success = story_dev.story_status(args.story_id)
    elif args.command == 'complete-story':
        success = story_dev.complete_story(args.story_id, args.notes)
    elif args.command == 'next-story':
        success = story_dev.next_story()
    else:
        parser.print_help()
        sys.exit(1)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
