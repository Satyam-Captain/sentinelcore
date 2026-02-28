# File: modules/dm_doctor/rules/no_transfer_jobs.py
"""STEP 8: Minimal DM-Doctor rule — No transfer jobs detected.

Purpose:
- Introduce minimal domain intelligence.
- Prove end-to-end pipeline correctness.

Constraints:
- Stateless, deterministic.
- Consumes NormalizedContext only.
- No fetching, no orchestration, no retries.
"""

from __future__ import annotations

from typing import Optional

from sentinelcore.core.contracts.base import Finding, NormalizedContextLike, Rule


class NoTransferJobsRule(Rule):
    """Detect absence of DM transfer activity for a job.

    Heuristic (minimal):
    - If dm_jobs_trace provider artifacts are absent or empty,
      suggest DM was not triggered or submission was incomplete.
    """

    rule_id: str = "DM.TRANSFER.NONE_FOUND"

    def evaluate(self, context: NormalizedContextLike) -> Optional[Finding]:
        # Artifacts are namespaced by provider under api_or_cli_outputs
        provider_outputs = context.artifacts.api_or_cli_outputs or {}
        dm_provider_artifacts = provider_outputs.get("dm_jobs_trace") or {}

        # If provider produced any payload, DM activity exists
        transfer_jobs = dm_provider_artifacts.get("transfer_jobs") or []
        if len(transfer_jobs) > 0:
            return None    

        # Construct a minimal, contract-compliant Finding
        return Finding(
            rule_id=self.rule_id,
            title="No Data Manager transfer jobs detected",
            description=(
                "No dm_jobs_trace artifacts were collected for this job. "
                "This suggests Data Manager transfers may not have been triggered "
                "or the submission did not include DM stages."
            ),
            severity="warn",
            confidence=0.6,
            specificity=0.5,
            suppressed_by=None,
            evidence={"dm_jobs_trace_present": False},
            metadata={},
        )
