"""Part tools: list, get, search, create, update."""

from __future__ import annotations

# Prevent InvenTree's plugin scanner from picking up the `mcp` FastMCP instance.
__all__: list[str] = []

from typing import Any

from ...mcp_server import mcp
from ...tools import django_orm

# Field → ORM column name for Part (non-tree model; .only() is safe).
_PART_COLS: dict[str, str] = {
    "name": "name",
    "description": "description",
    "category": "category_id",
    "active": "active",
    "IPN": "IPN",
    "revision": "revision",
    "units": "units",
}


@mcp.tool()
@django_orm
def list_parts(
    category_id: int | None = None,
    active: bool | None = None,
    tags: list[str] | None = None,
    limit: int = 100,
    offset: int = 0,
    fields: list[str] | None = None,
) -> list[dict[str, Any]]:
    """List parts with optional filtering by category, active status, and tags.

    Args:
        category_id: Filter by part category ID.
        active: Filter by active status.
        tags: Filter to parts that have ALL of the given tag names.
        limit: Maximum number of results to return.
        offset: Number of results to skip.
        fields: Fields to include in each result. Available: id, name, description,
                category, active, IPN, revision, units, total_stock, tags. Defaults to all.
                ``id`` is always included.
    """
    from part.models import Part

    want = set(fields) if fields is not None else set(_PART_COLS) | {"id", "total_stock", "tags"}

    queryset = Part.objects.all()
    if category_id is not None:
        queryset = queryset.filter(category_id=category_id)
    if active is not None:
        queryset = queryset.filter(active=active)
    if tags:
        for tag in tags:
            queryset = queryset.filter(tags__name=tag)
        queryset = queryset.distinct()

    orm_cols = {"pk"} | {_PART_COLS[f] for f in want if f in _PART_COLS}
    queryset = queryset.only(*orm_cols)

    want_tags = "tags" in want
    if want_tags:
        queryset = queryset.prefetch_related("tags")

    parts = queryset.order_by("pk")[offset : offset + limit]
    results: list[dict[str, Any]] = []
    for p in parts:
        row: dict[str, Any] = {"id": p.pk}
        if "name" in want:
            row["name"] = p.name
        if "description" in want:
            row["description"] = p.description
        if "category" in want:
            row["category"] = p.category_id
        if "active" in want:
            row["active"] = p.active
        if "IPN" in want:
            row["IPN"] = p.IPN or ""
        if "revision" in want:
            row["revision"] = p.revision or ""
        if "units" in want:
            row["units"] = p.units or ""
        if "total_stock" in want:
            row["total_stock"] = float(p.total_stock)
        if want_tags:
            row["tags"] = [t.name for t in p.tags.all()]
        results.append(row)
    return results


@mcp.tool()
@django_orm
def get_part(
    part_id: int,
    fields: list[str] | None = None,
) -> dict[str, Any]:
    """Get detailed information about a specific part.

    Args:
        part_id: The ID of the part to retrieve.
        fields: Fields to include. Available: id, name, description, category, active,
                IPN, revision, units, assembly, component, purchaseable, salable,
                trackable, virtual, total_stock, tags. Defaults to all.
                ``id`` is always included.
    """
    from part.models import Part

    detail_cols: dict[str, str] = {
        **_PART_COLS,
        "assembly": "assembly",
        "component": "component",
        "purchaseable": "purchaseable",
        "salable": "salable",
        "trackable": "trackable",
        "virtual": "virtual",
    }
    want = set(fields) if fields is not None else set(detail_cols) | {"id", "total_stock", "tags"}

    orm_cols = {"pk"} | {detail_cols[f] for f in want if f in detail_cols}
    queryset = Part.objects.only(*orm_cols)
    if "tags" in want:
        queryset = queryset.prefetch_related("tags")

    p = queryset.get(pk=part_id)
    row: dict[str, Any] = {"id": p.pk}
    if "name" in want:
        row["name"] = p.name
    if "description" in want:
        row["description"] = p.description
    if "category" in want:
        row["category"] = p.category_id
    if "active" in want:
        row["active"] = p.active
    if "IPN" in want:
        row["IPN"] = p.IPN or ""
    if "revision" in want:
        row["revision"] = p.revision or ""
    if "units" in want:
        row["units"] = p.units or ""
    if "assembly" in want:
        row["assembly"] = p.assembly
    if "component" in want:
        row["component"] = p.component
    if "purchaseable" in want:
        row["purchaseable"] = p.purchaseable
    if "salable" in want:
        row["salable"] = p.salable
    if "trackable" in want:
        row["trackable"] = p.trackable
    if "virtual" in want:
        row["virtual"] = p.virtual
    if "total_stock" in want:
        row["total_stock"] = float(p.total_stock)
    if "tags" in want:
        row["tags"] = [t.name for t in p.tags.all()]
    return row


