"""
Deterministic risk classifier for AI assistant actions.

Classifies the risk level of proposed tool executions based on
tool type, parameters, and organizational context.

Risk levels:
  - none: Read-only operations (search, list, preview)
  - low: Creates drafts/inactive resources
  - medium: Activates resources, modifies state
  - high: External dispatch, campaign scheduling, bulk operations

Returns: (risk_level, reason) tuple
"""

import logging

logger = logging.getLogger(__name__)

RISK_LEVELS = ("none", "low", "medium", "high")

# External-facing channels that carry higher risk
EXTERNAL_CHANNELS = ("smtp_native", "talkhub_omni", "whatsapp")


def classify_risk(tool_name, params, org=None):
    """
    Classify the risk of a tool execution.

    Args:
        tool_name: Name from TOOL_REGISTRY
        params: Parameters that will be passed to the tool
        org: Organization instance (optional, for org-specific thresholds)

    Returns:
        tuple: (risk_level: str, reason: str | None)
    """
    from assistant.tools import TOOL_REGISTRY

    tool = TOOL_REGISTRY.get(tool_name)
    if not tool:
        return "high", f"Ferramenta desconhecida: {tool_name}"

    base_risk = tool.get("risk", "low")

    # Escalation rules
    escalation_reason = None

    # Rule 1: Campaign scheduling with many recipients
    if tool_name == "create_campaign_draft":
        return "medium", "Campanhas requerem revisão antes do envio"

    # Rule 2: External channel dispatch
    channel_type = params.get("channel_config", {}).get("channel_type", "")
    if not channel_type:
        channel_type = params.get("channel_type", "")

    if channel_type in EXTERNAL_CHANNELS:
        if _risk_index(base_risk) < _risk_index("medium"):
            base_risk = "medium"
            escalation_reason = f"Canal externo ({channel_type}) eleva risco"

    # Rule 3: Activating a policy that targets many entities
    if tool_name == "activate_policy":
        target_count = params.get("estimated_targets", 0)
        if target_count > 50:
            base_risk = "high"
            escalation_reason = f"Ativação afeta {target_count} entidades"

    # Rule 4: Bulk operations
    if params.get("bulk", False) or params.get("count", 0) > 20:
        if _risk_index(base_risk) < _risk_index("medium"):
            base_risk = "medium"
            escalation_reason = "Operação em lote"

    return base_risk, escalation_reason


def requires_user_approval(tool_name, params, org=None):
    """
    Determine if a tool execution requires explicit user approval.

    All high-risk and some medium-risk operations require approval.
    """
    risk_level, reason = classify_risk(tool_name, params, org)

    from assistant.tools import TOOL_REGISTRY
    tool = TOOL_REGISTRY.get(tool_name, {})

    # Tool-level override
    if tool.get("requires_approval", False):
        return True, reason or "Ferramenta requer aprovação"

    # Risk-level based
    if risk_level == "high":
        return True, reason or "Operação de alto risco"

    return False, None


def _risk_index(level):
    """Convert risk level to numeric index for comparison."""
    try:
        return RISK_LEVELS.index(level)
    except ValueError:
        return 0
