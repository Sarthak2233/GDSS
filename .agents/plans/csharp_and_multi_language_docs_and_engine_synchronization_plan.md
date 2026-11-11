# Multi-Language Architecture & Documentation Synchronization Plan (GDSS + gdss-radar)

This plan outlines the final steps to make GDSS's multi-language, .NET enterprise support, and sub-document region projection **absolute and complete**. It synchronizes both repositories:
1. **GDSS (Core Engine & Internal Docs):** Adds zero-config heuristic auto-detection for .NET sandboxes (`dotnet build`, `dotnet test`, and `.sln` solution project tracking) and completes internal technical documentation.
2. **gdss-radar (Public Action & Client Docs):** Synchronizes user-facing documentation, recipes, and setup guides with **strict sanitization** (thin documentation that protects proprietary engine source code, regexes, and AST visitor mechanics).

---

## 🎯 Goal Description

Over the previous sessions, GDSS successfully promoted C# from a fragile regex fallback to an official Tree-sitter CST visitor, introduced MSBuild `<PackageReference>`/`<ProjectReference>` manifest diffing, built hybrid region projection for Blazor (`.razor`) and Vue (`.vue`), established auto-generated code exclusion, and demoted ungrammared extensions to a transparent `lexical_advisory` mode.

To finalize this work:
* **Eliminate Remaining Heuristic Gaps in GDSS:** If a .NET repository has **no `.gdss.yml`**, the ephemeral validation sandbox should still auto-detect that it is a .NET project and run `dotnet build` and `dotnet test`. Additionally, `.sln` Visual Studio solution files should be tracked by the manifest reducer when projects are added/removed.
* **Audit & Update Public Documentation (`gdss-radar`):** Update `gdss-radar/README.md`, `gdss-radar/docs/UNIVERSAL_MULTI_ASSET_GUIDE.md`, `gdss-radar/docs/CONFIGURATION_GUIDE.md`, and `gdss-radar/.gdss.yml.example` to document .NET/C# recipes, Blazor/Vue support, and generated code filters in **thin, clean, user-facing terms** that never leak internal engine implementations, python file paths, or private AST visitors.

---

## ⚠️ User Review Required

