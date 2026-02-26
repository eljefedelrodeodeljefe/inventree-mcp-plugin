"""Unit tests for stock tools."""

from __future__ import annotations

from unittest.mock import MagicMock


class TestListStockItems:
    async def test_list_stock_items(self, mock_stock_item_class: MagicMock) -> None:
        mock_item = MagicMock()
        mock_item.pk = 10
        mock_item.part_id = 1
        mock_item.part.name = "Resistor"
        mock_item.quantity = 100
        mock_item.location_id = 5
        mock_item.serial = None
        mock_item.batch = "B001"

        mock_stock_item_class.objects.all.return_value.order_by.return_value.__getitem__ = MagicMock(
            return_value=[mock_item]
        )

        from inventree_mcp_plugin.tools.simple.stock import list_stock_items

        result = await list_stock_items()
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["id"] == 10
        assert result[0]["quantity"] == 100.0
