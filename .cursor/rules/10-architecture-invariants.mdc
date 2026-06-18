---
description: GDSS architecture invariants - layer direction and two-brain purity
alwaysApply: true
---

# Architecture Invariants

GDSS has a layered, two-brain architecture. These invariants are mechanically enforced by
`harness/sensors/architecture_fitness.py`. Do not violate them; fix the design instead.

## Layer direction (high depends on low, never the reverse)

```
Layer 10: validation   (gdss/validation)
Layer 9:  ai           (gdss/ai)
Layer 8:  drift        (gdss/drift)
Layer 7:  conflict     (gdss/conflict)
Layer 6:  embeddings   (gdss/embeddings)
Layer 5:  graph        (gdss/graph)
Layer 4:  core         (gdss/core - transform algebra)
Layer 3:  core         (gdss/core - ast)
Layer 2:  watcher      (gdss/watcher)
Layer 1:  (git itself)
```

`gdss/cli` and `gdss/api` are entrypoints and may depend on any layer. Everything else
imports only from equal-or-lower layers.

## Two-brain purity (the load-bearing rule)

- **Deterministic brain** (TRUSTED): `gdss/core`, `gdss/graph`, `gdss/watcher`. Provides
  mathematical grounding via AST, dependency graphs, transform operators, commutativity.
- **Probabilistic brain** (ASSISTIVE): `gdss/embeddings`, `gdss/ai`. Provides embeddings,
  intent inference, suggestions.

Rule: the deterministic brain must **never import** the probabilistic brain. The
probabilistic brain never acts without deterministic validation.

## Examples

```python
# BAD: deterministic brain reaching into probabilistic brain
# file: gdss/core/transform_extractor.py
from gdss.ai.suggestions import suggest_rename   # FORBIDDEN

# GOOD: ai layer depends downward on core
# file: gdss/ai/suggestions.py
from gdss.core.transform_types import SemanticOperator   # allowed
```
