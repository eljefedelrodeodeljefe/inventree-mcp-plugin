"""Django view adapter for MCP Streamable HTTP transport."""

from __future__ import annotations

# Prevent InvenTree's plugin scanner from picking up the `mcp` FastMCP instance.
__all__: list[str] = []

import asyncio
import contextlib
import logging
from typing import TYPE_CHECKING, Any

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.urls import path
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt  # applied at class level via method_decorator
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager

from .mcp_server import mcp

if TYPE_CHECKING:
    from collections.abc import MutableMapping

    from starlette.types import Scope

logger = logging.getLogger("inventree_mcp_plugin")

_REQUEST_TIMEOUT_SECONDS: float = 60.0


def _new_session_manager() -> StreamableHTTPSessionManager:
    """Create a fresh StreamableHTTPSessionManager for a single request.

    StreamableHTTPSessionManager.run() can only be called once per instance,
    so a new instance must be created for every incoming request.
    """
    return StreamableHTTPSessionManager(
        app=mcp._mcp_server,
        json_response=True,
        stateless=True,
    )


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


def _cancel_pending_tasks(loop: asyncio.AbstractEventLoop) -> None:
    """Cancel all pending async tasks on *loop* before it is closed.

    Prevents ``coroutine was never awaited`` warnings and ensures MCP session
    resources are freed when the sync worker shuts down the event loop.
    """
    pending = asyncio.all_tasks(loop)
    if not pending:
        return
    for task in pending:
        task.cancel()
    with contextlib.suppress(Exception):
        loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))


async def _handle_mcp_request(request: HttpRequest) -> HttpResponse:
    """Dispatch a Django request to the MCP session manager via ASGI."""
    session_manager = _new_session_manager()
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

    async def send(message: MutableMapping[str, Any]) -> None:
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


@method_decorator(csrf_exempt, name="dispatch")
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

        logger.debug("MCP request started: %s %s", request.method, request.path)
        loop = asyncio.new_event_loop()
        try:
            response = loop.run_until_complete(
                asyncio.wait_for(_handle_mcp_request(request), timeout=_REQUEST_TIMEOUT_SECONDS)
            )
            logger.debug("MCP request completed: %s %s", request.method, request.path)
            return response
        except TimeoutError:
            logger.warning(
                "MCP request timed out after %.0fs: %s %s",
                _REQUEST_TIMEOUT_SECONDS,
                request.method,
                request.path,
            )
            return JsonResponse(
                {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32000,
                        "message": f"Request timed out after {_REQUEST_TIMEOUT_SECONDS:.0f}s",
                    },
                    "id": None,
                },
                status=504,
            )
        except Exception:
            logger.exception("MCP request failed: %s %s", request.method, request.path)
            return JsonResponse(
                {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32603,
                        "message": "Internal server error",
                    },
                    "id": None,
                },
                status=500,
            )
        finally:
            _cancel_pending_tasks(loop)
            loop.close()


urlpatterns = [
    path("mcp/", csrf_exempt(MCPView.as_view()), name="mcp-endpoint"),
]
