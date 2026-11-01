# Implementation Plan: Approach C — Standalone Compiled Binary & IDE MCP Server

## Goal Description
Implement **Approach C** from the GDSS Distribution Plan ([`docs/DISTRIBUTION_PLAN.md`](docs/DISTRIBUTION_PLAN.md)). 

This empowers external testers, developers, and teams to run GDSS locally as a **standalone compiled native executable** on developer workstations (Linux and macOS) without requiring Python 3.11, virtual environments, or `pip install`. The standalone binary bundles the complete deterministic AST engine, dependency graphs, and the **Model Context Protocol (MCP) server** (`gdss mcp`) to integrate natively with **Cursor**, **Claude Code**, and **VS Code Copilot** at **$0 API cost** to the GDSS project.

---

## Status: Approved by User ✅ (All-OS Support: Linux, macOS, Windows)

Execution is in progress. The build matrix has been expanded to support **all operating systems**:
- **Linux:** x86_64 (`linux-amd64`) via `ubuntu-22.04`
- **macOS Apple Silicon:** ARM64 (`darwin-arm64`) via `macos-14`
- **macOS Intel:** x86_64 (`darwin-amd64`) via `macos-13`
- **Windows:** x86_64 (`windows-amd64`) via `windows-latest` (with `.exe` and `install.ps1` PowerShell installer)

---

---

## Open Questions

> [!NOTE]
> 1. **Public Release Repository**: Do you prefer hosting the binary release assets directly in the public `Sarthak2233/gdss-radar` repository (under Releases), or would you prefer a separate dedicated public repository named `Sarthak2233/gdss-binaries`?  
>    *(Recommended: `Sarthak2233/gdss-radar`, as it already serves as the public product face).*
> 2. **Target Architectures**: Our initial build matrix covers **Linux x86_64**, **macOS Apple Silicon (ARM64)**, and **macOS Intel (x86_64)**. Would you like to include Windows (`windows-amd64`) in the first release, or keep it scoped to macOS and Linux first?  
>    *(Recommended: macOS and Linux first, Windows in follow-up).*

---

## Proposed Changes

```
┌─────────────────────────────────────────────────────────────┐
│ PRIVATE REPOSITORY: Sarthak2233/GDSS                        │
│                                                             │
│ 1. packaging/pyinstaller/gdss.spec                          │
│    - Bundles CLI, MCP server, AST Tree-sitter grammars      │
│                                                             │
│ 2. .github/workflows/build-binaries.yml                     │
│    - Matrix: Linux (x86_64), macOS (ARM64), macOS (Intel)   │
│    - Compiles standalone binaries & computes SHA-256        │
│    - Pushes release tarballs to public release channel      │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ PUBLIC CHANNEL / Sarthak2233/gdss-radar                     │
│                                                             │
│ 1. install.sh                                               │
│    - Auto-detects OS & Arch (uname -s, uname -m)            │
│    - Downloads matching tarball & verifies SHA-256          │
│    - Installs to /usr/local/bin/gdss (or ~/.local/bin)      │
│    - Verifies execution via `gdss --help`                   │
│                                                             │
│ 2. docs/STANDALONE_BINARY_AND_MCP_GUIDE.md                  │
│    - 1-click MCP setup for Cursor (~/.cursor/mcp.json)      │
│    - 1-command MCP setup for Claude Code                    │
│    - Local offline CLI usage (status, tensor, drift)        │
└─────────────────────────────────────────────────────────────┘
```

---

### Component 1: PyInstaller Packaging Specification

#### [NEW] `packaging/pyinstaller/gdss.spec`
A custom PyInstaller specification that:
- Packages `gdss/cli/main.py` as entry point.
- Collects all native dynamic libraries and data for:
  - `tree_sitter`
  - `tree_sitter_python`
  - `tree_sitter_javascript`
  - `tree_sitter_typescript`
  - `tree_sitter_go`
  - `tree_sitter_rust`
  - `tree_sitter_java`
  - `tree_sitter_c`
  - `tree_sitter_cpp`
- Bundles `networkx`, `uvicorn`, `fastapi`, `pydantic`, `rich`, `typer`, and `watchdog`.
- Excludes heavy unnecessary GUI/scientific modules (`tkinter`, `matplotlib`, `scipy`).
- Compiles into single-file executable `dist/gdss`.

---

### Component 2: Cross-Platform Build Workflow

