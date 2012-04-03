import os
import datetime

import meta
import sqlalchemy as sa
from core import DomainObject
from types import make_uuid
from package import Package

related_table = meta.Table('related',meta.metadata,
        meta.Column('id', meta.UnicodeText, primary_key=True, default=make_uuid),
        meta.Column('type', meta.UnicodeText, default=u'idea'),
        meta.Column('title', meta.UnicodeText),
        meta.Column('description', meta.UnicodeText),
        meta.Column('image_url', meta.UnicodeText),
        meta.Column('url', meta.UnicodeText),
        meta.Column('created', meta.DateTime, default=datetime.datetime.now),
        meta.Column('owner_id', meta.UnicodeText),
        )

related_dataset_table = meta.Table('related_dataset', meta.metadata,
    meta.Column('id', meta.UnicodeText, primary_key=True, default=make_uuid),
    meta.Column('dataset_id', meta.UnicodeText, meta.ForeignKey('package.id'),
           nullable=False),
    meta.Column('related_id', meta.UnicodeText, meta.ForeignKey('related.id'), nullable=False),
    meta.Column('status', meta.UnicodeText, default=u'active'),
    )

class RelatedDataset(DomainObject):
    pass

class Related(DomainObject):

    @classmethod
    def get_for_dataset(cls, package, status=u'active'):
        query = meta.Session.query(RelatedDataset)
        query = query.filter(RelatedDataset.dataset_id==package.id)
        query = query.filter(RelatedDataset.status==status)
        return query.all()


# The mapping between the Related, RelatedDataset and Package tables have
# been deliberately kept orthogonal as the join table 'related_dataset_table'
# has an extra field, which would result in a messy association.
# See http://bit.ly/sqlalchemy_association_object
meta.mapper(RelatedDataset, related_dataset_table)
meta.mapper(Related, related_table, properties={
    'datasets': meta.relation(Package, backref='related',
                              secondary=related_dataset_table,
                              secondaryjoin=sa.and_(related_dataset_table.c.dataset_id==Package.id,
                related_dataset_table.c.status=='active'))
})
