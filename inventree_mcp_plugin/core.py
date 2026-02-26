"""InvenTree MCP Plugin - main plugin class."""

from __future__ import annotations

from typing import Any, ClassVar

from plugin import InvenTreePlugin
from plugin.mixins import SettingsMixin, UrlsMixin

from . import PLUGIN_VERSION


class InvenTreeMCPPlugin(UrlsMixin, SettingsMixin, InvenTreePlugin):  # type: ignore[misc]
    """Plugin that exposes InvenTree data via Model Context Protocol (MCP)."""

    NAME = "InvenTreeMCPPlugin"
    SLUG = "inventree-mcp"
    TITLE = "InvenTree MCP Plugin"
    DESCRIPTION = "Exposes InvenTree data via Model Context Protocol (MCP)"
    VERSION = PLUGIN_VERSION
    AUTHOR = "eljefedelrodeodeljefe"
    MIN_VERSION = "0.18.0"

    SETTINGS: ClassVar[dict[str, Any]] = {
        "REQUIRE_AUTH": {
            "name": "Require Authentication",
            "description": "Require authentication for MCP endpoint",
            "default": True,
            "validator": bool,
        },
    }

    def setup_urls(self) -> list[Any]:
        from .mcp_transport import urlpatterns

        return urlpatterns