#### [NEW] `.github/workflows/build-binaries.yml`
Automated GitHub Actions workflow triggered on push of release tags (e.g., `v*`) or manual `workflow_dispatch`:
- **Runner Matrix:**
  - `linux-amd64`: `ubuntu-22.04`
  - `darwin-arm64`: `macos-14` (Apple Silicon M1–M4)
  - `darwin-amd64`: `macos-13` (Intel Mac)
- **Build Steps:**
  1. Setup Python 3.11.
  2. Install build requirements: `pip install .[embeddings] pyinstaller`.
  3. Execute `pyinstaller --clean packaging/pyinstaller/gdss.spec`.
  4. Smoke-test compiled binary: `./dist/gdss --help` and `./dist/gdss status`.
  5. Tar and gzip: `tar -czvf gdss-${VERSION}-${OS}-${ARCH}.tar.gz -C dist gdss`.
  6. Compute checksums: `sha256sum gdss-*.tar.gz > checksums-${OS}-${ARCH}.txt`.
  7. Aggregate checksums and publish release assets to GitHub Releases.

---

### Component 3: Universal 1-Line Installer Script

#### [NEW] `install.sh` (in both `GDSS/` and `gdss-radar/`)
POSIX-compliant installation script:
- Fetches the latest release metadata from GitHub.
- Identifies client operating system: `Linux` or `Darwin` (macOS).
- Identifies architecture: `x86_64` (amd64) or `arm64` / `aarch64`.
- Downloads `gdss-${VERSION}-${OS}-${ARCH}.tar.gz`.
- Verifies integrity using SHA-256 checksum.
- Extracts binary to `/usr/local/bin/gdss` (prompts for `sudo` if needed, or falls back gracefully to `~/.local/bin/gdss` with PATH warning).
- Verifies executable by invoking `gdss --help`.
- Prints friendly next steps for Cursor, Claude Code, and terminal CLI.

---

### Component 4: IDE MCP Server Documentation & Setup Recipes

#### [NEW] `docs/STANDALONE_BINARY_AND_MCP_GUIDE.md`
Comprehensive guide explaining:
1. **1-Line Quick Installation**:
   ```bash
   curl -fsSL https://raw.githubusercontent.com/sarthak2233/gdss-radar/main/install.sh | bash
   ```
2. **Cursor Integration (`~/.cursor/mcp.json` or `.cursor/mcp.json`)**:
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
3. **Claude Code CLI Integration**:
   ```bash
   claude mcp add gdss -- gdss mcp
   ```
4. **VS Code Copilot Integration**:
   Setting up the stdio MCP provider.
5. **The 6 Native Deterministic Tools Exposed to AI**:
   - `gdss_find_collisions`: Find active branch interference before merging.
   - `gdss_get_merge_order`: Determine optimal branch landing sequence.
   - `gdss_inspect_symbol_impact`: Check blast radius of a modified function/class.
   - `gdss_plan_semantic_rebase`: Rebase planning with semantic awareness.
   - `gdss_sandbox_validate_patch`: Test code diffs in an ephemeral worktree.
   - `gdss_validate_patch`: Syntax and typecheck validation.
6. **Zero Token Bleed Principle**: Explaining that all deterministic queries run locally on the developer's laptop, costing $0 in API fees.

#### [MODIFY] `gdss-radar/README.md`
Add a dedicated section for **Desktop CLI & IDE MCP Server (Cursor & Claude Code)** cross-linking to `install.sh`.

#### [MODIFY] `docs/USER_GUIDE.md` & `README.md`
Update Standalone Binary installation sections with the 1-line installer.

---

## Verification Plan

### Automated Tests
1. **PyInstaller Build Verification**:
   - Verify that `packaging/pyinstaller/gdss.spec` can be parsed without syntax errors.
   - Run sensor gate:
     ```bash
     bash harness/sensors/lint.sh
     bash harness/sensors/typecheck.sh
     python harness/sensors/architecture_fitness.py
     ```
2. **Installer Script Validation**:
   - Validate `install.sh` with `shellcheck` (or bash syntax check `bash -n install.sh`).
   - Run a dry-run / unit simulation of `install.sh` architecture detection (`Linux`, `Darwin`, `x86_64`, `arm64`).

### Manual Verification
1. Inspect generated `install.sh` to ensure it handles permissions (`sudo` vs non-root `~/.local/bin`), error handling, and clean feedback.
2. Confirm that `gdss mcp` runs over stdio and responds to MCP `initialize` JSON-RPC handshake correctly.
