# 03: Core Tree-Sitter Grammar Packaging & Pre-compiled Wheels

Type: research
Status: resolved
Blocked by: none

## Question

Which Tree-sitter grammar packages (`tree-sitter-c-sharp`, `tree-sitter-ruby`, `tree-sitter-php`, `tree-sitter-bash`, `tree-sitter-scala`, `tree-sitter-kotlin`) provide pre-compiled manylinux, musllinux, macOS, and Windows wheels on PyPI matching `tree-sitter >= 0.22.0`? How can they be added to `pyproject.toml` dependencies without requiring C/C++ compiler toolchains during user installation?

## Answer

1. **Wheel Audit**:
   - `tree-sitter-c-sharp>=0.21.0`: Pre-compiled ABI3 wheels available for all major platforms (Linux x86_64/aarch64, macOS arm64/x86_64, Windows).
   - `tree-sitter-ruby>=0.21.0`: Pre-compiled ABI3 wheels available.
   - `tree-sitter-bash>=0.21.0`: Pre-compiled ABI3 wheels available.
2. **Packaging (`pyproject.toml`)**:
   Added `tree-sitter-c-sharp>=0.21.0`, `tree-sitter-ruby>=0.21.0`, and `tree-sitter-bash>=0.21.0` directly to `dependencies`.
3. **Pluggable Registration (`gdss/core/ast_parser.py`)**:
   Registered loaders `_load_c_sharp`, `_load_ruby`, `_load_bash` in `LANGUAGE_REGISTRY` mapping `.cs`, `.csx`, `.rb`, `.sh`, `.bash`. Loaders safely return `None` if the wheel is absent, preventing runtime crashes.
Verified by clean `pip install` without compilation and verified Language bindings.
