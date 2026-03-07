"""
SLA indicator computation for Cases.

Provides visual SLA status indicators (green/yellow/red) based on
elapsed time vs. configured SLA hours.
"""


def compute_sla_indicator(sla_hours, elapsed_hours):
    """
    Compute SLA indicator based on elapsed time vs. target.

    Returns:
        "green"  — < 75% of SLA consumed
        "yellow" — 75-100% of SLA consumed
        "red"    — >= 100% of SLA consumed (breached)
    """
    if sla_hours <= 0:
        return "green"

    ratio = elapsed_hours / sla_hours

    if ratio >= 1.0:
        return "red"
    elif ratio >= 0.75:
        return "yellow"
    return "green"


def compute_case_sla_indicators(case):
    """
    Compute SLA indicators for a Case instance.

    Returns dict with first_response and resolution indicators.
    """
    from django.utils import timezone
    from datetime import timedelta

    now = timezone.now()
    result = {
        "first_response_indicator": "green",
        "resolution_indicator": "green",
        "first_response_elapsed_hours": None,
        "resolution_elapsed_hours": None,
    }

    if not case.created_at:
        return result

    # First response SLA
    if case.first_response_at:
        elapsed = (case.first_response_at - case.created_at).total_seconds() / 3600
    else:
        elapsed = (now - case.created_at).total_seconds() / 3600

    result["first_response_elapsed_hours"] = round(elapsed, 2)
    result["first_response_indicator"] = compute_sla_indicator(
        case.sla_first_response_hours, elapsed
    )

    # Resolution SLA
    if case.resolved_at:
        elapsed = (case.resolved_at - case.created_at).total_seconds() / 3600
    else:
        elapsed = (now - case.created_at).total_seconds() / 3600

    result["resolution_elapsed_hours"] = round(elapsed, 2)
    result["resolution_indicator"] = compute_sla_indicator(
        case.sla_resolution_hours, elapsed
    )

    return result
