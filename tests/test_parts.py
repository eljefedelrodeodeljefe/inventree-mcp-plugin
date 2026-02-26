"""Unit tests for part tools."""

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
    async def test_list_parts_returns_list(self, mock_part_class: MagicMock) -> None:
        mock_part = _make_mock_part(tag_names=["smd", "resistor"])
        mock_part_class.objects.all.return_value.order_by.return_value.__getitem__ = MagicMock(return_value=[mock_part])

        from inventree_mcp_plugin.tools.simple.parts import list_parts

        result = await list_parts(limit=10)
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["id"] == 1
        assert result[0]["name"] == "Resistor 10k"
        assert result[0]["tags"] == ["smd", "resistor"]

    async def test_list_parts_with_category_filter(self, mock_part_class: MagicMock) -> None:
        mock_part_class.objects.all.return_value.filter.return_value.order_by.return_value.__getitem__ = MagicMock(
            return_value=[]
        )

        from inventree_mcp_plugin.tools.simple.parts import list_parts

        result = await list_parts(category_id=5)
        mock_part_class.objects.all.return_value.filter.assert_called()
        assert isinstance(result, list)

    async def test_list_parts_filter_by_single_tag(self, mock_part_class: MagicMock) -> None:
        mock_part = _make_mock_part(tag_names=["smd"])
        qs = mock_part_class.objects.all.return_value
        qs.filter.return_value = qs
        qs.distinct.return_value = qs
        qs.order_by.return_value.__getitem__ = MagicMock(return_value=[mock_part])

        from inventree_mcp_plugin.tools.simple.parts import list_parts

        result = await list_parts(tags=["smd"])
        qs.filter.assert_called_with(tags__name="smd")
        qs.distinct.assert_called_once()
        assert result[0]["tags"] == ["smd"]

    async def test_list_parts_filter_by_multiple_tags(self, mock_part_class: MagicMock) -> None:
        mock_part = _make_mock_part(tag_names=["smd", "resistor"])
        qs = mock_part_class.objects.all.return_value
        qs.filter.return_value = qs
        qs.distinct.return_value = qs
        qs.order_by.return_value.__getitem__ = MagicMock(return_value=[mock_part])

        from inventree_mcp_plugin.tools.simple.parts import list_parts

        result = await list_parts(tags=["smd", "resistor"])
        assert qs.filter.call_count == 2
        qs.distinct.assert_called_once()
        assert set(result[0]["tags"]) == {"smd", "resistor"}


class TestGetPart:
    async def test_get_part_returns_dict(self, mock_part_class: MagicMock) -> None:
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

        result = await get_part(42)
        assert result["id"] == 42
        assert result["name"] == "Capacitor 100uF"
        assert result["total_stock"] == 250.0
        assert result["tags"] == []


class TestSearchParts:
    async def test_search_parts(self, mock_part_class: MagicMock) -> None:
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

        result = await search_parts("Resistor")
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["name"] == "Resistor"


class TestCreatePart:
    async def test_create_part(self, mock_part_class: MagicMock) -> None:
        mock_part = MagicMock()
        mock_part.pk = 99
        mock_part.name = "New Part"
        mock_part.description = "A new part"
        mock_part_class.objects.create.return_value = mock_part

        mock_category = MagicMock()
        with patch("part.models.PartCategory") as mock_cat_class:
            mock_cat_class.objects.get.return_value = mock_category

            from inventree_mcp_plugin.tools.simple.parts import create_part

            result = await create_part(name="New Part", description="A new part", category_id=1)
            assert result["id"] == 99
            assert result["name"] == "New Part"
