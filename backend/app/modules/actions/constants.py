"""Shared action type and status vocabulary."""

from __future__ import annotations

ACTION_TYPES = (
    "PAY",
    "RENEW",
    "REGISTER",
    "REVIEW",
    "FOLLOW_UP",
    "KEEP_FOR_RECORDS",
)

ACTION_STATUSES = (
    "suggested",
    "confirmed",
    "in_progress",
    "completed",
    "dismissed",
)

# Open / work-in-flight statuses returned by GET /actions by default.
ACTIVE_STATUSES = ("suggested", "confirmed", "in_progress")

# Statuses that may still appear in the actions UI (includes done work).
LISTABLE_STATUSES = ("suggested", "confirmed", "in_progress", "completed")

# Valid transitions: from_status → frozenset(to_status)
TRANSITIONS: dict[str, frozenset[str]] = {
    "suggested": frozenset({"confirmed", "dismissed"}),
    "confirmed": frozenset({"in_progress", "completed", "dismissed"}),
    "in_progress": frozenset({"completed", "dismissed"}),
    "completed": frozenset(),
    "dismissed": frozenset(),
}
