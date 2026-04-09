"""
ainative-agent-runtime — ModelSelector (Python)
Built by AINative Dev Team
Refs #248

Selects the best LLM provider based on availability and task complexity.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional


class ModelSelector:
    """
    Selects an LLM provider for a given task.

    Selection order:
        1. If complexity_threshold is set and task.metadata.complexity > threshold,
           prefer the last registered (cloud) provider.
        2. Otherwise prefer the first healthy provider (local).
        3. If no healthy provider, raise RuntimeError.

    Args:
        providers: List of LLM provider objects, each must have a `.name` attribute.
        complexity_threshold: Optional int/float. Tasks above this value route to cloud.
    """

    def __init__(
        self,
        providers: List[Any],
        complexity_threshold: Optional[float] = None,
    ) -> None:
        self._providers = providers
        self._complexity_threshold = complexity_threshold
        # Initially all providers assumed healthy
        self._health: Dict[str, bool] = {p.name: True for p in providers}

    # ─── select() ─────────────────────────────────────────────────────────────

    async def select(self, task: Dict[str, Any]) -> Any:
        if not self._providers:
            raise RuntimeError("No providers registered in ModelSelector")

        complexity = float(task.get("metadata", {}).get("complexity", 0) or 0)
        is_high_complexity = (
            self._complexity_threshold is not None
            and complexity > self._complexity_threshold
        )

        if is_high_complexity:
            cloud = self._providers[-1]
            if self._health.get(cloud.name, True):
                return cloud

        # Return first healthy provider
        for provider in self._providers:
            if self._health.get(provider.name, True):
                return provider

        raise RuntimeError("No healthy providers available")

    # ─── health_check() ───────────────────────────────────────────────────────

    async def health_check(self) -> List[Dict[str, Any]]:
        """Ping all providers and record their health status."""
        results = []

        for provider in self._providers:
            start = time.monotonic()
            healthy = True
            error: Optional[str] = None

            try:
                await provider.chat([{"role": "user", "content": "ping"}])
            except Exception as exc:
                healthy = False
                error = str(exc)

            latency_ms = (time.monotonic() - start) * 1000
            self._health[provider.name] = healthy

            results.append({
                "name": provider.name,
                "healthy": healthy,
                "latency_ms": latency_ms,
                "error": error,
            })

        return results
