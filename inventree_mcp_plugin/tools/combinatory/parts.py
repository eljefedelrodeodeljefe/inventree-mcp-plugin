"""Combinatory part tools: operations that compose multiple simple steps."""

from __future__ import annotations

# Prevent InvenTree's plugin scanner from picking up the `mcp` FastMCP instance.
__all__: list[str] = []

from typing import NotRequired

from typing_extensions import TypedDict

from ...mcp_server import mcp


class SkippedPart(TypedDict):
    id: int
    name: NotRequired[str]  # absent when the part ID was not found
    reason: str


class DeletePartsResult(TypedDict):
    deleted: list[int]
    deleted_count: int
    skipped: list[SkippedPart]
    skipped_count: int


@mcp.tool()
def delete_parts(
    part_ids: list[int],
    delete_from_assemblies: bool = False,
) -> DeletePartsResult:
    """Delete multiple parts by ID in bulk.

    Each part is first deactivated (active=False), then deleted. The following
    records are cascade-deleted automatically by the database:

    - StockItem records for that part
    - Build orders targeting that part
    - SupplierPart records for that part

    SalesOrder and PurchaseOrder line items that reference deleted parts are
    preserved with a null part reference — they are NOT removed.

    A part is skipped without error when any of these conditions hold:

    - The part ID does not exist
    - The part is locked
    - The part is used as a sub-part in an assembly BOM and
      delete_from_assemblies=False (the default)

    Args:
        part_ids: List of part IDs to delete.
        delete_from_assemblies: When True, also delete parts that appear as
            sub-parts in assembly BOMs (those BomItem rows are cascade-deleted).
            Defaults to False for safety.

    Returns:
        A dict with:
        - deleted: list of successfully deleted part IDs
        - deleted_count: number of parts deleted
        - skipped: list of dicts with id, name (if found), and reason
        - skipped_count: number of parts skipped
    """
    from part.models import BomItem, Part

    deleted: list[int] = []
    skipped: list[SkippedPart] = []

    for part_id in part_ids:
        try:
            part = Part.objects.get(pk=part_id)
        except Exception:
            skipped.append({"id": part_id, "reason": "Part not found"})
            continue

        if part.locked:
            skipped.append({"id": part_id, "name": part.name, "reason": "Part is locked"})
            continue

        if not delete_from_assemblies and BomItem.objects.filter(sub_part=part).exists():
            skipped.append({"id": part_id, "name": part.name, "reason": "Part is used in assemblies"})
            continue

        if part.active:
            part.active = False
            part.save()

        try:
            part.delete()
        except Exception as exc:
            skipped.append({"id": part_id, "name": part.name, "reason": str(exc)})
            continue

        deleted.append(part_id)

    return {
        "deleted": deleted,
        "deleted_count": len(deleted),
        "skipped": skipped,
        "skipped_count": len(skipped),
    }
