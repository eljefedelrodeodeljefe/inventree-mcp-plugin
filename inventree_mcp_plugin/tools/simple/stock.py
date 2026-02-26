"""Stock tools: list, get, adjust, transfer."""

from __future__ import annotations

# Prevent InvenTree's plugin scanner from picking up the `mcp` FastMCP instance.
__all__: list[str] = []

from typing_extensions import TypedDict

from ...mcp_server import mcp


class StockItemSummary(TypedDict):
    id: int
    part: int
    part_name: str
    quantity: float
    location: int | None
    serial: str | None
    batch: str | None


class StockItemDetail(TypedDict):
    id: int
    part: int
    part_name: str
    quantity: float
    location: int | None
    location_name: str | None
    serial: str | None
    batch: str | None
    status: int
    notes: str
    updated: str | None


class StockAdjustResult(TypedDict):
    id: int
    quantity: float
    notes: str


class StockTransferResult(TypedDict):
    id: int
    quantity: float
    location: int | None
    location_name: str | None


@mcp.tool()
def list_stock_items(
    part_id: int | None = None,
    location_id: int | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[StockItemSummary]:
    """List stock items with optional filtering.

    Args:
        part_id: Filter by part ID.
        location_id: Filter by stock location ID.
        limit: Maximum number of results.
        offset: Number of results to skip.
    """
    from stock.models import StockItem

    queryset = StockItem.objects.all()
    if part_id is not None:
        queryset = queryset.filter(part_id=part_id)
    if location_id is not None:
        queryset = queryset.filter(location_id=location_id)

    items = queryset.order_by("pk")[offset : offset + limit]
    return [
        {
            "id": item.pk,
            "part": item.part_id,
            "part_name": item.part.name,
            "quantity": float(item.quantity),
            "location": item.location_id,
            "serial": item.serial,
            "batch": item.batch,
        }
        for item in items
    ]


@mcp.tool()
def get_stock_item(stock_item_id: int) -> StockItemDetail:
    """Get detailed information about a specific stock item.

    Args:
        stock_item_id: The ID of the stock item.
    """
    from stock.models import StockItem

    item = StockItem.objects.get(pk=stock_item_id)
    return {
        "id": item.pk,
        "part": item.part_id,
        "part_name": item.part.name,
        "quantity": float(item.quantity),
        "location": item.location_id,
        "location_name": item.location.name if item.location else None,
        "serial": item.serial,
        "batch": item.batch,
        "status": item.status,
        "notes": item.notes,
        "updated": str(item.updated) if item.updated else None,
    }


@mcp.tool()
def adjust_stock(stock_item_id: int, quantity: float, notes: str = "") -> StockAdjustResult:
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
def transfer_stock(stock_item_id: int, location_id: int, notes: str = "") -> StockTransferResult:
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
