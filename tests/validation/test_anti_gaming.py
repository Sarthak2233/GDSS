"""Unit tests for Test Anti-Gaming Invariant Enforcement (Phase 2 of Solution)."""

from __future__ import annotations

from gdss.validation.diagnostic_extractor import (
    AntiGamingCheckResult,
    inspect_test_diff_anti_gaming,
)

ORIGINAL_TEST_CODE = """
def test_payment():
    order = {"id": 1, "total": 100}
    res = process_payment(order)
    assert res.status == "SUCCESS"
    assert res.amount == 100
"""

# Legitimate call site update: renamed function and added currency argument
VALID_ADAPTED_TEST_CODE = """
def test_payment():
    order = {"id": 1, "total": 100}
    res = execute_payment(order, currency="USD")
    assert res.status == "SUCCESS"
    assert res.amount == 100
"""

# Gaming attempt 1: deleted an assertion to make a failing test pass
DELETED_ASSERTION_CODE = """
def test_payment():
    order = {"id": 1, "total": 100}
    res = execute_payment(order, currency="USD")
    assert res.status == "SUCCESS"
    # assert res.amount == 100 was deleted!
"""

# Gaming attempt 2: weakened assertion to trivial truth
TRIVIAL_ASSERTION_CODE = """
def test_payment():
    order = {"id": 1, "total": 100}
    res = execute_payment(order, currency="USD")
    assert True
    assert res.amount == 100
"""


def test_anti_gaming_valid_call_site_adaptation():
    result = inspect_test_diff_anti_gaming(
        original_content=ORIGINAL_TEST_CODE,
        patched_content=VALID_ADAPTED_TEST_CODE,
        file_path="tests/test_payment.py",
    )

    assert isinstance(result, AntiGamingCheckResult)
    assert result.passed is True
    assert result.deleted_assertions_count == 0
    assert result.modified_assertions_count == 0
    assert len(result.warnings) == 0


def test_anti_gaming_detects_deleted_assertion():
    result = inspect_test_diff_anti_gaming(
        original_content=ORIGINAL_TEST_CODE,
        patched_content=DELETED_ASSERTION_CODE,
        file_path="tests/test_payment.py",
    )

    assert result.passed is False
    assert result.deleted_assertions_count == 1
    assert any("ANTI_GAMING_WARNING" in w for w in result.warnings)
    assert any("deleted" in w.lower() or "removed" in w.lower() for w in result.warnings)


def test_anti_gaming_detects_trivialized_assertion():
    result = inspect_test_diff_anti_gaming(
        original_content=ORIGINAL_TEST_CODE,
        patched_content=TRIVIAL_ASSERTION_CODE,
        file_path="tests/test_payment.py",
    )

    assert result.passed is False
    assert result.modified_assertions_count >= 1
    assert any("ANTI_GAMING_WARNING" in w for w in result.warnings)


def test_anti_gaming_typescript_jest():
    orig_ts = """
    test('checkout flow', () => {
        expect(res.total).toBe(100);
        expect(res.status).toEqual('OK');
    });
    """
    # Attempt to game by deleting an assertion
    deleted_ts = """
    test('checkout flow', () => {
        expect(res.total).toBe(100);
    });
    """
    res_del = inspect_test_diff_anti_gaming(orig_ts, deleted_ts, "src/checkout.test.ts")
    assert res_del.passed is False
    assert res_del.deleted_assertions_count == 1

    # Attempt to game by trivializing assertion
    trivial_ts = """
    test('checkout flow', () => {
        expect(true).toBe(true);
        expect(res.total).toBe(100);
    });
    """
    res_triv = inspect_test_diff_anti_gaming(orig_ts, trivial_ts, "src/checkout.test.ts")
    assert res_triv.passed is False
    assert res_triv.modified_assertions_count >= 1


def test_anti_gaming_rust():
    orig_rs = """
    #[test]
    fn test_calc() {
        assert_eq!(calc(5, 5), 10);
        assert!(calc(5, 5) > 0);
    }
    """
    # Deleting assertion
    del_rs = """
    #[test]
    fn test_calc() {
        assert_eq!(calc(5, 5), 10);
    }
    """
    res_del = inspect_test_diff_anti_gaming(orig_rs, del_rs, "tests/test_calc.rs")
    assert res_del.passed is False
    assert res_del.deleted_assertions_count == 1

    # Trivializing assertion
    triv_rs = """
    #[test]
    fn test_calc() {
        assert!(true);
        assert_eq!(calc(5, 5), 10);
    }
    """
    res_triv = inspect_test_diff_anti_gaming(orig_rs, triv_rs, "tests/test_calc.rs")
    assert res_triv.passed is False
    assert res_triv.modified_assertions_count >= 1


def test_anti_gaming_csharp():
    orig_cs = """
    [Fact]
    public void TestPayment() {
        Assert.Equal(100, res.Total);
        Assert.NotNull(res.Id);
    }
    """
    del_cs = """
    [Fact]
    public void TestPayment() {
        Assert.Equal(100, res.Total);
    }
    """
    res_del = inspect_test_diff_anti_gaming(orig_cs, del_cs, "PaymentTests.cs")
    assert res_del.passed is False
    assert res_del.deleted_assertions_count == 1

    triv_cs = """
    [Fact]
    public void TestPayment() {
        Assert.True(true);
        Assert.Equal(100, res.Total);
    }
    """
    res_triv = inspect_test_diff_anti_gaming(orig_cs, triv_cs, "PaymentTests.cs")
    assert res_triv.passed is False
    assert res_triv.modified_assertions_count >= 1


def test_anti_gaming_configurable_strict_mode():
    """Verify that strict=False allows deletion with warning, but still forbids trivialization."""
    # 1. In strict mode (default): deletion fails
    res_strict = inspect_test_diff_anti_gaming(
        ORIGINAL_TEST_CODE,
        DELETED_ASSERTION_CODE,
        file_path="tests/test_payment.py",
        strict=True,
    )
    assert res_strict.passed is False
    assert res_strict.deleted_assertions_count == 1

    # 2. In non-strict mode: deletion passes with warning recorded
    res_non_strict = inspect_test_diff_anti_gaming(
        ORIGINAL_TEST_CODE,
        DELETED_ASSERTION_CODE,
        file_path="tests/test_payment.py",
        strict=False,
    )
    assert res_non_strict.passed is True
    assert res_non_strict.deleted_assertions_count == 1
    assert len(res_non_strict.warnings) >= 1

    # 3. In non-strict mode: trivialization (assert True) STILL fails
    res_triv = inspect_test_diff_anti_gaming(
        ORIGINAL_TEST_CODE,
        TRIVIAL_ASSERTION_CODE,
        file_path="tests/test_payment.py",
        strict=False,
    )
    assert res_triv.passed is False
    assert res_triv.modified_assertions_count >= 1



