"""Unit tests for Semantic Impact Closure (SIC) Engine (Phase 1 of Solution)."""

from __future__ import annotations

from gdss.core.transform_types import CodeSymbol, SymbolType
from gdss.graph.code_graph import CodeGraph
from gdss.graph.impact_closure import (
    ImpactClosureResult,
    compute_semantic_impact_closure,
)


def _build_test_graph() -> tuple[CodeGraph, str, str, str, str]:
    """Constructs a deterministic multi-file dependency graph:

    payment_service.py::execute_payment (C_0)
      ^
      | calls (w=1.0)
    checkout.py::checkout_flow (Hop 1)
      ^
      | calls (w=1.0)
    order_service.py::place_order (Hop 2)

    tests/test_payment.py::test_execute_payment (Hop 1, Test, w=0.9) -> calls execute_payment
    """
    graph = CodeGraph()

    # 1. Target function in payment_service.py (C_0)
    payment_sym = CodeSymbol(
        name="execute_payment",
        type=SymbolType.FUNCTION,
        start_line=10,
        end_line=25,
        calls=[],
    )
    payment_sym.ensure_identity("payment_service.py")
    graph.add_file_symbols("payment_service.py", [payment_sym])
    payment_id = payment_sym.symbol_id
    assert payment_id is not None

    # 2. Direct caller in checkout.py (Hop 1)
    checkout_sym = CodeSymbol(
        name="checkout_flow",
        type=SymbolType.FUNCTION,
        start_line=15,
        end_line=40,
        calls=["execute_payment"],
    )
    checkout_sym.ensure_identity("checkout.py")
    graph.add_file_symbols(
        "checkout.py",
        [
            CodeSymbol(
                name="payment_service",
                type=SymbolType.IMPORT,
                start_line=1,
                end_line=1,
                module="payment_service",
            ),
            checkout_sym,
        ],
    )
    checkout_id = checkout_sym.symbol_id
    assert checkout_id is not None

    # 3. Transitive caller in order_service.py (Hop 2)
    order_sym = CodeSymbol(
        name="place_order",
        type=SymbolType.FUNCTION,
        start_line=5,
        end_line=30,
        calls=["checkout_flow"],
    )
    order_sym.ensure_identity("order_service.py")
    graph.add_file_symbols(
        "order_service.py",
        [
            CodeSymbol(
                name="checkout",
                type=SymbolType.IMPORT,
                start_line=1,
                end_line=1,
                module="checkout",
            ),
            order_sym,
        ],
    )
    order_id = order_sym.symbol_id
    assert order_id is not None

    # 4. Verifying test in tests/test_payment.py
    test_sym = CodeSymbol(
        name="test_execute_payment",
        type=SymbolType.FUNCTION,
        start_line=8,
        end_line=20,
        calls=["execute_payment"],
    )
    test_sym.ensure_identity("tests/test_payment.py")
    graph.add_file_symbols(
        "tests/test_payment.py",
        [
            CodeSymbol(
                name="payment_service",
                type=SymbolType.IMPORT,
                start_line=1,
                end_line=1,
                module="payment_service",
            ),
            test_sym,
        ],
    )
    test_id = test_sym.symbol_id
    assert test_id is not None

    graph.resolve_calls()
    return graph, payment_id, checkout_id, order_id, test_id


def test_compute_semantic_impact_closure_direct_and_transitive():
    graph, payment_id, checkout_id, order_id, test_id = _build_test_graph()

    closure = compute_semantic_impact_closure(
        graph,
        conflict_symbols=[payment_id],
        max_hops=2,
        relevance_threshold=0.70,
    )

    assert isinstance(closure, ImpactClosureResult)
    assert payment_id in closure.conflict_symbols

    # Verify implicated files
    implicated_files = set(closure.implicated_files)
    assert "payment_service.py" in implicated_files
    assert "checkout.py" in implicated_files
    assert "order_service.py" in implicated_files
    assert "tests/test_payment.py" in implicated_files

    # Verify node breakdown
    node_ids = {node.symbol_id: node for node in closure.closure_nodes}
    assert payment_id in node_ids
    assert node_ids[payment_id].hop_distance == 0
    assert node_ids[payment_id].weight == 1.0

    assert checkout_id in node_ids
    assert node_ids[checkout_id].hop_distance == 1
    assert node_ids[checkout_id].weight == 1.0
    assert node_ids[checkout_id].node_type == "function"

    assert order_id in node_ids
    assert node_ids[order_id].hop_distance == 2
    assert node_ids[order_id].weight == 1.0

    # Verify test discovery
    assert test_id in node_ids
    assert node_ids[test_id].node_type == "test"
    assert "tests/test_payment.py" in closure.target_tests


def test_compute_semantic_impact_closure_hop_limit():
    graph, payment_id, checkout_id, order_id, _ = _build_test_graph()

    # Limit to max_hops = 1
    closure = compute_semantic_impact_closure(
        graph,
        conflict_symbols=[payment_id],
        max_hops=1,
    )

    node_ids = {node.symbol_id for node in closure.closure_nodes}
    assert payment_id in node_ids
    assert checkout_id in node_ids
    assert order_id not in node_ids  # 2nd hop excluded when max_hops=1


