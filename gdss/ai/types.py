"""Public immutable contracts for the assistive AI convergence layer."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Any, Literal

ConflictTopologyKind = Literal["union", "intersection", "disjoint", "asymmetric"]
CommutativityVerdict = Literal["commute", "interfere", "independent"]
SuggestionSource = Literal["deterministic", "llm"]
PatchValidationStatus = Literal["not_requested", "draft", "validated", "rejected"]


@dataclass(frozen=True)
class SuggestionAnchor:
    """Exact target-frame symbol location used to constrain a suggestion."""

    file_path: str
    line_start: int
    line_end: int
    column_start: int = 1
    column_end: int = 1
    target_branch: str = "HEAD"
    content_digest: str = ""
    symbol_digest: str = ""

    def __post_init__(self) -> None:
        path = PurePosixPath(self.file_path)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("suggestion anchors require a repository-relative path")
        if self.line_start < 1 or self.line_end < self.line_start:
            raise ValueError("suggestion anchor line range is invalid")
        if self.column_start < 1 or self.column_end < 1:
            raise ValueError("suggestion anchor columns are one-based")

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_path": self.file_path,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "column_start": self.column_start,
            "column_end": self.column_end,
            "target_branch": self.target_branch,
            "content_digest": self.content_digest,
            "symbol_digest": self.symbol_digest,
        }


@dataclass(frozen=True)
class SuggestionContext:
    """Deterministic evidence associated with an anchored suggestion."""

    reference_branch: str
    candidate_branch: str
    omega: float
    merge_risk: float
    operator_i_id: str
    operator_j_id: str
    other_branch: str = ""

    def __post_init__(self) -> None:
        if not 0.0 <= self.omega <= 1.0 or not math.isfinite(self.omega):
            raise ValueError("omega must be a finite value in [0, 1]")
        if self.merge_risk < 0.0 or not math.isfinite(self.merge_risk):
            raise ValueError("merge risk must be finite and non-negative")

    def to_dict(self) -> dict[str, Any]:
        return {
            "reference_branch": self.reference_branch,
            "candidate_branch": self.candidate_branch,
            "omega": self.omega,
            "merge_risk": self.merge_risk,
            "operator_i_id": self.operator_i_id,
            "operator_j_id": self.operator_j_id,
            "other_branch": self.other_branch,
        }



@dataclass(frozen=True)
class ConflictTopology:
    """Deterministic classification of one pair of contacting operators."""

    kind: ConflictTopologyKind
    symbol_id: str
    operator_i: str
    operator_j: str
    commutativity: CommutativityVerdict
    justification: str

    def to_dict(self) -> dict[str, str]:
        return {
            "kind": self.kind,
            "symbol_id": self.symbol_id,
            "operator_i": self.operator_i,
            "operator_j": self.operator_j,
            "commutativity": self.commutativity,
            "justification": self.justification,
        }


@dataclass(frozen=True)
class PatchCombination:
    """One resolution strategy, optionally accompanied by a validated local draft."""

    label: str
    strategy: str
    patch_text: str | None = None
    source: SuggestionSource = "deterministic"
    validated: bool = False
    validation_error: str | None = None
    validation_status: PatchValidationStatus = "not_requested"

    def __post_init__(self) -> None:
        status = self.validation_status
        if self.validated and status != "validated":
            status = "validated"
        elif status == "validated" and not self.validated:
            object.__setattr__(self, "validated", True)
        object.__setattr__(self, "validation_status", status)

    def to_metadata(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "strategy": self.strategy,
            "source": self.source,
            "validated": self.validated,
            "validation_status": self.validation_status,
            "validation_error": self.validation_error,
        }

    def to_local_source(self) -> dict[str, Any]:
        data = self.to_metadata()
        data["patch_text"] = self.patch_text
        return data


@dataclass(frozen=True)
class Suggestion:
    """A location-anchored, assistive recommendation; never an applied change."""

    kind: str
    file_path: str
    line_start: int
    line_end: int
    symbol_id: str
    operator: str
    action: str
    rationale: str
    reason: tuple[str, ...]
    confidence: float
    rank: int = 0
    topology: ConflictTopology | None = None
    patch_combinations: Sequence[PatchCombination] = field(default_factory=tuple)
    source: SuggestionSource = "deterministic"
    validated: bool = False
    anchor: SuggestionAnchor | None = None
    context: SuggestionContext | None = None
    suggestion_id: str = ""

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0 or not math.isfinite(self.confidence):
            raise ValueError("suggestion confidence must be a finite value in [0, 1]")
        anchor = self.anchor or SuggestionAnchor(
            file_path=self.file_path,
            line_start=self.line_start,
            line_end=self.line_end,
        )
        object.__setattr__(self, "anchor", anchor)
        object.__setattr__(self, "patch_combinations", tuple(self.patch_combinations))
        object.__setattr__(self, "reason", tuple(self.reason))
        if not self.suggestion_id:
            object.__setattr__(self, "suggestion_id", self._derive_id())

    def _derive_id(self) -> str:
        payload = {
            "kind": self.kind,
            "anchor": self.anchor.to_dict() if self.anchor else {},
            "symbol_id": self.symbol_id,
            "operator": self.operator,
            "action": self.action,
            "context": self.context.to_dict() if self.context else {},
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()[:20]

    def to_metadata(self) -> dict[str, Any]:
        return {
            "id": self.suggestion_id,
            "kind": self.kind,
            "file_path": self.file_path,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "symbol_id": self.symbol_id,
            "operator": self.operator,
            "action": self.action,
            "rationale": self.rationale,
            "reason": list(self.reason),
            "confidence": self.confidence,
            "rank": self.rank,
            "topology": self.topology.to_dict() if self.topology else None,
            "anchor": self.anchor.to_dict() if self.anchor else None,
            "context": self.context.to_dict() if self.context else None,
            "strategies": [item.to_metadata() for item in self.patch_combinations],
            "source": self.source,
            "validated": self.validated,
        }

    def to_local_source(self) -> dict[str, Any]:
        data = self.to_metadata()
        data["patch_combinations"] = [
            item.to_local_source() for item in self.patch_combinations
        ]
        return data
