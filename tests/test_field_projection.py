"""Tests for the ``fields`` parameter (field projection) across tools.

Covers:
- ``_project`` helper directly
- Manual projection in list/get tools (parts, stock, builds)
- ``_project``-based projection (categories, locations, tags)
- ORM optimizations: conditional ``.only()``, ``.select_related()``, ``.prefetch_related()``
- Conditional count-query skipping (``get_category``, ``get_location``)
"""

from __future__ import annotations

from unittest.mock import MagicMock

from inventree_mcp_plugin.tools import _project

# ── _project helper ──────────────────────────────────────────────────────────


class TestProjectHelper:
    def test_none_returns_full_row(self) -> None:
        row = {"id": 1, "name": "X", "description": "Y"}
        assert _project(row, None) == row

    def test_filters_to_requested_fields(self) -> None:
        row = {"id": 1, "name": "X", "description": "Y", "active": True}
        assert _project(row, ["name"]) == {"id": 1, "name": "X"}

    def test_id_always_included_even_when_omitted(self) -> None:
        row = {"id": 1, "name": "X"}
        assert _project(row, []) == {"id": 1}

    def test_unknown_fields_silently_ignored(self) -> None:
        row = {"id": 1, "name": "X"}
        assert _project(row, ["name", "nonexistent"]) == {"id": 1, "name": "X"}

    def test_multiple_fields(self) -> None:
        row = {"id": 1, "name": "X", "description": "Y", "active": True}
        assert _project(row, ["name", "active"]) == {"id": 1, "name": "X", "active": True}


# ── list_parts fields ───────────────────────────────────────────────────────


def _make_mock_part() -> MagicMock:
    p = MagicMock()
    p.pk = 1
    p.name = "Resistor 10k"
    p.description = "10k ohm resistor"
    p.category_id = 5
    p.active = True
    p.IPN = "R-10K"
    p.revision = "A"
    p.units = "pcs"
    tag = MagicMock()
    tag.name = "smd"
    p.tags.all.return_value = [tag]
    return p


class TestListPartsFields:
    async def test_only_requested_fields_returned(self, mock_part_class: MagicMock) -> None:
        part = _make_mock_part()
        mock_part_class.objects.all.return_value.order_by.return_value.__getitem__ = MagicMock(return_value=[part])

        from inventree_mcp_plugin.tools.simple.parts import list_parts

        result = await list_parts(fields=["name", "active"])
        assert set(result[0].keys()) == {"id", "name", "active"}

    async def test_id_always_present(self, mock_part_class: MagicMock) -> None:
        part = _make_mock_part()
        mock_part_class.objects.all.return_value.order_by.return_value.__getitem__ = MagicMock(return_value=[part])

        from inventree_mcp_plugin.tools.simple.parts import list_parts

        result = await list_parts(fields=["name"])
        assert "id" in result[0]
        assert result[0]["id"] == 1

    async def test_empty_fields_returns_only_id(self, mock_part_class: MagicMock) -> None:
        part = _make_mock_part()
        mock_part_class.objects.all.return_value.order_by.return_value.__getitem__ = MagicMock(return_value=[part])

        from inventree_mcp_plugin.tools.simple.parts import list_parts

        result = await list_parts(fields=[])
        assert set(result[0].keys()) == {"id"}

    async def test_unknown_fields_silently_dropped(self, mock_part_class: MagicMock) -> None:
        part = _make_mock_part()
        mock_part_class.objects.all.return_value.order_by.return_value.__getitem__ = MagicMock(return_value=[part])

        from inventree_mcp_plugin.tools.simple.parts import list_parts

        result = await list_parts(fields=["name", "nonexistent_field"])
        assert set(result[0].keys()) == {"id", "name"}

    async def test_tags_excluded_skips_prefetch(self, mock_part_class: MagicMock) -> None:
        part = _make_mock_part()
        qs = mock_part_class.objects.all.return_value
        qs.order_by.return_value.__getitem__ = MagicMock(return_value=[part])

        from inventree_mcp_plugin.tools.simple.parts import list_parts

        result = await list_parts(fields=["name"])
        assert "tags" not in result[0]
        qs.prefetch_related.assert_not_called()

    async def test_tags_included_triggers_prefetch(self, mock_part_class: MagicMock) -> None:
        part = _make_mock_part()
        qs = mock_part_class.objects.all.return_value
        qs.order_by.return_value.__getitem__ = MagicMock(return_value=[part])

        from inventree_mcp_plugin.tools.simple.parts import list_parts

        result = await list_parts(fields=["name", "tags"])
        assert result[0]["tags"] == ["smd"]
        qs.prefetch_related.assert_called_with("tags")


# ── get_part fields ──────────────────────────────────────────────────────────


