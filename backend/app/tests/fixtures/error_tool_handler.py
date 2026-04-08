"""
Error tool handler fixture for PluginSandboxService exception-catching tests.

Built by AINative Dev Team
Refs #243
"""
from __future__ import annotations

from typing import Any, Dict


async def handle(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Error handler: always raises a RuntimeError to test exception catching."""
    raise RuntimeError("intentional handler failure for testing")
