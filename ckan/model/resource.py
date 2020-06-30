# encoding: utf-8

import datetime

from six import text_type
from collections import OrderedDict
from sqlalchemy.ext.orderinglist import ordering_list
from sqlalchemy import orm
from ckan.common import config
from sqlalchemy import types, func, Column, Table, ForeignKey

from ckan.model import (
    meta,
    core,
    types as _types,
    extension,
    domain_object,
)
import ckan.lib.dictization
from .package import Package
import ckan.model

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
    extra_columns = None

    def __init__(self, url=u'', format=u'', description=u'', hash=u'',
                 extras=None, package_id=None, **kwargs):
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

    def as_dict(self, core_columns_only=False):
        _dict = OrderedDict()
        cols = self.get_columns()
        if not core_columns_only:
            cols = ['id'] + cols + ['position']
        for col in cols:
            value = getattr(self, col)
            if isinstance(value, datetime.datetime):
                value = value.isoformat()
            _dict[col] = value
        for k, v in self.extras.items() if self.extras else []:
            _dict[k] = v
        if self.package_id and not core_columns_only:
            _dict["package_id"] = self.package_id
        return _dict

    def get_package_id(self):
        '''Returns the package id for a resource. '''
        return self.package_id

    @classmethod
    def get(cls, reference):
        '''Returns a resource object referenced by its name or id.'''
        if not reference:
            return None

        resource = meta.Session.query(cls).get(reference)
        if resource is None:
            resource = cls.by_name(reference)
        return resource

    @classmethod
    def get_columns(cls, extra_columns=True):
        '''Returns the core editable columns of the resource.'''
        if extra_columns:
            return CORE_RESOURCE_COLUMNS + cls.get_extra_columns()
        else:
            return CORE_RESOURCE_COLUMNS

    @classmethod
    def get_extra_columns(cls):
        if cls.extra_columns is None:
            cls.extra_columns = config.get(
                'ckan.extra_resource_fields', '').split()
            for field in cls.extra_columns:
                setattr(cls, field, DictProxy(field, 'extras'))
        return cls.extra_columns

    @classmethod
    def get_all_without_views(cls, formats=[]):
        '''Returns all resources that have no resource views

        :param formats: if given, returns only resources that have no resource
            views and are in any of the received formats
        :type formats: list

        :rtype: list of ckan.model.Resource objects
        '''
        query = meta.Session.query(cls).outerjoin(ckan.model.ResourceView) \
                    .filter(ckan.model.ResourceView.id == None)

        if formats:
            lowercase_formats = [f.lower() for f in formats]
            query = query.filter(func.lower(cls.format).in_(lowercase_formats))

        return query.all()

    def related_packages(self):
        return [self.package]


## Mappers

meta.mapper(Resource, resource_table, properties={
    'package': orm.relation(
        Package,
        # all resources including deleted
        # formally package_resources_all
        backref=orm.backref('resources_all',
                            collection_class=ordering_list('position'),
                            cascade='all, delete',
                            order_by=resource_table.c.position,
                            ),
    )
},
extension=[extension.PluginMapperExtension()],
)


def resource_identifier(obj):
    return obj.id


class DictProxy(object):

    def __init__(self, target_key, target_dict, data_type=text_type):
        self.target_key = target_key
        self.target_dict = target_dict
        self.data_type = data_type

    def __get__(self, obj, type):

        if not obj:
            return self

        proxied_dict = getattr(obj, self.target_dict)
        if proxied_dict:
            return proxied_dict.get(self.target_key)

    def __set__(self, obj, value):

        proxied_dict = getattr(obj, self.target_dict)
        if proxied_dict is None:
            proxied_dict = {}
            setattr(obj, self.target_dict, proxied_dict)

        proxied_dict[self.target_key] = self.data_type(value)

    def __delete__(self, obj):

        proxied_dict = getattr(obj, self.target_dict)
        proxied_dict.pop(self.target_key)
