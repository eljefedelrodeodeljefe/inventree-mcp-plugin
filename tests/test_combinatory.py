"""Unit tests for combinatory tools."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


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
