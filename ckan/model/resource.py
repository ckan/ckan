# encoding: utf-8
from __future__ import annotations

import datetime
from typing import Any, Callable, ClassVar, Optional


from collections import OrderedDict
from sqlalchemy.ext.orderinglist import ordering_list
from sqlalchemy import orm
from ckan.common import config
from sqlalchemy import types, Column, Table, ForeignKey
from typing_extensions import Self

import ckan.model.meta as meta
import ckan.model.core as core
import ckan.model.types as _types
import ckan.model.domain_object as domain_object

from .package import Package


__all__ = ['Resource', 'resource_table']

CORE_RESOURCE_COLUMNS = ['url', 'format', 'description', 'hash', 'name',
                         'resource_type', 'mimetype', 'mimetype_inner',
                         'size', 'created', 'last_modified',
                         'metadata_modified', 'cache_url',
                         'cache_last_updated', 'url_type']

##formally package_resource
resource_table = Table(
    'resource', meta.metadata,
    Column('id', types.UnicodeText, primary_key=True,
           default=_types.make_uuid),
    Column('package_id', types.UnicodeText,
           ForeignKey('package.id')),
    Column('url', types.UnicodeText, nullable=False, doc='remove_if_not_provided'),
    # XXX: format doc='remove_if_not_provided' makes lots of tests fail, fix tests?
    Column('format', types.UnicodeText),
    Column('description', types.UnicodeText, doc='remove_if_not_provided'),
    Column('hash', types.UnicodeText),
    Column('position', types.Integer),

    Column('name', types.UnicodeText),
    Column('resource_type', types.UnicodeText, doc='remove_if_not_provided'),
    Column('mimetype', types.UnicodeText, doc='remove_if_not_provided'),
    Column('mimetype_inner', types.UnicodeText, doc='remove_if_not_provided'),
    Column('size', types.BigInteger),
    Column('created', types.DateTime, default=datetime.datetime.utcnow),
    Column('last_modified', types.DateTime),
    Column('metadata_modified', types.DateTime, default=datetime.datetime.utcnow),
    Column('cache_url', types.UnicodeText),
    Column('cache_last_updated', types.DateTime),
    Column('url_type', types.UnicodeText),
    Column('extras', _types.JsonDictType),
    Column('state', types.UnicodeText, default=core.State.ACTIVE),
)


class Resource(core.StatefulObjectMixin,
               domain_object.DomainObject):
    id: str
    package_id: Optional[str]
    url: str
    format: str
    description: str
    hash: str
    position: int
    name: str
    resource_type: str
    mimetype: str
    size: int
    created: datetime.datetime
    last_modified: datetime.datetime
    metadata_modified: datetime.datetime
    cache_url: str
    cache_last_update: datetime.datetime
    url_type: str
    extras: dict[str, Any]
    state: str

    extra_columns: ClassVar[Optional[list[str]]] = None

    package: Package

    url_changed: Optional[bool]

    def __init__(self, url: str=u'', format: str=u'', description: str=u'',
                 hash: str=u'', extras: Optional[dict[str, Any]]=None,
                 package_id: Optional[str]=None, **kwargs: Any) -> None:
        self.id = _types.make_uuid()
        self.url = url
        self.format = format
        self.description = description
        self.hash = hash
        self.package_id = package_id
        # The base columns historically defaulted to empty strings
        # not None (Null). This is why they are seperate here.
        base_columns = ['url', 'format', 'description', 'hash']
        for key in set(CORE_RESOURCE_COLUMNS) - set(base_columns):
            setattr(self, key, kwargs.pop(key, None))
        self.extras = extras or {}
        extra_columns = self.get_extra_columns()
        for field in extra_columns:
            value = kwargs.pop(field, None)
            if value is not None:
                setattr(self, field, value)
        if kwargs:
            raise TypeError('unexpected keywords %s' % kwargs)

    def as_dict(self, core_columns_only: bool=False) -> dict[str, Any]:
        _dict: dict[str, Any] = OrderedDict()
        cols = self.get_columns()
        if not core_columns_only:
            cols = ['id'] + cols + ['position']
        for col in cols:
            value = getattr(self, col)
            if isinstance(value, datetime.datetime):
                value = value.isoformat()
            _dict[col] = value
        if self.extras:
            for k, v in self.extras.items():
                _dict[k] = v
        if self.package_id and not core_columns_only:
            _dict["package_id"] = self.package_id
        return _dict

    def get_package_id(self) -> Optional[str]:
        '''Returns the package id for a resource. '''
        return self.package_id

    @classmethod
    def get(cls, reference: str) -> Optional[Self]:
        '''Returns a resource object referenced by its name or id.'''
        if not reference:
            return None

        resource = meta.Session.query(cls).get(reference)
        if resource is None:
            resource = cls.by_name(reference)
        return resource

    @classmethod
    def get_columns(cls, extra_columns: bool=True) -> list[str]:
        '''Returns the core editable columns of the resource.'''
        if extra_columns:
            return CORE_RESOURCE_COLUMNS + cls.get_extra_columns()
        else:
            return CORE_RESOURCE_COLUMNS

    @classmethod
    def get_extra_columns(cls) -> list[str]:
        if cls.extra_columns is None:
            cls.extra_columns = config.get("ckan.extra_resource_fields")
            for field in cls.extra_columns:
                setattr(cls, field, DictProxy(field, 'extras'))
        assert cls.extra_columns is not None
        return cls.extra_columns

    def related_packages(self) -> list[Package]:
        return [self.package]


## Mappers

meta.mapper(Resource, resource_table, properties={
    'package': orm.relation(
        Package,
        # all resources including deleted
        # formally package_resources_all
        backref=orm.backref('resources_all',
                            collection_class=ordering_list('position'),
                            cascade='all, delete'
                            ),
    )
})


def resource_identifier(obj: Resource) -> str:
    return obj.id


class DictProxy(object):

    def __init__(
            self,
            target_key: str, target_dict: Any,
            data_type: Callable[[Any], Any] = str):
        self.target_key = target_key
        self.target_dict = target_dict
        self.data_type = data_type

    def __get__(self, obj: Any, type: Any):

        if not obj:
            return self

        proxied_dict = getattr(obj, self.target_dict)
        if proxied_dict:
            return proxied_dict.get(self.target_key)

    def __set__(self, obj: Any, value: Any):

        proxied_dict = getattr(obj, self.target_dict)
        if proxied_dict is None:
            proxied_dict = {}
            setattr(obj, self.target_dict, proxied_dict)

        proxied_dict[self.target_key] = self.data_type(value)

    def __delete__(self, obj: Any):

        proxied_dict = getattr(obj, self.target_dict)
        proxied_dict.pop(self.target_key)
