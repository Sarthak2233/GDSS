"""Tests for multi-language AST parsing, Tree-sitter extension, and Universal Fallback."""

from __future__ import annotations

from pathlib import Path

from gdss.core.ast_parser import (
    DEFAULT_SOURCE_EXTENSIONS,
    SOURCE_EXTENSIONS,
    ASTParser,
    get_source_extensions,
)
from gdss.core.transform_types import CodeSymbol, SymbolType


def test_default_source_extensions_includes_major_languages():
    exts = set(DEFAULT_SOURCE_EXTENSIONS)
    assert ".py" in exts
    assert ".ts" in exts
    assert ".js" in exts
    assert ".go" in exts
    assert ".rs" in exts
    assert ".java" in exts
    assert ".c" in exts
    assert ".cpp" in exts
    assert ".cs" in exts
    assert ".rb" in exts
    assert ".php" in exts
    assert ".sh" in exts
    # Backward-compatible module-level tuple
    assert set(SOURCE_EXTENSIONS) == exts


def test_get_source_extensions_with_gdss_config_override(tmp_path: Path):
    config = tmp_path / ".gdss.yml"
    config.write_text(
        "ast:\n  additional_extensions:\n    - .vue\n    - .sol\n",
        encoding="utf-8",
    )
    exts = get_source_extensions(tmp_path)
    assert ".vue" in exts
    assert ".sol" in exts
    assert ".py" in exts
    assert ".rs" in exts


def test_parse_rust_code():
    code = """
use std::collections::HashMap;

pub struct Point {
    x: i32,
    y: i32,
}

pub enum Direction {
    North,
    South,
}

impl Point {
    pub fn new(x: i32, y: i32) -> Self {
        Point { x, y }
    }
}

pub fn calculate_distance(p1: &Point, p2: &Point) -> f64 {
    let dx = p1.x - p2.x;
    let dy = p1.y - p2.y;
    ((dx * dx + dy * dy) as f64).sqrt()
}
"""
    parser = ASTParser()
    symbols = parser.parse_file("lib.rs", content=code)

    by_type = {s.name: s for s in symbols}

    assert "Point" in by_type
    assert by_type["Point"].type == SymbolType.CLASS

    assert "Direction" in by_type
    assert by_type["Direction"].type == SymbolType.CLASS

    assert "new" in by_type
    assert by_type["new"].type == SymbolType.FUNCTION
    assert by_type["new"].parent_class == "Point"

    assert "calculate_distance" in by_type
    assert by_type["calculate_distance"].type == SymbolType.FUNCTION

    # Check import
    imports = [s for s in symbols if s.type == SymbolType.IMPORT]
    assert len(imports) >= 1
    assert any("HashMap" in s.name or "std::collections" in (s.module or "") for s in imports)


def test_parse_java_code():
    code = """
package com.example.service;

import java.util.List;
import java.util.ArrayList;

public class OrderService {
    private List<String> orders;

    public OrderService() {
        this.orders = new ArrayList<>();
    }

    public boolean processOrder(String orderId) {
        validate(orderId);
        return true;
    }
}

public interface PaymentGateway {
    void charge(double amount);
}
"""
    parser = ASTParser()
    symbols = parser.parse_file("OrderService.java", content=code)

    classes = [s for s in symbols if s.type == SymbolType.CLASS]
    funcs = [s for s in symbols if s.type == SymbolType.FUNCTION]
    imports = [s for s in symbols if s.type == SymbolType.IMPORT]

    class_names = {c.name for c in classes}
    assert "OrderService" in class_names
    assert "PaymentGateway" in class_names

    func_names = {f.name: f for f in funcs}
    assert "processOrder" in func_names
    assert func_names["processOrder"].parent_class == "OrderService"

    import_names = {i.module or i.name for i in imports}
    assert any("java.util.List" in name for name in import_names)


def test_parse_c_cpp_code():
    code = """
#include <stdio.h>
#include "widget.h"

class Widget {
public:
    int render() {
        return 1;
    }
};

struct Config {
    int timeout;
};

int compute_metrics(int factor) {
    return factor * 2;
}
"""
    parser = ASTParser()
    symbols = parser.parse_file("widget.cpp", content=code)

    by_name = {s.name: s for s in symbols}

    assert "Widget" in by_name
    assert by_name["Widget"].type == SymbolType.CLASS

    assert "Config" in by_name
    assert by_name["Config"].type == SymbolType.CLASS

    assert "compute_metrics" in by_name
    assert by_name["compute_metrics"].type == SymbolType.FUNCTION

    assert "render" in by_name
    assert by_name["render"].type == SymbolType.FUNCTION
    assert by_name["render"].parent_class == "Widget"


