# 04: Generated Code Exclusion Policy Filter

Type: research
Status: resolved
Blocked by: none

## Question

What deterministic heuristic and naming patterns should GDSS use to filter out auto-generated source files across language ecosystems (e.g. `*.Designer.cs`, `*.g.cs`, `*.AssemblyInfo.cs`, `*.pb.go`, `*.generated.ts`) and prevent compiler artifact churn from inflating the collision intensity tensor $\Omega_{ij}$? Where should this filter sit in `ast_parser.py` and `discovery.py`?

## Answer

1. **Pattern Catalog (`gdss/core/config.py`)**:
   Established `DEFAULT_GENERATED_EXCLUDE_PATTERNS` covering:
   - **.NET**: `*.Designer.cs`, `*.g.cs`, `*.g.i.cs`, `*.generated.cs`, `*AssemblyInfo.cs`, `bin/**`, `obj/**`
   - **Go**: `*.pb.go`, `*.gen.go`, `*.generated.go`
   - **Web / TS**: `*.generated.ts`, `*.generated.js`, `*.min.js`, `*.min.css`
   - **Java / Rust**: `target/**`
2. **Deterministic Filter (`is_generated_or_excluded`)**:
   Created `is_generated_or_excluded(path, user_excludes)` in `gdss/core/config.py`.
3. **Pipeline Integration**:
   - Integrated into `gdss/graph/graph_builder.py` so generated files are never indexed into the code graph.
   - Integrated into `gdss/core/trajectory.py` so changes to generated files never trigger phantom collision operators in $\Omega_{ij}$.
Verified in `tests/core/test_generated_code_exclusion.py`.
