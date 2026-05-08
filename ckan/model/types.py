# encoding: utf-8

import uuid
from typing import Any, cast

from sqlalchemy import types


__all__ = ['make_uuid', 'UuidType']


def make_uuid() -> str:
    return str(uuid.uuid4())


class UuidType(types.TypeDecorator):  # type: ignore
    impl = types.Unicode

    def process_bind_param(self, value: Any, dialect: Any):
        return str(value)

    def process_result_value(self, value: Any, dialect: Any):
        return value

    def copy(self, **kw: Any):
        return UuidType(cast(Any, self.impl).length)

    @classmethod
    def default(cls):
        return str(uuid.uuid4())