@mcp.tool()
@django_orm
def search_parts(
    query: str,
    limit: int = 50,
    fields: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Search parts by name or description.

    Args:
        query: Search query string.
        limit: Maximum number of results.
        fields: Fields to include. Available: id, name, description, category, active.
                Defaults to all. ``id`` is always included.
    """
    from django.db.models import Q
    from part.models import Part

    search_cols: dict[str, str] = {
        "name": "name",
        "description": "description",
        "category": "category_id",
        "active": "active",
    }
    want = set(fields) if fields is not None else set(search_cols) | {"id"}
    orm_cols = {"pk"} | {search_cols[f] for f in want if f in search_cols}

    parts = (
        Part.objects
        .filter(Q(name__icontains=query) | Q(description__icontains=query))
        .only(*orm_cols)
        .order_by("name")[:limit]
    )
    results: list[dict[str, Any]] = []
    for p in parts:
        row: dict[str, Any] = {"id": p.pk}
        if "name" in want:
            row["name"] = p.name
        if "description" in want:
            row["description"] = p.description
        if "category" in want:
            row["category"] = p.category_id
        if "active" in want:
            row["active"] = p.active
        results.append(row)
    return results


@mcp.tool()
@django_orm
def create_part(
    name: str,
    description: str,
    category_id: int,
    IPN: str = "",
    revision: str = "",
    active: bool = True,
    assembly: bool = False,
    component: bool = True,
    purchaseable: bool = True,
    salable: bool = False,
    trackable: bool = False,
    virtual: bool = False,
    units: str = "",
) -> dict[str, Any]:
    """Create a new part.

    Args:
        name: Part name.
        description: Part description.
        category_id: Category ID to assign the part to.
        IPN: Internal Part Number.
        revision: Part revision string.
        active: Whether the part is active.
        assembly: Whether this part is an assembly.
        component: Whether this part is a component.
        purchaseable: Whether this part can be purchased.
        salable: Whether this part can be sold.
        trackable: Whether this part is trackable.
        virtual: Whether this part is virtual.
        units: Units of measure.
    """
    from part.models import Part, PartCategory

    category = PartCategory.objects.get(pk=category_id)
    p = Part.objects.create(
        name=name,
        description=description,
        category=category,
        IPN=IPN,
        revision=revision,
        active=active,
        assembly=assembly,
        component=component,
        purchaseable=purchaseable,
        salable=salable,
        trackable=trackable,
        virtual=virtual,
        units=units,
    )
    return {"id": p.pk, "name": p.name, "description": p.description}


@mcp.tool()
@django_orm
def update_part(part_id: int, **kwargs: bool | str) -> dict[str, Any]:
    """Update an existing part's fields.

    Args:
        part_id: The ID of the part to update.
        **kwargs: Fields to update (name, description, active, IPN, revision, units).
    """
    from part.models import Part

    allowed_fields = {"name", "description", "active", "IPN", "revision", "units"}
    p = Part.objects.get(pk=part_id)
    for field, value in kwargs.items():
        if field in allowed_fields:
            setattr(p, field, value)
    p.save()
    return {
        "id": p.pk,
        "name": p.name,
        "description": p.description,
        "active": p.active,
    }
