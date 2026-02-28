"""Finding resolution layer (STEP 10).

This module is a pure, deterministic post-processing step:
- Input: a list of Finding objects (unordered)
- Output: a ResolvedDiagnosis (primary/secondary/suppressed) + provenance

It MUST NOT:
- fetch evidence
- modify RuleEngine behavior
- introduce heuristics/ML
- change Finding schema

Frozen behavior (v0.1):
- Ranking (deterministic):
    1) severity (critical > error > warn > info)
    2) confidence (desc)
    3) specificity (desc)
    4) rule_id (asc)  # stable tie-break
- Suppression (minimal):
    If a finding has `suppressed_by` set AND that suppressor rule_id exists among
    the input findings, then the *suppressed finding* (the one with suppressed_by)
    is moved to the suppressed list.

The resolver is scheduler-agnostic and module-agnostic.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from sentinelcore.core.contracts.base import Finding


_SEVERITY_RANK: Mapping[str, int] = {
    "critical": 4,
    "error": 3,
    "warn": 2,
    "info": 1,
}


@dataclass(frozen=True)
class ResolvedDiagnosis:
    """Resolved diagnosis output for downstream renderers."""

    primary: Finding | None
    secondary: list[Finding]
    suppressed: list[Finding]
    provenance: Mapping[str, Any]


class FindingResolver:
    """Deterministically rank and optionally suppress findings."""

    def resolve(self, findings: Sequence[Finding]) -> ResolvedDiagnosis:
        findings_list = list(findings or [])

        # For suppression checks we only need to know which rule_ids are present.
        present_rule_ids = {f.rule_id for f in findings_list}

        suppressed_findings: list[Finding] = []
        remaining_findings: list[Finding] = []

        # Suppression (minimal v0.1):
        # Suppress the suppressed finding (the one that has `suppressed_by` set),
        # not the suppressor.
        for f in findings_list:
            suppressor_rule_id = getattr(f, "suppressed_by", None)
            if suppressor_rule_id is not None and suppressor_rule_id in present_rule_ids:
                suppressed_findings.append(f)
            else:
                remaining_findings.append(f)

        ranked_remaining = sorted(remaining_findings, key=_ranking_key)
        ranked_suppressed = sorted(suppressed_findings, key=_ranking_key)

        primary = ranked_remaining[0] if ranked_remaining else None
        secondary = ranked_remaining[1:] if len(ranked_remaining) > 1 else []

        provenance: dict[str, Any] = {
            "ranking": {
                "sort": [
                    "severity_desc(critical>error>warn>info)",
                    "confidence_desc",
                    "specificity_desc",
                    "rule_id_asc",
                ],
                "severity_rank_map": dict(_SEVERITY_RANK),
            },
            "suppression": {
                "policy": "if suppressed_by exists in findings -> suppress that finding",
                "present_rule_ids": sorted(present_rule_ids),
                "suppressed_rule_ids": [f.rule_id for f in ranked_suppressed],
            },
            "counts": {
                "input": len(findings_list),
                "remaining": len(ranked_remaining),
                "suppressed": len(ranked_suppressed),
            },
        }

        return ResolvedDiagnosis(
            primary=primary,
            secondary=secondary, 
            suppressed=ranked_suppressed, 
            provenance=MappingProxyType(provenance),
        )


def _ranking_key(f: Finding) -> tuple[int, float, float, str]:
    """Compute deterministic ranking key.

    Higher severity/confidence/specificity should come first.
    We implement this by sorting ascending on negative values.
    """

    severity = str(getattr(f, "severity", "info") or "info").lower()
    sev_rank = _SEVERITY_RANK.get(severity, 0)

    confidence = float(getattr(f, "confidence", 0.0) or 0.0)
    specificity = float(getattr(f, "specificity", 0.0) or 0.0)

    rule_id = str(getattr(f, "rule_id", "") or "")

    return (-sev_rank, -confidence, -specificity, rule_id)
