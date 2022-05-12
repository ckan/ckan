# -*- coding: utf-8 -*-

from typing import TYPE_CHECKING, Any, Callable, Dict, Generic, TypeVar

if TYPE_CHECKING:
    from . import Declaration


T = TypeVar("T", bound=Callable[..., Any])


class FormatHandler(Generic[T]):
    __slots__ = "_types"
    _types: Dict[str, T]

    def __init__(self):
        self._types = {}

    def register(self, fmt: str):
        def decorator(implementer: T):
            self._types[fmt] = implementer
            return implementer

        return decorator

    def handle(
        self, declaration: "Declaration", fmt: str, *args: Any, **kwargs: Any
    ):
        try:
            handler = self._types[fmt]
        except KeyError:
            raise TypeError(f"Cannot generate {fmt} annotation")
        return handler(declaration, *args, **kwargs)
