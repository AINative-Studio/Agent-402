"""
Slow tool handler fixture for PluginSandboxService timeout tests.

Built by AINative Dev Team
Refs #243
"""
from __future__ import annotations

import asyncio
from typing import Any, Dict


async def handle(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Slow handler: sleeps for a long time to trigger timeout."""
    await asyncio.sleep(9999)
    return {"result": "never reached"}
