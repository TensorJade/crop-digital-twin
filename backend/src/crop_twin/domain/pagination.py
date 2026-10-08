"""Immutable bounded page shared by business modules."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Page[T]:
    """A page of records with navigation facts, without transport dependencies."""

    items: list[T]
    total: int
    limit: int
    offset: int
