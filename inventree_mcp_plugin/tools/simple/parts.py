"""Part tools: list, get, search, create, update."""

from __future__ import annotations

# Prevent InvenTree's plugin scanner from picking up the `mcp` FastMCP instance.
__all__: list[str] = []

from typing_extensions import TypedDict

from ...mcp_server import mcp


class PartSummary(TypedDict):
    id: int
    name: str
    description: str
    category: int | None
    active: bool
    IPN: str
    revision: str
    units: str
    tags: list[str]


class PartDetail(TypedDict):
    id: int
    name: str
    description: str
    category: int | None
    active: bool
    IPN: str
    revision: str
    units: str
    assembly: bool
    component: bool
    purchaseable: bool
    salable: bool
    trackable: bool
    virtual: bool
    total_stock: float
    tags: list[str]


class PartSearchResult(TypedDict):
    id: int
    name: str
    description: str
    category: int | None
    active: bool


class PartCreateResult(TypedDict):
    id: int
    name: str
    description: str


class PartUpdateResult(TypedDict):
    id: int
    name: str
    description: str
    active: bool


@mcp.tool()
def list_parts(
    category_id: int | None = None,
    active: bool | None = None,
    tags: list[str] | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[PartSummary]:
    """List parts with optional filtering by category, active status, and tags.

    Args:
        category_id: Filter by part category ID.
        active: Filter by active status.
        tags: Filter to parts that have ALL of the given tag names.
        limit: Maximum number of results to return.
        offset: Number of results to skip.
    """
    from part.models import Part

    queryset = Part.objects.all()
    if category_id is not None:
        queryset = queryset.filter(category_id=category_id)
    if active is not None:
        queryset = queryset.filter(active=active)
    if tags:
        for tag in tags:
            queryset = queryset.filter(tags__name=tag)
        queryset = queryset.distinct()

    parts = queryset.order_by("pk")[offset : offset + limit]
    return [
        {
            "id": p.pk,
            "name": p.name,
            "description": p.description,
            "category": p.category_id,
            "active": p.active,
            "IPN": p.IPN,
            "revision": p.revision,
            "units": p.units,
            "tags": [t.name for t in p.tags.all()],
        }
        for p in parts
    ]


@mcp.tool()
def get_part(part_id: int) -> PartDetail:
    """Get detailed information about a specific part.

    Args:
        part_id: The ID of the part to retrieve.
    """
    from part.models import Part

    p = Part.objects.get(pk=part_id)
    return {
        "id": p.pk,
        "name": p.name,
        "description": p.description,
        "category": p.category_id,
        "active": p.active,
        "IPN": p.IPN,
        "revision": p.revision,
        "units": p.units,
        "assembly": p.assembly,
        "component": p.component,
        "purchaseable": p.purchaseable,
        "salable": p.salable,
        "trackable": p.trackable,
        "virtual": p.virtual,
        "total_stock": float(p.total_stock),
        "tags": [t.name for t in p.tags.all()],
    }


@mcp.tool()
def search_parts(query: str, limit: int = 50) -> list[PartSearchResult]:
    """Search parts by name or description.

    Args:
        query: Search query string.
        limit: Maximum number of results.
    """
    from django.db.models import Q
    from part.models import Part

    parts = Part.objects.filter(Q(name__icontains=query) | Q(description__icontains=query)).order_by("name")[:limit]
    return [
        {
            "id": p.pk,
            "name": p.name,
            "description": p.description,
            "category": p.category_id,
            "active": p.active,
        }
        for p in parts
    ]


@mcp.tool()
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
) -> PartCreateResult:
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
def update_part(part_id: int, **kwargs: bool | str) -> PartUpdateResult:
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
