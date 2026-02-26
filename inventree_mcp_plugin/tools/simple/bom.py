"""BOM (Bill of Materials) tools."""

from __future__ import annotations

# Prevent InvenTree's plugin scanner from picking up the `mcp` FastMCP instance.
__all__: list[str] = []

from typing import Any

from ...mcp_server import mcp
from ...tools import django_orm

_BOM_COLS: dict[str, str] = {
    "part": "part_id",
    "sub_part": "sub_part_id",
    "quantity": "quantity",
    "reference": "reference",
    "optional": "optional",
}


@mcp.tool()
@django_orm
def list_bom_items(
    part_id: int | None = None,
    sub_part_id: int | None = None,
    limit: int = 100,
    offset: int = 0,
    fields: list[str] | None = None,
) -> list[dict[str, Any]]:
    """List BOM items with optional filtering.

    Args:
        part_id: Filter by parent part ID.
        sub_part_id: Filter by sub-part ID.
        limit: Maximum number of results.
        offset: Number of results to skip.
        fields: Fields to include. Available: id, part, part_name, sub_part,
                sub_part_name, quantity, reference, optional. Defaults to all.
                ``id`` is always included.
    """
    from part.models import BomItem

    want = set(fields) if fields is not None else set(_BOM_COLS) | {"id", "part_name", "sub_part_name"}

    queryset = BomItem.objects.all()
    if part_id is not None:
        queryset = queryset.filter(part_id=part_id)
    if sub_part_id is not None:
        queryset = queryset.filter(sub_part_id=sub_part_id)

    orm_cols = {"pk"} | {_BOM_COLS[f] for f in want if f in _BOM_COLS}
    want_part_name = "part_name" in want
    want_sub_part_name = "sub_part_name" in want
    if want_part_name:
        orm_cols.add("part_id")
        queryset = queryset.select_related("part")
    if want_sub_part_name:
        orm_cols.add("sub_part_id")
        queryset = queryset.select_related("sub_part")
    queryset = queryset.only(*orm_cols)

    items = queryset.order_by("pk")[offset : offset + limit]
    results: list[dict[str, Any]] = []
    for item in items:
        row: dict[str, Any] = {"id": item.pk}
        if "part" in want:
            row["part"] = item.part_id
        if want_part_name:
            row["part_name"] = item.part.name
        if "sub_part" in want:
            row["sub_part"] = item.sub_part_id
        if want_sub_part_name:
            row["sub_part_name"] = item.sub_part.name
        if "quantity" in want:
            row["quantity"] = float(item.quantity)
        if "reference" in want:
            row["reference"] = item.reference or ""
        if "optional" in want:
            row["optional"] = item.optional
        results.append(row)
    return results


@mcp.tool()
@django_orm
def get_bom_for_part(part_id: int) -> dict[str, Any]:
    """Get the full BOM (Bill of Materials) for a specific part.

    Args:
        part_id: The ID of the parent part.
    """
    from part.models import BomItem, Part

    part = Part.objects.get(pk=part_id)
    bom_items = BomItem.objects.filter(part=part).select_related("sub_part").order_by("pk")
    return {
        "part_id": part.pk,
        "part_name": part.name,
        "bom_items": [
            {
                "id": item.pk,
                "sub_part": item.sub_part_id,
                "sub_part_name": item.sub_part.name,
                "quantity": float(item.quantity),
                "reference": item.reference or "",
                "optional": item.optional,
                "consumable": item.consumable,
                "allow_variants": item.allow_variants,
                "inherited": item.inherited,
            }
            for item in bom_items
        ],
    }
