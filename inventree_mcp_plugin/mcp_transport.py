"""Django view adapter for MCP Streamable HTTP transport."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import TYPE_CHECKING, Any

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.urls import path
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager

from .mcp_server import mcp

if TYPE_CHECKING:
    from starlette.types import Scope

logger = logging.getLogger("inventree_mcp_plugin")

_session_manager: StreamableHTTPSessionManager | None = None


def _get_session_manager() -> StreamableHTTPSessionManager:
    """Get or create the singleton StreamableHTTPSessionManager."""
    global _session_manager
    if _session_manager is None:
        _session_manager = StreamableHTTPSessionManager(
            app=mcp._mcp_server,
            json_response=True,
            stateless=True,
        )
    return _session_manager


def _check_auth(request: HttpRequest) -> bool:
    """Check if the request is authenticated.

    Returns True if the user is authenticated via session, token, or basic auth.
    InvenTree's AuthRequiredMiddleware already populates request.user from
    Token/Bearer headers and session cookies before the view is called.
    """
    return hasattr(request, "user") and request.user.is_authenticated


def _get_plugin_instance() -> Any:
    """Get the InvenTreeMCPPlugin instance from the plugin registry."""
    try:
        from plugin import registry

        return registry.get_plugin("inventree-mcp")
    except Exception:
        return None


def _build_asgi_scope(request: HttpRequest) -> Scope:
    """Convert a Django HttpRequest into an ASGI scope dict."""
    body = request.body
    headers: list[tuple[bytes, bytes]] = [
        (key.lower().encode("latin-1"), value.encode("latin-1"))
        for key, value in request.headers.items()
        if key.lower() != "content-length"
    ]
    headers.append((b"content-length", str(len(body)).encode("latin-1")))

    return {
        "type": "http",
        "http_version": "1.1",
        "method": request.method,
        "headers": headers,
        "path": request.path,
        "raw_path": request.get_full_path().encode("utf-8"),
        "query_string": request.META.get("QUERY_STRING", "").encode("latin-1"),
        "scheme": "https" if request.is_secure() else "http",
        "client": (request.META.get("REMOTE_ADDR", "127.0.0.1"), 0),
        "server": (request.get_host(), int(request.META.get("SERVER_PORT", 80))),
    }


async def _handle_mcp_request(request: HttpRequest) -> HttpResponse:
    """Dispatch a Django request to the MCP session manager via ASGI."""
    session_manager = _get_session_manager()
    body = request.body

    scope = _build_asgi_scope(request)

    async def receive() -> dict[str, Any]:
        return {
            "type": "http.request",
            "body": body,
            "more_body": False,
        }

    response_started: dict[str, Any] = {}
    response_body = bytearray()

    async def send(message: dict[str, Any]) -> None:
        if message["type"] == "http.response.start":
            response_started["status"] = message["status"]
            response_started["headers"] = message.get("headers", [])
        elif message["type"] == "http.response.body":
            response_body.extend(message.get("body", b""))

    async with session_manager.run():
        await session_manager.handle_request(scope, receive, send)

    status = response_started.get("status", 500)
    response = HttpResponse(bytes(response_body), status=status)
    for key, value in response_started.get("headers", []):
        header_name = key.decode("latin-1") if isinstance(key, bytes) else key
        header_value = value.decode("latin-1") if isinstance(value, bytes) else value
        response[header_name] = header_value

    return response


class MCPView(View):
    """Django view that handles MCP Streamable HTTP transport requests.

    Enforces authentication when the plugin's REQUIRE_AUTH setting is enabled.
    Supports InvenTree's standard auth methods: Token, Basic, and Session.
    """

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        # Check authentication if required by plugin settings
        plugin = _get_plugin_instance()
        require_auth = True  # safe default
        if plugin is not None:
            with contextlib.suppress(Exception):
                require_auth = plugin.get_setting("REQUIRE_AUTH")

        if require_auth and not _check_auth(request):
            return JsonResponse(
                {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32000,
                        "message": "Authentication required. Provide a valid Token, Bearer, or Basic credential.",
                    },
                    "id": None,
                },
                status=401,
            )

        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(_handle_mcp_request(request))
        finally:
            loop.close()


urlpatterns = [
    path("mcp/", csrf_exempt(MCPView.as_view()), name="mcp-endpoint"),
]
