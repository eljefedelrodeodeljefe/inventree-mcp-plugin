"""Purchase/Sales order tools."""

from __future__ import annotations

# Prevent InvenTree's plugin scanner from picking up the `mcp` FastMCP instance.
__all__: list[str] = []

from typing import Any

from ...mcp_server import mcp
from ...tools import django_orm

_PO_COLS: dict[str, str] = {
    "reference": "reference",
    "supplier": "supplier_id",
    "status": "status",
    "description": "description",
    "creation_date": "creation_date",
    "target_date": "target_date",
}

_SO_COLS: dict[str, str] = {
    "reference": "reference",
    "customer": "customer_id",
    "status": "status",
    "description": "description",
    "creation_date": "creation_date",
    "target_date": "target_date",
}


@mcp.tool()
@django_orm
def list_purchase_orders(
    supplier_id: int | None = None,
    outstanding: bool | None = None,
    limit: int = 100,
    offset: int = 0,
    fields: list[str] | None = None,
) -> list[dict[str, Any]]:
    """List purchase orders with optional filtering.

    Args:
        supplier_id: Filter by supplier company ID.
        outstanding: Filter by outstanding status.
        limit: Maximum number of results.
        offset: Number of results to skip.
        fields: Fields to include. Available: id, reference, supplier, supplier_name,
                status, description, creation_date, target_date. Defaults to all.
                ``id`` is always included.
    """
    from order.models import PurchaseOrder

    want = set(fields) if fields is not None else set(_PO_COLS) | {"id", "supplier_name"}

    queryset = PurchaseOrder.objects.all()
    if supplier_id is not None:
        queryset = queryset.filter(supplier_id=supplier_id)
    if outstanding is not None:
        queryset = queryset.filter(status__in=[10, 20]) if outstanding else queryset.exclude(status__in=[10, 20])

    orm_cols = {"pk"} | {_PO_COLS[f] for f in want if f in _PO_COLS}
    want_supplier_name = "supplier_name" in want
    if want_supplier_name:
        orm_cols.add("supplier_id")
        queryset = queryset.select_related("supplier").only(*orm_cols, "supplier__name")
    else:
        queryset = queryset.only(*orm_cols)

    orders = queryset.order_by("-creation_date")[offset : offset + limit]
    results: list[dict[str, Any]] = []
    for order in orders:
        row: dict[str, Any] = {"id": order.pk}
        if "reference" in want:
            row["reference"] = order.reference
        if "supplier" in want:
            row["supplier"] = order.supplier_id
        if want_supplier_name:
            row["supplier_name"] = order.supplier.name if order.supplier else None
        if "status" in want:
            row["status"] = order.status
        if "description" in want:
            row["description"] = order.description or ""
        if "creation_date" in want:
            row["creation_date"] = str(order.creation_date) if order.creation_date else None
        if "target_date" in want:
            row["target_date"] = str(order.target_date) if order.target_date else None
        results.append(row)
    return results


@mcp.tool()
@django_orm
def get_purchase_order(
    order_id: int,
    fields: list[str] | None = None,
) -> dict[str, Any]:
    """Get detailed information about a purchase order.

    Args:
        order_id: The ID of the purchase order.
        fields: Fields to include. Available: id, reference, supplier, supplier_name,
                status, description, creation_date, target_date, lines, total_price.
                Defaults to all. ``id`` is always included.
    """
    from order.models import PurchaseOrder

    want = set(fields) if fields is not None else None

    queryset = PurchaseOrder.objects.all()
    if want is None or "supplier_name" in want or "supplier" in want:
        queryset = queryset.select_related("supplier")

    order = queryset.get(pk=order_id)
    row: dict[str, Any] = {"id": order.pk}
    if want is None or "reference" in want:
        row["reference"] = order.reference
    if want is None or "supplier" in want:
        row["supplier"] = order.supplier_id
    if want is None or "supplier_name" in want:
        row["supplier_name"] = order.supplier.name if order.supplier else None
    if want is None or "status" in want:
        row["status"] = order.status
    if want is None or "description" in want:
        row["description"] = order.description or ""
    if want is None or "creation_date" in want:
        row["creation_date"] = str(order.creation_date) if order.creation_date else None
    if want is None or "target_date" in want:
        row["target_date"] = str(order.target_date) if order.target_date else None
    if want is None or "lines" in want:
        row["lines"] = [
            {
                "id": line.pk,
                "part": line.part.pk if line.part else None,
                "part_name": line.part.name if line.part else None,
                "quantity": float(line.quantity),
                "received": float(line.received),
                "reference": line.reference or "",
            }
            for line in order.lines.all()
        ]
    if want is None or "total_price" in want:
        row["total_price"] = str(order.total_price) if order.total_price else None
    return row


