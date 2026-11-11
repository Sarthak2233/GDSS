# 05: MSBuild Project Reference DAG & CPM Manifest Reducer

Type: grilling
Status: resolved
Blocked by: 01

## Question

How should GDSS parse `.csproj`, `.props` (`Directory.Build.props`, `Directory.Packages.props`), `.targets`, and `.sln`/`.slnx` files to build a deterministic `ProjectDAG`? Specifically:
1. How should `<ProjectReference Include="..." />` dependencies be represented in `CodeGraph`?
2. How should Central Package Management (CPM) version updates in `Directory.Packages.props` map to package dependency operators?

## Answer

1. **Manifest Reducer Expansion (`gdss/reducers/manifest_reducer.py`)**:
   Extended `ManifestReducer.can_handle` and added `_extract_msbuild` to parse MSBuild XML:
   - `<PackageReference>`: Extracts NuGet package name and version.
   - `<PackageVersion>`: Extracts Central Package Management (CPM) version declarations in `Directory.Packages.props`.
   - `<ProjectReference>`: Extracts referenced project name and relative path.
2. **Semantic Operators**:
   Emits `OperatorType.ADD_DEPENDENCY`, `REMOVE_DEPENDENCY`, and `MODIFY_DEPENDENCY` with symbol IDs of format `msbuild::{file_path}::{type}.{name}`.
3. **Sandbox Project Root Resolution (`gdss/validation/discovery.py`)**:
   Enhanced `find_project_root_for_file` to detect enclosing project directories containing `*.csproj`, `*.fsproj`, or `*.sln`, ensuring `dotnet build` and `dotnet test` execute within the correct subproject folder.
Verified in `tests/reducers/test_msbuild_manifest_reducer.py`.
