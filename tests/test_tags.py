"""Unit tests for tag tools."""

from __future__ import annotations

from unittest.mock import MagicMock


def _make_tag(pk: int, name: str, slug: str) -> MagicMock:
    tag = MagicMock()
    tag.pk = pk
    tag.name = name
    tag.slug = slug
    return tag


class TestListTags:
    async def test_list_tags_returns_list(self, mock_tag_class: MagicMock) -> None:
        tag = _make_tag(1, "smd", "smd")
        mock_tag_class.objects.order_by.return_value.__getitem__ = MagicMock(return_value=[tag])

        from inventree_mcp_plugin.tools.simple.tags import list_tags

        result = await list_tags()
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0] == {"id": 1, "name": "smd", "slug": "smd"}

    async def test_list_tags_empty(self, mock_tag_class: MagicMock) -> None:
        mock_tag_class.objects.order_by.return_value.__getitem__ = MagicMock(return_value=[])

        from inventree_mcp_plugin.tools.simple.tags import list_tags

        result = await list_tags()
        assert result == []


class TestSearchTags:
    async def test_search_tags_returns_matches(self, mock_tag_class: MagicMock) -> None:
        tag = _make_tag(2, "resistor", "resistor")
        mock_tag_class.objects.filter.return_value.order_by.return_value.__getitem__ = MagicMock(return_value=[tag])

        from inventree_mcp_plugin.tools.simple.tags import search_tags

        result = await search_tags("resi")  # cspell:disable-line
        mock_tag_class.objects.filter.assert_called_with(name__icontains="resi")  # cspell:disable-line
        assert len(result) == 1
        assert result[0]["name"] == "resistor"

    async def test_search_tags_no_results(self, mock_tag_class: MagicMock) -> None:
        mock_tag_class.objects.filter.return_value.order_by.return_value.__getitem__ = MagicMock(return_value=[])

        from inventree_mcp_plugin.tools.simple.tags import search_tags

        result = await search_tags("zzz")
        assert result == []
