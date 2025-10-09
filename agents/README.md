# DataHub AI Agents

This directory contains the Google ADK (Agent Development Kit) configuration for the DataHub multi-agent development team.

## Files

- **`team.py`** - Defines the agent team structure and workflow
- **`tools.py`** - Provides tools for file operations, testing, and code analysis

## Agent Team

### Agents
1. **Project Manager** - Converts business requirements into technical specifications
2. **Software Architect** - Designs solutions and proposes refactoring
3. **Developer** - Implements code changes
4. **Tester** - Writes and executes tests
5. **Documenter** - Creates comprehensive documentation

### Workflow
```
Requirement → PM → Architect → Developer ↔ Tester → Documenter → docs/AI/
```

## Quick Start

```bash
# Start ADK service
docker-compose up -d adk

# Access web UI
open http://localhost:7860
```

## Documentation

See `docs/AI/` for complete documentation:
- `SETUP_GUIDE.md` - Setup instructions
- `QUICK_REFERENCE.md` - Daily usage guide
- `INTEGRATION_SUMMARY.md` - Overview

## Customization

### Change Agent Models
Edit `team.py` and modify the `model` parameter:
```python
PM = LlmAgent(
  name="ProjectManager",
  model="gemini-1.5-pro",  # Change this
  ...
)
```

### Add Custom Tools
Edit `tools.py` and add your function:
```python
def my_custom_tool(param: str) -> dict:
    # Your logic here
    return {"result": "..."}

MyTool = FunctionTool(func=my_custom_tool)
```

Then add to an agent in `team.py`:
```python
Developer = LlmAgent(
  ...
  tools=[WriteText, MyTool]
)
```

### Adjust Security Settings
Edit the `allowed_dirs` lists in `tools.py`:
```python
def read_files(...):
    allowed_dirs = ['ingestion', 'data_warehouse', ...]  # Modify this
```

## Support

- Issues with setup: See `docs/AI/SETUP_GUIDE.md`
- Issues with agents: Check `docker-compose logs adk`
- Questions: Review `docs/AI/QUICK_REFERENCE.md`