@mcp.tool()
@django_orm
def list_sales_orders(
    customer_id: int | None = None,
    outstanding: bool | None = None,
    limit: int = 100,
    offset: int = 0,
    fields: list[str] | None = None,
) -> list[dict[str, Any]]:
    """List sales orders with optional filtering.

    Args:
        customer_id: Filter by customer company ID.
        outstanding: Filter by outstanding status.
        limit: Maximum number of results.
        offset: Number of results to skip.
        fields: Fields to include. Available: id, reference, customer, customer_name,
                status, description, creation_date, target_date. Defaults to all.
                ``id`` is always included.
    """
    from order.models import SalesOrder

    want = set(fields) if fields is not None else set(_SO_COLS) | {"id", "customer_name"}

    queryset = SalesOrder.objects.all()
    if customer_id is not None:
        queryset = queryset.filter(customer_id=customer_id)
    if outstanding is not None:
        queryset = queryset.filter(status__in=[10, 20]) if outstanding else queryset.exclude(status__in=[10, 20])

    orm_cols = {"pk"} | {_SO_COLS[f] for f in want if f in _SO_COLS}
    want_customer_name = "customer_name" in want
    if want_customer_name:
        orm_cols.add("customer_id")
        queryset = queryset.select_related("customer").only(*orm_cols, "customer__name")
    else:
        queryset = queryset.only(*orm_cols)

    orders = queryset.order_by("-creation_date")[offset : offset + limit]
    results: list[dict[str, Any]] = []
    for order in orders:
        row: dict[str, Any] = {"id": order.pk}
        if "reference" in want:
            row["reference"] = order.reference
        if "customer" in want:
            row["customer"] = order.customer_id
        if want_customer_name:
            row["customer_name"] = order.customer.name if order.customer else None
        if "status" in want:
            row["status"] = order.status
        if "description" in want:
            row["description"] = order.description or ""
        if "creation_date" in want:
            row["creation_date"] = str(order.creation_date) if order.creation_date else None
        if "target_date" in want:
            row["target_date"] = str(order.target_date) if order.target_date else None
        results.append(row)
    return results


@mcp.tool()
@django_orm
def get_sales_order(
    order_id: int,
    fields: list[str] | None = None,
) -> dict[str, Any]:
    """Get detailed information about a sales order.

    Args:
        order_id: The ID of the sales order.
        fields: Fields to include. Available: id, reference, customer, customer_name,
                status, description, creation_date, target_date, lines. Defaults to all.
                ``id`` is always included.
    """
    from order.models import SalesOrder

    want = set(fields) if fields is not None else None

    queryset = SalesOrder.objects.all()
    if want is None or "customer_name" in want or "customer" in want:
        queryset = queryset.select_related("customer")

    order = queryset.get(pk=order_id)
    row: dict[str, Any] = {"id": order.pk}
    if want is None or "reference" in want:
        row["reference"] = order.reference
    if want is None or "customer" in want:
        row["customer"] = order.customer_id
    if want is None or "customer_name" in want:
        row["customer_name"] = order.customer.name if order.customer else None
    if want is None or "status" in want:
        row["status"] = order.status
    if want is None or "description" in want:
        row["description"] = order.description or ""
    if want is None or "creation_date" in want:
        row["creation_date"] = str(order.creation_date) if order.creation_date else None
    if want is None or "target_date" in want:
        row["target_date"] = str(order.target_date) if order.target_date else None
    if want is None or "lines" in want:
        row["lines"] = [
            {
                "id": line.pk,
                "part": line.part.pk if line.part else None,
                "part_name": line.part.name if line.part else None,
                "quantity": float(line.quantity),
                "shipped": float(line.shipped),
                "reference": line.reference or "",
            }
            for line in order.lines.all()
        ]
    return row