def _make_mock_part_detail() -> MagicMock:
    p = MagicMock()
    p.pk = 42
    p.name = "Cap 100uF"
    p.description = "Electrolytic capacitor"
    p.category_id = 3
    p.active = True
    p.IPN = "C-100"
    p.revision = ""
    p.units = "pcs"
    p.assembly = False
    p.component = True
    p.purchaseable = True
    p.salable = False
    p.trackable = False
    p.virtual = False
    p.total_stock = 250
    p.tags.all.return_value = []
    return p


class TestGetPartFields:
    async def test_fields_filter(self, mock_part_class: MagicMock) -> None:
        part = _make_mock_part_detail()
        mock_part_class.objects.get.return_value = part

        from inventree_mcp_plugin.tools.simple.parts import get_part

        result = await get_part(42, fields=["name", "total_stock"])
        assert set(result.keys()) == {"id", "name", "total_stock"}
        assert result["name"] == "Cap 100uF"
        assert result["total_stock"] == 250.0

    async def test_tags_excluded_skips_prefetch(self, mock_part_class: MagicMock) -> None:
        part = _make_mock_part_detail()
        mock_part_class.objects.get.return_value = part
        qs = mock_part_class.objects.only.return_value

        from inventree_mcp_plugin.tools.simple.parts import get_part

        result = await get_part(42, fields=["name"])
        assert "tags" not in result
        qs.prefetch_related.assert_not_called()

    async def test_tags_included_triggers_prefetch(self, mock_part_class: MagicMock) -> None:
        part = _make_mock_part_detail()
        mock_part_class.objects.get.return_value = part
        qs = mock_part_class.objects.only.return_value

        from inventree_mcp_plugin.tools.simple.parts import get_part

        result = await get_part(42, fields=["name", "tags"])
        assert "tags" in result
        qs.prefetch_related.assert_called_with("tags")


# ── list_stock_items fields ──────────────────────────────────────────────────


def _make_mock_stock_item() -> MagicMock:
    item = MagicMock()
    item.pk = 10
    item.part_id = 1
    item.part.name = "Resistor"
    item.quantity = 100
    item.location_id = 5
    item.serial = None
    item.batch = "B001"
    return item


class TestListStockItemsFields:
    async def test_only_requested_fields_returned(self, mock_stock_item_class: MagicMock) -> None:
        item = _make_mock_stock_item()
        mock_stock_item_class.objects.all.return_value.order_by.return_value.__getitem__ = MagicMock(
            return_value=[item]
        )

        from inventree_mcp_plugin.tools.simple.stock import list_stock_items

        result = await list_stock_items(fields=["quantity", "location"])
        assert set(result[0].keys()) == {"id", "quantity", "location"}

    async def test_part_name_excluded_skips_select_related(self, mock_stock_item_class: MagicMock) -> None:
        item = _make_mock_stock_item()
        qs = mock_stock_item_class.objects.all.return_value
        qs.order_by.return_value.__getitem__ = MagicMock(return_value=[item])

        from inventree_mcp_plugin.tools.simple.stock import list_stock_items

        result = await list_stock_items(fields=["quantity"])
        assert "part_name" not in result[0]
        qs.select_related.assert_not_called()

    async def test_part_name_included_triggers_select_related(self, mock_stock_item_class: MagicMock) -> None:
        item = _make_mock_stock_item()
        qs = mock_stock_item_class.objects.all.return_value
        qs.order_by.return_value.__getitem__ = MagicMock(return_value=[item])

        from inventree_mcp_plugin.tools.simple.stock import list_stock_items

        result = await list_stock_items(fields=["part_name"])
        assert result[0]["part_name"] == "Resistor"
        qs.select_related.assert_called_with("part")


# ── list_categories fields (uses _project) ──────────────────────────────────


class TestListCategoriesFields:
    async def test_fields_filter(self, mock_part_category_class: MagicMock) -> None:
        cat = MagicMock()
        cat.pk = 1
        cat.name = "Electronics"
        cat.description = "Electronic components"
        cat.parent_id = None
        cat.pathstring = "Electronics"
        mock_part_category_class.objects.all.return_value.order_by.return_value.__getitem__ = MagicMock(
            return_value=[cat]
        )

        from inventree_mcp_plugin.tools.simple.categories import list_categories

        result = await list_categories(fields=["name"])
        assert set(result[0].keys()) == {"id", "name"}

    async def test_unknown_fields_ignored(self, mock_part_category_class: MagicMock) -> None:
        cat = MagicMock()
        cat.pk = 1
        cat.name = "Electronics"
        cat.description = "Electronic components"
        cat.parent_id = None
        cat.pathstring = "Electronics"
        mock_part_category_class.objects.all.return_value.order_by.return_value.__getitem__ = MagicMock(
            return_value=[cat]
        )

        from inventree_mcp_plugin.tools.simple.categories import list_categories

        result = await list_categories(fields=["name", "bogus"])
        assert set(result[0].keys()) == {"id", "name"}


