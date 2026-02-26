"""Purchase/Sales order tools."""

from __future__ import annotations

from typing import Any

from ...mcp_server import mcp


@mcp.tool()
def list_purchase_orders(
    supplier_id: int | None = None,
    outstanding: bool | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """List purchase orders with optional filtering.

    Args:
        supplier_id: Filter by supplier company ID.
        outstanding: Filter by outstanding status.
        limit: Maximum number of results.
        offset: Number of results to skip.
    """
    from order.models import PurchaseOrder

    queryset = PurchaseOrder.objects.all()
    if supplier_id is not None:
        queryset = queryset.filter(supplier_id=supplier_id)
    if outstanding is not None:
        queryset = queryset.filter(status__in=[10, 20]) if outstanding else queryset.exclude(status__in=[10, 20])

    orders = queryset.order_by("-creation_date")[offset : offset + limit]
    return [
        {
            "id": order.pk,
            "reference": order.reference,
            "supplier": order.supplier_id,
            "supplier_name": order.supplier.name if order.supplier else None,
            "status": order.status,
            "description": order.description,
            "creation_date": str(order.creation_date) if order.creation_date else None,
            "target_date": str(order.target_date) if order.target_date else None,
        }
        for order in orders
    ]


@mcp.tool()
def get_purchase_order(order_id: int) -> dict[str, Any]:
    """Get detailed information about a purchase order.

    Args:
        order_id: The ID of the purchase order.
    """
    from order.models import PurchaseOrder

    order = PurchaseOrder.objects.get(pk=order_id)
    lines = [
        {
            "id": line.pk,
            "part": line.part.pk if line.part else None,
            "part_name": line.part.name if line.part else None,
            "quantity": float(line.quantity),
            "received": float(line.received),
            "reference": line.reference,
        }
        for line in order.lines.all()
    ]
    return {
        "id": order.pk,
        "reference": order.reference,
        "supplier": order.supplier_id,
        "supplier_name": order.supplier.name if order.supplier else None,
        "status": order.status,
        "description": order.description,
        "creation_date": str(order.creation_date) if order.creation_date else None,
        "target_date": str(order.target_date) if order.target_date else None,
        "lines": lines,
        "total_price": str(order.total_price) if order.total_price else None,
    }


@mcp.tool()
def list_sales_orders(
    customer_id: int | None = None,
    outstanding: bool | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """List sales orders with optional filtering.

    Args:
        customer_id: Filter by customer company ID.
        outstanding: Filter by outstanding status.
        limit: Maximum number of results.
        offset: Number of results to skip.
    """
    from order.models import SalesOrder

    queryset = SalesOrder.objects.all()
    if customer_id is not None:
        queryset = queryset.filter(customer_id=customer_id)
    if outstanding is not None:
        queryset = queryset.filter(status__in=[10, 20]) if outstanding else queryset.exclude(status__in=[10, 20])

    orders = queryset.order_by("-creation_date")[offset : offset + limit]
    return [
        {
            "id": order.pk,
            "reference": order.reference,
            "customer": order.customer_id,
            "customer_name": order.customer.name if order.customer else None,
            "status": order.status,
            "description": order.description,
            "creation_date": str(order.creation_date) if order.creation_date else None,
            "target_date": str(order.target_date) if order.target_date else None,
        }
        for order in orders
    ]


@mcp.tool()
def get_sales_order(order_id: int) -> dict[str, Any]:
    """Get detailed information about a sales order.

    Args:
        order_id: The ID of the sales order.
    """
    from order.models import SalesOrder

    order = SalesOrder.objects.get(pk=order_id)
    lines = [
        {
            "id": line.pk,
            "part": line.part.pk if line.part else None,
            "part_name": line.part.name if line.part else None,
            "quantity": float(line.quantity),
            "shipped": float(line.shipped),
            "reference": line.reference,
        }
        for line in order.lines.all()
    ]
    return {
        "id": order.pk,
        "reference": order.reference,
        "customer": order.customer_id,
        "customer_name": order.customer.name if order.customer else None,
        "status": order.status,
        "description": order.description,
        "creation_date": str(order.creation_date) if order.creation_date else None,
        "target_date": str(order.target_date) if order.target_date else None,
        "lines": lines,
    }
