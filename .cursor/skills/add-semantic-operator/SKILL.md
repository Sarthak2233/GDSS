---
name: add-semantic-operator
description: Test-first workflow to add a new semantic transformation operator (OperatorType) to GDSS. Use when adding a new kind of detected change such as move_function, change_signature, or a new dependency operator to the transform algebra.
---

# Add a Semantic Operator

Add a new `OperatorType` to GDSS's transformation algebra, test-first. This is the
deterministic brain, so correctness and determinism matter more than cleverness.

## Background

- Operator definitions: `gdss/core/transform_types.py` (`OperatorType`, `SemanticOperator`).
- Detection logic: `gdss/core/transform_extractor.py` (`TransformExtractor.extract_operators`).
- Symbols come from `gdss/core/ast_parser.py` (`ASTParser.parse_file` -> `CodeSymbol`s).

Operators must respect the math model: a commit is a set of operators (tangent vector `dC`);
commutativity between operators feeds conflict detection. Keep operators atomic and precise.

## Workflow (red-green-refactor, one slice)

```
[ ] 1. RED: add a failing test in tests/ for the new operator's detection
[ ] 2. GREEN (types): add the OperatorType enum value + any SemanticOperator fields
[ ] 3. GREEN (logic): extend extract_operators to emit it; minimal code to pass
[ ] 4. REFACTOR: tidy while green
[ ] 5. VERIFY: bash harness/verify.sh is green (all three layers)
[ ] 6. STATE: update harness/state/progress.md and feature_list.json
```

## Step details

1. **RED** - Write the test first, asserting behavior through the public interface:

```python
def test_moving_a_function_between_files_is_detected():
    parser, extractor = ASTParser(), TransformExtractor()
    # ... build old/new symbol sets, then:
    ops = extractor.extract_operators("a.py", old, new)
    assert any(op.operator is OperatorType.MOVE_FUNCTION for op in ops)
```

2. **Types** - Add the enum value to `OperatorType`. If the operator needs new data, add a
   typed field to `SemanticOperator` and keep `to_dict` / `from_dict` in sync.

3. **Logic** - Emit the operator from `extract_operators`. Prefer detecting it before falling
   back to add/delete pairs (e.g. detect a move before reporting delete+add).

4. **Refactor** - Only while green.

5. **Verify** - `bash harness/verify.sh`. The architecture sensor must still pass (stay
   inside `gdss/core`; do not import higher layers).

## Definition of done

`bash harness/verify.sh` is green, the new behavior has a test, and state files are updated.
"Code written" is not done.
