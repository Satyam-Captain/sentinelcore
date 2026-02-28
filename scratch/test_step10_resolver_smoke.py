"""SentinelCore STEP 10 — FindingResolver smoke test.

Goal:
- Create a small set of Findings with different severities/confidence/specificity
- Include one suppressed finding (suppressed_by points to an existing finding)
- Run FindingResolver and print primary/secondary/suppressed + provenance

This is a manual smoke test.
Safe to delete anytime.
"""

from __future__ import annotations

from sentinelcore.core.contracts.base import Finding
from sentinelcore.core.engine.resolver import FindingResolver


def main() -> None:
    resolver = FindingResolver()

    findings = [
        Finding(
            rule_id="DM.STAGEOUT.MISSING",
            title="Stage-out transfer job missing",
            description="dm_jobs_trace shows transfer jobs but no STAGE-OUT job type.",
            severity="error",
            confidence=0.7,
            specificity=0.6,
            suppressed_by=None,
            evidence={"stageout_present": False, "transfer_job_count": 3},
            metadata={},
        ),
        Finding(
            rule_id="DM.TRANSFER.NONE_FOUND",
            title="No DM transfer jobs detected",
            description="No dm_jobs_trace transfer jobs found for this job.",
            severity="warn",
            confidence=0.6,
            specificity=0.5,
            suppressed_by=None,
            evidence={"dm_jobs_trace_present": True, "transfer_job_count": 0},
            metadata={},
        ),
        Finding(
            rule_id="DM.TRANSFER.JOBS_EXIST_BUT_SCHED_DONE",
            title="Transfer jobs exist after scheduler finished",
            description="Scheduler appears finished but transfer jobs still exist with no success evidence.",
            severity="warn",
            confidence=0.6,
            specificity=0.5,
            suppressed_by="DM.STAGEOUT.MISSING",  # suppressed because suppressor exists
            evidence={"scheduler_finished": True, "transfer_job_count": 2, "has_success": False},
            metadata={},
        ),
    ]

    resolved = resolver.resolve(findings)

    print("=== SentinelCore STEP 10 Resolver Smoke Test ===\n")

    print("Primary:")
    if resolved.primary is None:
        print("  None")
    else:
        f = resolved.primary
        print(f"  {f.rule_id} | severity={f.severity} confidence={f.confidence} specificity={f.specificity}")

    print("\nSecondary:")
    if not resolved.secondary:
        print("  (none)")
    else:
        for f in resolved.secondary:
            print(f"  {f.rule_id} | severity={f.severity} confidence={f.confidence} specificity={f.specificity}")

    print("\nSuppressed:")
    if not resolved.suppressed:
        print("  (none)")
    else:
        for f in resolved.suppressed:
            print(
                f"  {f.rule_id} suppressed_by={f.suppressed_by} | "
                f"severity={f.severity} confidence={f.confidence} specificity={f.specificity}"
            )

    print("\nProvenance:")
    print(dict(resolved.provenance))

    print("\n=== STEP 10 SMOKE TEST COMPLETE ===")


if __name__ == "__main__":
    main()
