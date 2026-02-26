"""Stock tools: list, get, adjust, transfer."""

from __future__ import annotations

# Prevent InvenTree's plugin scanner from picking up the `mcp` FastMCP instance.
__all__: list[str] = []

from typing import Any

from ...mcp_server import mcp
from ...tools import django_orm

# Direct ORM columns for StockItem (non-tree model; .only() is safe).
_STOCK_COLS: dict[str, str] = {
    "part": "part_id",
    "quantity": "quantity",
    "location": "location_id",
    "serial": "serial",
    "batch": "batch",
}


@mcp.tool()
@django_orm
def list_stock_items(
    part_id: int | None = None,
    location_id: int | None = None,
    limit: int = 100,
    offset: int = 0,
    fields: list[str] | None = None,
) -> list[dict[str, Any]]:
    """List stock items with optional filtering.

    Args:
        part_id: Filter by part ID.
        location_id: Filter by stock location ID.
        limit: Maximum number of results.
        offset: Number of results to skip.
        fields: Fields to include. Available: id, part, part_name, quantity, location,
                serial, batch. Defaults to all. ``id`` is always included.
    """
    from stock.models import StockItem

    want = set(fields) if fields is not None else set(_STOCK_COLS) | {"id", "part_name"}

    queryset = StockItem.objects.all()
    if part_id is not None:
        queryset = queryset.filter(part_id=part_id)
    if location_id is not None:
        queryset = queryset.filter(location_id=location_id)

    orm_cols = {"pk"} | {_STOCK_COLS[f] for f in want if f in _STOCK_COLS}
    want_part_name = "part_name" in want
    if want_part_name:
        orm_cols.add("part_id")
        queryset = queryset.select_related("part").only(*orm_cols, "part__name")
    else:
        queryset = queryset.only(*orm_cols)

    items = queryset.order_by("pk")[offset : offset + limit]
    results: list[dict[str, Any]] = []
    for item in items:
        row: dict[str, Any] = {"id": item.pk}
        if "part" in want:
            row["part"] = item.part_id
        if want_part_name:
            row["part_name"] = item.part.name
        if "quantity" in want:
            row["quantity"] = float(item.quantity)
        if "location" in want:
            row["location"] = item.location_id
        if "serial" in want:
            row["serial"] = item.serial
        if "batch" in want:
            row["batch"] = item.batch
        results.append(row)
    return results


@mcp.tool()
@django_orm
def get_stock_item(
    stock_item_id: int,
    fields: list[str] | None = None,
) -> dict[str, Any]:
    """Get detailed information about a specific stock item.

    Args:
        stock_item_id: The ID of the stock item.
        fields: Fields to include. Available: id, part, part_name, quantity, location,
                location_name, serial, batch, status, notes, updated. Defaults to all.
                ``id`` is always included.
    """
    from stock.models import StockItem

    detail_cols: dict[str, str] = {
        "part": "part_id",
        "quantity": "quantity",
        "location": "location_id",
        "serial": "serial",
        "batch": "batch",
        "status": "status",
        "notes": "notes",
        "updated": "updated",
    }
    want = set(fields) if fields is not None else set(detail_cols) | {"id", "part_name", "location_name"}

    want_part_name = "part_name" in want
    want_location_name = "location_name" in want

    orm_cols = {"pk"} | {detail_cols[f] for f in want if f in detail_cols}
    if want_part_name:
        orm_cols.add("part_id")
    if want_location_name:
        orm_cols.add("location_id")

    queryset = StockItem.objects.only(*orm_cols)
    if want_part_name:
        queryset = queryset.select_related("part")
    if want_location_name:
        queryset = queryset.select_related("location")

    item = queryset.get(pk=stock_item_id)
    row: dict[str, Any] = {"id": item.pk}
    if "part" in want:
        row["part"] = item.part_id
    if want_part_name:
        row["part_name"] = item.part.name
    if "quantity" in want:
        row["quantity"] = float(item.quantity)
    if "location" in want:
        row["location"] = item.location_id
    if want_location_name:
        row["location_name"] = item.location.name if item.location else None
    if "serial" in want:
        row["serial"] = item.serial
    if "batch" in want:
        row["batch"] = item.batch
    if "status" in want:
        row["status"] = item.status
    if "notes" in want:
        row["notes"] = item.notes or ""
    if "updated" in want:
        row["updated"] = str(item.updated) if item.updated else None
    return row


@mcp.tool()
@django_orm
def adjust_stock(stock_item_id: int, quantity: float, notes: str = "") -> dict[str, Any]:
    """Adjust the quantity of a stock item (add or remove stock).

    Args:
        stock_item_id: The ID of the stock item.
        quantity: Quantity to adjust by (positive to add, negative to remove).
        notes: Notes for the stock adjustment.
    """
    from decimal import Decimal

    from stock.models import StockItem

    item = StockItem.objects.get(pk=stock_item_id)
    if quantity > 0:
        item.add_stock(Decimal(str(quantity)), None, notes=notes)
    elif quantity < 0:
        item.take_stock(Decimal(str(abs(quantity))), None, notes=notes)

    item.refresh_from_db()
    return {
        "id": item.pk,
        "quantity": float(item.quantity),
        "notes": notes,
    }


@mcp.tool()
@django_orm
def transfer_stock(stock_item_id: int, location_id: int, notes: str = "") -> dict[str, Any]:
    """Transfer a stock item to a different location.

    Args:
        stock_item_id: The ID of the stock item to transfer.
        location_id: The destination location ID.
        notes: Notes for the transfer.
    """
    from stock.models import StockItem, StockLocation

    item = StockItem.objects.get(pk=stock_item_id)
    location = StockLocation.objects.get(pk=location_id)
    item.move(location, notes=notes, user=None)
    item.refresh_from_db()
    return {
        "id": item.pk,
        "quantity": float(item.quantity),
        "location": item.location_id,
        "location_name": item.location.name if item.location else None,
    }
