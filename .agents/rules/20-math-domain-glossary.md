---
description: GDSS ubiquitous language - use these exact terms in names, docs, and tests
alwaysApply: true
---

# Domain Glossary & Vocabulary Guidance

To maintain clarity and product adoption, GDSS enforces a strict distinction between
**External Developer Vocabulary** (CLI output, PR reports, error messages, user docs) and
**Internal Mathematical Representation** (data structures, algorithms, research docs).

## 1. External Developer Vocabulary (What Users See)
Use these terms across all user-facing interfaces, logs, PR comments, and CLI commands:
- **Branch Collision Radar** - the subsystem detecting semantic branch interference.
- **Collision Matrix / Interference Score** - pairwise risk between branch pairs.
- **Affected Symbols** - specific functions, classes, and callers modified or broken across branches.
- **Semantic Drift / Divergence** - how far a branch has evolved away from the base branch.
- **Base / Target Branch** - the branch branches will merge into (`main`, `dev`).
- **Recommended Merge Order** - optimal sequence to integrate branches with minimal conflict.
- **Resolution Proposal / Patch** - AI-generated, sandboxed resolution candidate.

## 2. Internal Mathematical Representation (Backend Code Only)
These terms describe the discrete algebraic structures in backend modules and tests:
- **transformation operator `T_i`** - a semantic delta (`SemanticOperator` in `gdss/core/transform_types.py`).
- **commutativity `[T_i, T_j]`** - discrete operator order-independence (`[T_i, T_j] = 0`).
- **pairwise interaction matrix `Omega_{ij}`** - the $N \times N$ discrete risk matrix in `gdss/conflict/tensor.py`.
- **trajectory** - sequence of semantic operators from `merge_base` to `HEAD`.

> [!IMPORTANT]
> **Jargon Rule:** Never expose academic terms like "Riemannian metric $G$", "Ricci curvature",
> "Christoffel symbols", or "smooth manifold geodesics" in CLI outputs, errors, or product UI.
> Codebases are discrete structures; convey concrete facts with traceable evidence.
