"""Build order tools."""

from __future__ import annotations

from typing import Any

from ...mcp_server import mcp


@mcp.tool()
def list_build_orders(
    part_id: int | None = None,
    active: bool | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """List build orders with optional filtering.

    Args:
        part_id: Filter by part being built.
        active: Filter by active status.
        limit: Maximum number of results.
        offset: Number of results to skip.
    """
    from build.models import Build

    queryset = Build.objects.all()
    if part_id is not None:
        queryset = queryset.filter(part_id=part_id)
    if active is not None:
        queryset = queryset.filter(status__in=[10, 20]) if active else queryset.exclude(status__in=[10, 20])

    builds = queryset.order_by("-creation_date")[offset : offset + limit]
    return [
        {
            "id": b.pk,
            "reference": b.reference,
            "part": b.part_id,
            "part_name": b.part.name,
            "quantity": float(b.quantity),
            "status": b.status,
            "creation_date": str(b.creation_date) if b.creation_date else None,
            "target_date": str(b.target_date) if b.target_date else None,
            "completed": float(b.completed),
        }
        for b in builds
    ]


@mcp.tool()
def get_build_order(build_id: int) -> dict[str, Any]:
    """Get detailed information about a build order.

    Args:
        build_id: The ID of the build order.
    """
    from build.models import Build

    b = Build.objects.get(pk=build_id)
    return {
        "id": b.pk,
        "reference": b.reference,
        "part": b.part_id,
        "part_name": b.part.name,
        "quantity": float(b.quantity),
        "completed": float(b.completed),
        "status": b.status,
        "creation_date": str(b.creation_date) if b.creation_date else None,
        "target_date": str(b.target_date) if b.target_date else None,
        "completion_date": str(b.completion_date) if b.completion_date else None,
        "notes": b.notes,
        "destination": b.destination_id,
    }
