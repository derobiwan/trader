# Archon MCP Server Integration

Optional integration of [Archon](https://github.com/coleam00/Archon) as an MCP (Model Context Protocol) server for enhanced task and project management.

## What is Archon?

**Archon** is an open-source command center for AI coding assistants that provides:

- 🧠 **Knowledge Base Management**: Web crawling, document uploads, smart search with RAG
- 📋 **Task Management**: Integrated with knowledge repositories and AI-assisted generation
- 🔍 **Context Sharing**: Real-time context distribution across AI tools (Claude Code, Cursor, etc.)
- 🏗️ **Project Management**: Hierarchical project structures with progress tracking
- 🤖 **Multi-AI Support**: Works with Claude, GPT-4, Gemini, Ollama

## Why Use Archon with This Framework?

### Current Framework (File-Based)
```
✅ Lightweight: Pure JSON and Markdown
✅ Git-friendly: Easy version control
✅ Simple: No external dependencies
⚠️  Manual: Command-line task management
⚠️  Local: Single machine, no collaboration
⚠️  No RAG: No knowledge base search
```

### With Archon MCP Integration
```
✅ Everything above, PLUS:
✅ Web UI: Visual task and project dashboard
✅ Knowledge Base: Search across docs, PRPs, code
✅ Collaborative: Multi-user, team-friendly
✅ AI-Enhanced: Smart task suggestions, context retrieval
✅ MCP Protocol: Seamless Claude Code integration
```

## Architecture: Hybrid Approach

### Option 1: File-Based Only (Current)
```
Claude Code
    ↓
File System
    ↓
.agent-system/registry/tasks.json
PRPs/
workspace/
```

**Use when**: Solo developer, simple projects, prefer command-line

### Option 2: Archon MCP Enhanced
```
Claude Code
    ↓
MCP Protocol
    ↓
Archon Server (port 8051)
    ↓
┌─────────────┬──────────────┬─────────────┐
│ Knowledge   │ Task Manager │ File System │
│ Base (RAG)  │ (Supabase)   │ (Fallback)  │
└─────────────┴──────────────┴─────────────┘
```

**Use when**: Team projects, need knowledge base, want web UI, collaborative work

### Option 3: Hybrid (Recommended)
```
Claude Code
    ↓
┌──────────────────┬───────────────────┐
│                  │                   │
Archon MCP         File System
(Optional)         (Always Available)
│                  │
├─ Tasks          ├─ PRPs/
├─ Knowledge      ├─ .agent-system/
└─ Projects       └─ workspace/
```

**Use when**: Flexibility needed, gradual adoption, offline work

## Installation & Setup

### Prerequisites

```bash
# 1. Docker Desktop (for Archon services)
# 2. Node.js 18+
# 3. Supabase account (free tier)
# 4. OpenAI/Anthropic API key
```

### Step 1: Install Archon

```bash
# Clone Archon
cd ~/Projects  # or your preferred location
git clone https://github.com/coleam00/Archon.git
cd Archon

# Copy environment template
cp .env.example .env

# Edit .env with your keys
vim .env
```

**Required Environment Variables**:
```env
# Supabase
SUPABASE_URL=your-supabase-url
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-key

# AI Provider (choose one)
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key

# Archon MCP Server
MCP_SERVER_PORT=8051
MCP_SERVER_HOST=localhost
```

### Step 2: Start Archon Services

```bash
# Start all services with Docker
docker-compose up -d

# Verify services running
docker-compose ps

# Expected output:
# archon-frontend    (port 3000)
# archon-server      (port 8000)
# archon-mcp         (port 8051)
# archon-agents      (port 8052)
```

### Step 3: Initialize Database

```bash
# Run database migrations
npm run db:migrate

# Seed initial data (optional)
npm run db:seed
```

### Step 4: Access Web UI

```bash
# Open browser
open http://localhost:3000

# Configure API keys in Settings
# Create your first project
```

## Integration with PRPs Framework

### Configure MCP Server in Claude Code

Create or update `.claude/mcp-servers.json`:

```json
{
  "mcpServers": {
    "archon": {
      "url": "http://localhost:8051",
      "protocol": "sse",
      "enabled": true,
      "capabilities": {
        "tasks": true,
        "projects": true,
        "knowledge": true,
        "rag": true
      }
    }
  }
}
```

### Update Context Loader

Edit `.claude/context-loader.yaml`:

```yaml
global:
  max_total_context: 50000
  compression_enabled: true
  mcp_integration:
    enabled: true
    server: "archon"
    fallback_to_files: true  # Use file system if MCP unavailable

agents:
  orchestrator:
    always_load:
      - ".agent-system/registry/tasks.json"
      - "mcp://archon/projects/current"  # NEW: Load from Archon
      - "mcp://archon/tasks/active"      # NEW: Active tasks
    mcp_features:
      - task_sync
      - project_sync
    max_context_tokens: 12000

  context-researcher:
    always_load:
      - ".agent-system/agents/context-researcher/context.json"
      - "mcp://archon/knowledge/search?topic={current_task}"  # NEW: RAG search
    mcp_features:
      - knowledge_search
      - document_retrieval
    max_context_tokens: 10000

  # ... other agents with optional MCP features
```

### Task Management: Dual Mode

The framework now supports **dual-mode task management**:

#### Mode 1: File-Based (Always Available)

```bash
# Create task (file-based)
python scripts/agent-task-manager.py create \
  --title "Implement feature" \
  --priority high \
  --hours 8

# Syncs to: .agent-system/registry/tasks.json
```

#### Mode 2: Archon MCP (If Enabled)

```bash
# Create task (Archon)
python scripts/agent-task-manager.py create \
  --title "Implement feature" \
  --priority high \
  --hours 8 \
  --use-mcp archon

# Syncs to: Archon Supabase + local file (backup)
```

#### Mode 3: Hybrid (Automatic Sync)

```bash
# With MCP auto-sync enabled
python scripts/agent-task-manager.py create \
  --title "Implement feature" \
  --priority high \
  --hours 8

# Automatically syncs to BOTH:
# 1. .agent-system/registry/tasks.json (local)
# 2. Archon MCP Server (cloud)
```

### Knowledge Base Integration

#### Store PRPs in Archon Knowledge Base

```bash
# Index all PRPs for RAG search
python scripts/archon-sync.py index-prps \
  --directory PRPs/ \
  --recursive

# Index specific PRP
python scripts/archon-sync.py index-prp \
  --file PRPs/implementation/in-progress/feature.md \
  --project "my-project"
```

#### Search Knowledge Base from Claude Code

In Claude Code session:

```
"Context Researcher, search Archon knowledge base for: authentication patterns"

# Archon MCP will:
# 1. Perform RAG search across indexed PRPs
# 2. Return relevant sections with embeddings
# 3. Provide context-aware results
```

### Project Hierarchy Sync

Archon supports hierarchical projects that map to our workspace:

```bash
# Create project in Archon
python scripts/archon-sync.py create-project \
  --name "payment-feature" \
  --workspace workspace/features/payment/

# Auto-sync PRPs to project
python scripts/archon-sync.py link-prps \
  --project "payment-feature" \
  --prp-path PRPs/implementation/in-progress/payment-impl.md

# Result: Archon knows about project structure
```

## Enhanced Workflows with Archon

### Workflow 1: AI-Assisted Task Creation

```bash
# In Claude Code with Archon MCP
"PRP Orchestrator, analyze PRPs/planning/active/feature.md and generate tasks using Archon"

# Archon MCP will:
# 1. Read PRP content
# 2. Use AI to break down into tasks
# 3. Estimate effort
# 4. Assign to agents
# 5. Create tasks in both Archon and local registry
```

### Workflow 2: Knowledge-Enhanced Context Research

```bash
# In Claude Code
"Context Researcher, investigate authentication patterns for our payment feature"

# With Archon MCP:
# 1. Searches Archon knowledge base (RAG)
# 2. Finds similar implementations in indexed PRPs
# 3. Retrieves relevant code snippets
# 4. Provides context-aware recommendations
# 5. Much richer than file-only search
```

### Workflow 3: Team Collaboration

**Developer A** (using Claude Code):
```bash
# Create task with Archon
python scripts/agent-task-manager.py create \
  --title "Implement OAuth flow" \
  --use-mcp archon \
  --assign team-member-b
```

**Developer B** (using Archon Web UI):
```bash
# Open http://localhost:3000
# See task appear in real-time
# Claim task, update status
# Add notes visible to Claude Code
```

**Developer A** (sees update in Claude Code):
```bash
# Sync from Archon
python scripts/agent-task-manager.py sync --from archon

# Task now shows: status=in-progress, notes added
```

### Workflow 4: Progress Dashboard

```bash
# Web UI Dashboard (http://localhost:3000)
├── Projects
│   ├── payment-feature
│   │   ├── Tasks: 5 total, 2 in-progress
│   │   ├── PRPs: 3 linked
│   │   └── Knowledge: 12 documents
│   └── auth-system
│       └── ...
│
├── Knowledge Base
│   ├── Search across all PRPs
│   ├── Code snippets indexed
│   └── External docs imported
│
└── Agents Activity
    ├── Recent completions
    └── Active sessions
```

## Archon-Specific Scripts

### archon-sync.py (New Script)

```python
#!/usr/bin/env python3
"""
Archon MCP Synchronization Script
Bidirectional sync between local files and Archon
"""

import argparse
import requests
import json
from pathlib import Path

ARCHON_MCP_URL = "http://localhost:8051"

def sync_tasks_to_archon():
    """Upload local tasks to Archon"""
    tasks = json.loads(Path(".agent-system/registry/tasks.json").read_text())

    for task_id, task in tasks['tasks'].items():
        response = requests.post(
            f"{ARCHON_MCP_URL}/api/tasks",
            json={
                "id": task_id,
                "title": task['title'],
                "status": task['status'],
                "priority": task['priority'],
                "metadata": task
            }
        )
        print(f"✅ Synced {task_id} to Archon")

def sync_tasks_from_archon():
    """Download tasks from Archon to local"""
    response = requests.get(f"{ARCHON_MCP_URL}/api/tasks")
    archon_tasks = response.json()

    local_tasks = json.loads(Path(".agent-system/registry/tasks.json").read_text())

    for task in archon_tasks:
        task_id = task['id']
        if task_id not in local_tasks['tasks']:
            local_tasks['tasks'][task_id] = task['metadata']
            print(f"⬇️  Downloaded {task_id} from Archon")

    Path(".agent-system/registry/tasks.json").write_text(json.dumps(local_tasks, indent=2))

def index_prps_in_archon():
    """Index all PRPs in Archon knowledge base"""
    prp_files = Path("PRPs").rglob("*.md")

    for prp_file in prp_files:
        if prp_file.parent.name in ['.cache', 'templates']:
            continue

        content = prp_file.read_text()

        response = requests.post(
            f"{ARCHON_MCP_URL}/api/knowledge/index",
            json={
                "document_id": str(prp_file),
                "content": content,
                "metadata": {
                    "type": "prp",
                    "path": str(prp_file),
                    "stage": prp_file.parent.name
                }
            }
        )
        print(f"📚 Indexed {prp_file}")

def search_knowledge(query):
    """Search Archon knowledge base"""
    response = requests.post(
        f"{ARCHON_MCP_URL}/api/knowledge/search",
        json={"query": query, "top_k": 5}
    )
    results = response.json()

    print(f"\n🔍 Search Results for: {query}\n")
    for result in results:
        print(f"📄 {result['metadata']['path']}")
        print(f"   Score: {result['score']:.2f}")
        print(f"   {result['snippet'][:200]}...\n")

# CLI interface
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['sync-to', 'sync-from', 'index-prps', 'search'])
    parser.add_argument('--query', help='Search query')

    args = parser.parse_args()

    if args.command == 'sync-to':
        sync_tasks_to_archon()
    elif args.command == 'sync-from':
        sync_tasks_from_archon()
    elif args.command == 'index-prps':
        index_prps_in_archon()
    elif args.command == 'search':
        search_knowledge(args.query)
```

### Usage Examples

```bash
# Sync local tasks to Archon
python scripts/archon-sync.py sync-to

# Pull tasks from Archon
python scripts/archon-sync.py sync-from

# Index all PRPs for RAG search
python scripts/archon-sync.py index-prps

# Search knowledge base
python scripts/archon-sync.py search --query "authentication patterns"
```

## Agent-Task-Manager Updates

Update `scripts/agent-task-manager.py` to support MCP:

```python
class AgentTaskManager:
    def __init__(self, use_mcp=False):
        self.registry_path = BASE_DIR / ".agent-system" / "registry" / "tasks.json"
        self.use_mcp = use_mcp or self._check_mcp_available()

        if self.use_mcp:
            self.mcp_client = ArchonMCPClient("http://localhost:8051")

    def _check_mcp_available(self):
        """Check if Archon MCP server is running"""
        try:
            response = requests.get("http://localhost:8051/health", timeout=1)
            return response.status_code == 200
        except:
            return False

    def create_task(self, title, description="", priority="medium", estimated_hours=4):
        """Create task in both local and MCP (if available)"""
        task_id = super().create_task(title, description, priority, estimated_hours)

        # Sync to Archon if available
        if self.use_mcp:
            try:
                self.mcp_client.create_task({
                    "id": task_id,
                    "title": title,
                    "description": description,
                    "priority": priority,
                    "estimated_hours": estimated_hours
                })
                print(f"✅ Also created in Archon MCP")
            except Exception as e:
                print(f"⚠️  MCP sync failed (task still created locally): {e}")

        return task_id
```

## Configuration Files

### .claude/mcp-config.yaml (New)

```yaml
# Archon MCP Server Configuration
mcp:
  enabled: true  # Set to false to disable MCP integration
  server: "archon"
  url: "http://localhost:8051"
  protocol: "sse"  # or "stdio"

  # Fallback behavior
  fallback_to_files: true  # Use local files if MCP unavailable

  # Sync settings
  sync:
    auto_sync: true  # Automatically sync tasks/projects
    interval_minutes: 5
    bidirectional: true  # Sync both ways

  # Features to enable
  features:
    task_management: true
    knowledge_base: true
    project_hierarchy: true
    rag_search: true

  # Agent-specific MCP features
  agents:
    orchestrator:
      - task_sync
      - project_overview
    context-researcher:
      - knowledge_search
      - rag_queries
    business-analyst:
      - project_info
      - task_suggestions
    implementation-specialist:
      - code_context
      - similar_implementations
```

## Benefits of Archon Integration

### For Solo Developers
- ✅ **Visual Dashboard**: See project status at a glance
- ✅ **Knowledge Search**: Find relevant PRPs/docs faster
- ✅ **AI Suggestions**: Get task breakdowns automatically
- ✅ **Offline Mode**: Falls back to files when needed

### For Teams
- ✅ **Collaboration**: Shared task board and knowledge base
- ✅ **Real-time Sync**: Changes appear instantly
- ✅ **Multi-Client**: Claude Code, Cursor, Web UI all in sync
- ✅ **Team Context**: Everyone sees same project state

### For Complex Projects
- ✅ **RAG Search**: Find similar implementations across codebase
- ✅ **Hierarchical Projects**: Organize large systems
- ✅ **Context Intelligence**: Better agent context with embeddings
- ✅ **Historical Search**: Find past solutions quickly

## Migration Path

### Phase 1: Keep Using Files (No Change)
```bash
# Current workflow works exactly as before
python scripts/agent-task-manager.py create --title "Feature"
```

### Phase 2: Install Archon (Parallel)
```bash
# Install Archon, start services
# Files still work, Archon available optionally
python scripts/archon-sync.py sync-to  # When you want to use web UI
```

### Phase 3: Enable Auto-Sync
```yaml
# .claude/mcp-config.yaml
mcp:
  enabled: true
  sync:
    auto_sync: true
```

### Phase 4: Primary Archon (Files as Backup)
```yaml
# .claude/mcp-config.yaml
mcp:
  enabled: true
  fallback_to_files: true  # Files become backup
```

## Troubleshooting

### MCP Server Not Available

```bash
# Check Archon is running
docker-compose ps

# Check MCP endpoint
curl http://localhost:8051/health

# If down, restart
docker-compose restart archon-mcp
```

### Sync Conflicts

```bash
# If local and Archon diverge
python scripts/archon-sync.py resolve-conflicts \
  --strategy prefer-local  # or prefer-archon or merge
```

### Performance Issues

```yaml
# Reduce sync frequency
mcp:
  sync:
    interval_minutes: 15  # Default is 5
```

## Best Practices

### DO:
✅ Start with files only, add Archon when needed
✅ Keep fallback_to_files: true for reliability
✅ Index PRPs regularly for best RAG results
✅ Use Archon for knowledge search, files for speed
✅ Enable auto-sync for team projects

### DON'T:
❌ Don't rely solely on Archon without file backup
❌ Don't index sensitive data without reviewing Archon security
❌ Don't disable local files unless Archon is proven stable
❌ Don't skip the migration phases

## Summary

Archon MCP integration provides:

- 🎨 **Optional Enhancement**: File-based system still works perfectly
- 🧠 **Knowledge Intelligence**: RAG search across all PRPs and docs
- 👥 **Team Collaboration**: Shared dashboard and real-time sync
- 🔌 **Pluggable**: Enable/disable without breaking existing workflows
- 🔄 **Bidirectional Sync**: Local files ↔ Archon always in sync
- 📊 **Visual Dashboard**: Web UI for project overview
- 🤖 **AI-Enhanced**: Smart task suggestions and context retrieval

**The framework remains simple and lightweight, with Archon as powerful optional enhancement for teams and complex projects.**

---

**Next Steps**:
1. Review this integration plan
2. Decide if Archon fits your use case
3. Install following Phase 1 of migration path
4. Enable features gradually as needed
