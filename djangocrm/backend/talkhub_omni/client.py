"""
TalkHub Omni API Client — httpx-based with retry + exponential backoff.

Base URL: https://chat.talkhub.me/api
Auth: Bearer token (API Key per organization/channel).
"""

import logging
import time
from typing import Any

import httpx

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 30
MAX_RETRIES = 3
BACKOFF_BASE = 2  # seconds


class TalkHubAPIError(Exception):
    """Raised when the TalkHub API returns a non-2xx response."""

    def __init__(self, message, status_code=None, response_data=None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data


class TalkHubClient:
    """Async-capable HTTP client for the TalkHub Omni API with retry."""

    def __init__(self, api_key: str, base_url: str = "https://chat.talkhub.me"):
        self.base_url = base_url.rstrip("/")
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    # ─── Internal helpers ─────────────────────────────────────────────

    def _request(self, method: str, path: str, **kwargs) -> Any:
        """Execute HTTP request with retry + exponential backoff."""
        url = f"{self.base_url}/api{path}"
        kwargs.setdefault("timeout", DEFAULT_TIMEOUT)

        last_exc = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                with httpx.Client(headers=self._headers) as client:
                    resp = client.request(method, url, **kwargs)
                    resp.raise_for_status()
                    if resp.status_code == 204:
                        return {}
                    return resp.json()
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                body = {}
                try:
                    body = exc.response.json()
                except Exception:
                    pass
                # Don't retry 4xx (client errors) except 429
                if 400 <= status < 500 and status != 429:
                    msg = body.get("message") or body.get("error") or str(exc)
                    raise TalkHubAPIError(msg, status_code=status, response_data=body) from exc
                last_exc = TalkHubAPIError(
                    body.get("message") or str(exc),
                    status_code=status, response_data=body,
                )
            except (httpx.ConnectError, httpx.TimeoutException, httpx.ReadTimeout) as exc:
                last_exc = TalkHubAPIError(f"Connection error: {exc}")

            if attempt < MAX_RETRIES:
                wait = BACKOFF_BASE ** (attempt + 1)
                logger.warning(
                    "TalkHub API retry %d/%d for %s %s (wait=%ds)",
                    attempt + 1, MAX_RETRIES, method, path, wait,
                )
                time.sleep(wait)

        raise last_exc

    def _get(self, path, **kw):
        return self._request("GET", path, **kw)

    def _post(self, path, **kw):
        return self._request("POST", path, **kw)

    def _put(self, path, **kw):
        return self._request("PUT", path, **kw)

    def _delete(self, path, **kw):
        return self._request("DELETE", path, **kw)

    def _patch(self, path, **kw):
        return self._request("PATCH", path, **kw)

    # ─── Module 1: Workspace / Connection ─────────────────────────────

    def get_me(self):
        """GET /me — current bot/workspace info."""
        return self._get("/me")

    def get_team_info(self):
        """GET /team-info — workspace details (validates API key)."""
        return self._get("/team-info")

    # ─── Module 2: Subscribers (Contacts) ─────────────────────────────

    def get_subscribers(self, page=1, limit=100):
        """GET /subscribers — paginated subscriber list."""
        return self._get("/subscribers", params={"page": page, "limit": limit})

    def get_subscriber_info(self, user_ns):
        """GET /subscriber/info — single subscriber by user_ns."""
        return self._get("/subscriber/info", params={"user_ns": user_ns})

    def update_subscriber(self, user_ns, data):
        """PUT /subscriber/update — update subscriber fields."""
        return self._put("/subscriber/update", json={"user_ns": user_ns, **data})

    def create_subscriber(self, data):
        """POST /subscriber/create — create a new subscriber."""
        return self._post("/subscriber/create", json=data)

    def set_user_fields(self, user_ns, fields: dict):
        """PUT /subscriber/set-user-fields-by-name — set custom user fields."""
        return self._put(
            "/subscriber/set-user-fields-by-name",
            json={"user_ns": user_ns, "fields": fields},
        )

    def get_chat_messages(self, user_ns):
        """GET /subscriber/chat-messages — conversation history."""
        return self._get("/subscriber/chat-messages", params={"user_ns": user_ns})

    # ─── Module 3: Messaging ──────────────────────────────────────────

    def send_text(self, user_ns, text, msg_type="text"):
        """POST /subscriber/send-text — send text message."""
        return self._post(
            "/subscriber/send-text",
            json={"user_ns": user_ns, "text": text, "type": msg_type},
        )

    def send_sms(self, user_ns, text):
        """POST /subscriber/send-sms — send SMS."""
        return self._post(
            "/subscriber/send-sms", json={"user_ns": user_ns, "text": text}
        )

    def send_email(self, user_ns, body, subject=""):
        """POST /subscriber/send-email — send email."""
        return self._post(
            "/subscriber/send-email",
            json={"user_ns": user_ns, "body": body, "subject": subject},
        )

    def send_content(self, user_ns, content_data: dict):
        """POST /subscriber/send-content — send rich content (image, video, etc.)."""
        return self._post(
            "/subscriber/send-content",
            json={"user_ns": user_ns, **content_data},
        )

    def send_whatsapp_template(self, user_ns, template_data: dict):
        """POST /subscriber/send-whatsapp-template — send WA template."""
        return self._post(
            "/subscriber/send-whatsapp-template",
            json={"user_ns": user_ns, **template_data},
        )

    def list_whatsapp_templates(self):
        """GET /flow/whatsapp-templates — list approved WA templates."""
        return self._get("/flow/whatsapp-templates")

    def send_broadcast(self, data: dict):
        """POST /subscriber/send-broadcast — send broadcast message."""
        return self._post("/subscriber/send-broadcast", json=data)

    def send_main_flow(self, user_ns, flow_ns):
        """POST /subscriber/send-main-flow — trigger main flow."""
        return self._post(
            "/subscriber/send-main-flow",
            json={"user_ns": user_ns, "flow_ns": flow_ns},
        )

    def send_sub_flow(self, user_ns, flow_ns):
        """POST /subscriber/send-sub-flow — trigger sub flow."""
        return self._post(
            "/subscriber/send-sub-flow",
            json={"user_ns": user_ns, "flow_ns": flow_ns},
        )

    def send_node(self, user_ns, node_ns):
        """POST /subscriber/send-node — trigger specific node."""
        return self._post(
            "/subscriber/send-node",
            json={"user_ns": user_ns, "node_ns": node_ns},
        )

    # ─── Module 4: Tags ───────────────────────────────────────────────

    def get_tags(self):
        """GET /flow/tags — all tags in workspace."""
        return self._get("/flow/tags")

    def get_flow_tags(self):
        """GET /flow-tags — alias for get_tags (legacy)."""
        return self._get("/flow-tags")

    def create_tag(self, name: str):
        """POST /flow/create-tag — create a new tag."""
        return self._post("/flow/create-tag", json={"name": name})

    def delete_tag(self, tag_ns: str):
        """DELETE /flow/delete-tag — delete a tag."""
        return self._delete("/flow/delete-tag", json={"ns": tag_ns})

    def add_tag(self, user_ns, tag_name: str):
        """POST /subscriber/add-tags-by-name — add tag to subscriber."""
        return self._post(
            "/subscriber/add-tags-by-name",
            json={"user_ns": user_ns, "tags": [tag_name]},
        )

    def remove_tag(self, user_ns, tag_name: str):
        """DELETE /subscriber/remove-tags-by-name — remove tag from subscriber."""
        return self._delete(
            "/subscriber/remove-tags-by-name",
            json={"user_ns": user_ns, "tags": [tag_name]},
        )

    def add_tags_by_name(self, user_ns, tags: list):
        """POST /subscriber/add-tags-by-name — add multiple tags."""
        return self._post(
            "/subscriber/add-tags-by-name",
            json={"user_ns": user_ns, "tags": tags},
        )

    def remove_tags_by_name(self, user_ns, tags: list):
        """DELETE /subscriber/remove-tags-by-name — remove multiple tags."""
        return self._delete(
            "/subscriber/remove-tags-by-name",
            json={"user_ns": user_ns, "tags": tags},
        )

    # ─── Module 5: Labels ─────────────────────────────────────────────

    def get_team_labels(self):
        """GET /team/labels — all team labels."""
        return self._get("/team/labels")

    def create_label(self, name: str, color: str = ""):
        """POST /team/create-label — create a label."""
        payload = {"name": name}
        if color:
            payload["color"] = color
        return self._post("/team/create-label", json=payload)

    def delete_label(self, label_id: str):
        """DELETE /team/delete-label — delete a label."""
        return self._delete("/team/delete-label", json={"id": label_id})

    def add_labels_by_name(self, user_ns, labels: list):
        """POST /subscriber/add-labels-by-name — add labels to subscriber."""
        return self._post(
            "/subscriber/add-labels-by-name",
            json={"user_ns": user_ns, "labels": labels},
        )

    def remove_labels_by_name(self, user_ns, labels: list):
        """DELETE /subscriber/remove-labels-by-name — remove labels."""
        return self._delete(
            "/subscriber/remove-labels-by-name",
            json={"user_ns": user_ns, "labels": labels},
        )

    # ─── Module 6: Ticket Lists ───────────────────────────────────────

    def get_ticket_lists(self):
        """GET /team/ticket-lists — all ticket lists."""
        return self._get("/team/ticket-lists")

    def get_ticket_list_items(self, list_id):
        """GET /team/ticket-lists/{list_id}/items — items in a list."""
        return self._get(f"/team/ticket-lists/{list_id}/items")

    def create_ticket_item(self, list_id, data):
        """POST /team/ticket-lists/{list_id}/create — create ticket item."""
        return self._post(f"/team/ticket-lists/{list_id}/create", json=data)

    def update_ticket_item(self, list_id, item_id, data):
        """PUT /team/ticket-lists/{list_id}/update/{item_id}."""
        return self._put(f"/team/ticket-lists/{list_id}/update/{item_id}", json=data)

    def delete_ticket_item(self, list_id, item_id):
        """DELETE /team/ticket-lists/{list_id}/delete/{item_id}."""
        return self._delete(f"/team/ticket-lists/{list_id}/delete/{item_id}")

    def get_ticket_list_fields(self, list_id):
        """GET /team/ticket-lists/{list_id}/fields — list field definitions."""
        return self._get(f"/team/ticket-lists/{list_id}/fields")

    def get_ticket_list_log(self, list_id):
        """GET /team/ticket-lists/{list_id}/log-data — activity log."""
        return self._get(f"/team/ticket-lists/{list_id}/log-data")

    # ─── Module 7: Team Members / Agent Assignment ────────────────────

    def get_team_members(self):
        """GET /team-members — all team members."""
        return self._get("/team-members")

    def assign_agent(self, user_ns, agent_id):
        """POST /subscriber/assign-agent."""
        return self._post(
            "/subscriber/assign-agent",
            json={"user_ns": user_ns, "agent_id": agent_id},
        )

    def unassign_agent(self, user_ns):
        """POST /subscriber/unassign-agent."""
        return self._post("/subscriber/unassign-agent", json={"user_ns": user_ns})

    def assign_agent_group(self, user_ns, group_id):
        """POST /subscriber/assign-agent-group."""
        return self._post(
            "/subscriber/assign-agent-group",
            json={"user_ns": user_ns, "group_id": group_id},
        )

    def move_chat_to(self, user_ns, target_agent_id):
        """POST /subscriber/move-chat-to — transfer chat to another agent."""
        return self._post(
            "/subscriber/move-chat-to",
            json={"user_ns": user_ns, "agent_id": target_agent_id},
        )

    # ─── Module 8: Opt-in / Opt-out ──────────────────────────────────

    def opt_in_sms(self, user_ns):
        """POST /subscriber/opt-in-sms."""
        return self._post("/subscriber/opt-in-sms", json={"user_ns": user_ns})

    def opt_out_sms(self, user_ns):
        """POST /subscriber/opt-out-sms."""
        return self._post("/subscriber/opt-out-sms", json={"user_ns": user_ns})

    def opt_in_email(self, user_ns):
        """POST /subscriber/opt-in-email."""
        return self._post("/subscriber/opt-in-email", json={"user_ns": user_ns})

    def opt_out_email(self, user_ns):
        """POST /subscriber/opt-out-email."""
        return self._post("/subscriber/opt-out-email", json={"user_ns": user_ns})

    def subscribe(self, user_ns):
        """POST /subscriber/subscribe — resubscribe user."""
        return self._post("/subscriber/subscribe", json={"user_ns": user_ns})

    def unsubscribe(self, user_ns):
        """POST /subscriber/unsubscribe — unsubscribe user."""
        return self._post("/subscriber/unsubscribe", json={"user_ns": user_ns})

    # ─── Module 9: Bot Control ────────────────────────────────────────

    def pause_bot(self, user_ns):
        """POST /subscriber/pause-bot."""
        return self._post("/subscriber/pause-bot", json={"user_ns": user_ns})

    def resume_bot(self, user_ns):
        """POST /subscriber/resume-bot."""
        return self._post("/subscriber/resume-bot", json={"user_ns": user_ns})

    def log_custom_event(self, user_ns, event_data):
        """POST /subscriber/log-custom-event."""
        return self._post(
            "/subscriber/log-custom-event",
            json={"user_ns": user_ns, **event_data},
        )

    def set_user_fields_by_name(self, user_ns, fields):
        """PUT /subscriber/set-user-fields-by-name."""
        return self._put(
            "/subscriber/set-user-fields-by-name",
            json={"user_ns": user_ns, "fields": fields},
        )

    # ─── Module 10: Analytics / Statistics ────────────────────────────

    def get_bot_users_count(self):
        """GET /flow/bot-users-count."""
        return self._get("/flow/bot-users-count")

    def get_agent_activity_log(self, **params):
        """GET /flow/agent-activity-log/data."""
        return self._get("/flow/agent-activity-log/data", params=params)

    def get_conversations_data(self, **params):
        """GET /flow/conversations/data."""
        return self._get("/flow/conversations/data", params=params)

    def get_custom_events(self):
        """GET /flow/custom-events."""
        return self._get("/flow/custom-events")

    def get_custom_events_summary(self, **params):
        """GET /flow/custom-events/summary."""
        return self._get("/flow/custom-events/summary", params=params)

    def get_custom_events_data(self, **params):
        """GET /flow/custom-events/data."""
        return self._get("/flow/custom-events/data", params=params)

    def get_flow_summary(self, **params):
        """GET /flow-summary — conversation metrics."""
        return self._get("/flow-summary", params=params)

    def get_flow_agent_summary(self, **params):
        """GET /flow-agent-summary — agent performance metrics."""
        return self._get("/flow-agent-summary", params=params)

    # ─── Module 11: Workspace / Channels / Flows ──────────────────────

    def get_channels(self):
        """GET /workspace-settings/channels — workspace channels."""
        return self._get("/workspace-settings/channels")

    def get_team_flows(self):
        """GET /team-flows — all flows."""
        return self._get("/team-flows")

    def get_subflows(self):
        """GET /flow/sub-flows — all sub-flows."""
        return self._get("/flow/sub-flows")


