# -*- coding: utf-8 -*-

from typing import Any, Callable, Dict, Generic, TypeVar


T = TypeVar("T", bound=Callable[..., Any])


class FormatHandler(Generic[T]):
    """Registry for different implementations of serializers, loaders, etc.

    Allows to collect a set of functions that can handle certain base value in
    different ways. For example, serializers can convert config declaration
    into config template, documentation, validation schema, etc.

    Usage:
        >>> registry = FormatHandler()
        >>>
        >>> # add a handler for "format-name"
        >>> @registry.register("format-name")
        >>> def format_handler(certain_base_value): ...
        >>>
        >>> # invoke a handler for `certain_base_value` in "format-name" mode
        >>> # i.e:  serializers.handle(declaration, "ini")
        >>> registry.handle(certain_base_value, "format-name")

    """
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
        self, subject: Any, fmt: str, *args: Any, **kwargs: Any
    ):
        try:
            handler = self._types[fmt]
        except KeyError:
            raise TypeError(
                "Cannot handle {}. Allowed formats are: {}".format(
                    fmt, list(self._types.keys())
                )
            )
        return handler(subject, *args, **kwargs)
