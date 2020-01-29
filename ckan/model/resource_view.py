# encoding: utf-8

import sqlalchemy as sa

from ckan.model import meta
from ckan.model import types as _types
from ckan.model import domain_object

__all__ = ['ResourceView', 'resource_view_table']


resource_view_table = sa.Table(
    'resource_view', meta.metadata,
    sa.Column('id', sa.types.UnicodeText, primary_key=True,
              default=_types.make_uuid),
    sa.Column('resource_id', sa.types.UnicodeText,
              sa.ForeignKey('resource.id')),
    sa.Column('title', sa.types.UnicodeText, nullable=True),
    sa.Column('description', sa.types.UnicodeText, nullable=True),
    sa.Column('view_type', sa.types.UnicodeText, nullable=False),
    sa.Column('order', sa.types.Integer, nullable=False),
    sa.Column('config', _types.JsonDictType))


class ResourceView(domain_object.DomainObject):
    @classmethod
    def get(cls, reference):
        '''Returns a ResourceView object referenced by its id.'''
        if not reference:
            return None

        view = meta.Session.query(cls).get(reference)

        return view

    @classmethod
    def get_columns(cls):
        return resource_view_table.columns.keys()

    @classmethod
    def get_count_not_in_view_types(cls, view_types):
        '''Returns the count of ResourceView not in the view types list'''
        query = meta.Session.query(ResourceView.view_type,
                                   sa.func.count(ResourceView.id)) \
                    .group_by(ResourceView.view_type) \
                    .filter(sa.not_(ResourceView.view_type.in_(view_types)))

        return query.all()

    @classmethod
    def delete_not_in_view_types(cls, view_types):
        '''Delete the Resource Views not in the received view types list'''
        query = meta.Session.query(ResourceView) \
                    .filter(sa.not_(ResourceView.view_type.in_(view_types)))

        return query.delete(synchronize_session='fetch')

    @classmethod
    def delete_all(cls, view_types=[]):
        '''Delete all Resource Views, or all of a particular type'''
        query = meta.Session.query(ResourceView)

        if view_types:
            query = query.filter(ResourceView.view_type.in_(view_types))

        return query.delete(synchronize_session='fetch')


meta.mapper(ResourceView, resource_view_table)
