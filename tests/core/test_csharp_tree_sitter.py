"""Comprehensive test suite for Level 3/4 C# Tree-Sitter AST parsing."""

from __future__ import annotations

from gdss.core.ast_parser import ASTParser
from gdss.core.transform_types import SymbolType


def test_parse_modern_csharp_constructs():
    code = """
using System;
using System.Threading.Tasks;

namespace MyApp.Services;

public interface IUserService
{
    Task<User> GetUserAsync(int id);
}

public partial class UserService<T> : BaseService, IUserService where T : IUser
{
    public required string Name { get; init; }
    public event EventHandler? Changed;
    public int Age => 42;

    public UserService(string name)
    {
        Name = name;
    }

    public async Task<T?> ExecuteAsync(Func<T, Task<T>> operation)
    {
        return await operation(default!);
    }
}

public record Person(string FirstName, string LastName);
public enum Status { Active, Inactive }
public struct Point { public int X; public int Y; }
"""
    parser = ASTParser()
    symbols = parser.parse_file("UserService.cs", content=code)

    classes = {s.name: s for s in symbols if s.type == SymbolType.CLASS}
    functions = {s.name: s for s in symbols if s.type == SymbolType.FUNCTION}

    # Verify imports
    imports = [s for s in symbols if s.type == SymbolType.IMPORT]
    assert len(imports) >= 2
    import_names = {s.name for s in imports}
    assert "System" in import_names
    assert "System.Threading.Tasks" in import_names

    # Verify Interface
    assert "IUserService" in classes
    assert classes["IUserService"].type == SymbolType.CLASS
    assert classes["IUserService"].parent_class == "MyApp.Services"

    # Verify Class with Type Parameters and Base list
    assert "UserService" in classes
    assert classes["UserService"].type == SymbolType.CLASS
    assert classes["UserService"].parent_class == "MyApp.Services"
    assert "<T>" in classes["UserService"].signature
    assert "IUserService" in classes["UserService"].signature

    # Verify Methods and Constructor
    assert "GetUserAsync" in functions
    assert functions["GetUserAsync"].type == SymbolType.FUNCTION
    assert functions["GetUserAsync"].parent_class == "IUserService"

    assert "UserService" in functions  # Constructor
    assert functions["UserService"].parent_class == "UserService"

    assert "ExecuteAsync" in functions
    assert functions["ExecuteAsync"].type == SymbolType.FUNCTION
    assert functions["ExecuteAsync"].parent_class == "UserService"

    # Verify Properties
    assert "Name" in functions
    assert functions["Name"].parent_class == "UserService"

    assert "Age" in functions
    assert functions["Age"].parent_class == "UserService"

    # Verify Record, Enum, Struct
    assert "Person" in classes
    assert classes["Person"].type == SymbolType.CLASS

    assert "Status" in classes
    assert classes["Status"].type == SymbolType.CLASS

    assert "Point" in classes
    assert classes["Point"].type == SymbolType.CLASS


def test_parse_csharp_calls_and_invocation():
    code = """
namespace MyApp;

public class OrderProcessor
{
    public void Process(Order order)
    {
        paymentService.Charge(order.Total);
        logger.LogInfo("Order processed");
        SendEmail();
    }
}
"""
    parser = ASTParser()
    symbols = parser.parse_file("OrderProcessor.cs", content=code)

    by_name = {s.name: s for s in symbols}
    proc_func = by_name["Process"]
    assert proc_func.type == SymbolType.FUNCTION
    assert "Charge" in proc_func.calls or "paymentService" in proc_func.calls
    assert "SendEmail" in proc_func.calls


def test_transform_extractor_with_csharp_modification():
    from gdss.core.transform_extractor import TransformExtractor
    from gdss.core.transform_types import OperatorType

    old_cs = """
public class Calculator
{
    public int Add(int a, int b) => a + b;
}
"""
    new_cs = """
public class Calculator
{
    public int Add(int a, int b, int c = 0) => a + b + c;
    public int Multiply(int a, int b) => a * b;
}
"""
    parser = ASTParser()
    old_syms = parser.parse_file("Calculator.cs", content=old_cs)
    new_syms = parser.parse_file("Calculator.cs", content=new_cs)

    extractor = TransformExtractor()
    ops = extractor.extract_operators("Calculator.cs", old_syms, new_syms)

    op_types = {op.operator for op in ops}
    assert OperatorType.MODIFY_FUNCTION in op_types or OperatorType.ADD_FUNCTION in op_types
    assert any(op.name == "Multiply" and op.operator == OperatorType.ADD_FUNCTION for op in ops)
