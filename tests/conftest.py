"""Test configuration and shared fixtures."""

from __future__ import annotations

import sys
from types import ModuleType
from unittest.mock import MagicMock

import pytest


def _make_stub_module(name: str) -> ModuleType:
    """Create a stub module."""
    mod = ModuleType(name)
    mod.__dict__.update({"__path__": [], "__file__": f"<stub:{name}>"})
    return mod


@pytest.fixture(autouse=True)
def _stub_inventree_modules(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stub out InvenTree and Django modules so tool code can be imported without a running InvenTree instance."""
    stubs: dict[str, ModuleType] = {}

    # Helper: create module and wire parent.child attribute
    def add_stub(name: str) -> ModuleType:
        mod = _make_stub_module(name)
        stubs[name] = mod
        # Wire parent -> child attribute
        if "." in name:
            parent_name, child_attr = name.rsplit(".", 1)
            if parent_name in stubs:
                setattr(stubs[parent_name], child_attr, mod)
        return mod

    # Django stubs
    for mod_name in [
        "django",
        "django.db",
        "django.db.models",
        "django.http",
        "django.urls",
        "django.views",
        "django.views.decorators",
        "django.views.decorators.csrf",
    ]:
        add_stub(mod_name)

    # DRF stubs
    for mod_name in [
        "rest_framework",
        "rest_framework.request",
    ]:
        add_stub(mod_name)

    # InvenTree plugin stubs
    for mod_name in [
        "plugin",
        "plugin.mixins",
    ]:
        add_stub(mod_name)

    # Add mock classes to plugin stubs
    stubs["plugin"].InvenTreePlugin = type("InvenTreePlugin", (), {})  # type: ignore[attr-defined]
    stubs["plugin.mixins"].SettingsMixin = type("SettingsMixin", (), {})  # type: ignore[attr-defined]
    stubs["plugin.mixins"].UrlsMixin = type("UrlsMixin", (), {})  # type: ignore[attr-defined]

    # Django ORM model stubs
    django_q = MagicMock()
    stubs["django.db.models"].Q = django_q  # type: ignore[attr-defined]
    stubs["django.db.models"].Sum = MagicMock()  # type: ignore[attr-defined]

    # InvenTree model stubs
    for mod_name in [
        "part",
        "part.models",
        "stock",
        "stock.models",
        "order",
        "order.models",
        "build",
        "build.models",
        "taggit",
        "taggit.models",
    ]:
        add_stub(mod_name)

    # Add placeholder model classes so monkeypatch.setattr works
    stubs["part.models"].Part = MagicMock()  # type: ignore[attr-defined]
    stubs["part.models"].PartCategory = MagicMock()  # type: ignore[attr-defined]
    stubs["part.models"].BomItem = MagicMock()  # type: ignore[attr-defined]
    stubs["stock.models"].StockItem = MagicMock()  # type: ignore[attr-defined]
    stubs["stock.models"].StockLocation = MagicMock()  # type: ignore[attr-defined]
    stubs["order.models"].PurchaseOrder = MagicMock()  # type: ignore[attr-defined]
    stubs["order.models"].SalesOrder = MagicMock()  # type: ignore[attr-defined]
    stubs["build.models"].Build = MagicMock()  # type: ignore[attr-defined]
    stubs["taggit.models"].Tag = MagicMock()  # type: ignore[attr-defined]

    for mod_name, mod in stubs.items():
        monkeypatch.setitem(sys.modules, mod_name, mod)


def _make_fluent_qs(mock_cls: MagicMock) -> MagicMock:
    """Return a queryset mock where all ORM chaining methods return the same object.

    This lets tests set up ``qs.order_by.return_value.__getitem__`` once and have
    the result survive any combination of ``.only()``, ``.select_related()``, etc.
    ``qs.get`` is aliased to ``mock_cls.objects.get`` so that tests can configure
    the return value on either path.
    """
    qs = mock_cls.objects.all.return_value
    for method in (
        "filter",
        "exclude",
        "only",
        "defer",
        "select_related",
        "prefetch_related",
        "distinct",
        "order_by",
        "values",
        "annotate",
        "values_list",
    ):
        getattr(qs, method).return_value = qs
    # Direct objects.* entry-points (tools that skip .all())
    mock_cls.objects.only.return_value = qs
    mock_cls.objects.filter.return_value = qs
    mock_cls.objects.order_by.return_value = qs
    # alias qs.get → objects.get so both code paths use the same mock
    qs.get = mock_cls.objects.get
    return qs


@pytest.fixture()
def mock_tag_class(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Provide a mock Tag model class."""
    mock_cls = MagicMock()
    _make_fluent_qs(mock_cls)
    monkeypatch.setattr("taggit.models.Tag", mock_cls)
    return mock_cls


@pytest.fixture()
def mock_part_class(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Provide a mock Part model class."""
    mock_cls = MagicMock()
    _make_fluent_qs(mock_cls)
    monkeypatch.setattr("part.models.Part", mock_cls)
    return mock_cls


@pytest.fixture()
def mock_bom_item_class(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Provide a mock BomItem model class."""
    mock_cls = MagicMock()
    _make_fluent_qs(mock_cls)
    monkeypatch.setattr("part.models.BomItem", mock_cls)
    return mock_cls


@pytest.fixture()
def mock_stock_item_class(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Provide a mock StockItem model class."""
    mock_cls = MagicMock()
    _make_fluent_qs(mock_cls)
    monkeypatch.setattr("stock.models.StockItem", mock_cls)
    return mock_cls


@pytest.fixture()
def mock_stock_location_class(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Provide a mock StockLocation model class."""
    mock_cls = MagicMock()
    _make_fluent_qs(mock_cls)
    monkeypatch.setattr("stock.models.StockLocation", mock_cls)
    return mock_cls


@pytest.fixture()
def mock_part_category_class(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Provide a mock PartCategory model class."""
    mock_cls = MagicMock()
    _make_fluent_qs(mock_cls)
    monkeypatch.setattr("part.models.PartCategory", mock_cls)
    return mock_cls


@pytest.fixture()
def mock_purchase_order_class(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Provide a mock PurchaseOrder model class."""
    mock_cls = MagicMock()
    _make_fluent_qs(mock_cls)
    monkeypatch.setattr("order.models.PurchaseOrder", mock_cls)
    return mock_cls


@pytest.fixture()
def mock_sales_order_class(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Provide a mock SalesOrder model class."""
    mock_cls = MagicMock()
    _make_fluent_qs(mock_cls)
    monkeypatch.setattr("order.models.SalesOrder", mock_cls)
    return mock_cls


@pytest.fixture()
def mock_build_class(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Provide a mock Build model class."""
    mock_cls = MagicMock()
    _make_fluent_qs(mock_cls)
    monkeypatch.setattr("build.models.Build", mock_cls)
    return mock_cls
