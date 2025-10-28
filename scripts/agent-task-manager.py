#!/usr/bin/env python3
"""
Agent Task Manager - Coordinate task assignment and tracking
"""
import json
import argparse
import uuid
from datetime import datetime
from pathlib import Path
import sys

# Base directory
BASE_DIR = Path(__file__).parent.parent

class AgentTaskManager:
    def __init__(self):
        self.registry_path = BASE_DIR / ".agent-system" / "registry" / "tasks.json"
        self.sessions_path = BASE_DIR / ".agent-system" / "sessions" / "active"
        self.handoffs_path = BASE_DIR / ".agent-system" / "sync" / "handoffs.json"
        
    def load_registry(self):
        """Load the task registry"""
        with open(self.registry_path, 'r') as f:
            return json.load(f)
    
    def save_registry(self, registry):
        """Save the task registry"""
        registry['updated'] = datetime.now().isoformat()
        with open(self.registry_path, 'w') as f:
            json.dump(registry, f, indent=2)
    
    def claim_task(self, agent_name, task_id):
        """Claim a task for an agent"""
        # Generate session ID
        session_id = f"claude-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6]}"
        
        # Load registry
        registry = self.load_registry()
        
        # Check if task exists
        if task_id not in registry['tasks']:
            print(f"❌ Error: Task {task_id} not found")
            return False
        
        task = registry['tasks'][task_id]
        
        # Check if task is available
        if task.get('status') == 'in-progress':
            print(f"⚠️  Warning: Task {task_id} is already in progress by {task.get('agent')}")
            return False
        
        # Update task
        task['status'] = 'in-progress'
        task['agent'] = agent_name
        task['session'] = session_id
        task['claimed_at'] = datetime.now().isoformat()
        
        # Update statistics
        registry['statistics']['in_progress'] += 1
        if task.get('status') == 'pending':
            registry['statistics']['pending'] -= 1
        
        # Save registry
        self.save_registry(registry)
        
        # Create session lock file
        session_data = {
            "session_id": session_id,
            "agent": agent_name,
            "started": datetime.now().isoformat(),
            "last_heartbeat": datetime.now().isoformat(),
            "claimed_tasks": [task_id],
            "working_directory": f"workspace/features/{task_id.lower().replace('-', '_')}"
        }
        
        session_file = self.sessions_path / f"{session_id}.lock"
        with open(session_file, 'w') as f:
            json.dump(session_data, f, indent=2)
        
        print(f"✅ Task {task_id} claimed by {agent_name}")
        print(f"📝 Session ID: {session_id}")
        return True
    
    def complete_task(self, task_id, notes=""):
        """Mark a task as complete"""
        registry = self.load_registry()
        
        if task_id not in registry['tasks']:
            print(f"❌ Error: Task {task_id} not found")
            return False
        
        task = registry['tasks'][task_id]
        
        # Update task
        task['status'] = 'completed'
        task['completed_at'] = datetime.now().isoformat()
        if notes:
            task['completion_notes'] = notes
        
        # Update statistics
        registry['statistics']['completed'] += 1
        registry['statistics']['in_progress'] -= 1
        
        # Save registry
        self.save_registry(registry)
        
        # Clean up session if it exists
        if 'session' in task:
            session_file = self.sessions_path / f"{task['session']}.lock"
            if session_file.exists():
                # Move to history
                history_path = BASE_DIR / ".agent-system" / "sessions" / "history"
                history_path.mkdir(exist_ok=True)
                session_file.rename(history_path / session_file.name)
        
        print(f"✅ Task {task_id} completed")
        return True
    
    def create_task(self, title, description="", priority="medium", estimated_hours=4):
        """Create a new task"""
        registry = self.load_registry()
        
        # Generate task ID
        task_count = registry['statistics']['total']
        task_id = f"TASK-{task_count + 1:03d}"
        
        # Create task
        task = {
            "title": title,
            "description": description,
            "phase": 4,  # Default to implementation phase
            "status": "pending",
            "priority": priority,
            "estimated_hours": estimated_hours,
            "created_at": datetime.now().isoformat(),
            "dependencies": [],
            "files": [],
            "context_refs": []
        }
        
        # Add to registry
        registry['tasks'][task_id] = task
        registry['statistics']['total'] += 1
        registry['statistics']['pending'] += 1
        
        # Save registry
        self.save_registry(registry)
        
        print(f"✅ Created task {task_id}: {title}")
        return task_id
    
    def list_tasks(self, status=None, agent=None):
        """List tasks with optional filters"""
        registry = self.load_registry()
        
        tasks = registry['tasks']
        
        # Apply filters
        if status:
            tasks = {k: v for k, v in tasks.items() if v.get('status') == status}
        if agent:
            tasks = {k: v for k, v in tasks.items() if v.get('agent') == agent}
        
        if not tasks:
            print("No tasks found matching criteria")
            return
        
        # Display tasks
        print(f"\n{'ID':<10} {'Status':<12} {'Priority':<8} {'Agent':<20} {'Title':<40}")
        print("-" * 90)
        
        for task_id, task in tasks.items():
            status_emoji = {
                'pending': '⏸️',
                'in-progress': '🔄',
                'completed': '✅',
                'blocked': '🔴'
            }.get(task.get('status', 'pending'), '❓')
            
            priority_emoji = {
                'critical': '🔴',
                'high': '🟠',
                'medium': '🟡',
                'low': '🟢'
            }.get(task.get('priority', 'medium'), '⚪')
            
            print(f"{task_id:<10} {status_emoji} {task.get('status', 'pending'):<10} "
                  f"{priority_emoji} {task.get('priority', 'medium'):<6} "
                  f"{task.get('agent', '-'):<20} {task.get('title', 'Untitled')[:40]:<40}")
    
    def handoff_task(self, task_id, to_agent, notes=""):
        """Create a handoff from one agent to another"""
        registry = self.load_registry()
        
        if task_id not in registry['tasks']:
            print(f"❌ Error: Task {task_id} not found")
            return False
        
        task = registry['tasks'][task_id]
        from_agent = task.get('agent', 'unknown')
        
        # Create handoff record
        with open(self.handoffs_path, 'r') as f:
            handoffs = json.load(f)
        
        handoff = {
            "handoff_id": f"HO-{len(handoffs.get('handoffs', [])) + 1:03d}",
            "timestamp": datetime.now().isoformat(),
            "task": task_id,
            "from_agent": from_agent,
            "to_agent": to_agent,
            "status": task.get('status', 'unknown'),
            "notes": notes,
            "files_modified": task.get('files', [])
        }
        
        handoffs.setdefault('handoffs', []).append(handoff)
        
        with open(self.handoffs_path, 'w') as f:
            json.dump(handoffs, f, indent=2)
        
        # Update task assignment
        task['agent'] = to_agent
        task['handoff_at'] = datetime.now().isoformat()
        self.save_registry(registry)
        
        print(f"✅ Handoff created: {task_id} from {from_agent} to {to_agent}")
        return True
    
    def status(self, task_id=None):
        """Show status of a specific task or overall statistics"""
        registry = self.load_registry()
        
        if task_id:
            if task_id not in registry['tasks']:
                print(f"❌ Error: Task {task_id} not found")
                return
            
            task = registry['tasks'][task_id]
            print(f"\n📋 Task Details: {task_id}")
            print(f"{'='*50}")
            print(f"Title: {task.get('title', 'Untitled')}")
            print(f"Status: {task.get('status', 'unknown')}")
            print(f"Priority: {task.get('priority', 'medium')}")
            print(f"Agent: {task.get('agent', 'unassigned')}")
            print(f"Session: {task.get('session', 'none')}")
            print(f"Created: {task.get('created_at', 'unknown')}")
            if task.get('claimed_at'):
                print(f"Claimed: {task['claimed_at']}")
            if task.get('completed_at'):
                print(f"Completed: {task['completed_at']}")
            if task.get('description'):
                print(f"Description: {task['description']}")
            if task.get('dependencies'):
                print(f"Dependencies: {', '.join(task['dependencies'])}")
            if task.get('files'):
                print(f"Files: {', '.join(task['files'][:3])}...")
        else:
            # Show overall statistics
            stats = registry['statistics']
            print(f"\n📊 Task Registry Statistics")
            print(f"{'='*50}")
            print(f"Total Tasks: {stats['total']}")
            print(f"✅ Completed: {stats['completed']}")
            print(f"🔄 In Progress: {stats['in_progress']}")
            print(f"⏸️  Pending: {stats['pending']}")
            print(f"🔴 Blocked: {stats['blocked']}")
            
            # Show active sessions
            active_sessions = list(self.sessions_path.glob("*.lock"))
            if active_sessions:
                print(f"\n🔗 Active Sessions: {len(active_sessions)}")
                for session_file in active_sessions:
                    with open(session_file, 'r') as f:
                        session = json.load(f)
                    print(f"  - {session['session_id']}: {session['agent']} "
                          f"({len(session.get('claimed_tasks', []))} tasks)")

