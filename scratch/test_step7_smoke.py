"""
SentinelCore STEP 7 — Smoke Test

Purpose:
- Validate end-to-end plumbing:
  SchedulerAdapter → EvidenceProvider → ContextBuilder → RuleEngine

This is NOT a unit test.
This is NOT CI.
This is a manual developer smoke test.

Safe to delete anytime.
"""

from sentinelcore.adapters.lsf.scheduler_adapter import LsfSchedulerAdapter
from sentinelcore.modules.dm_doctor.providers.dm_jobs_trace import DmJobsTraceProvider
from sentinelcore.core.context.builder import DefaultContextBuilder
from sentinelcore.core.engine.rule_engine import DefaultRuleEngine


def main() -> None:
    JOB_ID = "7859311"  # change if needed
    DM_JOBS_TRACE_PATH = "/opt/lsf10/10.1/linux3.10-glibc2.17-x86_64/bin/dm_jobs_trace"

    print("=== SentinelCore STEP 7 Smoke Test ===\n")

    # ------------------------------------------------------------------
    # 1. Build Context
    # ------------------------------------------------------------------
    print("[1] Building context...")

    builder = DefaultContextBuilder(
        scheduler_adapter=LsfSchedulerAdapter(),
        providers=[
            DmJobsTraceProvider(
                dm_jobs_trace_path=DM_JOBS_TRACE_PATH
            )
        ],
    )

    context = builder.build(job_id=JOB_ID, mode="check")

    print("  Meta:")
    print("   - job_id:", context.meta.main_job_id)
    print("   - scheduler:", context.meta.scheduler)
    print("   - user:", context.meta.user)

    print("\n  Artifacts keys:")
    for k in context.artifacts.model_dump(exclude_none=True).keys():
        print("   -", k)

    print("\n  Provenance:")
    for w in context.provenance.warnings:
        print("   - warning:", w)
    for e in context.provenance.collection_errors:
        print("   - error:", e)

    # ------------------------------------------------------------------
    # 2. Run RuleEngine with NO rules
    # ------------------------------------------------------------------
    print("\n[2] Running RuleEngine with zero rules...")

    engine = DefaultRuleEngine(rules=[])

    result = engine.evaluate(context, mode="check")

    print("  Findings:", result.findings)
    print("  Rule provenance:", result.provenance)

    print("\n=== SMOKE TEST COMPLETE ===")


if __name__ == "__main__":
    main()