> [!IMPORTANT]
> **Strict Documentation Boundary (GDSS vs. gdss-radar):**
> * **`GDSS` (Internal Engine):** Holds complete technical architecture, Python class signatures (`_parse_csharp`, `RegionProjector`, `is_generated_or_excluded`), code links, and developer tests.
> * **`gdss-radar` (Public Action):** Exclusively holds **thin, user-centric documentation** for developers installing the GitHub Marketplace Action. It explains *what* GDSS detects (e.g. C# AST symbols, Blazor `@code`, MSBuild project couplings) and *how to configure it* in `.gdss.yml`, but contains **zero internal regex patterns, zero proprietary module paths (`gdss/core/...`), and zero internal enum names (`OperatorType`)**.

> [!NOTE]
> **Zero-Config .NET Experience:**
> Adding automatic detection for `dotnet build` and `dotnet test` in `typechecker.py` and `test_runner.py` means .NET teams can add the GitHub Action with zero boilerplate and get sandbox compilation and test verification out of the box.

---

## 📋 Proposed Changes

### Component 1: GDSS Core Validation & Solution Topology (`GDSS`)

Ensure zero-config execution and complete solution-level tracking.

---

#### [MODIFY] [`gdss/validation/typechecker.py`](file:///home/sarakb/projects/GDSS/gdss/validation/typechecker.py)
* In `detect_typecheck_command`:
  Add heuristic auto-detection for .NET solutions and projects:
  ```python
  # C# / .NET (Solution or Project)
  try:
      if any(root.glob("*.sln")) or any(root.glob("*.csproj")):
          return "dotnet build --no-build-incrementally", "dotnet"
  except Exception:
      pass
  ```

---

#### [MODIFY] [`gdss/validation/test_runner.py`](file:///home/sarakb/projects/GDSS/gdss/validation/test_runner.py)
* In `detect_test_command`:
  Add heuristic auto-detection for .NET test execution:
  ```python
  # C# / .NET
  try:
      if any(root.glob("*.sln")) or any(root.glob("*.csproj")):
          return "dotnet test", "dotnet"
  except Exception:
      pass
  ```

---

#### [MODIFY] [`gdss/reducers/manifest_reducer.py`](file:///home/sarakb/projects/GDSS/gdss/reducers/manifest_reducer.py)
* Add `.sln` and `.slnx` to `_MSBUILD_EXTENSIONS`.
* In `_extract_msbuild`:
  Add regex parser for Visual Studio `.sln` files:
  ```text
  Project("{FAE04EC0-301F-11D3-BF4B-00C04F79EFBC}") = "Api", "src\Api\Api.csproj", "{...}"
  ```
  Extracts project membership so adding, removing, or renaming projects inside a `.sln` triggers `ADD_DEPENDENCY`, `REMOVE_DEPENDENCY`, or `MODIFY_DEPENDENCY` operators.

---

#### [NEW] [`tests/validation/test_csharp_sandbox_detection.py`](file:///home/sarakb/projects/GDSS/tests/validation/test_csharp_sandbox_detection.py)
* Author unit tests verifying:
  1. `detect_typecheck_command` automatically returns `dotnet build --no-build-incrementally` when a `.csproj` or `.sln` exists.
  2. `detect_test_command` automatically returns `dotnet test` when a `.csproj` or `.sln` exists.
  3. Explicit `.gdss.yml` overrides take precedence over the heuristic defaults.

---

### Component 2: Core Repository Technical Documentation (`GDSS`)

Document complete architecture and internal mechanics.

---

#### [MODIFY] [`README.md`](file:///home/sarakb/projects/GDSS/README.md)
* Update multi-language AST overview to highlight C# (Level 3/4), Ruby, Bash, Blazor/Vue sub-document projection, and MSBuild project graph modeling.
* Update Phase 1 roadmap table.

---

#### [MODIFY] [`docs/UNIVERSAL_MULTI_ASSET_GUIDE.md`](file:///home/sarakb/projects/GDSS/docs/UNIVERSAL_MULTI_ASSET_GUIDE.md)
* Maintain full technical depth on:
  - MSBuild manifest reducer (`.csproj`, `.props`, `.targets`, `Directory.Packages.props`).
  - `RegionProjector` sub-document coordinate remapping.
  - `DEFAULT_GENERATED_EXCLUDE_PATTERNS` and `is_generated_or_excluded`.

---

#### [MODIFY] [`docs/CONFIGURATION_GUIDE.md`](file:///home/sarakb/projects/GDSS/docs/CONFIGURATION_GUIDE.md)
* Include Recipe 5 for .NET/C# in the stack recipes section.
* Document `ast.exclude_patterns` and automatic generated file filtering.

---

### Component 3: Public Action Documentation (`gdss-radar/`) (Thin & Sanitized)

User-centric, client-facing documentation that shields proprietary engine internals.

---

#### [MODIFY] [`gdss-radar/README.md`](file:///home/sarakb/projects/GDSS/gdss-radar/README.md)
* **Clean Typo:** Remove accidental artifact on line 501 (`what extension does .net has in project files mostly`).
* **Add Stack Recipe 5:** Add `.NET / C# (Solution & Project Builds)` recipe alongside TypeScript, Python, Go, and Rust:
  ```yaml
  ### 5. .NET / C# (Solution & Project Builds)
  radar:
    model: "gpt-4o"
    context_window: 128000
    provider: "openrouter"
    risk_threshold: 0.1
    max_refinements: 2

  validation:
    test_command: "dotnet test --no-build"
    typecheck_command: "dotnet build --no-incremental"
    timeout_seconds: 90

  hierarchy:
    reference_branch: "main"
    same_base_only: true
  ```
* **Supported Stacks List:** Update the supported language listing to include C# (.NET 6/7/8/9, Blazor), Ruby, and Bash.

---

#### [MODIFY] [`gdss-radar/docs/UNIVERSAL_MULTI_ASSET_GUIDE.md`](file:///home/sarakb/projects/GDSS/gdss-radar/docs/UNIVERSAL_MULTI_ASSET_GUIDE.md)
* **Sanitized Additions:**
  - Update **Stage A Advisory Path Sniffer** to list `.csproj`, `.props`, `Directory.Packages.props`, and C# / Blazor / Vue.
  - In **Dependency Manifest & Lockfile Reconciliation**, describe support for NuGet packages (`<PackageReference>`), Central Package Management (CPM), and project references (`<ProjectReference>`) in conceptual terms.
  - Add a conceptual section on **Hybrid Frameworks (Blazor & Vue/Svelte)** explaining that GDSS extracts embedded C# and TypeScript code and checks contracts without treating them as generic unparsed text.
  - Add a section on **Automated Noise Exclusion** explaining that compiler artifacts (`*.Designer.cs`, `*.g.cs`, `*AssemblyInfo.cs`, `bin/**`, `obj/**`) are automatically excluded from collision scoring.
  - **Zero Leaks:** Ensure zero references to internal Python files (`gdss/...`), regexes, or engine-internal enums (`OperatorType`).

---

#### [MODIFY] [`gdss-radar/docs/CONFIGURATION_GUIDE.md`](file:///home/sarakb/projects/GDSS/gdss-radar/docs/CONFIGURATION_GUIDE.md)
* Add Recipe 5 for .NET in the configuration recipe catalog.
* Document automatic exclusion of generated files in `ast.exclude_patterns`.

---

#### [MODIFY] [`gdss-radar/docs/GITHUB_ACTIONS_GUIDE.md`](file:///home/sarakb/projects/GDSS/gdss-radar/docs/GITHUB_ACTIONS_GUIDE.md)
* Add a note/example showing how .NET repositories include `actions/setup-dotnet@v4` on their GitHub Actions runner when sandbox validation is enabled.

---

#### [MODIFY] [`gdss-radar/.gdss.yml.example`](file:///home/sarakb/projects/GDSS/gdss-radar/.gdss.yml.example)
* Add commented examples for `dotnet build` and `dotnet test` under the validation section.

---

## 🧪 Verification Plan

### Automated Tests
1. Run new sandbox detection tests:
   ```bash
   python3 -m pytest tests/validation/test_csharp_sandbox_detection.py -v
   ```
2. Run full GDSS test suite:
   ```bash
   python3 -m pytest -q
   ```
3. Run the full verification gate (backend Layer 1/2/3 + frontend F1/F2/F3):
   ```bash
   bash harness/verify.sh
   ```

### Documentation Sanitization Audit
1. Audit `gdss-radar/` for leaks:
   ```bash
   # Verify zero local paths
   grep -rn "file:///" gdss-radar/
   grep -rn "/home/sarakb" gdss-radar/

   # Verify zero internal engine references
   grep -rn "OperatorType" gdss-radar/
   grep -rn "gdss/core" gdss-radar/
   grep -rn "_parse_csharp" gdss-radar/
   ```

---

## 🚀 Execution & Review Checkpoints

1. Implement heuristic auto-detection in `typechecker.py`, `test_runner.py`, and `manifest_reducer.py`.
2. Add tests in `test_csharp_sandbox_detection.py` and verify green.
3. Update internal docs in `GDSS`.
4. Update sanitized client docs and recipes in `gdss-radar`.
5. Run full `harness/verify.sh` and sanitization checks.
6. Commit changes to both repositories.

