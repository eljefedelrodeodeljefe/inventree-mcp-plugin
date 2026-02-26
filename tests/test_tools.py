"""Unit tests for MCP tool functions."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


def _make_mock_part(pk: int = 1, name: str = "Resistor 10k", tag_names: list[str] | None = None) -> MagicMock:
    mock_part = MagicMock()
    mock_part.pk = pk
    mock_part.name = name
    mock_part.description = "10k ohm resistor"
    mock_part.category_id = 5
    mock_part.active = True
    mock_part.IPN = "R-10K"
    mock_part.revision = "A"
    mock_part.units = "pcs"
    mock_tags = []
    for t in tag_names or []:
        tag_mock = MagicMock()
        tag_mock.name = t
        mock_tags.append(tag_mock)
    mock_part.tags.all.return_value = mock_tags
    return mock_part


class TestListParts:
    def test_list_parts_returns_list(self, mock_part_class: MagicMock) -> None:
        mock_part = _make_mock_part(tag_names=["smd", "resistor"])
        mock_part_class.objects.all.return_value.order_by.return_value.__getitem__ = MagicMock(return_value=[mock_part])

        from inventree_mcp_plugin.tools.simple.parts import list_parts

        result = list_parts(limit=10)
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["id"] == 1
        assert result[0]["name"] == "Resistor 10k"
        assert result[0]["tags"] == ["smd", "resistor"]

    def test_list_parts_with_category_filter(self, mock_part_class: MagicMock) -> None:
        mock_part_class.objects.all.return_value.filter.return_value.order_by.return_value.__getitem__ = MagicMock(
            return_value=[]
        )

        from inventree_mcp_plugin.tools.simple.parts import list_parts

        result = list_parts(category_id=5)
        mock_part_class.objects.all.return_value.filter.assert_called()
        assert isinstance(result, list)

    def test_list_parts_filter_by_single_tag(self, mock_part_class: MagicMock) -> None:
        mock_part = _make_mock_part(tag_names=["smd"])
        qs = mock_part_class.objects.all.return_value
        qs.filter.return_value = qs
        qs.distinct.return_value = qs
        qs.order_by.return_value.__getitem__ = MagicMock(return_value=[mock_part])

        from inventree_mcp_plugin.tools.simple.parts import list_parts

        result = list_parts(tags=["smd"])
        qs.filter.assert_called_with(tags__name="smd")
        qs.distinct.assert_called_once()
        assert result[0]["tags"] == ["smd"]

    def test_list_parts_filter_by_multiple_tags(self, mock_part_class: MagicMock) -> None:
        mock_part = _make_mock_part(tag_names=["smd", "resistor"])
        qs = mock_part_class.objects.all.return_value
        qs.filter.return_value = qs
        qs.distinct.return_value = qs
        qs.order_by.return_value.__getitem__ = MagicMock(return_value=[mock_part])

        from inventree_mcp_plugin.tools.simple.parts import list_parts

        result = list_parts(tags=["smd", "resistor"])
        assert qs.filter.call_count == 2
        qs.distinct.assert_called_once()
        assert set(result[0]["tags"]) == {"smd", "resistor"}


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
        mock_part.tags.all.return_value = []

        mock_part_class.objects.get.return_value = mock_part

        from inventree_mcp_plugin.tools.simple.parts import get_part

        result = get_part(42)
        assert result["id"] == 42
        assert result["name"] == "Capacitor 100uF"
        assert result["total_stock"] == 250.0
        assert result["tags"] == []


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


class TestDeleteParts:
    def _make_part(self, pk: int, name: str, active: bool = True, locked: bool = False) -> MagicMock:
        part = MagicMock()
        part.pk = pk
        part.name = name
        part.active = active
        part.locked = locked
        return part

    def test_deletes_active_parts(self, mock_part_class: MagicMock) -> None:
        part = self._make_part(1, "Resistor")
        mock_part_class.objects.get.return_value = part

        with patch("part.models.BomItem") as mock_bom:
            mock_bom.objects.filter.return_value.exists.return_value = False

            from inventree_mcp_plugin.tools.combinatory.parts import delete_parts

            result = delete_parts([1])

        assert result["deleted"] == [1]
        assert result["deleted_count"] == 1
        assert result["skipped"] == []
        assert result["skipped_count"] == 0
        # Part was active so it must be deactivated first
        assert part.active is False
        part.save.assert_called_once()
        part.delete.assert_called_once()

    def test_skips_already_inactive_save(self, mock_part_class: MagicMock) -> None:
        part = self._make_part(1, "Old Part", active=False)
        mock_part_class.objects.get.return_value = part

        with patch("part.models.BomItem") as mock_bom:
            mock_bom.objects.filter.return_value.exists.return_value = False

            from inventree_mcp_plugin.tools.combinatory.parts import delete_parts

            result = delete_parts([1])

        assert result["deleted"] == [1]
        part.save.assert_not_called()
        part.delete.assert_called_once()

    def test_skips_locked_part(self, mock_part_class: MagicMock) -> None:
        part = self._make_part(2, "Locked Part", locked=True)
        mock_part_class.objects.get.return_value = part

        from inventree_mcp_plugin.tools.combinatory.parts import delete_parts

        result = delete_parts([2])

        assert result["deleted"] == []
        assert result["skipped_count"] == 1
        assert result["skipped"][0]["reason"] == "Part is locked"
        part.delete.assert_not_called()

    def test_skips_part_in_assembly_by_default(self, mock_part_class: MagicMock) -> None:
        part = self._make_part(3, "Sub-part")
        mock_part_class.objects.get.return_value = part

        with patch("part.models.BomItem") as mock_bom:
            mock_bom.objects.filter.return_value.exists.return_value = True

            from inventree_mcp_plugin.tools.combinatory.parts import delete_parts

            result = delete_parts([3])

        assert result["deleted"] == []
        assert result["skipped"][0]["reason"] == "Part is used in assemblies"
        part.delete.assert_not_called()

    def test_deletes_part_in_assembly_when_flag_set(self, mock_part_class: MagicMock) -> None:
        part = self._make_part(3, "Sub-part")
        mock_part_class.objects.get.return_value = part

        with patch("part.models.BomItem") as mock_bom:
            mock_bom.objects.filter.return_value.exists.return_value = True

            from inventree_mcp_plugin.tools.combinatory.parts import delete_parts

            result = delete_parts([3], delete_from_assemblies=True)

        assert result["deleted"] == [3]
        part.delete.assert_called_once()

    def test_skips_missing_part(self, mock_part_class: MagicMock) -> None:
        mock_part_class.objects.get.side_effect = Exception("DoesNotExist")

        from inventree_mcp_plugin.tools.combinatory.parts import delete_parts

        result = delete_parts([99])

        assert result["deleted"] == []
        assert result["skipped"][0] == {"id": 99, "reason": "Part not found"}

    def test_mixed_batch(self, mock_part_class: MagicMock) -> None:
        ok_part = self._make_part(1, "OK Part")
        locked_part = self._make_part(2, "Locked", locked=True)

        def get_side_effect(pk: int) -> MagicMock:
            return {1: ok_part, 2: locked_part}[pk]

        mock_part_class.objects.get.side_effect = get_side_effect

        with patch("part.models.BomItem") as mock_bom:
            mock_bom.objects.filter.return_value.exists.return_value = False

            from inventree_mcp_plugin.tools.combinatory.parts import delete_parts

            result = delete_parts([1, 2])

        assert result["deleted"] == [1]
        assert result["skipped_count"] == 1
        assert result["skipped"][0]["id"] == 2


class TestListTags:
    def _make_tag(self, pk: int, name: str, slug: str) -> MagicMock:
        tag = MagicMock()
        tag.pk = pk
        tag.name = name
        tag.slug = slug
        return tag

    def test_list_tags_returns_list(self, mock_tag_class: MagicMock) -> None:
        tag = self._make_tag(1, "smd", "smd")
        mock_tag_class.objects.order_by.return_value.__getitem__ = MagicMock(return_value=[tag])

        from inventree_mcp_plugin.tools.simple.tags import list_tags

        result = list_tags()
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0] == {"id": 1, "name": "smd", "slug": "smd"}

    def test_list_tags_empty(self, mock_tag_class: MagicMock) -> None:
        mock_tag_class.objects.order_by.return_value.__getitem__ = MagicMock(return_value=[])

        from inventree_mcp_plugin.tools.simple.tags import list_tags

        result = list_tags()
        assert result == []


class TestSearchTags:
    def _make_tag(self, pk: int, name: str, slug: str) -> MagicMock:
        tag = MagicMock()
        tag.pk = pk
        tag.name = name
        tag.slug = slug
        return tag

    def test_search_tags_returns_matches(self, mock_tag_class: MagicMock) -> None:
        tag = self._make_tag(2, "resistor", "resistor")
        mock_tag_class.objects.filter.return_value.order_by.return_value.__getitem__ = MagicMock(return_value=[tag])

        from inventree_mcp_plugin.tools.simple.tags import search_tags

        result = search_tags("resi")  # cspell:disable-line
        mock_tag_class.objects.filter.assert_called_with(name__icontains="resi")  # cspell:disable-line
        assert len(result) == 1
        assert result[0]["name"] == "resistor"

    def test_search_tags_no_results(self, mock_tag_class: MagicMock) -> None:
        mock_tag_class.objects.filter.return_value.order_by.return_value.__getitem__ = MagicMock(return_value=[])

        from inventree_mcp_plugin.tools.simple.tags import search_tags

        result = search_tags("zzz")
        assert result == []
