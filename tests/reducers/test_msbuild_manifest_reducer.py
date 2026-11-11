"""Tests for MSBuild (.csproj, .props, .targets) Manifest Reducer."""

from __future__ import annotations

from gdss.core.transform_types import OperatorType
from gdss.reducers.manifest_reducer import ManifestReducer


def test_msbuild_can_handle():
    reducer = ManifestReducer()
    assert reducer.can_handle("src/Api/Api.csproj") is True
    assert reducer.can_handle("Directory.Build.props") is True
    assert reducer.can_handle("Directory.Packages.props") is True
    assert reducer.can_handle("build/Common.targets") is True
    assert reducer.can_handle("package.json") is True
    assert reducer.can_handle("src/Api/Program.cs") is False


def test_package_reference_changes():
    old_csproj = """<Project Sdk="Microsoft.NET.Sdk">
  <ItemGroup>
    <PackageReference Include="Newtonsoft.Json" Version="12.0.1" />
    <PackageReference Include="Serilog" Version="2.10.0" />
  </ItemGroup>
</Project>"""

    new_csproj = """<Project Sdk="Microsoft.NET.Sdk">
  <ItemGroup>
    <PackageReference Include="Newtonsoft.Json" Version="13.0.3" />
    <PackageReference Include="Microsoft.EntityFrameworkCore" Version="8.0.0" />
  </ItemGroup>
</Project>"""

    reducer = ManifestReducer()
    ops = reducer.extract_operators("Api.csproj", old_csproj, new_csproj, commit_sha="abc1234")

    by_name = {op.name: op for op in ops}

    # Newtonsoft.Json version modified
    assert "Newtonsoft.Json" in by_name
    assert by_name["Newtonsoft.Json"].operator == OperatorType.MODIFY_DEPENDENCY

    # EF Core added
    assert "Microsoft.EntityFrameworkCore" in by_name
    assert by_name["Microsoft.EntityFrameworkCore"].operator == OperatorType.ADD_DEPENDENCY

    # Serilog removed
    assert "Serilog" in by_name
    assert by_name["Serilog"].operator == OperatorType.REMOVE_DEPENDENCY


def test_project_reference_changes():
    old_csproj = """<Project Sdk="Microsoft.NET.Sdk">
  <ItemGroup>
    <ProjectReference Include="../Domain/Domain.csproj" />
  </ItemGroup>
</Project>"""

    new_csproj = """<Project Sdk="Microsoft.NET.Sdk">
  <ItemGroup>
    <ProjectReference Include="../Domain/Domain.csproj" />
    <ProjectReference Include="../Infrastructure/Infrastructure.csproj" />
  </ItemGroup>
</Project>"""

    reducer = ManifestReducer()
    ops = reducer.extract_operators("Api.csproj", old_csproj, new_csproj, commit_sha="def5678")

    assert len(ops) == 1
    op = ops[0]
    assert op.name == "Infrastructure"
    assert op.operator == OperatorType.ADD_DEPENDENCY
    assert op.details.get("type") == "project_reference"


def test_central_package_management_directory_packages_props():
    old_props = """<Project>
  <ItemGroup>
    <PackageVersion Include="FluentValidation" Version="11.0.0" />
  </ItemGroup>
</Project>"""

    new_props = """<Project>
  <ItemGroup>
    <PackageVersion Include="FluentValidation" Version="11.8.0" />
  </ItemGroup>
</Project>"""

    reducer = ManifestReducer()
    ops = reducer.extract_operators("Directory.Packages.props", old_props, new_props)

    assert len(ops) == 1
    assert ops[0].name == "FluentValidation"
    assert ops[0].operator == OperatorType.MODIFY_DEPENDENCY


def test_visual_studio_sln_project_membership_changes():
    old_sln = """Microsoft Visual Studio Solution File, Format Version 12.00
# Visual Studio Version 17
Project("{FAE04EC0-301F-11D3-BF4B-00C04F79EFBC}") = "Api", "src\\Api\\Api.csproj", "{8F123456-1234-1234-1234-1234567890AB}"
EndProject
"""
    new_sln = """Microsoft Visual Studio Solution File, Format Version 12.00
# Visual Studio Version 17
Project("{FAE04EC0-301F-11D3-BF4B-00C04F79EFBC}") = "Api", "src\\Api\\Api.csproj", "{8F123456-1234-1234-1234-1234567890AB}"
EndProject
Project("{FAE04EC0-301F-11D3-BF4B-00C04F79EFBC}") = "Domain", "src\\Domain\\Domain.csproj", "{9F123456-1234-1234-1234-1234567890AB}"
EndProject
"""
    reducer = ManifestReducer()
    assert reducer.can_handle("MySolution.sln") is True
    ops = reducer.extract_operators("MySolution.sln", old_sln, new_sln)

    assert len(ops) == 1
    assert ops[0].name == "Domain"
    assert ops[0].operator == OperatorType.ADD_DEPENDENCY
    assert ops[0].details.get("type") == "solution_project"


def test_visual_studio_slnx_project_membership_changes():
    old_slnx = """<Solution>
  <Project Path="src/Api/Api.csproj" />
</Solution>"""
    new_slnx = """<Solution>
  <Project Path="src/Api/Api.csproj" />
  <Project Path="src/Web/Web.csproj" />
</Solution>"""
    reducer = ManifestReducer()
    assert reducer.can_handle("MySolution.slnx") is True
    ops = reducer.extract_operators("MySolution.slnx", old_slnx, new_slnx)

    assert len(ops) == 1
    assert ops[0].name == "Web"
    assert ops[0].operator == OperatorType.ADD_DEPENDENCY
    assert ops[0].details.get("type") == "solution_project"


