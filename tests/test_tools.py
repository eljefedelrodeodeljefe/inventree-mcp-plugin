"""Unit tests for MCP tool functions."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


class TestListParts:
    def test_list_parts_returns_list(self, mock_part_class: MagicMock) -> None:
        mock_part = MagicMock()
        mock_part.pk = 1
        mock_part.name = "Resistor 10k"
        mock_part.description = "10k ohm resistor"
        mock_part.category_id = 5
        mock_part.active = True
        mock_part.IPN = "R-10K"
        mock_part.revision = "A"
        mock_part.units = "pcs"

        mock_part_class.objects.all.return_value.order_by.return_value.__getitem__ = MagicMock(return_value=[mock_part])

        from inventree_mcp_plugin.tools.simple.parts import list_parts

        result = list_parts(limit=10)
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["id"] == 1
        assert result[0]["name"] == "Resistor 10k"

    def test_list_parts_with_category_filter(self, mock_part_class: MagicMock) -> None:
        mock_part_class.objects.all.return_value.filter.return_value.order_by.return_value.__getitem__ = MagicMock(
            return_value=[]
        )

        from inventree_mcp_plugin.tools.simple.parts import list_parts

        result = list_parts(category_id=5)
        mock_part_class.objects.all.return_value.filter.assert_called()
        assert isinstance(result, list)


class TestGetPart:
    def test_get_part_returns_dict(self, mock_part_class: MagicMock) -> None:
        mock_part = MagicMock()
        mock_part.pk = 42
        mock_part.name = "Capacitor 100uF"
        mock_part.description = "100uF electrolytic capacitor"
        mock_part.category_id = 3
        mock_part.active = True
        mock_part.IPN = "C-100UF"
        mock_part.revision = ""
        mock_part.units = "pcs"
        mock_part.assembly = False
        mock_part.component = True
        mock_part.purchaseable = True
        mock_part.salable = False
        mock_part.trackable = False
        mock_part.virtual = False
        mock_part.total_stock = 250

        mock_part_class.objects.get.return_value = mock_part

        from inventree_mcp_plugin.tools.simple.parts import get_part

        result = get_part(42)
        assert result["id"] == 42
        assert result["name"] == "Capacitor 100uF"
        assert result["total_stock"] == 250.0


class TestSearchParts:
    def test_search_parts(self, mock_part_class: MagicMock) -> None:
        mock_part = MagicMock()
        mock_part.pk = 1
        mock_part.name = "Resistor"
        mock_part.description = "Generic resistor"
        mock_part.category_id = 2
        mock_part.active = True

        mock_part_class.objects.filter.return_value.order_by.return_value.__getitem__ = MagicMock(
            return_value=[mock_part]
        )

        from inventree_mcp_plugin.tools.simple.parts import search_parts

        result = search_parts("Resistor")
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["name"] == "Resistor"


class TestCreatePart:
    def test_create_part(self, mock_part_class: MagicMock) -> None:
        mock_part = MagicMock()
        mock_part.pk = 99
        mock_part.name = "New Part"
        mock_part.description = "A new part"
        mock_part_class.objects.create.return_value = mock_part

        mock_category = MagicMock()
        with patch("part.models.PartCategory") as mock_cat_class:
            mock_cat_class.objects.get.return_value = mock_category

            from inventree_mcp_plugin.tools.simple.parts import create_part

            result = create_part(name="New Part", description="A new part", category_id=1)
            assert result["id"] == 99
            assert result["name"] == "New Part"


class TestListStockItems:
    def test_list_stock_items(self, mock_stock_item_class: MagicMock) -> None:
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

        result = list_stock_items()
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["id"] == 10
        assert result[0]["quantity"] == 100.0


class TestListLocations:
    def test_list_locations(self, mock_stock_location_class: MagicMock) -> None:
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

        result = list_locations()
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["name"] == "Warehouse A"


class TestListCategories:
    def test_list_categories(self, mock_part_category_class: MagicMock) -> None:
        mock_cat = MagicMock()
        mock_cat.pk = 1
        mock_cat.name = "Electronics"
        mock_cat.description = "Electronic components"
        mock_cat.parent_id = None
        mock_cat.pathstring = "Electronics"

        mock_part_category_class.objects.all.return_value.order_by.return_value.__getitem__ = MagicMock(
            return_value=[mock_cat]
        )

        from inventree_mcp_plugin.tools.simple.categories import list_categories

        result = list_categories()
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["name"] == "Electronics"
