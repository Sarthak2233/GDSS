---
name: tdd
description: Test-driven development for GDSS using red-green-refactor in vertical slices. Use when building features, fixing bugs, or adding any behavior to gdss/, when writing tests, or when the user mentions TDD, red-green-refactor, or test-first development.
---

# Test-Driven Development (GDSS)

Build behavior test-first. The harness's definition of done is externalized to
`bash harness/verify.sh`; TDD is how you get there reliably.

## The loop

```
1. RED:      write ONE failing test for ONE behavior
2. GREEN:    write the minimal code to pass it
3. REFACTOR: clean up (only while green)
   -> repeat for the next behavior
```

Rules:

- One test at a time. Never write all tests first, then all code (horizontal slicing
  produces tests of imagined behavior).
- Only enough code to pass the current test.
- Never refactor while red. Get to green first.
- No premature optimization: verify core behavior before performance or style.

## What a good GDSS test looks like

- Asserts **behavior through public interfaces** (e.g. call `TransformExtractor.extract_operators`
  and assert on returned `SemanticOperator`s), not private helpers.
- Survives refactors: renaming an internal function should not break it.
- Uses **real** `tree-sitter` and `GitPython`. Mock only true externals (network, clock,
  randomness). Do not mock GDSS's own modules.
- One logical assertion per test; test name describes WHAT, not HOW.

See [tests.md](tests.md) for good vs bad examples. Existing exemplars:
`tests/test_transform_extractor.py`, `tests/test_ast_parser.py`,
`tests/test_code_graph.py`, `tests/test_git_observer.py`.

## Interface design for testability

- Inject dependencies; do not construct them inside the unit under test.
- Return results; prefer pure functions over side effects.
- Aim for **deep modules**: small interface, deep implementation. Fewer methods and
  parameters mean fewer, clearer tests.

## Commands

```bash
# Run one focused test while iterating
python -m pytest tests/test_transform_extractor.py::test_name -q

# Run the runtime layer
bash harness/sensors/run_tests.sh

# Full three-layer gate (must be green before claiming done)
bash harness/verify.sh
```

## Per-cycle checklist

```
[ ] Test describes behavior, not implementation
[ ] Test uses a public interface only
[ ] Test would survive an internal refactor
[ ] Code is minimal for this test
[ ] No speculative features added
[ ] Refactored only while green
```