def main():
    parser = argparse.ArgumentParser(description='Agent Task Manager')
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Claim command
    claim_parser = subparsers.add_parser('claim', help='Claim a task')
    claim_parser.add_argument('--agent', required=True, help='Agent name')
    claim_parser.add_argument('--task', required=True, help='Task ID')
    
    # Complete command
    complete_parser = subparsers.add_parser('complete', help='Complete a task')
    complete_parser.add_argument('--task', required=True, help='Task ID')
    complete_parser.add_argument('--notes', default='', help='Completion notes')
    
    # Create command
    create_parser = subparsers.add_parser('create', help='Create a new task')
    create_parser.add_argument('--title', required=True, help='Task title')
    create_parser.add_argument('--description', default='', help='Task description')
    create_parser.add_argument('--priority', default='medium', 
                              choices=['critical', 'high', 'medium', 'low'])
    create_parser.add_argument('--hours', type=int, default=4, help='Estimated hours')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List tasks')
    list_parser.add_argument('--status', help='Filter by status')
    list_parser.add_argument('--agent', help='Filter by agent')
    
    # Handoff command
    handoff_parser = subparsers.add_parser('handoff', help='Handoff task to another agent')
    handoff_parser.add_argument('--task', required=True, help='Task ID')
    handoff_parser.add_argument('--to-agent', required=True, help='Target agent')
    handoff_parser.add_argument('--notes', default='', help='Handoff notes')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Show task or system status')
    status_parser.add_argument('--task', help='Task ID (optional)')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    manager = AgentTaskManager()
    
    if args.command == 'claim':
        manager.claim_task(args.agent, args.task)
    elif args.command == 'complete':
        manager.complete_task(args.task, args.notes)
    elif args.command == 'create':
        manager.create_task(args.title, args.description, args.priority, args.hours)
    elif args.command == 'list':
        manager.list_tasks(args.status, args.agent)
    elif args.command == 'handoff':
        manager.handoff_task(args.task, args.to_agent, args.notes)
    elif args.command == 'status':
        manager.status(args.task)

if __name__ == "__main__":
    main()
