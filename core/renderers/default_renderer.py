# File: sentinelcore/core/renderers/default_renderer.py
"""
STEP 11: Default Renderer (formatting only)

Frozen signatures:
- render_text(context, eval_result, resolved, mode) -> str
- render_json(context, eval_result, resolved) -> dict

Renderer MUST:
- Accept already-built objects (NormalizedContext, RuleEvaluationResult, ResolvedDiagnosis)
- Produce deterministic text/JSON
- Always include: Primary / Secondary / Suppressed
- In mode="explain": include resolved.provenance (ranking + suppression reasons)

Renderer MUST NOT:
- Fetch data, run commands, call providers/engine/resolver
- Apply diagnosis logic
"""

from __future__ import annotations

import json
import pprint
from typing import Any, Mapping, Optional, Sequence

from sentinelcore.core.contracts.base import (
    ExecutionMode,
    Finding,
    NormalizedContextLike,
    RuleEvaluationResult,
)
from sentinelcore.core.engine.resolver import ResolvedDiagnosis


# ---------------------------------------------------------------------------
# Public API (frozen function signatures)
# ---------------------------------------------------------------------------

def render_text(
    context: NormalizedContextLike,
    eval_result: RuleEvaluationResult,
    resolved: ResolvedDiagnosis,
    mode: ExecutionMode,
) -> str:
    """Render human-readable text report (deterministic; formatting only)."""
    meta_map = _best_effort_meta(context)

    # MetaContext in v0.1 uses main_job_id
    job_id = meta_map.get("main_job_id") or meta_map.get("job_id") or "<unknown>"
    scheduler = meta_map.get("scheduler") or "<unknown>"
    user = meta_map.get("user") or "<unknown>"
    end_time = meta_map.get("end_time") or "<none>"

    lines: list[str] = []
    lines.append("=== SentinelCore Diagnose ===")
    lines.append("")
    lines.append("Context:")
    lines.append(f"  Job ID   : {job_id}")
    lines.append(f"  Scheduler: {scheduler}")
    lines.append(f"  User     : {user}")
    lines.append(f"  End Time (if known): {end_time}")
    lines.append("")

    # Required sections
    lines.extend(_render_primary(resolved.primary))
    lines.append("")
    lines.extend(_render_list("Secondary", list(resolved.secondary)))
    lines.append("")
    lines.extend(_render_list("Suppressed", list(resolved.suppressed), show_suppressed_by=True))

    if str(mode) == "explain":
        lines.append("")
        lines.append("Resolver provenance:")
        lines.append(_pretty_obj(dict(resolved.provenance)))

    return "\n".join(lines).rstrip() + "\n"


def render_json(
    context: NormalizedContextLike,
    eval_result: RuleEvaluationResult,
    resolved: ResolvedDiagnosis,
) -> dict[str, Any]:
    """Render JSON-serializable dict (formatting only)."""
    meta_map = _best_effort_meta(context)

    payload: dict[str, Any] = {
        "schema_version": getattr(context, "schema_version", None),
        "meta": {
            # explicit stable keys
            "main_job_id": meta_map.get("main_job_id"),
            "scheduler": meta_map.get("scheduler"),
            "cluster": meta_map.get("cluster"),
            "user": meta_map.get("user"),
            "submit_time": meta_map.get("submit_time"),
            "start_time": meta_map.get("start_time"),
            "end_time": meta_map.get("end_time"),
            "exit_code": meta_map.get("exit_code"),
        },
        "evaluation": {
            "findings": [_finding_to_dict(f) for f in (eval_result.findings or [])],
            "provenance": _to_jsonable(eval_result.provenance),
        },
        "resolved": {
            "primary": _finding_to_dict(resolved.primary) if resolved.primary else None,
            "secondary": [_finding_to_dict(f) for f in resolved.secondary],
            "suppressed": [_finding_to_dict(f) for f in resolved.suppressed],
            "provenance": _to_jsonable(resolved.provenance),
        },
    }
    return payload


# ---------------------------------------------------------------------------
# Helpers (private)
# ---------------------------------------------------------------------------

def _best_effort_meta(context: NormalizedContextLike) -> dict[str, Any]:
    """Extract meta safely; Protocol doesn’t guarantee .meta shape."""
    meta = getattr(context, "meta", None)
    if meta is None:
        return {}
    if hasattr(meta, "model_dump"):
        try:
            return dict(meta.model_dump())
        except Exception:
            return {}
    if isinstance(meta, dict):
        return dict(meta)
    return {}


def _finding_to_dict(f: Finding) -> dict[str, Any]:
    """Stable whitelist serialization for Finding (no vars())."""
    return {
        "rule_id": f.rule_id,
        "severity": f.severity,
        "confidence": f.confidence,
        "specificity": f.specificity,
        "title": f.title,
        "description": f.description,
        "suppressed_by": f.suppressed_by,
        "evidence": _to_jsonable(f.evidence),
        "metadata": _to_jsonable(f.metadata),
    }


def _render_primary(primary: Optional[Finding]) -> list[str]:
    lines = ["Primary:"]
    if primary is None:
        lines.append("  (none)")
        return lines
    lines.append(
        f"  {primary.rule_id} | severity={primary.severity} confidence={primary.confidence} specificity={primary.specificity}"
    )
    lines.append(f"  Title: {primary.title}")
    if primary.description:
        lines.append(f"  Desc : {primary.description}")
    return lines


def _render_list(title: str, findings: Sequence[Finding], *, show_suppressed_by: bool = False) -> list[str]:
    lines = [f"{title}:"]
    if not findings:
        lines.append("  (none)")
        return lines

    for f in findings:
        line = f"  {f.rule_id} | severity={f.severity} confidence={f.confidence} specificity={f.specificity}"
        if show_suppressed_by and f.suppressed_by:
            line += f" suppressed_by={f.suppressed_by}"
        lines.append(line)
        lines.append(f"    Title: {f.title}")
    return lines


def _pretty_obj(obj: Any) -> str:
    try:
        return pprint.pformat(obj, sort_dicts=True, width=120)
    except Exception:
        try:
            return json.dumps(_to_jsonable(obj), indent=2, sort_keys=True, default=str)
        except Exception:
            return "<unprintable>"


def _to_jsonable(obj: Any) -> Any:
    """Best-effort conversion to JSON-safe primitives."""
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, Mapping):
        return {str(k): _to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [_to_jsonable(v) for v in obj]
    if hasattr(obj, "model_dump"):
        try:
            return _to_jsonable(obj.model_dump())
        except Exception:
            return str(obj)
    return str(obj)
