"""SentinelCore v0.1 — STEP 4: EvidenceProvider Base Infrastructure

AUTHORITATIVE SOURCE:
- “SentinelCore v0.1 – Architecture & Contracts Specification (DM-Engineer Handoff)”

Scope (STRICT):
- Define base infrastructure for EvidenceProviders.
- Enforce timeout handling semantics, partial failure, warnings, provider identity.

IMPORTANT TIMEOUT SEMANTICS (EXPLICIT):
- This base class enforces **cooperative (soft) timeouts only**.
- Blocking providers (I/O, network, subprocess) MUST enforce hard time limits internally.
- If the soft timeout is exceeded, collected artifacts are discarded.

Explicitly OUT OF SCOPE:
- DM logic
- SSH / SCP
- dm_jobs_trace
- Orchestration of multiple providers
- Knowledge of SchedulerAdapter
- Building NormalizedContext

This module creates the *collection substrate* only.
"""

from __future__ import annotations

import time
from abc import ABC
from typing import Any, Callable, List, Mapping, Optional

from sentinelcore.core.contracts.base import ExecutionMode, ProviderResult


# ---------------------------------------------------------------------------
# Exceptions (internal only)
# ---------------------------------------------------------------------------


class ProviderFatalError(Exception):
    """Internal exception for provider-fatal failures.

This exception MUST NOT escape to callers. It is caught and translated
into ProviderResult.errors by the base class.
"""


# ---------------------------------------------------------------------------
# EvidenceProvider Base
# ---------------------------------------------------------------------------


class EvidenceProviderBase(ABC):
    """Base class for all EvidenceProviders.

Responsibilities enforced by this base:
- Provider identity (mandatory)
- Cooperative timeout handling (soft timeout)
- Partial failure semantics
- Warning/error collection

Timeout model (EXPLICIT):
- `soft_timeout_s` is measured wall time for `_collect_impl`.
- If exceeded, artifacts are discarded and a warning is emitted.
- Hard timeouts MUST be enforced by subclasses when performing blocking I/O.

Subclasses MUST:
- Override `provider_id`
- Implement `_collect_impl()` only

Subclasses MUST NOT:
- Perform diagnosis
- Orchestrate other providers
- Access SchedulerAdapter
"""

    #: Cooperative timeout in seconds (soft timeout)
    soft_timeout_s: float = 10.0

    #: Stable provider identifier (MUST be overridden)
    provider_id: str = "base"

    def collect(
        self,
        *,
        job_id: str,
        context_seed: Mapping[str, Any],
        mode: ExecutionMode,
    ) -> ProviderResult:
        """Collect evidence with enforced safety guarantees.

        This wrapper enforces:
        - mandatory provider identity
        - cooperative timeout semantics
        - partial failure behavior
        - structured result shape
        """

        if self.provider_id == "base":
            raise NotImplementedError(
                "EvidenceProviderBase requires subclasses to override provider_id"
            )

        warnings: List[str] = []
        errors: List[str] = []
        artifacts: Mapping[str, Any] = {}

        start = time.monotonic()

        try:
            artifacts = (
                self._collect_impl(
                    job_id=job_id,
                    context_seed=context_seed,
                    mode=mode,
                    warnings=warnings,
                )
                or {}
            )
        except ProviderFatalError as e:
            errors.append(f"{self.provider_id}: {e}")
            artifacts = {}
        except Exception as e:
            warnings.append(f"{self.provider_id}: provider exception: {e}")
            artifacts = {}
        finally:
            elapsed = time.monotonic() - start
            if elapsed > self.soft_timeout_s:
                warnings.append(
                    f"{self.provider_id}: soft timeout exceeded ({elapsed:.2f}s > {self.soft_timeout_s:.2f}s); artifacts discarded"
                )
                artifacts = {}

        return ProviderResult(
            artifacts=artifacts,
            warnings=warnings,
            errors=errors,
        )

    # ------------------------------------------------------------------
    # Subclass contract
    # ------------------------------------------------------------------

    def _collect_impl(
        self,
        *,
        job_id: str,
        context_seed: Mapping[str, Any],
        mode: ExecutionMode,
        warnings: List[str],
    ) -> Optional[Mapping[str, Any]]:
        """Subclass implementation hook.

        Must return a mapping of artifacts or None.
        May append to `warnings`.

        IMPORTANT:
        - Must be cooperative with `soft_timeout_s`.
        - Blocking operations MUST enforce hard limits internally.
        - Must NOT raise uncaught exceptions.
        - Must NOT perform diagnosis.
        """

        raise NotImplementedError


# ---------------------------------------------------------------------------
# Helper utilities (best-effort only)
# ---------------------------------------------------------------------------


def bounded_call(
    *,
    func: Callable[[], Any],
    soft_timeout_s: float,
    warnings: List[str],
    label: str,
) -> Any:
    """Execute a callable with best-effort time bounding.

    WARNING:
    - This helper provides **no hard timeout guarantee**.
    - It is intended for short, cooperative operations only.
    - Providers performing blocking I/O MUST enforce hard limits themselves.
    """

    start = time.monotonic()
    try:
        return func()
    except Exception as e:
        warnings.append(f"{label} failed: {e}")
        return None
    finally:
        elapsed = time.monotonic() - start
        if elapsed > soft_timeout_s:
            warnings.append(f"{label} exceeded soft timeout ({elapsed:.2f}s)")

