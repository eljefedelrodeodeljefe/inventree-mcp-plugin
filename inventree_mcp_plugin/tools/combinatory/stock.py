"""Combinatory stock tools: aggregation across stock, categories, and locations."""

from __future__ import annotations

# Prevent InvenTree's plugin scanner from picking up the `mcp` FastMCP instance.
__all__: list[str] = []

from typing_extensions import TypedDict

from ...mcp_server import mcp
from ...tools import django_orm


class StockByCategoryLocationRow(TypedDict):
    category_id: int
    category_name: str
    location_id: int | None
    location_name: str
    total_quantity: float


@mcp.tool()
@django_orm
def stock_by_category_and_location(
    category_id: int | None = None,
) -> list[StockByCategoryLocationRow]:
    """Pivot-table view of stock quantity aggregated by part category and stock location.

    Returns a flat list of rows, each with a category/location pair and the total
    stock quantity for that combination. Useful for warehouse-level overviews
    without needing multiple round-trips.

    Args:
        category_id: Optional category ID to scope results to a single category.
    """
    from django.db.models import Sum
    from part.models import PartCategory
    from stock.models import StockItem, StockLocation

    queryset = StockItem.objects.all()
    if category_id is not None:
        queryset = queryset.filter(part__category=category_id)

    rows = list(
        queryset
        .values("part__category", "location")
        .annotate(total_quantity=Sum("quantity"))
        .order_by("part__category", "location")
    )

    cat_ids = {r["part__category"] for r in rows if r["part__category"] is not None}
    loc_ids = {r["location"] for r in rows if r["location"] is not None}

    cat_names: dict[int, str] = dict(PartCategory.objects.filter(pk__in=cat_ids).values_list("pk", "name"))
    loc_names: dict[int, str] = dict(StockLocation.objects.filter(pk__in=loc_ids).values_list("pk", "name"))

    return [
        {
            "category_id": r["part__category"],
            "category_name": cat_names.get(r["part__category"], "Unknown"),
            "location_id": r["location"],
            "location_name": loc_names.get(r["location"], "Unassigned") if r["location"] is not None else "Unassigned",
            "total_quantity": float(r["total_quantity"]),
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# stock_pivot — hierarchical stock pivot with full category/location paths
# ---------------------------------------------------------------------------


class StockPivotRow(TypedDict):
    category_id: int | None
    category_name: str
    category_path: str
    location_id: int | None
    location_name: str
    location_path: str
    total_quantity: float


@mcp.tool()
@django_orm
def stock_pivot(
    category_id: int | None = None,
    location_id: int | None = None,
    max_depth: int | None = None,
) -> list[StockPivotRow]:
    """Stock quantity pivot with full category/location hierarchy paths.

    Like ``stock_by_category_and_location`` but includes the full
    ``pathstring`` for both category and location, supports location subtree
    filtering, and optional depth limiting. Designed to replace multiple
    paginated calls with a single request.

    Args:
        category_id: Scope to this category and its descendants.
        location_id: Scope to this location and its descendants.
        max_depth: Maximum category tree depth relative to the root
            category (0 = root only, 1 = root + direct children, etc.).
            Ignored when *category_id* is None.
    """
    from django.db.models import Q, Sum
    from part.models import PartCategory
    from stock.models import StockItem, StockLocation

    queryset = StockItem.objects.all()

    # --- category subtree filter ---
    if category_id is not None:
        root_cat = PartCategory.objects.filter(pk=category_id).values_list("pathstring", flat=True).first()
        if root_cat is not None:
            cat_q = Q(part__category=category_id) | Q(part__category__pathstring__startswith=root_cat + " / ")
            queryset = queryset.filter(cat_q)
        else:
            queryset = queryset.filter(part__category=category_id)

    # --- location subtree filter ---
    if location_id is not None:
        root_loc = StockLocation.objects.filter(pk=location_id).values_list("pathstring", flat=True).first()
        if root_loc is not None:
            loc_q = Q(location=location_id) | Q(location__pathstring__startswith=root_loc + " / ")
            queryset = queryset.filter(loc_q)
        else:
            queryset = queryset.filter(location=location_id)

    # --- aggregate ---
    rows = list(
        queryset
        .values("part__category", "location")
        .annotate(total_quantity=Sum("quantity"))
        .order_by("part__category", "location")
    )

    # --- resolve names + paths in bulk ---
    cat_ids = {r["part__category"] for r in rows if r["part__category"] is not None}
    loc_ids = {r["location"] for r in rows if r["location"] is not None}

    cat_info: dict[int, tuple[str, str]] = {
        pk: (name, pathstring)
        for pk, name, pathstring in PartCategory.objects.filter(pk__in=cat_ids).values_list("pk", "name", "pathstring")
    }
    loc_info: dict[int, tuple[str, str]] = {
        pk: (name, pathstring)
        for pk, name, pathstring in StockLocation.objects.filter(pk__in=loc_ids).values_list("pk", "name", "pathstring")
    }

    # --- optional max_depth pruning ---
    if category_id is not None and max_depth is not None:
        root_cat = PartCategory.objects.filter(pk=category_id).values_list("pathstring", flat=True).first()
        if root_cat is not None:
            root_depth = root_cat.count(" / ")
            cat_ids_to_keep = {
                cid for cid, (_, pathstring) in cat_info.items() if pathstring.count(" / ") - root_depth <= max_depth
            }
            rows = [r for r in rows if r["part__category"] in cat_ids_to_keep]

    # --- build result ---
    result: list[StockPivotRow] = []
    for r in rows:
        cid = r["part__category"]
        lid = r["location"]
        c_name, c_path = cat_info.get(cid, ("Unknown", "Unknown"))
        if lid is not None:
            l_name, l_path = loc_info.get(lid, ("Unknown", "Unknown"))
        else:
            l_name, l_path = "Unassigned", "Unassigned"
        result.append({
            "category_id": cid,
            "category_name": c_name,
            "category_path": c_path,
            "location_id": lid,
            "location_name": l_name,
            "location_path": l_path,
            "total_quantity": float(r["total_quantity"]),
        })

    return result
