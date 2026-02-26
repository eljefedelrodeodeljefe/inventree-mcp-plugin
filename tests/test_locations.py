"""Unit tests for location tools."""

from __future__ import annotations

from unittest.mock import MagicMock


class TestListLocations:
    async def test_list_locations(self, mock_stock_location_class: MagicMock) -> None:
        mock_loc = MagicMock()
        mock_loc.pk = 1
        mock_loc.name = "Warehouse A"
        mock_loc.description = "Main warehouse"
        mock_loc.parent_id = None
        mock_loc.pathstring = "Warehouse A"

        mock_stock_location_class.objects.all.return_value.order_by.return_value.__getitem__ = MagicMock(
            return_value=[mock_loc]
        )

        from inventree_mcp_plugin.tools.simple.locations import list_locations

        result = await list_locations()
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["name"] == "Warehouse A"


class TestGetLocationTree:
    def _make_loc(self, pk: int, name: str, parent_id: int | None) -> MagicMock:
        loc = MagicMock()
        loc.pk = pk
        loc.name = name
        loc.description = f"{name} description"
        loc.parent_id = parent_id
        return loc

    def _setup(self, mock_cls: MagicMock, locs: list) -> None:
        mock_cls.objects.all.return_value.order_by.return_value = locs

    async def test_single_db_query_regardless_of_depth(self, mock_stock_location_class: MagicMock) -> None:
        root = self._make_loc(1, "Warehouse", None)
        shelf = self._make_loc(2, "Shelf A", 1)
        bin_ = self._make_loc(3, "Bin 1", 2)
        self._setup(mock_stock_location_class, [root, shelf, bin_])

        from inventree_mcp_plugin.tools.simple.locations import get_location_tree

        await get_location_tree()
        mock_stock_location_class.objects.all.assert_called_once()

    async def test_correct_nesting_three_levels(self, mock_stock_location_class: MagicMock) -> None:
        root = self._make_loc(1, "Warehouse", None)
        shelf = self._make_loc(2, "Shelf A", 1)
        bin_ = self._make_loc(3, "Bin 1", 2)
        self._setup(mock_stock_location_class, [root, shelf, bin_])

        from inventree_mcp_plugin.tools.simple.locations import get_location_tree

        result = await get_location_tree()
        assert [r["name"] for r in result] == ["Warehouse"]
        assert result[0]["children"][0]["name"] == "Shelf A"
        assert result[0]["children"][0]["children"][0]["name"] == "Bin 1"
        assert result[0]["children"][0]["children"][0]["children"] == []

    async def test_root_id_returns_children_not_node_itself(self, mock_stock_location_class: MagicMock) -> None:
        root = self._make_loc(1, "Warehouse", None)
        shelf = self._make_loc(2, "Shelf A", 1)
        self._setup(mock_stock_location_class, [root, shelf])

        from inventree_mcp_plugin.tools.simple.locations import get_location_tree

        result = await get_location_tree(root_id=1)
        assert [r["name"] for r in result] == ["Shelf A"]

    async def test_multiple_roots(self, mock_stock_location_class: MagicMock) -> None:
        w1 = self._make_loc(1, "Warehouse 1", None)
        w2 = self._make_loc(2, "Warehouse 2", None)
        self._setup(mock_stock_location_class, [w1, w2])

        from inventree_mcp_plugin.tools.simple.locations import get_location_tree

        result = await get_location_tree()
        assert [r["name"] for r in result] == ["Warehouse 1", "Warehouse 2"]
