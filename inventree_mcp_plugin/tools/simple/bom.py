"""BOM (Bill of Materials) tools."""

from __future__ import annotations

from typing import Any

from ...mcp_server import mcp


@mcp.tool()
def list_bom_items(
    part_id: int | None = None,
    sub_part_id: int | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """List BOM items with optional filtering.

    Args:
        part_id: Filter by parent part ID.
        sub_part_id: Filter by sub-part ID.
        limit: Maximum number of results.
        offset: Number of results to skip.
    """
    from part.models import BomItem

    queryset = BomItem.objects.all()
    if part_id is not None:
        queryset = queryset.filter(part_id=part_id)
    if sub_part_id is not None:
        queryset = queryset.filter(sub_part_id=sub_part_id)

    items = queryset.order_by("pk")[offset : offset + limit]
    return [
        {
            "id": item.pk,
            "part": item.part_id,
            "part_name": item.part.name,
            "sub_part": item.sub_part_id,
            "sub_part_name": item.sub_part.name,
            "quantity": float(item.quantity),
            "reference": item.reference,
            "optional": item.optional,
        }
        for item in items
    ]


@mcp.tool()
def get_bom_for_part(part_id: int) -> dict[str, Any]:
    """Get the full BOM (Bill of Materials) for a specific part.

    Args:
        part_id: The ID of the parent part.
    """
    from part.models import BomItem, Part

    part = Part.objects.get(pk=part_id)
    bom_items = BomItem.objects.filter(part=part).order_by("pk")
    return {
        "part_id": part.pk,
        "part_name": part.name,
        "bom_items": [
            {
                "id": item.pk,
                "sub_part": item.sub_part_id,
                "sub_part_name": item.sub_part.name,
                "quantity": float(item.quantity),
                "reference": item.reference,
                "optional": item.optional,
                "consumable": item.consumable,
                "allow_variants": item.allow_variants,
                "inherited": item.inherited,
            }
            for item in bom_items
        ],
    }
