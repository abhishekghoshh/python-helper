"""
DateTime tool — returns the current date and time.

Uses Python's standard library ``datetime`` and ``zoneinfo`` modules.
No external API calls — works offline.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.tools.base import Tool, ToolResult


class DateTimeTool(Tool):
    """Returns the current date and time, with optional timezone and format."""

    name = "datetime_now"
    description = (
        "Returns the current date and time. Useful when the user asks "
        "about the current time, date, day of week, or timestamp."
    )
    category = "utility"
    parameters = {
        "type": "object",
        "properties": {
            "timezone": {
                "type": "string",
                "description": "Timezone name (e.g. 'UTC', 'America/New_York'). Defaults to UTC.",
                "default": "UTC",
            },
            "format": {
                "type": "string",
                "description": "strftime format string (e.g. '%Y-%m-%d %H:%M:%S'). Defaults to ISO 8601.",
                "default": "%Y-%m-%dT%H:%M:%S%z",
            },
        },
        "required": [],
    }

    async def execute(self, timezone: str = "UTC", fmt: str = "%Y-%m-%dT%H:%M:%S%z", **kwargs: Any) -> ToolResult:
        try:
            from zoneinfo import ZoneInfo

            tz = ZoneInfo(timezone)
        except Exception:
            tz = None  # fall back to local time

        now = datetime.now(tz) if tz is not None else datetime.now()
        formatted = now.strftime(fmt)
        # Also include human-readable components for the LLM
        human = (
            f"Current date/time: {formatted}\n"
            f"Year: {now.year}, Month: {now.month}, Day: {now.day}\n"
            f"Hour: {now.hour}, Minute: {now.minute}, Second: {now.second}\n"
            f"Weekday: {now.strftime('%A')}"
        )
        return ToolResult(self.name, human)
