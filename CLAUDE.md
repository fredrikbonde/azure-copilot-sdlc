# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

`azure-copilot-sdlc` drives **GitHub Copilot CLI** against **Azure DevOps** to automate the **plan → develop → review** work-item lifecycle. This repo is our **fork** of `berkslv/azure-copilot-sdlc` (`origin` = fork, `upstream` = original). See `STATUS.md` for current state, applied fixes, and the roadmap toward a full-SDLC tool.

## Commands

All code lives in `src/`.

```sh
# install dependencies
cd src && uv sync

# run a stage against a target repo (grammar is "<stage> <id>", NOT "<stage> execute <id>")
uv run azure-copilot-sdlc plan    <work-item-id> -d <path-to-target-repo>
uv run azure-copilot-sdlc develop <work-item-id> -d <path-to-target-repo>
uv run azure-copilot-sdlc review  <work-item-id> -d <path-to-target-repo>

# build a standalone executable
cd src && python build.py
```

(The `<stage> execute <id>` form in `src/README.md` is stale — `cli.py` registers the commands directly.)

## Architecture

- `src/cli.py` — Typer entry point; registers `plan`/`develop`/`review` as direct commands; loads `~/.azure-copilot-sdlc/.env` on startup.
- `src/commands/` — one module per stage. Each builds a prompt and runs the Copilot agent against the target repo's matching `.github/agents/<stage>.agent.md`.
- `src/services/`
  - `agent_discovery.py` — locates the agent `.md` file in the target repo.
  - `copilot_agent.py` — runs `copilot --additional-mcp-config <json> --yolo --model <m> --prompt <p> --agent <name>` (one-shot per stage) and streams output.
  - `mcp_configuration.py` — builds the MCP config for the `filesystem` + `azure-devops` servers (launched via `npx`).
  - `git_service.py` — branch/commit/push helpers.
- `src/utilities/` — `config.py` (.env load/prompt), `validators.py`, `console_helper.py`, `plan_parser.py`.
- `src/models/` — data models.

## Conventions & gotchas

- **Azure DevOps MCP auth:** use `--authentication pat` with `PERSONAL_ACCESS_TOKEN = base64(":" + PAT)`. Do **not** use `--authentication envvar` — it sends the PAT as a bearer token and fails with `TF400813` (anonymous access).
- **Default branch:** `git_service.create_branch` resolves the target repo's actual default branch (don't reintroduce a hardcoded `main`).
- **Secrets:** live in `~/.azure-copilot-sdlc/.env` (`ADO_MCP_AUTH_TOKEN`, `GITHUB_PAT`, `AZURE_DEVOPS_ORG`, `AZURE_DEVOPS_PROJECT`) — never commit them.
- **Requirements:** Python 3.12+, `uv`, Node.js (MCP servers via `npx`), and the Copilot CLI on `PATH`.

## Stack

Python 3.12+, Typer (CLI), GitPython, requests, python-dotenv, MCP; PyInstaller for builds.
