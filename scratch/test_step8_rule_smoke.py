"""
SentinelCore STEP 8 — Rule Smoke Test

Purpose:
- Validate that a DM rule fires correctly
- End-to-end: Adapter → Provider → ContextBuilder → RuleEngine → Finding

This is a manual smoke test.
Safe to delete anytime.
"""

from sentinelcore.adapters.lsf.scheduler_adapter import LsfSchedulerAdapter
from sentinelcore.modules.dm_doctor.providers.dm_jobs_trace import DmJobsTraceProvider
from sentinelcore.modules.dm_doctor.rules.no_transfer_jobs import NoTransferJobsRule
from sentinelcore.core.context.builder import DefaultContextBuilder
from sentinelcore.core.engine.rule_engine import DefaultRuleEngine


def main() -> None:
    JOB_ID = "7859311"  # job with DM evidence (adjust if needed)
    DM_JOBS_TRACE_PATH = "/opt/lsf10/10.1/linux3.10-glibc2.17-x86_64/bin/dm_jobs_trace"

    print("=== SentinelCore STEP 8 Rule Smoke Test ===\n")

    # ------------------------------------------------------------------
    # 1. Build context
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

    print("  Context built.")
    print("  DM provider artifacts present:",
          bool(
              context.artifacts.api_or_cli_outputs
              and context.artifacts.api_or_cli_outputs.get("dm_jobs_trace")
          ))

    # ------------------------------------------------------------------
    # 2. Run RuleEngine with ONE rule
    # ------------------------------------------------------------------
    print("\n[2] Running RuleEngine with NoTransferJobsRule...")

    engine = DefaultRuleEngine(
        rules=[NoTransferJobsRule()]
    )

    result = engine.evaluate(context, mode="check")

    # ------------------------------------------------------------------
    # 3. Inspect findings
    # ------------------------------------------------------------------
    print("\n[3] Findings:")
    if not result.findings:
        print("  No findings produced.")
    else:
        for f in result.findings:
            print("  - Rule ID:", f.rule_id)
            print("    Title:", f.title)
            print("    Severity:", f.severity)
            print("    Confidence:", f.confidence)
            print("    Evidence:", f.evidence)

    print("\nRule provenance:", result.provenance)
    print("\n=== STEP 8 SMOKE TEST COMPLETE ===")


if __name__ == "__main__":
    main()
