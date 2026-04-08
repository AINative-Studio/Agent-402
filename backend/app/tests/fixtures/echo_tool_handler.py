"""
Echo tool handler fixture for PluginSandboxService tests.

This module simulates a real plugin handler module.
The sandbox service will dynamically import it for tool execution.

Built by AINative Dev Team
Refs #243
"""
from __future__ import annotations

from typing import Any, Dict


async def handle(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Echo handler: returns the input message back as output."""
    message = input_data.get("message", "")
    return {"echo": message}
