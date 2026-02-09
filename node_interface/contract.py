"""
Router Contract v1 — Formal action whitelist and request/response schema

This module defines the ONLY valid actions that any interface (Telegram, voice, CLI)
can invoke on the system. No interface may bypass this contract.

Design principles:
- Closed whitelist: only listed actions are valid
- Read/write classification: enables permission enforcement per interface
- Typed request/response: eliminates implicit coupling
- Interface-agnostic: contract knows nothing about Telegram, voice, etc.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional
from datetime import datetime


class Action(Enum):
    """
    Closed whitelist of all valid system actions.
    
    Derived directly from existing Router methods.
    Adding a new action requires explicit modification here.
    """
    # --- Read-only actions ---
    SYSTEM_STATUS = "system_status"
    PROJECT_INFO = "project_info"
    PROJECT_SUMMARY = "project_summary"
    PROJECT_LIST = "project_list"
    PROJECT_STATUS = "project_status"
    INBOX = "inbox"
    DDS_LIST = "dds_list"
    DDS_LIST_PROPOSED = "dds_list_proposed"
    EXEC_STATUS = "exec_status"
    TODO_LIST = "todo_list"

    # --- Write actions (mutate state) ---
    DDS_NEW = "dds_new"
    DDS_APPROVE = "dds_approve"
    DDS_REJECT = "dds_reject"
    EXECUTE = "execute"
    TODO_TO_DDS = "todo_to_dds"


# Classification: which actions are read-only
_READ_ONLY_ACTIONS = frozenset({
    Action.SYSTEM_STATUS,
    Action.PROJECT_INFO,
    Action.PROJECT_SUMMARY,
    Action.PROJECT_LIST,
    Action.PROJECT_STATUS,
    Action.INBOX,
    Action.DDS_LIST,
    Action.DDS_LIST_PROPOSED,
    Action.EXEC_STATUS,
    Action.TODO_LIST,
})

_WRITE_ACTIONS = frozenset({
    Action.DDS_NEW,
    Action.DDS_APPROVE,
    Action.DDS_REJECT,
    Action.EXECUTE,
    Action.TODO_TO_DDS,
})


def is_read_only(action: Action) -> bool:
    """Check if an action is read-only (does not mutate system state)."""
    return action in _READ_ONLY_ACTIONS


def is_write(action: Action) -> bool:
    """Check if an action mutates system state."""
    return action in _WRITE_ACTIONS


@dataclass
class ContractRequest:
    """
    Typed request that any interface must construct to invoke a system action.
    
    Fields:
        action: The action to perform (must be in Action enum)
        payload: Action-specific parameters (dict, validated per action)
        source: Identifier of the calling interface (e.g. "telegram", "voice", "cli")
        user_id: Identifier of the user making the request (for audit trail)
        timestamp: When the request was created (auto-generated)
    """
    action: Action
    payload: Dict[str, Any] = field(default_factory=dict)
    source: str = "unknown"
    user_id: str = "unknown"
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ContractResponse:
    """
    Typed response returned by the Router for every action.
    
    Fields:
        status: "ok" or "error"
        message: Human-readable result text (what interfaces display)
        data: Structured data for programmatic consumers (optional)
        action: Which action produced this response
        read_only: Whether the action was read-only
        audit_id: Unique identifier for this request/response pair
    """
    status: str
    message: str
    data: Optional[Dict[str, Any]] = None
    action: Optional[Action] = None
    read_only: bool = True
    audit_id: str = field(default_factory=lambda: f"AUD-{datetime.now().strftime('%Y%m%d%H%M%S%f')}")


class ContractError(Exception):
    """Raised when a contract violation occurs (unknown action, bad payload, etc.)"""
    pass


# Payload schemas: defines required keys per action
# Actions not listed here accept empty payload
PAYLOAD_SCHEMAS: Dict[Action, Dict[str, bool]] = {
    # Action: {field_name: required}
    Action.PROJECT_INFO: {"name": True},
    Action.PROJECT_SUMMARY: {"name": True},
    Action.PROJECT_STATUS: {"name": True},
    Action.INBOX: {"count": False},
    Action.DDS_NEW: {"project": True, "title": True, "description": True},
    Action.DDS_APPROVE: {"proposal_id": True},
    Action.DDS_REJECT: {"proposal_id": True},
    Action.EXECUTE: {"dds_id": True},
    Action.TODO_TO_DDS: {"todo_id": True},
}


def validate_payload(action: Action, payload: Dict[str, Any]) -> None:
    """
    Validate that a payload contains required fields for the given action.
    
    Raises:
        ContractError: If required fields are missing
    """
    schema = PAYLOAD_SCHEMAS.get(action)
    if schema is None:
        # Actions without schema accept any (including empty) payload
        return

    for field_name, required in schema.items():
        if required and field_name not in payload:
            raise ContractError(
                f"Action {action.value} requires field '{field_name}' in payload"
            )


# ──────────────────────────────────────────────
# SOURCE PERMISSIONS — which sources can invoke which actions
# ──────────────────────────────────────────────

# Known sources and their permissions.
# "all" means every action in the whitelist is allowed.
# A frozenset restricts to specific actions only.
SOURCE_PERMISSIONS: Dict[str, Any] = {
    "telegram": "all",
    "cli": "all",
    "voice": _READ_ONLY_ACTIONS,  # voice v0: read-only only
    # Unknown sources get rejected by default
}


def validate_source_permission(source: str, action: Action) -> None:
    """
    Validate that a source is allowed to invoke a given action.
    
    Raises:
        ContractError: If source is unknown or action not permitted for source
    """
    permissions = SOURCE_PERMISSIONS.get(source)

    if permissions is None:
        raise ContractError(
            f"Unknown source '{source}'. Registered sources: {list(SOURCE_PERMISSIONS.keys())}"
        )

    if permissions == "all":
        return

    if action not in permissions:
        raise ContractError(
            f"Source '{source}' is not allowed to invoke action '{action.value}'. "
            f"This source only has access to read-only actions."
        )
