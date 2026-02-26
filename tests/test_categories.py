"""Unit tests for category tools."""

from __future__ import annotations

from unittest.mock import MagicMock


class TestListCategories:
    async def test_list_categories(self, mock_part_category_class: MagicMock) -> None:
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

        result = await list_categories()
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["name"] == "Electronics"


class TestGetCategoryTree:
    def _make_cat(self, pk: int, name: str, parent_id: int | None) -> MagicMock:
        cat = MagicMock()
        cat.pk = pk
        cat.name = name
        cat.description = f"{name} description"
        cat.parent_id = parent_id
        return cat

    def _setup(self, mock_cls: MagicMock, cats: list) -> None:
        mock_cls.objects.all.return_value.order_by.return_value = cats

    async def test_single_db_query_regardless_of_depth(self, mock_part_category_class: MagicMock) -> None:
        """The whole tree must be fetched with exactly one objects.all() call."""
        root = self._make_cat(1, "Root", None)
        child = self._make_cat(2, "Child", 1)
        grandchild = self._make_cat(3, "Grandchild", 2)
        self._setup(mock_part_category_class, [root, child, grandchild])

        from inventree_mcp_plugin.tools.simple.categories import get_category_tree

        await get_category_tree()
        mock_part_category_class.objects.all.assert_called_once()

    async def test_correct_nesting_three_levels(self, mock_part_category_class: MagicMock) -> None:
        root = self._make_cat(1, "Root", None)
        child = self._make_cat(2, "Child", 1)
        grandchild = self._make_cat(3, "Grandchild", 2)
        self._setup(mock_part_category_class, [root, child, grandchild])

        from inventree_mcp_plugin.tools.simple.categories import get_category_tree

        result = await get_category_tree()
        assert [r["name"] for r in result] == ["Root"]
        assert [r["name"] for r in result[0]["children"]] == ["Child"]
        assert [r["name"] for r in result[0]["children"][0]["children"]] == ["Grandchild"]
        assert result[0]["children"][0]["children"][0]["children"] == []

    async def test_multiple_roots_returned(self, mock_part_category_class: MagicMock) -> None:
        """All top-level categories appear as roots when root_id is None."""
        a = self._make_cat(1, "Alpha", None)
        b = self._make_cat(2, "Beta", None)
        self._setup(mock_part_category_class, [a, b])

        from inventree_mcp_plugin.tools.simple.categories import get_category_tree

        result = await get_category_tree()
        assert [r["name"] for r in result] == ["Alpha", "Beta"]
        assert result[0]["children"] == []
        assert result[1]["children"] == []

    async def test_multiple_children_under_one_parent(self, mock_part_category_class: MagicMock) -> None:
        root = self._make_cat(1, "Root", None)
        c1 = self._make_cat(2, "Child A", 1)
        c2 = self._make_cat(3, "Child B", 1)
        self._setup(mock_part_category_class, [root, c1, c2])

        from inventree_mcp_plugin.tools.simple.categories import get_category_tree

        result = await get_category_tree()
        assert len(result) == 1
        assert [c["name"] for c in result[0]["children"]] == ["Child A", "Child B"]

    async def test_root_id_returns_children_of_that_node(self, mock_part_category_class: MagicMock) -> None:
        """root_id=N returns the children of N, not N itself."""
        root = self._make_cat(1, "Root", None)
        child = self._make_cat(2, "Child", 1)
        grandchild = self._make_cat(3, "Grandchild", 2)
        self._setup(mock_part_category_class, [root, child, grandchild])

        from inventree_mcp_plugin.tools.simple.categories import get_category_tree

        result = await get_category_tree(root_id=1)
        # Root itself is NOT in the result; its child is the top-level entry
        names = [r["name"] for r in result]
        assert "Root" not in names
        assert names == ["Child"]
        assert result[0]["children"][0]["name"] == "Grandchild"

    async def test_leaf_node_root_id_returns_empty(self, mock_part_category_class: MagicMock) -> None:
        """A leaf has no children, so root_id pointing to it returns []."""
        leaf = self._make_cat(5, "Leaf", 1)
        self._setup(mock_part_category_class, [leaf])

        from inventree_mcp_plugin.tools.simple.categories import get_category_tree

        result = await get_category_tree(root_id=5)
        assert result == []

    async def test_empty_database(self, mock_part_category_class: MagicMock) -> None:
        self._setup(mock_part_category_class, [])

        from inventree_mcp_plugin.tools.simple.categories import get_category_tree

        assert await get_category_tree() == []
        assert await get_category_tree(root_id=99) == []
