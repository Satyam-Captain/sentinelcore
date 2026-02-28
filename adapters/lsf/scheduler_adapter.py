# File: adapters/lsf/scheduler_adapter.py
"""LSF SchedulerAdapter implementation (STEP 3).

Scope:
- Implements the SchedulerAdapter contract only.
- Returns structured, normalized scheduler metadata.

Non-goals (explicitly out of scope):
- DM logic, evidence providers, orchestration, rule evaluation.
"""



import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Mapping, Optional, Sequence

from core.contracts.base import CommandResult, ExecutionMode, SchedulerAdapter


@dataclass(frozen=True)
class LsfAdapterLimits:
    """Static safety bounds for command execution.

Collectors and context builders may enforce additional bounds.
"""

    timeout_s: float = 10.0
    max_stdout_chars: int = 500_000
    max_stderr_chars: int = 200_000


class LsfSchedulerAdapter(SchedulerAdapter):
    """Scheduler adapter for IBM Spectrum LSF.

This adapter translates scheduler-native command outputs into a normalized
structured mapping.

It MUST NOT:
- Perform diagnosis
- Parse DM logs
- Print to CLI
- Return raw command output from get_job_metadata
"""

    def __init__(self, *, limits: Optional[LsfAdapterLimits] = None, bjobs_path: str = "bjobs") -> None:
        self._limits = limits or LsfAdapterLimits()
        self._bjobs_path = bjobs_path

    @property
    def name(self) -> str:
        return "lsf"

    def run_command(self, args: Sequence[str], *, timeout_s: float, mode: ExecutionMode) -> CommandResult:
        # SchedulerAdapter may execute scheduler-native commands.
        # Caller is responsible for passing an appropriate timeout; we cap it
        # to adapter safety limits.
        if mode == "replay":
            return CommandResult(exit_code=125, stdout="", stderr="replay mode: command execution disabled")

        effective_timeout = min(timeout_s, self._limits.timeout_s)

        try:
            cp = subprocess.run(
                list(args),
                capture_output=True,
                text=True,
                timeout=effective_timeout,
                check=False,
                close_fds=True,
                env=None,
            )
        except subprocess.TimeoutExpired:
            return CommandResult(exit_code=124, stdout="", stderr=f"timeout after {effective_timeout:.1f}s")
        except OSError as e:
            return CommandResult(exit_code=126, stdout="", stderr=f"os error: {e}")

        stdout = (cp.stdout or "")
        stderr = (cp.stderr or "")

        if len(stdout) > self._limits.max_stdout_chars:
            stdout = stdout[: self._limits.max_stdout_chars]
        if len(stderr) > self._limits.max_stderr_chars:
            stderr = stderr[: self._limits.max_stderr_chars]

        return CommandResult(exit_code=int(cp.returncode), stdout=stdout, stderr=stderr)

    def get_job_metadata(self, job_id: str, *, mode: ExecutionMode) -> Mapping[str, Any]:
        """Return normalized scheduler metadata for an LSF job.

        This method never returns raw command output. It returns structured fields only.
        Any collection/parsing issues are reported via `adapter_warnings`.
        """

        warnings: list[str] = []

        # Prefer JSON output to avoid brittle text parsing.
        cmd = [self._bjobs_path, "-json", "-o", "jobid stat user exec_host queue submit_time start_time finish_time exit_code exit_reason", job_id]
        res = self.run_command(cmd, timeout_s=self._limits.timeout_s, mode=mode)

        if res.exit_code != 0:
            warnings.append(f"bjobs non-zero exit ({res.exit_code})")
            # Continue with empty payload. No exception.
            return {
                "scheduler": self.name,
                "job_id": str(job_id),
                "job_state": None,
                "user": None,
                "execution_hosts": None,
                "queue_or_partition": None,
                "submit_time": None,
                "start_time": None,
                "end_time": None,
                "exit_code": None,
                "term_reason": None,
                "adapter_warnings": warnings + ([res.stderr] if res.stderr else []),
            }

        job = _parse_bjobs_json_first_job(res.stdout, warnings)
        normalized = _normalize_job_dict(job, warnings)

        # Ensure essential identity fields.
        normalized.setdefault("scheduler", self.name)
        normalized.setdefault("job_id", str(job_id))

        

        return normalized


