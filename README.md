# test-autonomous-coding Agentic System

Autonomous coding framework combining:
- **GSD Framework** - Get Shit Done for spawning fresh agent contexts
- **Claude Skills** - Auto-loading best practices
- **GitHub MCP** - Direct GitHub integration
- **Railway** - Auto-deploy and testing

## Quick Start

### Prerequisites
- Node.js 18+
- Python 3.11+
- Git
- GitHub account
- Railway account (optional)

### Installation

1. Clone this repository:
```bash
git clone https://github.com/irra7/test-autonomous-coding-agentic-system.git
cd test-autonomous-coding-agentic-system
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Install GSD globally:
```bash
npm install -g @get-shit-done/cli
```

4. Configure environment:
```bash
cp .env.example .env
# Edit .env with your tokens
```

5. Configure Claude Desktop (see [Claude Desktop Setup](#claude-desktop-setup))

### Usage

#### Option 1: Using Orchestrator directly

```python
from src.orchestrator import Orchestrator

orchestrator = Orchestrator(
    github_token="ghp_xxx",
    anthropic_api_key="sk-ant-xxx"
)

pr_url = await orchestrator.handle_request(
    user_input="Añade autenticación OAuth2 a la API",
    repo="irra7/your-repo"
)

print(f"PR created: {pr_url}")
```

#### Option 2: Using Claude Code with GSD

```bash
# In Claude Code chat
/gsd:new-project
> "Añade autenticación OAuth2 a la API"
```

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

## Workflows

See [docs/WORKFLOWS.md](docs/WORKFLOWS.md)

## Troubleshooting

See [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)

## License

MIT

## Created by Bootstrap Agent

This repository was auto-generated on 2026-02-18 19:00:55
