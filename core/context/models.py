"""SentinelCore v0.1 — STEP 2: NormalizedContext (Pydantic Model Only)

AUTHORITATIVE SOURCE:
- “SentinelCore v0.1 – Architecture & Contracts Specification (DM-Engineer Handoff)”

Scope (Frozen by instruction for STEP 2):
- Define NormalizedContext as a Pydantic model only.
- No orchestration, no adapters, no providers, no rules.

Model Requirements:
- Scheduler-agnostic.
- Supports partial data (missing fields allowed).
- Supports replay mode (context is self-contained and serializable).
- Immutable/frozen.
- Bounded collections where applicable (static bounds only; dynamic enforcement is handled by collectors).

Placement (recommended):
- sentinelcore/core/context/models.py

Notes:
- This file contains only schema, defaults, and validation.
- No I/O, no command execution, no diagnosis.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Mapping, Optional

from pydantic import BaseModel, Field, ConfigDict


# ---------------------------------------------------------------------------
# Leaf models
# ---------------------------------------------------------------------------


class MetaContext(BaseModel):
    """Frozen v1 meta fields for a diagnosis context.

All fields are optional to support partial collection and replay fixtures.
Times are parsed as datetimes when provided.
"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    main_job_id: Optional[str] = None
    scheduler: Optional[str] = None
    cluster: Optional[str] = None
    user: Optional[str] = None

    stage: Optional[str] = None
    transfer_job_id: Optional[str] = None
    transfer_node: Optional[str] = None

    exec_hosts: Optional[List[str]] = None
    queue_or_partition: Optional[str] = None

    submit_time: Optional[datetime] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    term_reason: Optional[str] = None
    exit_code: Optional[int] = None


class LogsContext(BaseModel):
    """Frozen v1 log slots.

Each field is optional and expected to be already trimmed/bounded by collectors.
Values are plain text (string). Binary data is out of scope.
"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    dm_stagein: Optional[str] = None
    dm_stageout: Optional[str] = None
    dm_transcmd: Optional[str] = None
    ssh_debug: Optional[str] = None
    sbatchd: Optional[str] = None
    res: Optional[str] = None
    dmd: Optional[str] = None
    mbatchd: Optional[str] = None


class ArtifactsContext(BaseModel):
    """Frozen v1 artifacts grouping.

Artifacts are structured data products produced by adapters/providers.
They are treated as untrusted input and validated only structurally here.

All fields are optional to support partial collection.
"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    scheduler_metadata: Optional[Mapping[str, Any]] = None
    dm_transfer_info: Optional[Mapping[str, Any]] = None
    bdata_cache: Optional[Mapping[str, Any]] = None
    api_or_cli_outputs: Optional[Mapping[str, Any]] = None


class ProvenanceContext(BaseModel):
    """Frozen v1 provenance.

Used for explainability/replay:
- which providers ran
- warnings
- collection errors (rare)

Static bounds are applied to lists to keep payloads sane.
"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    evidence_providers_used: List[str] = Field(default_factory=list, max_length=200)
    warnings: List[str] = Field(default_factory=list, max_length=500)
    collection_errors: List[str] = Field(default_factory=list, max_length=200)


class ConstraintsContext(BaseModel):
    """Frozen v1 constraints that guided collection.

Collectors enforce the limits. This model stores the declared limits so
replay/explain can be consistent.
"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    max_lines_per_log: Optional[int] = None
    timeouts: Optional[Mapping[str, float]] = None
    redaction: Optional[Mapping[str, Any]] = None


# ---------------------------------------------------------------------------
# Root context model
# ---------------------------------------------------------------------------


class NormalizedContext(BaseModel):
    """Frozen v1 NormalizedContext.

High-level shape (frozen):
- meta
- logs
- artifacts
- provenance
- constraints

Supports partial data: all sections exist by default (empty or None).
"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: str = Field(default="v1")

    meta: MetaContext = Field(default_factory=MetaContext)
    logs: LogsContext = Field(default_factory=LogsContext)
    artifacts: ArtifactsContext = Field(default_factory=ArtifactsContext)
    provenance: ProvenanceContext = Field(default_factory=ProvenanceContext)
    constraints: ConstraintsContext = Field(default_factory=ConstraintsContext)


# Convenience type alias for contracts
NormalizedContextV1 = NormalizedContext

