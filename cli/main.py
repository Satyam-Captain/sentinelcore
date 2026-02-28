# File: sentinelcore/cli/main.py
"""SentinelCore CLI (STEP 11).

Entrypoint:
  sentinelcore diagnose <JOB_ID>

Pipeline (FROZEN):
  Adapter -> Providers -> ContextBuilder -> RuleEngine -> Resolver -> Renderer

NOTE (v0.1 scope):
- This CLI wires ONLY the DM-Doctor pipeline on LSF (hard-coded adapter/providers/rules).
- Scheduler/module plugin registries come in later steps.
"""


from __future__ import annotations

import argparse
import json
import sys
from typing import Sequence

from sentinelcore.adapters.lsf.scheduler_adapter import LsfSchedulerAdapter
from sentinelcore.core.context.builder import DefaultContextBuilder
from sentinelcore.core.engine import DefaultRuleEngine
from sentinelcore.core.engine.resolver import FindingResolver
from sentinelcore.core.renderers import render_json, render_text
from sentinelcore.modules.dm_doctor.providers.dm_jobs_trace import DmJobsTraceProvider
from sentinelcore.modules.dm_doctor.rules.no_transfer_jobs import NoTransferJobsRule
from sentinelcore.modules.dm_doctor.rules.stageout_missing import StageOutMissingRule
from sentinelcore.modules.dm_doctor.rules.transfer_jobs_exist_but_sched_done import (
    TransferJobsExistButSchedulerDoneRule,
)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
    prog="sentinelcore",
    description="SentinelCore diagnostics CLI (v0.1: DM-Doctor on LSF)",
    )

    sub = p.add_subparsers(dest="command", required=True)

    d = sub.add_parser("diagnose", help="Diagnose a scheduler job")
    d.add_argument("job_id", help="Scheduler job id")
    d.add_argument("--mode", choices=["check", "collect", "replay", "explain"], default="check")
    d.add_argument("--format", choices=["text", "json"], default="text")
    d.add_argument("--dm-jobs-trace-path", default="dm_jobs_trace", help="Path to dm_jobs_trace executable")

    return p


def _cmd_diagnose(args: argparse.Namespace) -> int:
    mode = args.mode
    out_format = args.format

    # 1) Adapter
    scheduler = LsfSchedulerAdapter()

    # 2) Providers (explicit order)
    providers = [
        DmJobsTraceProvider(dm_jobs_trace_path=args.dm_jobs_trace_path),
    ]

    # 3) ContextBuilder
    builder = DefaultContextBuilder(
        scheduler_adapter=scheduler,
        providers=providers,
    )
    context = builder.build(job_id=str(args.job_id), mode=mode)

    # 4) Rules (explicit order)
    rules = [
        NoTransferJobsRule(),
        StageOutMissingRule(),
        TransferJobsExistButSchedulerDoneRule(),
    ]

    # 5) RuleEngine
    engine = DefaultRuleEngine(rules=rules)
    eval_result = engine.evaluate(context, mode=mode)

    # 6) Resolver
    resolver = FindingResolver()
    resolved = resolver.resolve(eval_result.findings or [])

    # 7) Renderer (formatting only)
    if out_format == "json":
        payload = render_json(context, eval_result, resolved)
        sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n")
    else:
        sys.stdout.write(render_text(context, eval_result, resolved, mode))

    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "diagnose":
        return _cmd_diagnose(args)

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
