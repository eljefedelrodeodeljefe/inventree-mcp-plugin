from collections.abc import Iterator
from datetime import date
from decimal import Decimal
from typing import Any, Generic, TypeVar

_T = TypeVar("_T")

class _QuerySet(Generic[_T]):
    def filter(self, *args: Any, **kwargs: Any) -> _QuerySet[_T]: ...
    def exclude(self, *args: Any, **kwargs: Any) -> _QuerySet[_T]: ...
    def order_by(self, *fields: str) -> _QuerySet[_T]: ...
    def all(self) -> _QuerySet[_T]: ...
    def get(self, **kwargs: Any) -> _T: ...
    def count(self) -> int: ...
    def __iter__(self) -> Iterator[_T]: ...
    def __getitem__(self, index: int | slice) -> Any: ...

class _Manager(Generic[_T]):
    def all(self) -> _QuerySet[_T]: ...
    def filter(self, *args: Any, **kwargs: Any) -> _QuerySet[_T]: ...
    def exclude(self, *args: Any, **kwargs: Any) -> _QuerySet[_T]: ...
    def get(self, **kwargs: Any) -> _T: ...
    def order_by(self, *fields: str) -> _QuerySet[_T]: ...

class _LineItem:
    pk: int
    part: Any
    quantity: float
    reference: str

class PurchaseOrderLineItem(_LineItem):
    received: float

class SalesOrderLineItem(_LineItem):
    shipped: float

class PurchaseOrder:
    pk: int
    reference: str
    supplier_id: int
    supplier: Any
    status: int
    description: str
    creation_date: date | None
    target_date: date | None
    total_price: Decimal | None
    lines: _Manager[PurchaseOrderLineItem]
    objects: _Manager[PurchaseOrder]

class SalesOrder:
    pk: int
    reference: str
    customer_id: int
    customer: Any
    status: int
    description: str
    creation_date: date | None
    target_date: date | None
    lines: _Manager[SalesOrderLineItem]
    objects: _Manager[SalesOrder]
