"""Unified repository configuration loader for GDSS (.gdss.yml / .gdss.yaml).

Provides typed, immutable schema dataclasses and a single authoritative
loader for the deterministic core, collision radar, and validation sandbox.
"""

from __future__ import annotations

import fnmatch
import os
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

from gdss.logger import get_logger

logger = get_logger("gdss.core.config")


@dataclass(frozen=True)
class RadarConfig:
    """Configuration for PR collision radar and AI convergence."""

    provider: str = "openrouter"
    model: str = "openrouter/free"
    base_url: str | None = None
    context_window: int = 128_000
    risk_threshold: float = 0.1
    max_refinements: int = 2
    concurrency_limit: int = 4
    condensation: str = "lossless"
    fail_on_collision: bool = False
    same_base_only: bool = True
    include: tuple[str, ...] = ()
    exclude: tuple[str, ...] = ()
    target_bases: tuple[str, ...] = ()


@dataclass(frozen=True)
class ValidationConfig:
    """Configuration for ephemeral sandbox validation."""

    test_command: str | None = None
    typecheck_command: str | None = None
    syntax_command: str | None = None
    install_command: str | None = None
    mode: str = "targeted"
    symlink_dependencies: bool = True
    timeout_seconds: int = 30
    anti_gaming_strict: bool = True
    allow_callsite_updates: bool = True


@dataclass(frozen=True)
class ImpactClosureConfig:
    """Configuration for deterministic Semantic Impact Closure (SIC)."""

    max_hops: int = 2
    relevance_threshold: float = 0.70
    token_budget: int = 4000
    test_patterns: tuple[str, ...] = ()
    contract_patterns: tuple[str, ...] = ()


@dataclass(frozen=True)
class HierarchyConfig:
    """Configuration for branch hierarchies and landing precedence."""

    reference_branch: str = "main"
    priority_chain: tuple[str, ...] = ("main", "develop")
    same_base_only: bool = True
    include: tuple[str, ...] = ()
    exclude: tuple[str, ...] = ()
    target_bases: tuple[str, ...] = ()


@dataclass(frozen=True)
class ASTConfig:
    """Configuration for multi-language AST scanning and path filtering."""

    additional_extensions: tuple[str, ...] = ()
    exclude_patterns: tuple[str, ...] = ()


@dataclass(frozen=True)
class MigrationsConfig:
    """Configuration for database migration directories and DAG tracking."""

    paths: tuple[str, ...] = ()
    framework: str | None = None


@dataclass(frozen=True)
class GDSSConfig:
    """Top-level unified GDSS repository configuration."""

    version: int = 1
    radar: RadarConfig = field(default_factory=RadarConfig)
    validation: ValidationConfig = field(default_factory=ValidationConfig)
    impact_closure: ImpactClosureConfig = field(default_factory=ImpactClosureConfig)
    hierarchy: HierarchyConfig = field(default_factory=HierarchyConfig)
    ast: ASTConfig = field(default_factory=ASTConfig)
    migrations: MigrationsConfig = field(default_factory=MigrationsConfig)
    raw_data: dict[str, Any] = field(default_factory=dict)


DEFAULT_GENERATED_EXCLUDE_PATTERNS: tuple[str, ...] = (
    "*.Designer.cs",
    "*.g.cs",
    "*.g.i.cs",
    "*.generated.cs",
    "*.AssemblyInfo.cs",
    "*AssemblyInfo.cs",
    "*.pb.go",
    "*.gen.go",
    "*.generated.go",
    "*.generated.ts",
    "*.generated.js",
    "*.min.js",
    "*.min.css",
    "bin/**",
    "obj/**",
    "target/**",
)


def is_path_excluded(rel_path: str, exclude_patterns: Sequence[str]) -> bool:
    """Check if a relative path matches any exclusion pattern."""
    if not exclude_patterns:
        return False
    norm_path = rel_path.replace("\\", "/").strip("/")
    p = PurePosixPath(norm_path)
    for pattern in exclude_patterns:
        pat = pattern.replace("\\", "/").strip("/")
        if not pat:
            continue
        # 1. Direct fnmatch against full path
        if fnmatch.fnmatch(norm_path, pat):
            return True
        # 2. Match basename
        if fnmatch.fnmatch(p.name, pat):
            return True
        # 3. Path match (e.g. dist/** or node_modules/**)
        try:
            if p.match(pat):
                return True
        except Exception:
            pass
        # 4. Handle dir/** or dir/* prefix pattern
        if pat.endswith("/**"):
            dir_prefix = pat[:-3]
            if norm_path == dir_prefix or norm_path.startswith(dir_prefix + "/"):
                return True
        elif pat.endswith("/*"):
            dir_prefix = pat[:-2]
            if norm_path == dir_prefix or norm_path.startswith(dir_prefix + "/"):
                return True
        elif norm_path == pat or norm_path.startswith(pat + "/"):
            return True
    return False


