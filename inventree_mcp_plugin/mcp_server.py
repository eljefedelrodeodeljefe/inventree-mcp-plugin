"""FastMCP server instance and tool registration."""

# Prevent InvenTree's plugin scanner from adding the FastMCP instance to its
# module-attribute context (which causes inspect.getmembers to crash on the
# session_manager property).  Explicit imports (from .mcp_server import mcp)
# are unaffected by __all__.
__all__: list[str] = []

from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "InvenTree MCP",
    instructions="MCP server for interacting with InvenTree inventory management data.",
    stateless_http=True,
    json_response=True,
)

# Import tool modules to trigger @mcp.tool() registration
from .tools.combinatory import parts as _combinatory_parts  # noqa: E402, F401
from .tools.combinatory import stock as _combinatory_stock  # noqa: E402, F401
from .tools.simple import bom as _bom  # noqa: E402, F401
from .tools.simple import builds as _builds  # noqa: E402, F401
from .tools.simple import categories as _categories  # noqa: E402, F401
from .tools.simple import locations as _locations  # noqa: E402, F401
from .tools.simple import orders as _orders  # noqa: E402, F401
from .tools.simple import parts as _parts  # noqa: E402, F401
from .tools.simple import stock as _stock  # noqa: E402, F401
from .tools.simple import tags as _tags  # noqa: E402, F401
