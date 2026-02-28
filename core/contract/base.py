"""SentinelCore v0.1 — Core Contracts (Interfaces Only)

AUTHORITATIVE SOURCE:
- “SentinelCore v0.1 – Architecture & Contracts Specification (DM-Engineer Handoff)”

This module defines *interfaces only* (no implementation logic).

Frozen invariants:
- core/ is scheduler-agnostic.
- Adapters translate; they do not diagnose.
- RuleEngine is pure and deterministic.
- EvidenceProviders may fail partially, never fatally.

Keep contracts minimal and factual.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, List, Mapping, Optional, Protocol, Sequence

from typing_extensions import Literal


# ---------------------------------------------------------------------------
# Shared Types (Contracts)
# ---------------------------------------------------------------------------

ExecutionMode = Literal["check", "collect", "replay", "explain"]
"""Frozen execution modes (v0.1)."""


@dataclass(frozen=True)
class ProviderResult:
    """Result contract for EvidenceProvider collection (frozen failure policy).

Providers MUST NOT raise for collection failures.
Partial data is allowed via `warnings`.
`errors` is reserved for rare provider-fatal conditions (still returned, not raised).
"""

    artifacts: Mapping[str, Any]
    warnings: List[str]
    errors: List[str]


@dataclass(frozen=True)
class Finding:
    """Diagnostic finding contract (minimal, scheduler-agnostic)."""

    rule_id: str
    title: str
    description: str
    severity: str
    confidence: float
    specificity: float
    suppressed_by: Optional[str]
    evidence: Mapping[str, Any]
    metadata: Mapping[str, Any]


@dataclass(frozen=True)
class CommandResult:
    """Bounded, non-interactive command execution result."""

    exit_code: int
    stdout: str
    stderr: str


class NormalizedContextLike(Protocol):
    """Read-only protocol for normalized context (v0.1).

Attribute-only access.
Rules and engines may access mapping contents via these attributes
(e.g., `context.artifacts.get("key")`).
"""

    schema_version: str
    artifacts: Mapping[str, Any]
    provenance: Mapping[str, Any]


# ---------------------------------------------------------------------------
# Core Contracts (Frozen)
# ---------------------------------------------------------------------------


class SchedulerAdapter(ABC):
    """SchedulerAdapter (frozen v0.1).

Responsibility:
- Fetch normalized scheduler metadata for a job id.
- Execute scheduler-native commands.

Must NOT:
- Perform diagnosis.
- Print to CLI.
- Return raw command output from metadata APIs.
"""

    @property
    @abstractmethod
    def name(self) -> str:
        """Canonical scheduler name (e.g., "lsf", "slurm")."""

    @abstractmethod
    def get_job_metadata(self, job_id: str, *, mode: ExecutionMode) -> Mapping[str, Any]:
        """Return normalized scheduler metadata for `job_id`."""

    @abstractmethod
    def run_command(self, args: Sequence[str], *, timeout_s: float, mode: ExecutionMode) -> CommandResult:
        """Execute a scheduler-native command with bounds and timeout."""


class EvidenceProvider(ABC):
    """EvidenceProvider (frozen v0.1).

Responsibility:
- Collect evidence from a single source.
- Normalize raw data into artifacts.
- Enforce bounds, timeouts, and non-interactive behavior.

Failure policy:
- Never raise for collection failures.
"""

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Stable identifier for provenance."""

    @abstractmethod
    def collect(self, *, job_id: str, context_seed: Mapping[str, Any], mode: ExecutionMode) -> ProviderResult:
        """Collect evidence for `job_id` and return a ProviderResult."""


class ContextBuilder(ABC):
    """ContextBuilder (frozen v0.1).

Responsibility:
- Invoke SchedulerAdapter.
- Invoke EvidenceProviders (ordered).
- Merge artifacts and populate provenance.

ContextBuilder is the only orchestration layer.
"""

    @abstractmethod
    def build(self, job_id: str, *, mode: ExecutionMode) -> NormalizedContextLike:
        """Build and return a normalized context."""


class Rule(Protocol):
    """Rule protocol (scheduler-agnostic, deterministic)."""

    rule_id: str

    def evaluate(self, context: NormalizedContextLike) -> Optional[Finding]:
        ...


@dataclass(frozen=True)
class RuleEvaluationResult:
    """Outcome of rule evaluation.

NOTE (v0.1): structure is intentionally minimal and not frozen.
Consumers MUST rely only on `findings` and `provenance`.
"""

    findings: List[Finding]
    provenance: Mapping[str, Any]


class RuleEngine(ABC):
    """RuleEngine (frozen v0.1).

Responsibility:
- Evaluate rules against NormalizedContext.
- Produce findings deterministically.
"""

    @abstractmethod
    def evaluate(self, context: NormalizedContextLike, *, mode: ExecutionMode) -> RuleEvaluationResult:
        """Evaluate registered rules and return findings."""


class Renderer(ABC):
    """Renderer (frozen v0.1)."""

    @abstractmethod
    def render_json(self, *, context: NormalizedContextLike, result: RuleEvaluationResult) -> Mapping[str, Any]:
        """Render a JSON-serializable structure."""

    @abstractmethod
    def render_text(self, *, context: NormalizedContextLike, result: RuleEvaluationResult, mode: ExecutionMode) -> str:
        """Render human-readable text for CLI."""

