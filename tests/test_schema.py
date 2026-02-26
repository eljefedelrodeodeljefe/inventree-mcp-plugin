"""Schema snapshot tests for registered MCP tools.

Verifies that all expected tools are registered with the correct names,
non-empty descriptions, and required parameters. These tests run without
InvenTree and catch accidental renames, removals, or signature changes.
"""

from __future__ import annotations

import pytest

# All 27 tools: name -> set of required parameter names (non-defaulted).
_EXPECTED_TOOLS: dict[str, set[str]] = {
    # Parts
    "list_parts": set(),
    "get_part": {"part_id"},
    "search_parts": {"query"},
    "create_part": {"name", "description", "category_id"},
    "update_part": {"part_id"},
    # Stock
    "list_stock_items": set(),
    "get_stock_item": {"stock_item_id"},
    "adjust_stock": {"stock_item_id", "quantity"},
    "transfer_stock": {"stock_item_id", "location_id"},
    # Locations
    "list_locations": set(),
    "get_location": {"location_id"},
    "get_location_tree": set(),
    # Categories
    "list_categories": set(),
    "get_category": {"category_id"},
    "get_category_tree": set(),
    # Orders
    "list_purchase_orders": set(),
    "get_purchase_order": {"order_id"},
    "list_sales_orders": set(),
    "get_sales_order": {"order_id"},
    # BOM
    "list_bom_items": set(),
    "get_bom_for_part": {"part_id"},
    # Builds
    "list_build_orders": set(),
    "get_build_order": {"build_id"},
    # Tags
    "list_tags": set(),
    "search_tags": {"query"},
    # Combinatory
    "delete_parts": {"part_ids"},
    "stock_by_category_and_location": set(),
}


@pytest.fixture(scope="module")
def registered_tools() -> dict[str, object]:
    """Import the MCP server and return {name: Tool} for all registered tools.

    Scoped to the module so the import only happens once per test session.
    The autouse stub fixture sets up sys.modules before the first test in
    this module runs, so Django/InvenTree imports are satisfied.
    """
    from inventree_mcp_plugin.mcp_server import mcp

    return {t.name: t for t in mcp._tool_manager.list_tools()}


class TestToolRegistry:
    def test_total_tool_count(self, registered_tools: dict) -> None:
        assert len(registered_tools) == len(_EXPECTED_TOOLS), (
            f"Expected {len(_EXPECTED_TOOLS)} tools, got {len(registered_tools)}.\n"
            f"Extra:   {set(registered_tools) - set(_EXPECTED_TOOLS)}\n"
            f"Missing: {set(_EXPECTED_TOOLS) - set(registered_tools)}"
        )

    def test_all_expected_names_registered(self, registered_tools: dict) -> None:
        missing = set(_EXPECTED_TOOLS) - set(registered_tools)
        assert not missing, f"Tools missing from registry: {sorted(missing)}"

    def test_no_unexpected_tools_registered(self, registered_tools: dict) -> None:
        extra = set(registered_tools) - set(_EXPECTED_TOOLS)
        assert not extra, f"Unexpected tools found in registry: {sorted(extra)}"

    @pytest.mark.parametrize("name", sorted(_EXPECTED_TOOLS))
    def test_tool_has_description(self, name: str, registered_tools: dict) -> None:
        if name not in registered_tools:
            pytest.skip(f"Tool '{name}' not registered")
        tool = registered_tools[name]
        assert tool.description, f"Tool '{name}' has no description"

    @pytest.mark.parametrize("name,required_params", sorted(_EXPECTED_TOOLS.items()))
    def test_tool_required_params(self, name: str, required_params: set[str], registered_tools: dict) -> None:
        if name not in registered_tools:
            pytest.skip(f"Tool '{name}' not registered")
        tool = registered_tools[name]
        schema_required: set[str] = set(tool.parameters.get("required", []))
        missing = required_params - schema_required
        assert not missing, (
            f"Tool '{name}' is missing required params: {sorted(missing)}. Schema required: {sorted(schema_required)}"
        )
