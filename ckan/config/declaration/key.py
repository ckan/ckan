# -*- coding: utf-8 -*-
"""This module defines utilitis for manipulations with the name of config
option.

"""
import fnmatch
from typing import Any, Iterable, Tuple, Union


class Wildcard(str):
    """Dynamic part of the Pattern.

    Behaves as basic strings but adds angles around the value in human-readable
    form. Used in Pattern in order to distinguish it from static fragment of
    the Key.

    """

    def __str__(self):
        s = super(Wildcard, self).__str__()
        return "<" + s + ">"


class Key:
    """Generic interface for accessing config options.

    In the simplest case, `Key` objects completely interchangeable with the
    corresponding config option names represented by string. Example::

        site_url = Key().ckan.site_url

        assert site_url == "ckan.site_url"
        assert config[site_url] is config["ckan.site_url"]

    In addition, `Key` objects are similar to the curried functions. Existing
    `key` can be extended to the sub-key at any moment. Example::

        key = Key()
        ckan = key.ckan
        assert ckan == "ckan"

        auth = ckan.auth
        assert auth == "ckan.auth"

        unowned = auth.create_unowned_datasets
        assert unowned == "ckan.auth.create_unowned_datasets"
        assert unowned == Key().ckan.auth.create_unowned_datasets

    """

    __slots__ = ("_path",)
    _path: Tuple[str, ...]

    def __init__(self, path: Iterable[str] = ()):
        self._path = tuple(path)

    def __str__(self):
        return ".".join(map(str, self._path))

    def __repr__(self):
        return f"<{self.__class__.__name__} {self}>"

    def __len__(self):
        return len(self._path)

    def __hash__(self):
        return hash(str(self))

    def __eq__(self, other: Any):
        if isinstance(other, str):
            return str(self) == other

        elif isinstance(other, Key):
            return self._path == other._path

        return super().__eq__(other)

    def __lt__(self, other: Any):
        if isinstance(other, str):
            return str(self) < other
        elif isinstance(other, Key):
            return self._path < other._path
        return NotImplemented

    def __add__(self, other: Any):
        return self._combine(self, other)

    def __radd__(self, other: Any):
        return self._combine(other, self)

    def __getitem__(self, idx: int):
        fragment = self._path[idx]
        if isinstance(fragment, tuple):
            return self.__class__(fragment)
        return fragment

    def __getattr__(self, fragment: str):
        return self._descend(fragment)

    def __iter__(self):
        return iter(self._path)

    def _descend(self, fragment: str):
        """Create sub-key."""
        return self.__class__(self._path + (fragment,))

    def _ascend(self):
        """Get parent key for the current one.

        Explicit version of `key[:-1]`.
        """
        return self.__class__(self._path[:-1])

    def dynamic(self, name: str):
        """Turn Key into a dynamic pattern: `a.b.c.<NAME>.prop`"""
        return Pattern.from_iterable(self._descend(Wildcard(name)))

    @classmethod
    def _as_key(cls, value: Any):
        if isinstance(value, cls):
            return value

        if isinstance(value, str):
            return cls.from_string(value)

        try:
            return cls(value)
        except TypeError:
            type_ = type(value).__name__
            raise TypeError(f"{type_} cannot be converted into Key")

    @classmethod
    def _combine(cls, left: Any, right: Any):
        head = cls._as_key(left)
        tail = cls._as_key(right)

        return cls(head._path + tail._path)

    @classmethod
    def from_string(cls, path: str):
        return cls([fragment for fragment in path.split(".") if fragment])

    @classmethod
    def from_iterable(cls, path: Iterable[str]):
        return cls(path)


class Pattern(Key):
    """Key with dynamic segment, that can match everything.

    Example:

        >>> pattern = Key().ckan.dynamic("anything")
        >>> assert pattern == "ckan.hello"
        >>> assert pattern == "ckan.world"
        >>> assert pattern == "ckan.x.y.z"
        >>> assert pattern != "not-ckan.hello"
    """
    __slots__ = ()
    _path: Tuple[Union[str, Wildcard], ...]

    __hash__ = Key.__hash__

    def __eq__(self, other: Any):
        if isinstance(other, Key):
            other = str(other)

        if isinstance(other, str):
            parts = ("*" if isinstance(p, Wildcard) else p for p in self)
            pat = ".".join(parts)
            return fnmatch.fnmatch(other, pat)

        return super().__eq__(other)
