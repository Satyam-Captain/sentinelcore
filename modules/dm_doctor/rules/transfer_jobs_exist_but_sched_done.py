# File: modules/dm_doctor/rules/transfer_jobs_exist_but_sched_done.py
"""STEP 9: DM-Doctor rule — Transfer jobs exist but scheduler job finished."""

from __future__ import annotations

from typing import Optional

from sentinelcore.core.contracts.base import Finding, NormalizedContextLike, Rule


class TransferJobsExistButSchedulerDoneRule(Rule):
    """Detect DM transfer jobs when scheduler job is finished.

    NOTE:
    - `meta.end_time` is used strictly as a proxy for scheduler completion
      (job finished), NOT scheduler success.
    """

    rule_id: str = "DM.TRANSFER.JOBS_EXIST_BUT_SCHED_DONE"

    def evaluate(self, context: NormalizedContextLike) -> Optional[Finding]:
        meta = context.meta
        

        # Scheduler finished = end_time present (completion proxy only)
        scheduler_finished = meta.end_time is not None
        if not scheduler_finished:
            return None

        provider_outputs = context.artifacts.api_or_cli_outputs or {}
        dm_artifacts = provider_outputs.get("dm_jobs_trace") or {}
        transfer_jobs = dm_artifacts.get("transfer_jobs") or []

        if not transfer_jobs:
            return None

        # No evidence of successful completion
        has_success = any(job.get("status") == "DONE" for job in transfer_jobs)
        if has_success:
            return None

        return Finding(
            rule_id=self.rule_id,
            title="Transfer jobs exist after scheduler finished",
            description=(
                "The scheduler job has completed, but Data Manager transfer jobs "
                "exist with no evidence of successful completion. This may indicate "
                "a Data Manager failure occurring after scheduler completion."
            ),
            severity="warn",
            confidence=0.6,
            specificity=0.5,
            suppressed_by=None,
            evidence={
                "scheduler_finished": True,
                "dm_transfer_job_count": len(transfer_jobs),
                "dm_transfer_success": False,
            },
            metadata={},
        )
