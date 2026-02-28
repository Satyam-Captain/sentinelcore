# File: scratch/test_step11_cli_smoke.py
"""STEP 11 CLI smoke test.

Usage:
  python -m scratch.test_step11_cli_smoke

Env overrides:
  JOB_ID
  DM_JOBS_TRACE_PATH
"""

from __future__ import annotations

import io
import os
from contextlib import redirect_stdout

from sentinelcore.cli.main import main as cli_main


def main() -> None:
    job_id = os.environ.get("JOB_ID", "7859311")
    dm_path = os.environ.get(
        "DM_JOBS_TRACE_PATH",
        "/opt/lsf10/10.1/linux3.10-glibc2.17-x86_64/bin/dm_jobs_trace",
    )

    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = cli_main(
            [
                "diagnose",
                job_id,
                "--mode",
                "explain",
                "--format",
                "text",
                "--dm-jobs-trace-path",
                dm_path,
            ]
        )

    out = buf.getvalue()

    assert rc == 0, f"expected rc=0, got {rc}"
    assert "Primary:" in out
    assert "Secondary:" in out
    assert "Suppressed:" in out
    assert "Resolver provenance:" in out

    print("=== STEP 11 CLI SMOKE TEST PASS ===")


if __name__ == "__main__":
    main()
