import sqlalchemy as sa

import meta
import types as _types
import domain_object

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
        query = meta.Session.query(cls).filter(cls.id == reference)
        return query.first()


meta.mapper(ResourceView, resource_view_table)
