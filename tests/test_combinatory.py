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
