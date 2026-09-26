from pipelineiq.contracts import (
    PolicyAction,
    RiskAssessment,
    RiskBand,
    RiskFactor,
    RiskProfile,
    RiskSignals,
)


def assess_risk(signals: RiskSignals, profile: RiskProfile) -> RiskAssessment:
    """Produce a deterministic, explainable risk score from pipeline signals."""
    factors: list[RiskFactor] = []

    def add(name: str, points: int, reason: str) -> None:
        if points:
            factors.append(RiskFactor(name=name, points=points, reason=reason))

    add("failed_tests", 20 if signals.tests_failed else 0, "The pipeline contains failed tests.")
    add(
        "production_branch",
        25 if signals.branch == profile.production_branch else 0,
        f"The change targets the protected {profile.production_branch!r} branch.",
    )
    add(
        "change_size",
        min(20, signals.lines_changed // 50),
        f"The change modifies {signals.lines_changed} lines.",
    )
    add(
        "file_count",
        min(10, signals.files_changed // 3),
        f"The change spans {signals.files_changed} files.",
    )
    add(
        "sensitive_files",
        25 if signals.touches_sensitive_files else 0,
        "Security, deployment, or dependency files are affected.",
    )
    add(
        "missing_review",
        10 if not signals.has_required_review else 0,
        "The change has no required review approval.",
    )
    add(
        "repeat_failure",
        min(10, signals.prior_similar_failures * 2),
        f"There are {signals.prior_similar_failures} similar prior failures.",
    )

    score = min(100, sum(factor.points for factor in factors))
    band = RiskBand.LOW if score < 30 else RiskBand.MEDIUM if score < 60 else RiskBand.HIGH

    if score < profile.auto_fix_below:
        action = PolicyAction.AUTO_FIX
    elif score < profile.require_approval_above:
        action = PolicyAction.APPROVAL_REQUIRED
    else:
        action = PolicyAction.BLOCK_ONLY

    return RiskAssessment(score=score, band=band, action=action, factors=factors)

