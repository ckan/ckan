# encoding: utf-8
from __future__ import annotations

from typing import Any, Collection, Optional

import sqlalchemy as sa
from sqlalchemy.orm import Mapped
from typing_extensions import Self

import ckan.model.meta as meta
import ckan.model.types as _types
import ckan.model.domain_object as domain_object

__all__ = ['ResourceView', 'resource_view_table']


resource_view_table = sa.Table(
    'resource_view', meta.metadata,
    sa.Column('id', sa.types.UnicodeText, primary_key=True,
              default=_types.make_uuid),
    sa.Column('resource_id', sa.types.UnicodeText,
              sa.ForeignKey('resource.id',
                            onupdate='CASCADE', ondelete='CASCADE')),
    sa.Column('title', sa.types.UnicodeText, nullable=True),
    sa.Column('description', sa.types.UnicodeText, nullable=True),
    sa.Column('view_type', sa.types.UnicodeText, nullable=False),
    sa.Column('order', sa.types.Integer, nullable=False),
    sa.Column('config', _types.JsonDictType),
    sa.Index('idx_view_resource_id', 'resource_id'),
)


class ResourceView(domain_object.DomainObject):
    id: Mapped[str]
    resource_id: Mapped[str]
    title: Mapped[Optional[str]]
    description: Mapped[Optional[str]]
    view_type: Mapped[str]
    order: Mapped[int]
    config: Mapped[dict[str, Any]]

    @classmethod
    def get(cls, reference: str) -> Optional[Self]:
        '''Returns a ResourceView object referenced by its id.'''
        if not reference:
            return None

        view = meta.Session.get(cls, reference)
        return view

    @classmethod
    def get_columns(cls) -> list[str]:
        return resource_view_table.columns.keys()

    @classmethod
    def get_count_not_in_view_types(
            cls, view_types: Collection[str]) -> list[sa.Row[tuple[str, int]]]:
        '''Returns the count of ResourceView not in the view types list'''
        view_type = cls.view_type
        query = meta.Session.query(
            view_type, sa.func.count(cls.id)).group_by(view_type).filter(
                sa.not_(view_type.in_(view_types)))

        return query.all()

    @classmethod
    def delete_not_in_view_types(cls, view_types: Collection[str]) -> int:
        '''Delete the Resource Views not in the received view types list'''
        query = meta.Session.query(cls).filter(
            sa.not_(cls.view_type.in_(view_types))
        )

        return query.delete(synchronize_session='fetch')

    @classmethod
    def delete_all(cls, view_types: Optional[Collection[str]] = None) -> int:
        '''Delete all Resource Views, or all of a particular type'''
        query = meta.Session.query(cls)

        if view_types:
            query = query.filter(cls.view_type.in_(view_types))

        return query.delete(synchronize_session='fetch')


meta.registry.map_imperatively(ResourceView, resource_view_table)
