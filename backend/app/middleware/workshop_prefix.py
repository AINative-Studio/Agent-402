"""
Workshop-mode path-rewrite ASGI middleware.

Refs #300, #285. Enables workshop tutorials to hit endpoints under a flat
`/api/v1/*` prefix without duplicating handlers. The middleware rewrites
incoming paths before routing, so all existing route handlers remain the
source of truth.

Behavior:
- Only active when `enabled=True` (driven by `settings.workshop_mode`).
- Default convention: `/api/v1/<suffix>` -> `/v1/public/<default_project_id>/<suffix>`
- Override registry rewrites non-conventional paths (e.g. `/hcs10/*`,
  `/marketplace/*`) to their true prefix. Overrides are checked first.
- Legacy paths are never modified.
- Non-HTTP ASGI scopes (lifespan, websocket) are passed through unchanged.

Implemented as a pure ASGI middleware (not BaseHTTPMiddleware) so the rewrite
lands on `scope["path"]` before route matching, not after the handler has
already been selected.

Built by AINative Dev Team
"""
from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict, Mapping, MutableMapping, Optional

_API_V1_PREFIX = "/api/v1/"


Scope = MutableMapping[str, Any]
Receive = Callable[[], Awaitable[MutableMapping[str, Any]]]
Send = Callable[[MutableMapping[str, Any]], Awaitable[None]]


class WorkshopPrefixMiddleware:
    """
    Rewrite `/api/v1/*` requests to their underlying router prefix.

    Args:
        app: Downstream ASGI application.
        enabled: When False, the middleware is a no-op and `/api/v1/*` paths
            are left alone (and will 404 unless another router claims them).
        default_project_id: Substituted into the convention mapping
            `/api/v1/<suffix>` -> `/v1/public/<default_project_id>/<suffix>`.
        overrides: Optional mapping of `suffix -> target_prefix`. When the
            stripped `/api/v1/` remainder starts with one of the suffixes,
            the remainder after the suffix is appended to the target prefix.
            Example: `{"hcs10/": "/hcs10/"}` routes `/api/v1/hcs10/send` to
            `/hcs10/send`.
    """

    def __init__(
        self,
        app: Any,
        enabled: bool = False,
        default_project_id: str = "",
        overrides: Optional[Mapping[str, str]] = None,
    ) -> None:
        self.app = app
        self.enabled = enabled
        self.default_project_id = default_project_id
        self.overrides: Dict[str, str] = dict(overrides or {})

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if not self._should_rewrite(scope):
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        new_path = self._rewrite_path(path)
        if new_path == path:
            await self.app(scope, receive, send)
            return

        # Shallow-copy scope and replace path + raw_path. Starlette routing reads
        # both; keep them in sync so path parameters and query strings resolve
        # against the rewritten URL.
        new_scope: Scope = dict(scope)
        new_scope["path"] = new_path
        new_scope["raw_path"] = new_path.encode("utf-8")
        await self.app(new_scope, receive, send)

    def _should_rewrite(self, scope: Mapping[str, Any]) -> bool:
        """Only rewrite live HTTP requests when the feature flag is on."""
        if not self.enabled:
            return False
        return scope.get("type") == "http"

    def _rewrite_path(self, path: str) -> str:
        """Compute the rewritten path, or return the original if no rule matches."""
        if not path.startswith(_API_V1_PREFIX):
            return path

        suffix = path[len(_API_V1_PREFIX):]

        # Overrides win over convention so non-project-scoped routes (hcs10,
        # marketplace, anchor/*) can be mapped to their true prefix.
        for key, target in self.overrides.items():
            if suffix.startswith(key):
                remainder = suffix[len(key):]
                if not target.endswith("/"):
                    target = target + "/"
                return target + remainder

        # Default convention: prefix with default project id
        if not self.default_project_id:
            return path
        return f"/v1/public/{self.default_project_id}/{suffix}"
