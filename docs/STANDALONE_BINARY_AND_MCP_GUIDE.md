# 💻 GDSS Standalone Binary & IDE MCP Server Guide

> **Run GDSS natively on developer workstations across Linux, macOS, and Windows with zero Python setup. Connect deterministic repository intelligence directly into Cursor, Claude Code, and Copilot via the Model Context Protocol (MCP).**

---

## 📑 Table of Contents
- [🎯 Overview: Zero-Dependency Local Intelligence](#-overview-zero-dependency-local-intelligence)
- [🚀 1-Line Universal Installation](#-1-line-universal-installation)
  - [macOS & Linux (Bash)](#1-macos--linux-bash)
  - [Windows (PowerShell)](#2-windows-powershell)
  - [Manual Download from GitHub Releases](#3-manual-download-from-github-releases)
- [🧠 IDE MCP Server Setup (Cursor, Claude Code, Copilot)](#-ide-mcp-server-setup-cursor-claude-code-copilot)
  - [Cursor Setup (`~/.cursor/mcp.json`)](#cursor-setup-cursor-mcpjson)
  - [Claude Code Setup](#claude-code-setup)
  - [VS Code / GitHub Copilot Setup](#vs-code--github-copilot-setup)
- [🛠️ The 6 Native MCP Tools Available to AI](#️-the-6-native-mcp-tools-available-to-ai)
- [💻 Local CLI Offline Workflows](#-local-cli-offline-workflows)
- [🛡️ Privacy, Deterministic Core ($0 Tokens) & BYOK Model](#️-privacy-deterministic-core-0-tokens--byok-model)

---

## 🎯 Overview: Zero-Dependency Local Intelligence

The standalone GDSS binary is a self-contained native executable compiled with embedded Tree-sitter parsers and algebraic collision engines.

- **Zero Python Installation Required**: Developers do not need Python 3.11, `.venv`, or `pip`.
- **Cross-Platform Support**: Built natively for:
  - **Linux x86_64** (`linux-amd64`)
  - **macOS Apple Silicon M1/M2/M3/M4** (`darwin-arm64`)
  - **macOS Intel** (`darwin-amd64`)
  - **Windows x86_64** (`windows-amd64`)
- **Dual-Purpose Engine**: Functions both as a terminal CLI tool (`gdss status`, `gdss tensor`, `gdss drift`) and as a background stdio server for IDE agents (`gdss mcp`).

---

## 🚀 1-Line Universal Installation

### 1. macOS & Linux (Bash)
Run this command in your terminal:

```bash
curl -fsSL https://raw.githubusercontent.com/sarthak2233/gdss-radar/main/install.sh | bash
```

**What the installer does:**
1. Auto-detects operating system (`Darwin` vs `Linux`) and architecture (`arm64` vs `amd64`).
2. Downloads the matching archive (`.tar.gz`) from GitHub Releases.
3. Verifies integrity against the published SHA-256 checksum.
4. Installs the binary to `/usr/local/bin/gdss` (or `~/.local/bin/gdss`).
5. Verifies installation with `gdss --help`.

---

### 2. Windows (PowerShell)
Open PowerShell and run:

```powershell
irm https://raw.githubusercontent.com/sarthak2233/gdss-radar/main/install.ps1 | iex
```

**What the Windows installer does:**
1. Downloads `gdss-v1-windows-amd64.zip`.
2. Extracts `gdss.exe` into `%LOCALAPPDATA%\Programs\gdss\gdss.exe`.
3. Adds the installation folder to your User `PATH` environment variable.
4. Verifies installation with `gdss.exe --help`.

---

### 3. Manual Download from GitHub Releases
If your workstation has restricted internet access, download the pre-compiled archive directly from [GitHub Releases](https://github.com/sarthak2233/gdss-radar/releases):

| Target Operating System | Architecture | Archive Format | File Name |
| :--- | :--- | :---: | :--- |
| **Linux** | x86_64 (amd64) | `.tar.gz` | `gdss-v1-linux-amd64.tar.gz` |
| **macOS (Apple Silicon)** | M1 / M2 / M3 / M4 (`arm64`) | `.tar.gz` | `gdss-v1-darwin-arm64.tar.gz` |
| **macOS (Intel)** | x86_64 (`amd64`) | `.tar.gz` | `gdss-v1-darwin-amd64.tar.gz` |
| **Windows** | x86_64 (`amd64`) | `.zip` | `gdss-v1-windows-amd64.zip` |

Extract the binary and place it in your system `PATH`.

---

## 🧠 IDE MCP Server Setup (Cursor, Claude Code, Copilot)

The Model Context Protocol (MCP) allows your AI coding assistants to call GDSS deterministic functions directly while you chat or edit code.

### Cursor Setup (`~/.cursor/mcp.json`)

To enable GDSS across all projects in Cursor:
1. Open or create `~/.cursor/mcp.json` (on Windows: `%USERPROFILE%\.cursor\mcp.json`).
2. Add the `gdss` server configuration:

```json
{
  "mcpServers": {
    "gdss": {
      "command": "gdss",
      "args": ["mcp"]
    }
  }
}
```
3. Restart Cursor. In the Cursor Settings under **Features ➔ MCP**, verify that `gdss` shows green with 6 active tools.

*(Optional per-project config: You can also place this in `.cursor/mcp.json` inside individual git repositories).*

---

### Claude Code Setup

In your terminal, add GDSS to Claude Code with a single command:

```bash
claude mcp add gdss -- gdss mcp
```

Verify with:
```bash
claude mcp list
```
Claude Code now has access to the full GDSS PR collision radar and blast radius inspector!

---

### VS Code / GitHub Copilot Setup

If using the VS Code MCP extension or Copilot Chat with MCP support, add the server to your VS Code settings or `.vscode/mcp.json`:

```json
{
  "mcpServers": {
    "gdss": {
      "command": "gdss",
      "args": ["mcp"]
    }
  }
}
```

---

## 🛠️ The 6 Native MCP Tools Available to AI

When connected via MCP, your AI assistant can invoke these 6 deterministic tools:

| MCP Tool Name | Description | What the AI Uses It For |
| :--- | :--- | :--- |
| `gdss_find_collisions` | Computes pairwise collision tensor ($\Omega_{ij}$) and commutativity violations. | Asking: *"Are my branch changes going to conflict with Alice's or Bob's open branches?"* |
| `gdss_get_merge_order` | Calculates the mathematically optimal merge sequence minimizing integration friction. | Asking: *"In what order should our team land these 4 open feature branches?"* |
| `gdss_inspect_symbol_impact` | Evaluates blast radius, callers, and contractual dependencies of a modified symbol. | Asking: *"If I refactor `validate_token()`, what other files and branches will be affected?"* |
| `gdss_plan_semantic_rebase` | Proposes commutativity-aware rebase steps distinguishing signature shifts from textual noise. | Asking: *"How should I rebase `feature/billing` onto `main` without breaking changes?"* |
| `gdss_sandbox_validate_patch` | Compiles and tests a candidate patch in an ephemeral Git worktree sandbox. | Asking: *"Validate this proposed reconciliation patch against our test suite before I commit."* |
| `gdss_validate_patch` | Rapid syntax and typecheck validation of proposed code changes. | Asking: *"Check if this code block has any syntax or typing errors."* |

---

## 💻 Local CLI Offline Workflows

In addition to MCP, the standalone binary provides immediate terminal commands:

### 1. Repository Status & Semantic Operators
```bash
gdss status --ref main
```
Reports active branch trajectories, uncommitted semantic operators ($dC$), and drift distance from `main`.

### 2. PR Collision Matrix ($\Omega_{ij}$)
```bash
# Check collisions across all local branches
gdss tensor --ref main

# Check targeted feature branches only
gdss tensor --ref main -b feature/auth -b feature/billing
```

### 3. Semantic Drift Tracking
```bash
gdss drift --ref main
```

### 4. Assisted Convergence & Guarded Apply
```bash
# Generate candidate suggestions locally
gdss suggest --repo . --ref main -b feature/auth -b feature/billing

# Preview patch with colorized unified diff (disk untouched)
gdss apply sug_8f2a91c3 --dry-run

# Apply patch to working tree
gdss apply sug_8f2a91c3
```

---

## 🛡️ Privacy, Deterministic Core ($0 Tokens) & BYOK Model

- **100% Free Deterministic Core (0 Tokens)**: AST parsing, dependency mapping, caller/callee graphs, and collision tensors run locally on developer CPU. They cost $0 and require 0 external AI tokens.
- **Zero-Inference MCP Tool Server**: GDSS acts purely as a deterministic tool provider over `stdio`. The developer's own Cursor, Claude Code, or Copilot subscription powers the chat conversation. GDSS collects zero token fees and incurs zero LLM liability.
- **Strict BYOK for CLI AI Features**: If you choose to run `gdss suggest --llm` from your terminal, you bring your own key (`export OPENAI_API_KEY=...`) or connect to free local compute (Ollama/vLLM).
- **Zero Cloud Telemetry**: Your source code stays on your laptop. No code or metadata is transmitted to external GDSS servers.

