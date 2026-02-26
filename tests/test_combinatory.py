"""Unit tests for combinatory tools."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


def _make_part(pk: int, name: str, active: bool = True, locked: bool = False) -> MagicMock:
    part = MagicMock()
    part.pk = pk
    part.name = name
    part.active = active
    part.locked = locked
    return part


class TestDeleteParts:
    async def test_deletes_active_parts(self, mock_part_class: MagicMock) -> None:
        part = _make_part(1, "Resistor")
        mock_part_class.objects.get.return_value = part

        with patch("part.models.BomItem") as mock_bom:
            mock_bom.objects.filter.return_value.exists.return_value = False

            from inventree_mcp_plugin.tools.combinatory.parts import delete_parts

            result = await delete_parts([1])

        assert result["deleted"] == [1]
        assert result["deleted_count"] == 1
        assert result["skipped"] == []
        assert result["skipped_count"] == 0
        # Part was active so it must be deactivated first
        assert part.active is False
        part.save.assert_called_once()
        part.delete.assert_called_once()

    async def test_skips_already_inactive_save(self, mock_part_class: MagicMock) -> None:
        part = _make_part(1, "Old Part", active=False)
        mock_part_class.objects.get.return_value = part

        with patch("part.models.BomItem") as mock_bom:
            mock_bom.objects.filter.return_value.exists.return_value = False

            from inventree_mcp_plugin.tools.combinatory.parts import delete_parts

            result = await delete_parts([1])

        assert result["deleted"] == [1]
        part.save.assert_not_called()
        part.delete.assert_called_once()

    async def test_skips_locked_part(self, mock_part_class: MagicMock) -> None:
        part = _make_part(2, "Locked Part", locked=True)
        mock_part_class.objects.get.return_value = part

        from inventree_mcp_plugin.tools.combinatory.parts import delete_parts

        result = await delete_parts([2])

        assert result["deleted"] == []
        assert result["skipped_count"] == 1
        assert result["skipped"][0]["reason"] == "Part is locked"
        part.delete.assert_not_called()

    async def test_skips_part_in_assembly_by_default(self, mock_part_class: MagicMock) -> None:
        part = _make_part(3, "Sub-part")
        mock_part_class.objects.get.return_value = part

        with patch("part.models.BomItem") as mock_bom:
            mock_bom.objects.filter.return_value.exists.return_value = True

            from inventree_mcp_plugin.tools.combinatory.parts import delete_parts

            result = await delete_parts([3])

        assert result["deleted"] == []
        assert result["skipped"][0]["reason"] == "Part is used in assemblies"
        part.delete.assert_not_called()

    async def test_deletes_part_in_assembly_when_flag_set(self, mock_part_class: MagicMock) -> None:
        part = _make_part(3, "Sub-part")
        mock_part_class.objects.get.return_value = part

        with patch("part.models.BomItem") as mock_bom:
            mock_bom.objects.filter.return_value.exists.return_value = True

            from inventree_mcp_plugin.tools.combinatory.parts import delete_parts

            result = await delete_parts([3], delete_from_assemblies=True)

        assert result["deleted"] == [3]
        part.delete.assert_called_once()

    async def test_skips_missing_part(self, mock_part_class: MagicMock) -> None:
        mock_part_class.objects.get.side_effect = Exception("DoesNotExist")

        from inventree_mcp_plugin.tools.combinatory.parts import delete_parts

        result = await delete_parts([99])

        assert result["deleted"] == []
        assert result["skipped"][0] == {"id": 99, "reason": "Part not found"}

    async def test_mixed_batch(self, mock_part_class: MagicMock) -> None:
        ok_part = _make_part(1, "OK Part")
        locked_part = _make_part(2, "Locked", locked=True)

        def get_side_effect(pk: int) -> MagicMock:
            return {1: ok_part, 2: locked_part}[pk]

        mock_part_class.objects.get.side_effect = get_side_effect

        with patch("part.models.BomItem") as mock_bom:
            mock_bom.objects.filter.return_value.exists.return_value = False

            from inventree_mcp_plugin.tools.combinatory.parts import delete_parts

            result = await delete_parts([1, 2])

        assert result["deleted"] == [1]
        assert result["skipped_count"] == 1
        assert result["skipped"][0]["id"] == 2


class TestStockPivot:
    @pytest.fixture()
    def stock_mocks(
        self,
        mock_stock_item_class: MagicMock,
        mock_part_category_class: MagicMock,
        mock_stock_location_class: MagicMock,
    ) -> tuple[MagicMock, MagicMock, MagicMock]:
        return mock_stock_item_class, mock_part_category_class, mock_stock_location_class

    async def test_basic_pivot_with_paths(self, stock_mocks: tuple[MagicMock, ...]) -> None:
        mock_si, mock_cat, mock_loc = stock_mocks

        # Aggregate rows returned by the ORM
        qs = mock_si.objects.all.return_value
        qs.values.return_value.annotate.return_value.order_by.return_value = [
            {"part__category": 1, "location": 10, "total_quantity": 100},
            {"part__category": 2, "location": 20, "total_quantity": 50},
        ]

        # Category info (pk, name, pathstring) — no subtree lookup when category_id is None
        mock_cat.objects.filter.return_value.values_list.side_effect = [
            [(1, "Electronics", "Electronics"), (2, "Mechanical", "Mechanical")],
        ]
        # Location info
        mock_loc.objects.filter.return_value.values_list.side_effect = [
            [(10, "Warehouse A", "Warehouse A"), (20, "Warehouse B", "Warehouse B")],
        ]

        from inventree_mcp_plugin.tools.combinatory.stock import stock_pivot

        result = await stock_pivot()
        assert len(result) == 2
        assert result[0] == {
            "category_id": 1,
            "category_name": "Electronics",
            "category_path": "Electronics",
            "location_id": 10,
            "location_name": "Warehouse A",
            "location_path": "Warehouse A",
            "total_quantity": 100.0,
        }
        assert result[1]["category_path"] == "Mechanical"
        assert result[1]["location_path"] == "Warehouse B"

    async def test_null_location_shown_as_unassigned(self, stock_mocks: tuple[MagicMock, ...]) -> None:
        mock_si, mock_cat, mock_loc = stock_mocks

        qs = mock_si.objects.all.return_value
        qs.values.return_value.annotate.return_value.order_by.return_value = [
            {"part__category": 1, "location": None, "total_quantity": 25},
        ]

        mock_cat.objects.filter.return_value.values_list.side_effect = [
            [(1, "Electronics", "Electronics")],
        ]
        mock_loc.objects.filter.return_value.values_list.side_effect = [
            [],
        ]

        from inventree_mcp_plugin.tools.combinatory.stock import stock_pivot

        result = await stock_pivot()
        assert len(result) == 1
        assert result[0]["location_id"] is None
        assert result[0]["location_name"] == "Unassigned"
        assert result[0]["location_path"] == "Unassigned"

    async def test_category_subtree_filter(self, stock_mocks: tuple[MagicMock, ...]) -> None:
        mock_si, mock_cat, mock_loc = stock_mocks

        # Root category pathstring lookup
        mock_cat.objects.filter.return_value.values_list.return_value.first.return_value = "Electronics"

        qs = mock_si.objects.all.return_value
        # After filter() for subtree, the chaining continues
        qs.filter.return_value.values.return_value.annotate.return_value.order_by.return_value = [
            {"part__category": 5, "location": 10, "total_quantity": 75},
        ]

        mock_cat.objects.filter.return_value.values_list.side_effect = [
            # first call: pathstring flat=True
            MagicMock(first=MagicMock(return_value="Electronics")),
            # second call: bulk info (pk, name, pathstring)
            [(5, "Sensors", "Electronics / Sensors")],
            # third call: max_depth check — not triggered (max_depth is None)
        ]
        mock_loc.objects.filter.return_value.values_list.side_effect = [
            [(10, "Shelf 1", "Warehouse / Shelf 1")],
        ]

        from inventree_mcp_plugin.tools.combinatory.stock import stock_pivot

        result = await stock_pivot(category_id=5)
        assert len(result) == 1
        assert result[0]["category_path"] == "Electronics / Sensors"
        assert result[0]["location_path"] == "Warehouse / Shelf 1"

    async def test_location_subtree_filter(self, stock_mocks: tuple[MagicMock, ...]) -> None:
        mock_si, mock_cat, mock_loc = stock_mocks

        # Location pathstring lookup
        mock_loc.objects.filter.return_value.values_list.return_value.first.return_value = "Warehouse"

        qs = mock_si.objects.all.return_value
        qs.filter.return_value.values.return_value.annotate.return_value.order_by.return_value = [
            {"part__category": 1, "location": 10, "total_quantity": 60},
        ]

        mock_cat.objects.filter.return_value.values_list.side_effect = [
            [(1, "Electronics", "Electronics")],
        ]
        mock_loc.objects.filter.return_value.values_list.side_effect = [
            # first call: pathstring flat=True
            MagicMock(first=MagicMock(return_value="Warehouse")),
            # second call: bulk info
            [(10, "Shelf 1", "Warehouse / Shelf 1")],
        ]

        from inventree_mcp_plugin.tools.combinatory.stock import stock_pivot

        result = await stock_pivot(location_id=10)
        assert len(result) == 1
        assert result[0]["location_path"] == "Warehouse / Shelf 1"

    async def test_max_depth_filter(self, stock_mocks: tuple[MagicMock, ...]) -> None:
        mock_si, mock_cat, mock_loc = stock_mocks

        qs = mock_si.objects.all.return_value
        qs.filter.return_value.values.return_value.annotate.return_value.order_by.return_value = [
            {"part__category": 1, "location": 10, "total_quantity": 100},
            {"part__category": 2, "location": 10, "total_quantity": 50},
            {"part__category": 3, "location": 10, "total_quantity": 30},
        ]

        # Category info: depth 0 = root, depth 1 = child, depth 2 = grandchild
        cat_data = [
            (1, "Electronics", "Electronics"),  # depth 0
            (2, "Sensors", "Electronics / Sensors"),  # depth 1
            (3, "Temp", "Electronics / Sensors / Temp"),  # depth 2
        ]

        mock_cat.objects.filter.return_value.values_list.side_effect = [
            # first call: pathstring flat=True for subtree filter
            MagicMock(first=MagicMock(return_value="Electronics")),
            # second call: bulk info
            cat_data,
            # third call: pathstring flat=True for max_depth check
            MagicMock(first=MagicMock(return_value="Electronics")),
        ]
        mock_loc.objects.filter.return_value.values_list.side_effect = [
            [(10, "Shelf 1", "Warehouse / Shelf 1")],
        ]

        from inventree_mcp_plugin.tools.combinatory.stock import stock_pivot

        # max_depth=1 should keep root (depth 0) and direct children (depth 1), prune depth 2
        result = await stock_pivot(category_id=1, max_depth=1)
        assert len(result) == 2
        category_ids = [r["category_id"] for r in result]
        assert 1 in category_ids  # root
        assert 2 in category_ids  # direct child
        assert 3 not in category_ids  # pruned grandchild


class TestStockByCategoryAndLocation:
    @pytest.fixture()
    def stock_mocks(
        self,
        mock_stock_item_class: MagicMock,
        mock_part_category_class: MagicMock,
        mock_stock_location_class: MagicMock,
    ) -> tuple[MagicMock, MagicMock, MagicMock]:
        return mock_stock_item_class, mock_part_category_class, mock_stock_location_class

    def _setup_stock_query(
        self,
        mock_stock_item_class: MagicMock,
        rows: list[dict[str, object]],
        *,
        with_filter: bool = False,
    ) -> None:
        qs = mock_stock_item_class.objects.all.return_value
        if with_filter:
            qs = qs.filter.return_value
        qs.values.return_value.annotate.return_value.order_by.return_value = rows

    async def test_aggregates_by_category_and_location(self, stock_mocks: tuple[MagicMock, ...]) -> None:
        mock_si, mock_cat, mock_loc = stock_mocks
        self._setup_stock_query(
            mock_si,
            [
                {"part__category": 1, "location": 10, "total_quantity": 100},
                {"part__category": 2, "location": 20, "total_quantity": 50},
            ],
        )
        mock_cat.objects.filter.return_value.values_list.return_value = [(1, "Electronics"), (2, "Mechanical")]
        mock_loc.objects.filter.return_value.values_list.return_value = [(10, "Warehouse A"), (20, "Warehouse B")]

        from inventree_mcp_plugin.tools.combinatory.stock import stock_by_category_and_location

        result = await stock_by_category_and_location()
        assert len(result) == 2
        assert result[0] == {
            "category_id": 1,
            "category_name": "Electronics",
            "location_id": 10,
            "location_name": "Warehouse A",
            "total_quantity": 100.0,
        }
        assert result[1] == {
            "category_id": 2,
            "category_name": "Mechanical",
            "location_id": 20,
            "location_name": "Warehouse B",
            "total_quantity": 50.0,
        }

    async def test_null_location_shown_as_unassigned(self, stock_mocks: tuple[MagicMock, ...]) -> None:
        mock_si, mock_cat, mock_loc = stock_mocks
        self._setup_stock_query(
            mock_si,
            [{"part__category": 1, "location": None, "total_quantity": 25}],
        )
        mock_cat.objects.filter.return_value.values_list.return_value = [(1, "Electronics")]
        mock_loc.objects.filter.return_value.values_list.return_value = []

        from inventree_mcp_plugin.tools.combinatory.stock import stock_by_category_and_location

        result = await stock_by_category_and_location()
        assert len(result) == 1
        assert result[0]["location_id"] is None
        assert result[0]["location_name"] == "Unassigned"

    async def test_category_filter(self, stock_mocks: tuple[MagicMock, ...]) -> None:
        mock_si, mock_cat, mock_loc = stock_mocks
        self._setup_stock_query(
            mock_si,
            [{"part__category": 5, "location": 10, "total_quantity": 75}],
            with_filter=True,
        )
        mock_cat.objects.filter.return_value.values_list.return_value = [(5, "Sensors")]
        mock_loc.objects.filter.return_value.values_list.return_value = [(10, "Shelf 1")]

        from inventree_mcp_plugin.tools.combinatory.stock import stock_by_category_and_location

        result = await stock_by_category_and_location(category_id=5)
        mock_si.objects.all.return_value.filter.assert_called_with(part__category=5)
        assert len(result) == 1
        assert result[0]["category_id"] == 5
        assert result[0]["category_name"] == "Sensors"