def _parse_bjobs_json_first_job(stdout: str, warnings: list[str]) -> Dict[str, Any]:
    """Parse LSF bjobs JSON and return the first job dictionary.

    Returns empty dict on parse failure.
    """

    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        warnings.append("failed to parse bjobs JSON")
        return {}

    # Common LSF JSON shape is expected to contain JOBS.
    jobs = payload.get("JOBS")
    if isinstance(jobs, list) and jobs:
        job = jobs[0]
        if isinstance(job, dict):
            return job

    # Some deployments may nest differently.
    warnings.append("bjobs JSON had no JOBS[0] entry")
    return {}


def _normalize_job_dict(job: Dict[str, Any], warnings: list[str]) -> Dict[str, Any]:
    """Normalize a bjobs job dict into scheduler-agnostic fields."""

    def pick(*keys: str) -> Any:
        for k in keys:
            if k in job:
                return job[k]
        return None

    stat = pick("STAT", "stat")
    user = pick("USER", "user")
    queue = pick("QUEUE", "queue")

    exec_host_raw = pick("EXEC_HOST", "exec_host")
    execution_hosts = _normalize_exec_hosts(exec_host_raw, warnings)

    submit_time = _normalize_time(pick("SUBMIT_TIME", "submit_time"), warnings)
    start_time = _normalize_time(pick("START_TIME", "start_time"), warnings)
    end_time = _normalize_time(pick("FINISH_TIME", "finish_time", "END_TIME", "end_time"), warnings)

    exit_code = _normalize_int(pick("EXIT_CODE", "exit_code"), warnings)
    exit_reason = pick("EXIT_REASON", "exit_reason")

    term_reason = _pass_through_exit_reason(exit_reason)

    return {
        "scheduler": "lsf",
        "job_state": stat,
        "user": user,
        "execution_hosts": execution_hosts,
        "queue_or_partition": queue,
        "submit_time": submit_time,
        "start_time": start_time,
        "end_time": end_time,
        "exit_code": exit_code,
        "term_reason_raw": term_reason,
    }


def _normalize_exec_hosts(value: Any, warnings: list[str]) -> Optional[list[str]]:
    """Normalize LSF exec host field into a list of hostnames.

    LSF formats vary; we do best-effort normalization without diagnosis.
    """

    if value is None:
        return None

    if isinstance(value, list):
        # Sometimes already tokenized.
        return [str(x) for x in value if x is not None]

    s = str(value).strip()
    if not s:
        return None

    # Typical exec_host looks like: "hostA*32 hostB*32" or "hostA".
    hosts: list[str] = []
    for tok in s.split():
        base = tok.split("*")[0].strip()
        if base:
            hosts.append(base)

    return hosts or None


def _normalize_int(value: Any, warnings: list[str]) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        warnings.append("exit_code not an int")
        return None


def _normalize_time(value: Any, warnings: list[str]) -> Optional[str]:
    """Normalize time-like fields.

    Returns ISO-8601 string in UTC when input looks like epoch seconds.
    Passes through ISO-like strings.
    """

    if value is None:
        return None

    # Epoch seconds.
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(float(value), tz=timezone.utc).isoformat()
        except (OverflowError, OSError, ValueError):
            warnings.append("invalid epoch time")
            return None

    s = str(value).strip()
    if not s:
        return None

    # If it's already a date-like string, keep it as-is.
    return s


# NOTE: Adapters must not perform diagnosis or semantic interpretation.
# Termination reason is exposed losslessly for rules to interpret later.


def _pass_through_exit_reason(exit_reason: Any) -> Optional[str]:
    if exit_reason is None:
        return None
    s = str(exit_reason).strip()
    return s or None

