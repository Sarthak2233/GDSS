# Good and Bad Tests (GDSS)

## Good: behavior through the public interface

```python
def test_renaming_a_function_is_detected_as_a_rename_operator():
    parser = ASTParser()
    extractor = TransformExtractor()
    old = parser.parse_file("billing.py", "def process_payment():\n    pass\n")
    new = parser.parse_file("billing.py", "def execute_payment():\n    pass\n")

    ops = extractor.extract_operators("billing.py", old, new)

    assert any(
        op.operator is OperatorType.RENAME_FUNCTION
        and op.from_name == "process_payment"
        and op.to_name == "execute_payment"
        for op in ops
    )
```

Why it is good:

- Calls the public API (`parse_file`, `extract_operators`) only.
- Asserts the observable result (a rename operator), not internal steps.
- Uses the real parser/extractor; no mocks of GDSS internals.
- Survives refactors of how rename detection works internally.

## Bad: coupled to implementation

```python
# BAD: asserts on a private helper / call count
def test_extractor_calls_match_symbols(mocker):
    spy = mocker.spy(TransformExtractor, "_match_symbols")
    TransformExtractor().extract_operators("f.py", [], [])
    spy.assert_called()   # breaks on any refactor, proves nothing about behavior
```

```python
# BAD: mocks GDSS's own module instead of using it
def test_status_uses_graph(mocker):
    mocker.patch("gdss.graph.code_graph.CodeGraph")   # don't mock your own code
    ...
```

Red flags: mocking internal collaborators, testing private methods, asserting call
counts/order, a test that breaks when you refactor without changing behavior.

## Mock only at boundaries

Mock: network calls, the system clock, randomness. Everything GDSS owns (parser, extractor,
graph, observer) should run for real in tests.
