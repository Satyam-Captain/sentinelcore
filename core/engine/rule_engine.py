"""SentinelCore v0.1 — STEP 7: RuleEngine skeleton

PLAIN PYTHON ONLY.
- No markdown.
- No backticks.
- Deterministic evaluation (rule order preserved).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, List, Mapping

from sentinelcore.core.contracts.base import (
    ExecutionMode,
    Finding,
    NormalizedContextLike,
    Rule,
    RuleEngine,
    RuleEvaluationResult,
)


@dataclass(frozen=True)
class RuleEngineConfig:
    """Configuration for DefaultRuleEngine.

    continue_on_rule_error:
        If True, rule exceptions are recorded in provenance and
        evaluation continues with the next rule.
    """

    continue_on_rule_error: bool = True


class DefaultRuleEngine(RuleEngine):
    """Deterministic, scheduler-agnostic RuleEngine skeleton.

    Responsibilities:
    - Iterate rules in provided order
    - Evaluate each rule against NormalizedContextLike
    - Collect non-None Finding objects
    - Shield rule errors and record provenance

    Out of scope:
    - Ranking/suppression
    - Domain semantics (DM)
    - Any fetching or I/O
    """

    def __init__(
        self,
        *,
        rules: Iterable[Rule],
        config: RuleEngineConfig | None = None,
    ) -> None:
        self._rules: List[Rule] = list(rules)
        self._config: RuleEngineConfig = config or RuleEngineConfig()

    def evaluate(
        self,
        context: NormalizedContextLike,
        *,
        mode: ExecutionMode,
    ) -> RuleEvaluationResult:
        """Evaluate rules against a normalized context.

        Provenance keys:
        - mode: execution mode
        - rules_evaluated: ordered list of rule identifiers
        - rule_errors: list of rule execution errors (if any)
        """
        findings: List[Finding] = []
        rule_errors: List[Mapping[str, Any]] = []
        rules_evaluated: List[str] = []

        for index, rule in enumerate(self._rules):
            rule_id = getattr(rule, "rule_id", f"<unknown:{index}>")
            rules_evaluated.append(rule_id)

            try:
                finding = rule.evaluate(context)
            except Exception as exc:
                if not self._config.continue_on_rule_error:
                    raise
                rule_errors.append(
                    {
                        "index": index,
                        "rule_id": rule_id,
                        "error": str(exc),
                    }
                )
                continue

            if finding is not None:
                findings.append(finding)

        provenance: Mapping[str, Any] = {
            "mode": mode,
            "rules_evaluated": rules_evaluated,
            "rule_errors": rule_errors,
        }

        return RuleEvaluationResult(findings=findings, provenance=provenance)
