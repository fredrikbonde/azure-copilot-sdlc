# azure-copilot-sdlc — Project Status

_Last updated: 2026-06-17_

## What this is

An AI-driven SDLC automation tool that drives **GitHub Copilot CLI** against **Azure DevOps** work items, automating the **plan → develop → review** cycle. Each stage reads a custom agent file from the target repo (`.github/agents/*.agent.md`) and talks to Azure Boards/Repos via the Model Context Protocol (MCP).

This repo is a **fork** of [berkslv/azure-copilot-sdlc](https://github.com/berkslv/azure-copilot-sdlc) (`origin` = our fork, `upstream` = the original). We intend to build our own full-SDLC tool on top of this base.

## Working today ✅

The three-stage loop runs end-to-end (verified manually against a test repo + a real Azure DevOps work item):

| Stage | What it does | Azure DevOps side effects |
|---|---|---|
| `plan` | Analyzes the work item + repo, produces an implementation plan | Posts a `# COPILOT PLAN` comment, sets work item to **Active** |
| `develop` | Creates `feature/<id>`, implements the change, adds tests, commits | Pushes branch, opens a **pull request** |
| `review` | Reviews the branch changes, produces a prioritized findings report | Posts a `# COPILOT REVIEW` comment on the PR |

Usage: `uv run azure-copilot-sdlc <plan|develop|review> <work-item-id> -d <repo-path>`

## Fixes applied in this fork (vs. upstream)

These were needed to get the loop actually working; several are also worth contributing back upstream:

1. **PAT authentication** — was sending the Azure DevOps PAT as an OAuth bearer token (→ `TF400813`, anonymous access). Now uses `--authentication pat` with a base64-encoded `PERSONAL_ACCESS_TOKEN`.
2. **Default branch** — branch creation was hardcoded to `main`; now detects the repo's actual default branch (works on `master` repos).
3. **`branch_exists` detection** — couldn't see the branch you were currently on (`* branch`), causing failed re-runs; fixed.
4. **Copilot CLI availability check** — a slow cold start was misreported as "CLI not installed"; now a fast PATH check, tolerant of slow startup.
5. **Review posts to the PR** — `review` was console-only; it now posts the full review as a PR comment. Docstring corrected (it's advisory — no auto-fix/merge).
6. **PAT input hardening** — trims the entered PAT (a mangled paste had been stored verbatim).

## Known limitations

- **No remediation loop** — the flow is linear (`develop` → `review` → stop). Review findings are not fed back into `develop`, so there's no automated "iterate until the review is clean" cycle. Fixing review issues is currently manual. (See roadmap.)
- **Advisory review only** — `review` reports findings; it does not auto-fix code, merge, or change work item state. Merging the PR remains a human decision.
- **Interactive / manual operation** — currently run by hand from a developer machine. Not yet runnable unattended in a pipeline (see roadmap).

## Roadmap

### 1. Make it pipeline-ready (run unattended in Azure DevOps)

Intended trigger (per the original author's design): Work Item → **Active** → webhook → Azure Function → pipeline runs `plan` + `develop`. Blockers to solve:

- **Headless Copilot CLI auth** (top priority) — today relies on a prior interactive login; a fresh pipeline agent has none. Needs token-based auth via pipeline secrets.
- **Non-interactive operation** — several prompts (branch-exists choice, missing env vars, PAT entry) block on stdin and would hang in CI. Needs a non-interactive mode with safe defaults.
- **Runtime dependencies** — MCP servers are launched via `npx -y …` (download at run time); needs Node + network on the agent, or pre-installed/pinned deps. Git push needs agent credentials for the Azure DevOps remote.
- **Token scope** — the pipeline identity needs Work Items R/W (plan) and Code R/W (develop push, PR create, review comment).

### 2. Expand to the full SDLC

Target end-to-end flow (note the develop ↔ review loop):

```
idea → brainstorm/grill → PRD → Azure PBIs → plan → develop → test → review
                                                       ↑__________________|
                                              (loop back while issues remain)
                                                              → deploy
```

New capabilities to build:

- **Review → develop remediation loop** — when `review` reports issues above a chosen severity, re-invoke `develop` to address them (feeding the review findings back in as input), then re-review; repeat until the review is clean or a max-iteration guard is hit. Needs: a way to parse/threshold review findings, a termination/iteration cap to avoid infinite loops, and develop consuming the prior review as context.

- **Discovery (upstream of the current loop):**
  - **Brainstorm / "grill-me"** agent — interactive, Socratic ideation that challenges the user to flesh out an idea.
  - **PRD generator** — turns the brainstorm into a Product Requirements Document.
  - **PBI generator** — turns the PRD into Azure DevOps PBIs/work items (the input the existing loop consumes).
- **Build / quality / release (downstream):**
  - **Test agent** — generate and run tests beyond what `develop` produces.
  - **"Thermonuclear" code reviewer** — exhaustive, multi-pass review of the whole codebase (not just the PR diff). Implemented via Copilot subagents / `/delegate` so each sweep runs in its own context.
  - **Deploy agent** — handle deployment.

## Tech notes

- **Stack:** Python + Typer (CLI) + GitPython + MCP. Built to a standalone executable via PyInstaller.
- **Copilot CLI extensibility** (relevant for the new agents): supports custom **skills** (`.github/skills/<name>/SKILL.md`), custom **agents** (`.github/agents/`), **subagents + `/delegate`**, hooks, and `.github/copilot-instructions.md`. The discovery skills (grill/PRD/PBI) map onto skills; the deep reviewer maps onto subagents/delegate. (Copilot CLI evolves quickly — re-check the installed version's capabilities when building.)
- **Config:** credentials in `~/.azure-copilot-sdlc/.env` (`ADO_MCP_AUTH_TOKEN`, `GITHUB_PAT`, `AZURE_DEVOPS_ORG`, `AZURE_DEVOPS_PROJECT`).
