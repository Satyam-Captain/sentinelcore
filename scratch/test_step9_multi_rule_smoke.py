"""
SentinelCore STEP 9 — Multi-rule overlap smoke test

Goal:
- Build a real NormalizedContext
- Run all DM rules together
- Observe overlapping findings
- No ranking, no suppression
"""

from sentinelcore.adapters.lsf.scheduler_adapter import LsfSchedulerAdapter
from sentinelcore.core.context.builder import DefaultContextBuilder
from sentinelcore.core.engine.rule_engine import DefaultRuleEngine
from sentinelcore.modules.dm_doctor.providers.dm_jobs_trace import DmJobsTraceProvider

from sentinelcore.modules.dm_doctor.rules.no_transfer_jobs import NoTransferJobsRule
from sentinelcore.modules.dm_doctor.rules.stageout_missing import StageOutMissingRule
from sentinelcore.modules.dm_doctor.rules.transfer_jobs_exist_but_sched_done import (
    TransferJobsExistButSchedulerDoneRule,
)

JOB_ID = "7859311"   # adjust if needed


def main():
    print("=== SentinelCore STEP 9 Multi-Rule Smoke Test ===\n")

    # ------------------------------------------------------------------
    # Build context
    # ------------------------------------------------------------------
    print("[1] Building NormalizedContext...")

    scheduler = LsfSchedulerAdapter()
    providers = [
        DmJobsTraceProvider(
            dm_jobs_trace_path="/opt/lsf10/10.1/linux3.10-glibc2.17-x86_64/bin/dm_jobs_trace"
        )
    ]

    builder = DefaultContextBuilder(
        scheduler_adapter=scheduler,
        providers=providers,
    )

    context = builder.build(job_id=JOB_ID, mode="check")

    print("  Context built.")
    print("  Scheduler:", context.meta.scheduler)
    print("  Job end_time:", context.meta.end_time)
    print("  DM transfer jobs:",
          len(
              context.artifacts.api_or_cli_outputs
              .get("dm_jobs_trace", {})
              .get("transfer_jobs", [])
          ))
    print()

    # ------------------------------------------------------------------
    # Run rules
    # ------------------------------------------------------------------
    print("[2] Running RuleEngine with STEP 9 rules...\n")

    rules = [
        NoTransferJobsRule(),
        StageOutMissingRule(),
        TransferJobsExistButSchedulerDoneRule(),
    ]

    engine = DefaultRuleEngine(rules=rules)
    result = engine.evaluate(context, mode="check")

    # ------------------------------------------------------------------
    # Display findings
    # ------------------------------------------------------------------
    print("[3] Findings:\n")

    if not result.findings:
        print("  No findings produced.")
    else:
        for idx, finding in enumerate(result.findings, start=1):
            print(f"  [{idx}] {finding.rule_id}")
            print(f"      Severity   : {finding.severity}")
            print(f"      Confidence : {finding.confidence}")
            print(f"      Specificity: {finding.specificity}")
            print(f"      Title      : {finding.title}")
            print()

    print("Rule provenance:")
    print(result.provenance)

    print("\n=== STEP 9 SMOKE TEST COMPLETE ===")


if __name__ == "__main__":
    main()
