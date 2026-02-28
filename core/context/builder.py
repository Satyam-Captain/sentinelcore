"""SentinelCore v0.1 — STEP 6: ContextBuilder

AUTHORITATIVE SOURCE:
- “SentinelCore v0.1 – Architecture & Contracts Specification (DM-Engineer Handoff)”

Goal:
- Combine exactly one SchedulerAdapter with multiple EvidenceProviders
- Build a NormalizedContext by orchestration only (plumbing)

Scope (STRICT):
- Instantiate ONE SchedulerAdapter (provided/injected)
- Invoke multiple EvidenceProviders in a defined order
- Merge artifacts without flattening provider namespaces
- Populate NormalizedContext: meta, artifacts, provenance
- Respect execution modes

Must NOT:
- Apply diagnosis
- Evaluate rules
- Render output
- Know DM semantics

ContextBuilder is plumbing only, not intelligence.
"""

from __future__ import annotations

from typing import Any, Iterable, List, Mapping, Dict

from sentinelcore.core.contracts.base import (
    ContextBuilder as ContextBuilderContract,
    ExecutionMode,
    SchedulerAdapter,
)
from sentinelcore.core.context.models import (
    NormalizedContext,
    MetaContext,
    ArtifactsContext,
    ProvenanceContext,
    ConstraintsContext,
)
from sentinelcore.core.providers.base import EvidenceProviderBase


class DefaultContextBuilder(ContextBuilderContract):
    """Default ContextBuilder implementation (v0.1).

    Performs orchestration only:
    - calls SchedulerAdapter
    - calls EvidenceProviders in explicit order
    - assembles NormalizedContext
    """

    def __init__(
        self,
        *,
        scheduler_adapter: SchedulerAdapter,
        providers: Iterable[EvidenceProviderBase],
    ) -> None:
        self._scheduler = scheduler_adapter
        # preserve explicit order
        self._providers = list(providers)

    def build(self, job_id: str, *, mode: ExecutionMode) -> NormalizedContext:
        # ------------------------------------------------------------------
        # Scheduler metadata (opaque, lossless)
        # ------------------------------------------------------------------
        try:
            scheduler_meta: Mapping[str, Any] = self._scheduler.get_job_metadata(
                job_id, mode=mode
            )
            scheduler_warning: str | None = None
        except Exception as e:
            # Defensive guardrail; adapter SHOULD NOT throw
            scheduler_meta = {}
            scheduler_warning = f"scheduler adapter error: {e}"

        # ------------------------------------------------------------------
        # Meta context (IDENTITY FIELDS ONLY — frozen by spec)
        # ------------------------------------------------------------------
        meta = MetaContext(
            main_job_id=str(job_id),
            scheduler=scheduler_meta.get("scheduler"),
            user=scheduler_meta.get("user"),
        )

        # ------------------------------------------------------------------
        # Evidence providers (explicit order)
        # ------------------------------------------------------------------
        artifacts_by_provider: Dict[str, Mapping[str, Any]] = {}
        provider_execution: List[Mapping[str, Any]] = []
        warnings: List[str] = []
        errors: List[str] = []

        # Context seed is owned by ContextBuilder
        context_seed: Mapping[str, Any] = {
            "scheduler_metadata": scheduler_meta,
            "meta": meta.model_dump(),
        }

        for idx, provider in enumerate(self._providers):
            result = provider.collect(
                job_id=job_id,
                context_seed=context_seed,
                mode=mode,
            )

            provider_execution.append(provider.provider_id)

            # Preserve provider namespace; no flattening
            artifacts_by_provider[provider.provider_id] = result.artifacts

            warnings.extend(result.warnings)
            errors.extend(result.errors)

        if scheduler_warning:
            warnings.insert(0, scheduler_warning)

        # ------------------------------------------------------------------
        # Assemble final context
        # ------------------------------------------------------------------
        return NormalizedContext(
            meta=meta,
            artifacts=ArtifactsContext(
                scheduler_metadata=scheduler_meta or None,
                api_or_cli_outputs=artifacts_by_provider or None,
            ),
            provenance=ProvenanceContext(
                evidence_providers_used=provider_execution,
                warnings=warnings,
                collection_errors=errors,
            ),
            constraints=ConstraintsContext(),
        )

