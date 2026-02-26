from collections.abc import Iterator
from typing import Any, Generic, TypeVar

_T = TypeVar("_T")

class _QuerySet(Generic[_T]):
    def filter(self, *args: Any, **kwargs: Any) -> _QuerySet[_T]: ...
    def exclude(self, *args: Any, **kwargs: Any) -> _QuerySet[_T]: ...
    def order_by(self, *fields: str) -> _QuerySet[_T]: ...
    def distinct(self) -> _QuerySet[_T]: ...
    def all(self) -> _QuerySet[_T]: ...
    def get(self, **kwargs: Any) -> _T: ...
    def create(self, **kwargs: Any) -> _T: ...
    def count(self) -> int: ...
    def __iter__(self) -> Iterator[_T]: ...
    def __getitem__(self, index: int | slice) -> Any: ...

class _Manager(Generic[_T]):
    def all(self) -> _QuerySet[_T]: ...
    def filter(self, *args: Any, **kwargs: Any) -> _QuerySet[_T]: ...
    def exclude(self, *args: Any, **kwargs: Any) -> _QuerySet[_T]: ...
    def get(self, **kwargs: Any) -> _T: ...
    def create(self, **kwargs: Any) -> _T: ...
    def order_by(self, *fields: str) -> _QuerySet[_T]: ...

class _Tag:
    name: str
    slug: str

class _TaggableManager:
    def all(self) -> _QuerySet[_Tag]: ...
    def count(self) -> int: ...

class Part:
    pk: int
    name: str
    description: str
    category_id: int | None
    active: bool
    IPN: str
    revision: str
    units: str
    assembly: bool
    component: bool
    purchaseable: bool
    salable: bool
    trackable: bool
    virtual: bool
    total_stock: float
    locked: bool
    tags: _TaggableManager
    objects: _Manager[Part]
    def save(self) -> None: ...
    def delete(self, **kwargs: Any) -> tuple[int, dict[str, int]]: ...

class PartCategory:
    pk: int
    name: str
    description: str
    parent_id: int | None
    pathstring: str
    parts: _Manager[Part]
    children: _Manager[PartCategory]
    objects: _Manager[PartCategory]

class BomItem:
    pk: int
    part_id: int
    part: Part
    sub_part_id: int
    sub_part: Part
    quantity: float
    reference: str
    optional: bool
    consumable: bool
    allow_variants: bool
    inherited: bool
    objects: _Manager[BomItem]
