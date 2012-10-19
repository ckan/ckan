import datetime

import sqlalchemy as sa
from sqlalchemy import orm
from sqlalchemy import types, Column, Table, ForeignKey, and_, func

import meta
import domain_object
import types as _types
import package as _package

__all__ = ['Related', 'RelatedDataset', 'related_dataset_table',
           'related_table']

related_table = sa.Table('related',meta.metadata,
        sa.Column('id', types.UnicodeText, primary_key=True, default=_types.make_uuid),
        sa.Column('type', types.UnicodeText, default=u'idea'),
        sa.Column('title', types.UnicodeText),
        sa.Column('description', types.UnicodeText),
        sa.Column('image_url', types.UnicodeText),
        sa.Column('url', types.UnicodeText),
        sa.Column('created', types.DateTime, default=datetime.datetime.now),
        sa.Column('owner_id', types.UnicodeText),
        sa.Column('view_count', types.Integer, default=0),
        sa.Column('featured', types.Integer, default=0)
)

related_dataset_table = Table('related_dataset', meta.metadata,
    Column('id', types.UnicodeText, primary_key=True, default=_types.make_uuid),
    Column('dataset_id', types.UnicodeText, ForeignKey('package.id'),
      nullable=False),
    Column('related_id', types.UnicodeText, ForeignKey('related.id'), nullable=False),
    Column('status', types.UnicodeText, default=u'active'),
    )

class RelatedDataset(domain_object.DomainObject):
    pass

class Related(domain_object.DomainObject):

    @classmethod
    def get(cls, id):
        return meta.Session.query(Related).filter(Related.id == id).first()

    @classmethod
    def get_for_dataset(cls, package, status=u'active'):
        """
        Allows the caller to get non-active state relations between
        the dataset and related, using the RelatedDataset object
        """
        query = meta.Session.query(RelatedDataset).\
                filter(RelatedDataset.dataset_id==package.id).\
                filter(RelatedDataset.status==status).all()
        return query

    def deactivate(self, package):
        related_ds = meta.Session.query(RelatedDataset).\
                          filter(RelatedDataset.dataset_id==package.id).\
                          filter(RelatedDataset.status=='active').first()
        if related_ds:
            related_ds.status = 'inactive'
            meta.Session.commit()


# We have avoided using SQLAlchemy association objects see
# http://bit.ly/sqlalchemy_association_object by only having the
# relation be for 'active' related objects.  For non-active states
# the caller will have to use get_for_dataset() in Related.
meta.mapper(RelatedDataset, related_dataset_table, properties={
    'related': orm.relation(Related),
    'dataset': orm.relation(_package.Package)
})
meta.mapper(Related, related_table, properties={
'datasets': orm.relation(_package.Package,
    backref=orm.backref('related'),
    secondary=related_dataset_table,
    secondaryjoin=and_(related_dataset_table.c.dataset_id==_package.Package.id,
                          RelatedDataset.status=='active'))
})

def _related_count(dataset):
    """
    Returns the *number* of (active) related items for the given dataset.
    """
    return meta.Session.query(func.count(RelatedDataset.id)).\
                        filter(RelatedDataset.dataset_id==dataset.id).\
                        filter(RelatedDataset.status=='active').\
                        scalar()

if hasattr(_package.Package, 'related_count'):
    raise Exception, 'Unable to attach `related_count` to Package class.'

_package.Package.related_count = property(_related_count)
