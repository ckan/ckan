# encoding: utf-8
from __future__ import annotations

import copy
import datetime
from secrets import token_urlsafe
from typing import Any, Optional

from sqlalchemy import types, Column, Table, ForeignKey, orm
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.mutable import MutableDict
from typing_extensions import Self

from ckan.model import meta, User, DomainObject
from ckan.common import config

__all__ = [u"ApiToken", u"api_token_table"]


def _make_token() -> str:
    nbytes = config.get(u"api_token.nbytes")
    return token_urlsafe(nbytes)


api_token_table = Table(
    u"api_token",
    meta.metadata,
    Column(u"id", types.UnicodeText, primary_key=True, default=_make_token),
    Column(u"name", types.UnicodeText),
    Column(u"user_id", types.UnicodeText, ForeignKey(u"user.id")),
    Column(u"created_at", types.DateTime, default=datetime.datetime.utcnow),
    Column(u"last_access", types.DateTime, nullable=True),
    Column(u"plugin_extras", MutableDict.as_mutable(JSONB)),
)


class ApiToken(DomainObject):
    id: str
    name: str
    user_id: Optional[str]
    created_at: datetime.datetime
    last_access: Optional[datetime.datetime]
    plugin_extras: dict[str, Any]
    owner: Optional[User]

    def __init__(
            self, user_id: Optional[str] = None,
            name: str = 'Unnamed') -> None:
        self.id = _make_token()
        self.user_id = user_id
        self.name = name

    @classmethod
    def get(cls, id: Optional[str]) -> Optional[Self]:
        if not id:
            return None

        return meta.Session.query(cls).get(id)

    @classmethod
    def revoke(cls, id: Optional[str]) -> bool:
        token = cls.get(id)
        if token:
            meta.Session.delete(token)
            meta.Session.commit()
            return True
        return False

    def touch(self, commit: bool = False) -> None:
        self.last_access = datetime.datetime.utcnow()
        if commit:
            meta.Session.commit()

    def set_extra(self, key: str, value: Any, commit: bool = False) -> None:
        extras = self.plugin_extras or {}
        extras[key] = value
        self.plugin_extras = copy.deepcopy(extras)
        if commit:
            meta.Session.commit()


meta.mapper(
    ApiToken,
    api_token_table,
    properties={
        u"owner": orm.relation(
            User, backref=orm.backref(u"api_tokens",
                                      cascade=u"all, delete")
        )
    },
)