def is_generated_or_excluded(rel_path: str, user_excludes: Sequence[str] = ()) -> bool:
    """Check if a relative path matches auto-generated code patterns or user excludes."""
    return is_path_excluded(rel_path, tuple(user_excludes) + DEFAULT_GENERATED_EXCLUDE_PATTERNS)


def load_env_file(repo_root: Path | str | os.PathLike[str] | None = None) -> dict[str, str]:
    """Parse key=value pairs from a project .env file without external dependencies.

    Loaded keys are populated into os.environ only if not already present,
    ensuring that existing shell environment variables and CI runner secrets
    always take precedence.
    """
    if repo_root is None:
        try:
            repo_root = Path.cwd()
        except Exception:
            return {}
    try:
        root_path = Path(repo_root).resolve()
        env_file = root_path / ".env"
        if not env_file.is_file():
            return {}
        loaded: dict[str, str] = {}
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip().strip("'\"")
            if k and k not in os.environ:
                os.environ[k] = v
                loaded[k] = v
        return loaded
    except Exception as exc:
        logger.debug("Failed to read .env from %s: %s", repo_root, exc)
        return {}


def load_gdss_config(repo_root: Path | str | os.PathLike[str] | None = None) -> GDSSConfig:
    """Load and normalize .gdss.yml or .gdss.yaml from repo_root if present."""
    empty_cfg = GDSSConfig()
    if repo_root is None:
        load_env_file()
        return empty_cfg

    root_path = Path(repo_root).resolve()
    load_env_file(root_path)

    config_file = root_path / ".gdss.yml"
    has_config = config_file.is_file()
    if not has_config:
        config_file = root_path / ".gdss.yaml"
        has_config = config_file.is_file()  # dsa:ignore

    if not has_config:
        return empty_cfg

    try:
        data = yaml.safe_load(config_file.read_text(encoding="utf-8")) or {}
        if not isinstance(data, dict):
            return empty_cfg
    except Exception as exc:
        logger.warning("Failed to parse %s: %s", config_file, exc)
        return empty_cfg

    def _to_clean_tuple(raw_items: Any) -> tuple[str, ...]:
        if not isinstance(raw_items, (list, tuple)):
            return ()
        out: list[str] = []
        for item in raw_items:
            clean = str(item).strip()
            if clean:
                out.append(clean)
        return tuple(out)

    # 0. Parse version
    raw_version = data.get("version", 1)
    try:
        parsed_version = int(raw_version)
    except (ValueError, TypeError):
        logger.warning(
            "Invalid 'version' value in %s: %r. Defaulting to version 1.",
            config_file,
            raw_version,
        )
        parsed_version = 1

    if parsed_version != 1:
        logger.warning(
            "Unsupported GDSS schema version %s in %s. Supported version is 1. Parsing with best-effort compatibility.",
            parsed_version,
            config_file,
        )

    # 1. Parse hierarchy block
    h_data = data.get("hierarchy", {})
    if not isinstance(h_data, dict):
        h_data = {}

    # 2. Parse radar block
    r_data = data.get("radar", {})
    if not isinstance(r_data, dict):
        r_data = {}

    h_ref = str(h_data.get("reference_branch", "main")).strip() or "main"
    h_chain = _to_clean_tuple(h_data.get("priority_chain", ["main", "develop"])) or ("main", "develop")
    h_same_base = bool(h_data.get("same_base_only", True))
    h_inc = _to_clean_tuple(h_data.get("include", ()))
    h_exc = _to_clean_tuple(h_data.get("exclude", ()))
    h_targets = _to_clean_tuple(h_data.get("target_bases", ()))

    r_inc_raw = _to_clean_tuple(r_data.get("include", ()))
    r_exc_raw = _to_clean_tuple(r_data.get("exclude", ()))
    r_targets_raw = _to_clean_tuple(r_data.get("target_bases", ()))

    # Bidirectional fallback: branch filters in either block apply across analysis
    effective_inc = h_inc or r_inc_raw
    effective_exc = h_exc or r_exc_raw
    effective_targets = h_targets or r_targets_raw
    r_same_base = bool(r_data.get("same_base_only", h_same_base))

    hierarchy_cfg = HierarchyConfig(
        reference_branch=h_ref,
        priority_chain=h_chain,
        same_base_only=h_same_base,
        include=effective_inc,
        exclude=effective_exc,
        target_bases=effective_targets,
    )

    base_url_raw = r_data.get("base_url")
    base_url = str(base_url_raw).strip() if base_url_raw else None

    radar_cfg = RadarConfig(
        provider=str(r_data.get("provider", "openrouter")).strip() or "openrouter",
        model=str(r_data.get("model", "openrouter/free")).strip() or "openrouter/free",
        base_url=base_url,
        context_window=int(r_data.get("context_window", 128_000)),
        risk_threshold=float(r_data.get("risk_threshold", 0.1)),
        max_refinements=int(r_data.get("max_refinements", 2)),
        concurrency_limit=int(r_data.get("concurrency_limit", 4)),
        condensation=str(r_data.get("condensation", "lossless")).strip() or "lossless",
        fail_on_collision=bool(r_data.get("fail_on_collision", False)),
        same_base_only=r_same_base,
        include=effective_inc,
        exclude=effective_exc,
        target_bases=effective_targets,
    )

    # 3. Parse validation block
    v_data = data.get("validation", {})
    if not isinstance(v_data, dict):
        v_data = {}

    test_cmd = str(v_data.get("test_command") or "").strip() or None
    type_cmd = str(v_data.get("typecheck_command") or "").strip() or None
    syntax_cmd = str(v_data.get("syntax_command") or "").strip() or None
    install_cmd = str(v_data.get("install_command") or "").strip() or None
    val_mode = str(v_data.get("mode") or "targeted").strip().lower() or "targeted"
    symlink_deps = bool(v_data.get("symlink_dependencies", True))

    validation_cfg = ValidationConfig(
        test_command=test_cmd,
        typecheck_command=type_cmd,
        syntax_command=syntax_cmd,
        install_command=install_cmd,
        mode=val_mode,
        symlink_dependencies=symlink_deps,
        timeout_seconds=int(v_data.get("timeout_seconds", 30)),
        anti_gaming_strict=bool(v_data.get("anti_gaming_strict", True)),
        allow_callsite_updates=bool(v_data.get("allow_callsite_updates", True)),
    )

    # 4. Parse impact_closure block
    ic_data = data.get("impact_closure", {})
    if not isinstance(ic_data, dict):
        ic_data = {}

    ic_test_pats = _to_clean_tuple(ic_data.get("test_patterns", ()))
    ic_contract_pats = _to_clean_tuple(ic_data.get("contract_patterns", ()))

    impact_closure_cfg = ImpactClosureConfig(
        max_hops=int(ic_data.get("max_hops", 2)),
        relevance_threshold=float(ic_data.get("relevance_threshold", 0.70)),
        token_budget=int(ic_data.get("token_budget", 4000)),
        test_patterns=ic_test_pats,
        contract_patterns=ic_contract_pats,
    )

    # 4. Parse AST block
    a_data = data.get("ast", {})
    if not isinstance(a_data, dict):
        a_data = {}

    raw_exts = a_data.get("additional_extensions", ())
    norm_exts: list[str] = []
    if isinstance(raw_exts, (list, tuple)):
        for e in raw_exts:
            e_str = str(e).lower().strip()
            if e_str and not e_str.startswith("."):
                e_str = f".{e_str}"
            if e_str and e_str not in norm_exts:
                norm_exts.append(e_str)

    raw_excl = a_data.get("exclude_patterns", ())
    norm_excl: list[str] = []
    if isinstance(raw_excl, (list, tuple)):
        for pat in raw_excl:
            p_str = str(pat).strip()
            if p_str and p_str not in norm_excl:
                norm_excl.append(p_str)

    ast_cfg = ASTConfig(
        additional_extensions=tuple(norm_exts),
        exclude_patterns=tuple(norm_excl),
    )

    # 5. Parse migrations block
    m_data = data.get("migrations", {})
    if not isinstance(m_data, dict):
        m_data = {}

    raw_paths = m_data.get("paths", ())
    norm_paths: list[str] = []
    if isinstance(raw_paths, (list, tuple)):
        for p in raw_paths:
            p_str = str(p).strip()
            if p_str and p_str not in norm_paths:
                norm_paths.append(p_str)

    m_framework = str(m_data.get("framework") or "").strip().lower() or None
    migrations_cfg = MigrationsConfig(paths=tuple(norm_paths), framework=m_framework)

    return GDSSConfig(
        version=parsed_version,
        radar=radar_cfg,
        validation=validation_cfg,
        impact_closure=impact_closure_cfg,
        hierarchy=hierarchy_cfg,
        ast=ast_cfg,
        migrations=migrations_cfg,
        raw_data=data,
    )
