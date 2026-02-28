# File: modules/dm_doctor/rules/stageout_missing.py
"""STEP 9: DM-Doctor rule — Stage-out missing.

Conditions:
- dm_jobs_trace artifacts exist
- transfer jobs present
- no job_type == "STAGE-OUT"
"""

from __future__ import annotations

from typing import Optional

from sentinelcore.core.contracts.base import Finding, NormalizedContextLike, Rule


class StageOutMissingRule(Rule):
    """Detect missing stage-out transfer jobs."""

    rule_id: str = "DM.STAGEOUT.MISSING"

    def evaluate(self, context: NormalizedContextLike) -> Optional[Finding]:
        provider_outputs = context.artifacts.api_or_cli_outputs or {}
        dm_artifacts = provider_outputs.get("dm_jobs_trace") or {}

        if not dm_artifacts:
            return None

        transfer_jobs = dm_artifacts.get("transfer_jobs") or []
        if not transfer_jobs:
            return None

        has_stageout = any(job.get("job_type") == "STAGE-OUT" for job in transfer_jobs)
        if has_stageout:
            return None

        return Finding(
            rule_id=self.rule_id,
            title="Stage-out transfer jobs missing",
            description=(
                "Data Manager transfer jobs were detected, but no STAGE-OUT jobs "
                "were found. This suggests stage-out may not have been executed."
            ),
            severity="error",
            confidence=0.7,
            specificity=0.6,
            suppressed_by=None,
            evidence={"stageout_present": False},
            metadata={},
        )


