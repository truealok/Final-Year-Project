"""Shared response schemas: messages and generic pagination envelope."""

import math
from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Message(BaseModel):
    """Simple message response."""

    message: str


class Page(BaseModel, Generic[T]):
    """Generic paginated list response."""

    items: list[T]
    total: int
    page: int
    size: int
    pages: int

    @classmethod
    def build(cls, items: list[T], total: int, page: int, size: int) -> "Page[T]":
        return cls(
            items=items,
            total=total,
            page=page,
            size=size,
            pages=math.ceil(total / size) if total else 0,
        )
