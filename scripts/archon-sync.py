#!/usr/bin/env python3
"""
Archon MCP Synchronization Script
Bidirectional sync between local files and Archon MCP server
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List

try:
    import requests
except ImportError:
    print("❌ Error: 'requests' library not found")
    print("Install with: pip install requests")
    sys.exit(1)

# Base directories
BASE_DIR = Path(__file__).parent.parent
ARCHON_MCP_URL = "http://localhost:8051"

class ArchonMCPClient:
    """Client for Archon MCP Server communication"""

    def __init__(self, url: str = ARCHON_MCP_URL):
        self.url = url
        self.available = self._check_health()

    def _check_health(self) -> bool:
        """Check if Archon MCP server is available"""
        try:
            response = requests.get(f"{self.url}/health", timeout=2)
            return response.status_code == 200
        except:
            return False

    def create_task(self, task_data: Dict) -> Dict:
        """Create task in Archon"""
        response = requests.post(
            f"{self.url}/api/tasks",
            json=task_data,
            timeout=5
        )
        response.raise_for_status()
        return response.json()

    def get_tasks(self) -> List[Dict]:
        """Get all tasks from Archon"""
        response = requests.get(f"{self.url}/api/tasks", timeout=5)
        response.raise_for_status()
        return response.json()

    def index_document(self, doc_data: Dict) -> Dict:
        """Index document in Archon knowledge base"""
        response = requests.post(
            f"{self.url}/api/knowledge/index",
            json=doc_data,
            timeout=10
        )
        response.raise_for_status()
        return response.json()

    def search_knowledge(self, query: str, top_k: int = 5) -> List[Dict]:
        """Search Archon knowledge base"""
        response = requests.post(
            f"{self.url}/api/knowledge/search",
            json={"query": query, "top_k": top_k},
            timeout=10
        )
        response.raise_for_status()
        return response.json()


class ArchonSync:
    """Synchronization manager between local files and Archon"""

    def __init__(self):
        self.base_dir = BASE_DIR
        self.registry_path = self.base_dir / ".agent-system" / "registry" / "tasks.json"
        self.prps_dir = self.base_dir / "PRPs"
        self.client = ArchonMCPClient()

    def check_availability(self) -> bool:
        """Check if Archon is available"""
        if not self.client.available:
            print("⚠️  Archon MCP server not available at", ARCHON_MCP_URL)
            print("   Make sure Archon is running: docker-compose up -d")
            return False
        return True

    def sync_tasks_to_archon(self):
        """Upload local tasks to Archon"""
        if not self.check_availability():
            return False

        print("📤 Syncing tasks to Archon...")

        try:
            with open(self.registry_path, 'r') as f:
                registry = json.load(f)
        except FileNotFoundError:
            print("❌ Error: Task registry not found at", self.registry_path)
            return False

        synced = 0
        errors = 0

        for task_id, task in registry.get('tasks', {}).items():
            if task_id == 'TASK-EXAMPLE':  # Skip example task
                continue

            try:
                self.client.create_task({
                    "id": task_id,
                    "title": task.get('title', 'Untitled'),
                    "description": task.get('description', ''),
                    "status": task.get('status', 'pending'),
                    "priority": task.get('priority', 'medium'),
                    "estimated_hours": task.get('estimated_hours', 4),
                    "phase": task.get('phase', 4),
                    "metadata": task
                })
                print(f"  ✅ {task_id}: {task.get('title', 'Untitled')}")
                synced += 1
            except Exception as e:
                print(f"  ❌ {task_id}: {str(e)}")
                errors += 1

        print(f"\n📊 Synced: {synced}, Errors: {errors}")
        return True

    def sync_tasks_from_archon(self):
        """Download tasks from Archon to local"""
        if not self.check_availability():
            return False

        print("📥 Syncing tasks from Archon...")

        try:
            with open(self.registry_path, 'r') as f:
                registry = json.load(f)
        except FileNotFoundError:
            print("❌ Error: Task registry not found")
            return False

        try:
            archon_tasks = self.client.get_tasks()
        except Exception as e:
            print(f"❌ Error fetching tasks from Archon: {e}")
            return False

        added = 0
        updated = 0

        for task in archon_tasks:
            task_id = task.get('id')
            if not task_id:
                continue

            # Convert Archon task to local format
            local_task = task.get('metadata', {})
            if not local_task:
                local_task = {
                    "title": task.get('title'),
                    "description": task.get('description', ''),
                    "status": task.get('status', 'pending'),
                    "priority": task.get('priority', 'medium'),
                    "estimated_hours": task.get('estimated_hours', 4),
                    "created_at": task.get('created_at', datetime.now().isoformat()),
                    "dependencies": [],
                    "files": []
                }

            if task_id not in registry['tasks']:
                registry['tasks'][task_id] = local_task
                print(f"  ⬇️  Added {task_id}: {local_task.get('title')}")
                added += 1
            else:
                # Update if Archon version is newer
                if task.get('updated_at', '') > registry['tasks'][task_id].get('updated_at', ''):
                    registry['tasks'][task_id].update(local_task)
                    print(f"  🔄 Updated {task_id}: {local_task.get('title')}")
                    updated += 1

        # Update statistics
        registry['statistics'] = {
            "total": len(registry['tasks']),
            "completed": sum(1 for t in registry['tasks'].values() if t.get('status') == 'completed'),
            "in_progress": sum(1 for t in registry['tasks'].values() if t.get('status') == 'in-progress'),
            "blocked": sum(1 for t in registry['tasks'].values() if t.get('status') == 'blocked'),
            "pending": sum(1 for t in registry['tasks'].values() if t.get('status') == 'pending')
        }

        # Save updated registry
        with open(self.registry_path, 'w') as f:
            json.dump(registry, f, indent=2)

        print(f"\n📊 Added: {added}, Updated: {updated}")
        return True

    def index_prps_in_archon(self, directory: Optional[Path] = None):
        """Index all PRPs in Archon knowledge base"""
        if not self.check_availability():
            return False

        print("📚 Indexing PRPs in Archon knowledge base...")

        search_dir = directory if directory else self.prps_dir
        prp_files = search_dir.rglob("*.md")

        indexed = 0
        errors = 0

        for prp_file in prp_files:
            # Skip cache and templates
            if '.cache' in prp_file.parts or 'templates' in prp_file.parts:
                continue

            try:
                content = prp_file.read_text()

                # Determine stage from path
                stage = "unknown"
                if "planning" in prp_file.parts:
                    if "backlog" in prp_file.parts:
                        stage = "backlog"
                    elif "active" in prp_file.parts:
                        stage = "active-planning"
                    elif "completed" in prp_file.parts:
                        stage = "completed-planning"
                elif "implementation" in prp_file.parts:
                    if "in-progress" in prp_file.parts:
                        stage = "in-progress"
                    elif "completed" in prp_file.parts:
                        stage = "completed"
                elif "architecture" in prp_file.parts:
                    stage = "architecture"
                elif "contracts" in prp_file.parts:
                    stage = "contracts"
                elif "security" in prp_file.parts:
                    stage = "security"

                self.client.index_document({
                    "document_id": str(prp_file.relative_to(self.base_dir)),
                    "content": content,
                    "metadata": {
                        "type": "prp",
                        "path": str(prp_file.relative_to(self.base_dir)),
                        "stage": stage,
                        "filename": prp_file.name,
                        "size": len(content)
                    }
                })

                print(f"  ✅ {prp_file.relative_to(self.base_dir)}")
                indexed += 1

            except Exception as e:
                print(f"  ❌ {prp_file.name}: {str(e)}")
                errors += 1

        print(f"\n📊 Indexed: {indexed}, Errors: {errors}")
        return True

    def search_knowledge(self, query: str, top_k: int = 5):
        """Search Archon knowledge base"""
        if not self.check_availability():
            return False

        print(f"🔍 Searching for: '{query}'\n")

        try:
            results = self.client.search_knowledge(query, top_k)

            if not results:
                print("No results found.")
                return True

            for i, result in enumerate(results, 1):
                metadata = result.get('metadata', {})
                score = result.get('score', 0)
                snippet = result.get('snippet', '')

                print(f"{i}. 📄 {metadata.get('path', 'Unknown')}")
                print(f"   Score: {score:.2f} | Stage: {metadata.get('stage', 'unknown')}")
                print(f"   {snippet[:200]}...")
                print()

        except Exception as e:
            print(f"❌ Error searching: {e}")
            return False

        return True


def main():
    parser = argparse.ArgumentParser(
        description='Sync tasks and PRPs with Archon MCP Server',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Sync local tasks to Archon
  python scripts/archon-sync.py sync-to

  # Pull tasks from Archon
  python scripts/archon-sync.py sync-from

  # Index all PRPs
  python scripts/archon-sync.py index-prps

  # Search knowledge base
  python scripts/archon-sync.py search --query "authentication patterns"
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Sync to Archon
    subparsers.add_parser('sync-to', help='Upload local tasks to Archon')

    # Sync from Archon
    subparsers.add_parser('sync-from', help='Download tasks from Archon')

    # Index PRPs
    index_parser = subparsers.add_parser('index-prps', help='Index PRPs in Archon knowledge base')
    index_parser.add_argument('--directory', type=Path, help='Directory to index (default: PRPs/)')

    # Search
    search_parser = subparsers.add_parser('search', help='Search Archon knowledge base')
    search_parser.add_argument('--query', required=True, help='Search query')
    search_parser.add_argument('--top-k', type=int, default=5, help='Number of results (default: 5)')

    # Health check
    subparsers.add_parser('health', help='Check Archon MCP server availability')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    sync = ArchonSync()

    if args.command == 'sync-to':
        success = sync.sync_tasks_to_archon()
    elif args.command == 'sync-from':
        success = sync.sync_tasks_from_archon()
    elif args.command == 'index-prps':
        success = sync.index_prps_in_archon(args.directory)
    elif args.command == 'search':
        success = sync.search_knowledge(args.query, args.top_k)
    elif args.command == 'health':
        success = sync.check_availability()
        if success:
            print("✅ Archon MCP server is healthy")
    else:
        parser.print_help()
        sys.exit(1)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
