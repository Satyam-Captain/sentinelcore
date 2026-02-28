# File: modules/dm_doctor/providers/dm_jobs_trace.py
"""STEP 5: dm_jobs_trace EvidenceProvider (DM-Doctor).

Scope:
- Subclasses EvidenceProviderBase.
- Executes: dm_jobs_trace <jobid> --format json
- Returns artifacts only.

Non-goals:
- No diagnosis, no semantic interpretation.
- No log parsing.
- No NormalizedContext building.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from typing import Any, Mapping, Optional

from sentinelcore.core.contracts.base import ExecutionMode
from sentinelcore.core.providers.base import EvidenceProviderBase, ProviderFatalError


@dataclass(frozen=True)
class DmJobsTraceLimits:
    """Static safety limits for dm_jobs_trace execution."""

    hard_timeout_s: float = 15.0
    max_stdout_chars: int = 2_000_000
    max_stderr_chars: int = 200_000


class DmJobsTraceProvider(EvidenceProviderBase):
    """Collect dm_jobs_trace output as untrusted JSON artifacts."""

    provider_id: str = "dm_jobs_trace"

    def __init__(
        self,
        *,
        dm_jobs_trace_path: str = "dm_jobs_trace",
        limits: Optional[DmJobsTraceLimits] = None,
        soft_timeout_s: float = 10.0,
    ) -> None:
        self._path = dm_jobs_trace_path
        self._limits = limits or DmJobsTraceLimits()
        # configure cooperative timeout from base
        self.soft_timeout_s = float(soft_timeout_s)

    def _collect_impl(
        self,
        *,
        job_id: str,
        context_seed: Mapping[str, Any],
        mode: ExecutionMode,
        warnings: list[str],
    ) -> Optional[Mapping[str, Any]]:
        # In replay mode, no external actions should happen.
        if mode == "replay":
            warnings.append("replay mode: dm_jobs_trace execution disabled")
            return {}

        cmd = [self._path, str(job_id), "--format", "json"]

        try:
            cp = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self._limits.hard_timeout_s,
                check=False,
                close_fds=True,
                env=None,
            )
        except subprocess.TimeoutExpired:
            warnings.append(f"dm_jobs_trace hard timeout after {self._limits.hard_timeout_s:.1f}s")
            return {}
        except OSError as e:
            warnings.append(f"dm_jobs_trace os error: {e}")
            return {}

        stdout = (cp.stdout or "")
        stderr = (cp.stderr or "")

        if len(stdout) > self._limits.max_stdout_chars:
            warnings.append("dm_jobs_trace stdout trimmed")
            stdout = stdout[: self._limits.max_stdout_chars]
        if len(stderr) > self._limits.max_stderr_chars:
            warnings.append("dm_jobs_trace stderr trimmed")
            stderr = stderr[: self._limits.max_stderr_chars]

        if cp.returncode != 0:
            # Treat as non-fatal collection failure.
            warnings.append(f"dm_jobs_trace non-zero exit ({cp.returncode})")
            if stderr:
                warnings.append(stderr)
            return {}

        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError:
            # Provider-fatal: tool promised JSON but did not deliver (still no raise outward)
            raise ProviderFatalError("dm_jobs_trace returned invalid JSON")

        # Artifacts only: store raw (but structured) JSON under a stable key.
        # No interpretation here.
        return payload