def test_parse_universal_fallback_ruby():
    code = """
class Account
  def deposit(amount)
    @balance += amount
  end

  def withdraw(amount)
    @balance -= amount
  end
end

def transfer(from_acc, to_acc, amount)
  from_acc.withdraw(amount)
  to_acc.deposit(amount)
end
"""
    parser = ASTParser()
    symbols = parser.parse_file("account.rb", content=code)
    assert len(symbols) >= 3

    by_name = {s.name: s for s in symbols}
    assert "Account" in by_name
    assert by_name["Account"].type == SymbolType.CLASS

    assert "deposit" in by_name
    assert by_name["deposit"].type == SymbolType.FUNCTION
    assert by_name["deposit"].parent_class == "Account"

    assert "transfer" in by_name
    assert by_name["transfer"].type == SymbolType.FUNCTION
    assert by_name["transfer"].parent_class is None


def test_parse_universal_fallback_php():
    code = """<?php
class UserManager {
    public function findUser($id) {
        return $id;
    }
}

function verifyToken($token) {
    return true;
}
"""
    parser = ASTParser()
    symbols = parser.parse_file("user.php", content=code)
    by_name = {s.name: s for s in symbols}

    assert "UserManager" in by_name
    assert by_name["UserManager"].type == SymbolType.CLASS

    assert "findUser" in by_name
    assert by_name["findUser"].type == SymbolType.FUNCTION

    assert "verifyToken" in by_name
    assert by_name["verifyToken"].type == SymbolType.FUNCTION


def test_parse_universal_fallback_shell_and_unknown():
    code = """
#!/usr/bin/env bash

function deploy_service() {
    echo "deploying"
}

run_healthcheck() {
    echo "checking"
}
"""
    parser = ASTParser()
    symbols = parser.parse_file("deploy.sh", content=code)
    func_names = {s.name for s in symbols if s.type == SymbolType.FUNCTION}
    assert "deploy_service" in func_names
    assert "run_healthcheck" in func_names


def test_register_language_dynamic():
    def dummy_visitor(
        parser,
        root,
        content_bytes,
        symbols,
        parent_class=None,
        language="custom",
        chart_location=None,
    ):
        symbols.append(
            CodeSymbol(
                name="custom_symbol",
                type=SymbolType.FUNCTION,
                start_line=1,
                end_line=2,
                start_column=1,
                end_column=10,
                signature="()",
                body="custom body",
                language=language,
                chart_location=chart_location,
            )
        )

    ASTParser.register_language(
        ext=".custom",
        language_name="custom_lang",
        visitor=dummy_visitor,
    )
    assert ".custom" in get_source_extensions()
    parser = ASTParser()
    symbols = parser.parse_file("foo.custom", content="dummy content")
    assert len(symbols) == 1
    assert symbols[0].name == "custom_symbol"


def test_universal_tree_sitter_node_walker():
    # Register an extension mapped to Go grammar but without a custom visitor
    import tree_sitter_go
    from tree_sitter import Language

    ASTParser.register_language(
        ext=".genericgo",
        language_name="generic_go",
        loader=lambda: Language(tree_sitter_go.language()),
    )

    code = """
package main

type Point struct {
    X int
    Y int
}

func Add(a int, b int) int {
    return a + b
}
"""
    parser = ASTParser()
    symbols = parser.parse_file("sample.genericgo", content=code)
    names = {s.name for s in symbols}
    assert "Point" in names
    assert "Add" in names


def test_transform_extractor_with_multi_language_ast():
    from gdss.core.transform_extractor import TransformExtractor
    from gdss.core.transform_types import OperatorType

    old_rust = """
pub fn compute(a: i32) -> i32 {
    a * 2
}
"""
    new_rust = """
pub fn compute(a: i32, b: i32) -> i32 {
    a * 2 + b
}
"""
    parser = ASTParser()
    old_syms = parser.parse_file("lib.rs", content=old_rust)
    new_syms = parser.parse_file("lib.rs", content=new_rust)

    extractor = TransformExtractor()
    ops = extractor.extract_operators("lib.rs", old_syms, new_syms)
    assert len(ops) >= 1
    assert any(op.name == "compute" and op.operator == OperatorType.MODIFY_FUNCTION for op in ops)