def test_compute_semantic_impact_closure_budget_pruning():
    graph, payment_id, checkout_id, order_id, test_id = _build_test_graph()

    # Set token budget that fits Hop 0 (250), Test (150), and Hop 1 (250) = 650 tokens, but not Hop 2 (250)
    closure = compute_semantic_impact_closure(
        graph,
        conflict_symbols=[payment_id],
        max_hops=2,
        token_budget=700,  # Room for Hop 0, Test, and Hop 1 (650), but not Hop 2 (900)
    )

    node_ids = {node.symbol_id for node in closure.closure_nodes}
    assert payment_id in node_ids
    assert checkout_id in node_ids
    assert test_id in node_ids  # Tests are prioritized over Hop 2
    assert order_id not in node_ids  # Hop 2 pruned to satisfy budget


def test_compute_semantic_impact_closure_empty_or_unknown():
    graph = CodeGraph()
    closure = compute_semantic_impact_closure(graph, conflict_symbols=["non_existent_sym"])

    assert len(closure.closure_nodes) == 1
    assert closure.closure_nodes[0].symbol_id == "non_existent_sym"
    assert len(closure.implicated_files) == 0


def test_is_test_path_multi_language_support():
    """Verify test path detection works across all GDSS-supported programming languages."""
    from gdss.graph.impact_closure import is_test_path

    # Python
    assert is_test_path("tests/test_payment.py") is True
    assert is_test_path("src/payment_test.py") is True

    # TypeScript / JavaScript
    assert is_test_path("src/__tests__/checkout.test.ts") is True
    assert is_test_path("components/Button.spec.tsx") is True
    assert is_test_path("web/tests/unit/api.test.js") is True

    # Go
    assert is_test_path("pkg/payment/payment_test.go") is True

    # Rust
    assert is_test_path("tests/payment_test.rs") is True
    assert is_test_path("src/lib_test.rs") is True

    # C# (.NET)
    assert is_test_path("src/Services/PaymentServiceTests.cs") is True
    assert is_test_path("tests/Unit/PaymentTest.cs") is True

    # Java
    assert is_test_path("src/test/java/com/app/PaymentServiceTest.java") is True

    # C / C++
    assert is_test_path("tests/test_allocator.cpp") is True
    assert is_test_path("test/test_core.c") is True

    # Non-test source files
    assert is_test_path("src/payment_service.py") is False
    assert is_test_path("pkg/payment/payment.go") is False
    assert is_test_path("src/lib.rs") is False
    assert is_test_path("Services/PaymentService.cs") is False


def test_is_contract_path_multi_language_and_schemas():
    """Verify contract and schema file detection across IDLs and languages."""
    from gdss.graph.impact_closure import is_contract_path

    # IDLs and Schemas
    assert is_contract_path("proto/payment_service.proto") is True
    assert is_contract_path("schema/api.graphql") is True
    assert is_contract_path("api/v1/swagger.json") is True
    assert is_contract_path("api/openapi.yaml") is True
    assert is_contract_path("db/schema.sql") is True
    assert is_contract_path("prisma/schema.prisma") is True

    # C# / TypeScript Interfaces
    assert is_contract_path("src/Services/IPaymentService.cs") is True
    assert is_contract_path("src/contracts/IPayment.ts") is True

    # Route / Controller / Repository naming conventions
    assert is_contract_path("src/controllers/payment_controller.py") is True
    assert is_contract_path("src/routes/api.js") is True
    assert is_contract_path("internal/repository/user_repo.go") is True

    # Plain implementation files
    assert is_contract_path("src/utils/math_helpers.py") is False
    assert is_contract_path("pkg/worker/worker.go") is False


def test_is_test_path_custom_pattern_precedence():
    """Verify that user-configured test_patterns in .gdss.yml take precedence over heuristics."""
    from gdss.graph.impact_closure import is_test_path

    unconventional_path = "qa/sanity/verify_payment_flow.py"
    # By default, does not match standard test indicators
    assert is_test_path(unconventional_path) is False

    # When explicit glob is provided from .gdss.yml, it is recognized immediately
    assert is_test_path(unconventional_path, custom_patterns=["qa/**"]) is True
    assert is_test_path(unconventional_path, custom_patterns=["**/verify_*.py"]) is True


def test_is_contract_path_custom_pattern_precedence():
    """Verify that user-configured contract_patterns in .gdss.yml take precedence over heuristics."""
    from gdss.graph.impact_closure import is_contract_path

    unconventional_contract = "specifications/internal_rpc/payment.dsl"
    # By default, unknown DSL is not recognized as a contract
    assert is_contract_path(unconventional_contract) is False

    # When configured via contract_patterns in .gdss.yml, it is recognized immediately
    assert is_contract_path(unconventional_contract, custom_patterns=["specifications/**"]) is True
    assert is_contract_path(unconventional_contract, custom_patterns=["*.dsl"]) is True


def test_compute_semantic_impact_closure_with_config():
    """Verify that compute_semantic_impact_closure respects an explicit ImpactClosureConfig."""
    from gdss.core.config import ImpactClosureConfig

    graph, payment_id, checkout_id, order_id, test_id = _build_test_graph()

    cfg = ImpactClosureConfig(
        max_hops=1,
        relevance_threshold=0.80,
        token_budget=5000,
        test_patterns=("tests/**",),
    )

    closure = compute_semantic_impact_closure(
        graph,
        conflict_symbols=[payment_id],
        config=cfg,
    )

    node_ids = {node.symbol_id for node in closure.closure_nodes}
    assert payment_id in node_ids
    assert checkout_id in node_ids
    assert test_id in node_ids
    assert order_id not in node_ids  # Pruned because config.max_hops == 1