# ── get_category fields (conditional count queries) ─────────────────────────


class TestGetCategoryFields:
    async def test_skips_count_queries_when_not_requested(self, mock_part_category_class: MagicMock) -> None:
        cat = MagicMock()
        cat.pk = 1
        cat.name = "Electronics"
        cat.description = "Electronic components"
        cat.parent_id = None
        cat.pathstring = "Electronics"
        mock_part_category_class.objects.get.return_value = cat

        from inventree_mcp_plugin.tools.simple.categories import get_category

        result = await get_category(1, fields=["name"])
        assert set(result.keys()) == {"id", "name"}
        cat.parts.count.assert_not_called()
        cat.children.count.assert_not_called()

    async def test_includes_counts_when_requested(self, mock_part_category_class: MagicMock) -> None:
        cat = MagicMock()
        cat.pk = 1
        cat.name = "Electronics"
        cat.parts.count.return_value = 42
        cat.children.count.return_value = 3
        mock_part_category_class.objects.get.return_value = cat

        from inventree_mcp_plugin.tools.simple.categories import get_category

        result = await get_category(1, fields=["name", "parts_count", "children_count"])
        assert result["parts_count"] == 42
        assert result["children_count"] == 3
        cat.parts.count.assert_called_once()
        cat.children.count.assert_called_once()


# ── get_location fields (conditional count queries) ──────────────────────────


class TestGetLocationFields:
    async def test_skips_count_queries_when_not_requested(self, mock_stock_location_class: MagicMock) -> None:
        loc = MagicMock()
        loc.pk = 1
        loc.name = "Warehouse A"
        loc.description = "Main warehouse"
        loc.parent_id = None
        loc.pathstring = "Warehouse A"
        mock_stock_location_class.objects.get.return_value = loc

        from inventree_mcp_plugin.tools.simple.locations import get_location

        result = await get_location(1, fields=["name"])
        assert set(result.keys()) == {"id", "name"}
        loc.stock_items.count.assert_not_called()
        loc.children.count.assert_not_called()

    async def test_includes_counts_when_requested(self, mock_stock_location_class: MagicMock) -> None:
        loc = MagicMock()
        loc.pk = 1
        loc.name = "Warehouse A"
        loc.stock_items.count.return_value = 100
        loc.children.count.return_value = 5
        mock_stock_location_class.objects.get.return_value = loc

        from inventree_mcp_plugin.tools.simple.locations import get_location

        result = await get_location(1, fields=["name", "items_count", "children_count"])
        assert result["items_count"] == 100
        assert result["children_count"] == 5


# ── list_tags fields (uses _project) ─────────────────────────────────────────


class TestListTagsFields:
    async def test_fields_filter(self, mock_tag_class: MagicMock) -> None:
        tag = MagicMock()
        tag.pk = 1
        tag.name = "smd"
        tag.slug = "smd"
        mock_tag_class.objects.order_by.return_value.__getitem__ = MagicMock(return_value=[tag])

        from inventree_mcp_plugin.tools.simple.tags import list_tags

        result = await list_tags(fields=["name"])
        assert set(result[0].keys()) == {"id", "name"}
        assert "slug" not in result[0]

    async def test_search_tags_fields_filter(self, mock_tag_class: MagicMock) -> None:
        tag = MagicMock()
        tag.pk = 2
        tag.name = "resistor"
        tag.slug = "resistor"
        mock_tag_class.objects.filter.return_value.order_by.return_value.__getitem__ = MagicMock(return_value=[tag])

        from inventree_mcp_plugin.tools.simple.tags import search_tags

        result = await search_tags("resi", fields=["name"])  # cspell:disable-line
        assert set(result[0].keys()) == {"id", "name"}


# ── list_locations fields (uses _project) ────────────────────────────────────


class TestListLocationsFields:
    async def test_fields_filter(self, mock_stock_location_class: MagicMock) -> None:
        loc = MagicMock()
        loc.pk = 1
        loc.name = "Warehouse A"
        loc.description = "Main warehouse"
        loc.parent_id = None
        loc.pathstring = "Warehouse A"
        mock_stock_location_class.objects.all.return_value.order_by.return_value.__getitem__ = MagicMock(
            return_value=[loc]
        )

        from inventree_mcp_plugin.tools.simple.locations import list_locations

        result = await list_locations(fields=["name", "pathstring"])
        assert set(result[0].keys()) == {"id", "name", "pathstring"}
