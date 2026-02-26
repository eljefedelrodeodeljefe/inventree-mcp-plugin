"""Build order tools."""

from __future__ import annotations

# Prevent InvenTree's plugin scanner from picking up the `mcp` FastMCP instance.
__all__: list[str] = []

from typing import Any

from ...mcp_server import mcp
from ...tools import django_orm

_BUILD_COLS: dict[str, str] = {
    "reference": "reference",
    "part": "part_id",
    "quantity": "quantity",
    "status": "status",
    "creation_date": "creation_date",
    "target_date": "target_date",
    "completed": "completed",
}


@mcp.tool()
@django_orm
def list_build_orders(
    part_id: int | None = None,
    active: bool | None = None,
    limit: int = 100,
    offset: int = 0,
    fields: list[str] | None = None,
) -> list[dict[str, Any]]:
    """List build orders with optional filtering.

    Args:
        part_id: Filter by part being built.
        active: Filter by active status.
        limit: Maximum number of results.
        offset: Number of results to skip.
        fields: Fields to include. Available: id, reference, part, part_name, quantity,
                status, creation_date, target_date, completed. Defaults to all.
                ``id`` is always included.
    """
    from build.models import Build

    want = set(fields) if fields is not None else set(_BUILD_COLS) | {"id", "part_name"}

    queryset = Build.objects.all()
    if part_id is not None:
        queryset = queryset.filter(part_id=part_id)
    if active is not None:
        queryset = queryset.filter(status__in=[10, 20]) if active else queryset.exclude(status__in=[10, 20])

    orm_cols = {"pk"} | {_BUILD_COLS[f] for f in want if f in _BUILD_COLS}
    want_part_name = "part_name" in want
    if want_part_name:
        orm_cols.add("part_id")
        queryset = queryset.select_related("part").only(*orm_cols, "part__name")
    else:
        queryset = queryset.only(*orm_cols)

    builds = queryset.order_by("-creation_date")[offset : offset + limit]
    results: list[dict[str, Any]] = []
    for b in builds:
        row: dict[str, Any] = {"id": b.pk}
        if "reference" in want:
            row["reference"] = b.reference
        if "part" in want:
            row["part"] = b.part_id
        if want_part_name:
            row["part_name"] = b.part.name
        if "quantity" in want:
            row["quantity"] = float(b.quantity)
        if "status" in want:
            row["status"] = b.status
        if "creation_date" in want:
            row["creation_date"] = str(b.creation_date) if b.creation_date else None
        if "target_date" in want:
            row["target_date"] = str(b.target_date) if b.target_date else None
        if "completed" in want:
            row["completed"] = float(b.completed)
        results.append(row)
    return results


@mcp.tool()
@django_orm
def get_build_order(
    build_id: int,
    fields: list[str] | None = None,
) -> dict[str, Any]:
    """Get detailed information about a build order.

    Args:
        build_id: The ID of the build order.
        fields: Fields to include. Available: id, reference, part, part_name, quantity,
                completed, status, creation_date, target_date, completion_date, notes,
                destination. Defaults to all. ``id`` is always included.
    """
    from build.models import Build

    want = set(fields) if fields is not None else None

    queryset = Build.objects.all()
    if want is None or "part_name" in want or "part" in want:
        queryset = queryset.select_related("part")

    b = queryset.get(pk=build_id)
    row: dict[str, Any] = {"id": b.pk}
    if want is None or "reference" in want:
        row["reference"] = b.reference
    if want is None or "part" in want:
        row["part"] = b.part_id
    if want is None or "part_name" in want:
        row["part_name"] = b.part.name
    if want is None or "quantity" in want:
        row["quantity"] = float(b.quantity)
    if want is None or "completed" in want:
        row["completed"] = float(b.completed)
    if want is None or "status" in want:
        row["status"] = b.status
    if want is None or "creation_date" in want:
        row["creation_date"] = str(b.creation_date) if b.creation_date else None
    if want is None or "target_date" in want:
        row["target_date"] = str(b.target_date) if b.target_date else None
    if want is None or "completion_date" in want:
        row["completion_date"] = str(b.completion_date) if b.completion_date else None
    if want is None or "notes" in want:
        row["notes"] = b.notes or ""
    if want is None or "destination" in want:
        row["destination"] = b.destination_id
    return row
