import datetime
import meta
from sqlalchemy import orm
from sqlalchemy import types, Column, Table, ForeignKey, and_
import domain_object
import types as _types
from package import Package


related_table = Table('related',meta.metadata,
        Column('id', types.UnicodeText, primary_key=True, default=_types.make_uuid),
        Column('type', types.UnicodeText, default=u'idea'),
        Column('title', types.UnicodeText),
        Column('description', types.UnicodeText),
        Column('image_url', types.UnicodeText),
        Column('url', types.UnicodeText),
        Column('created', types.DateTime, default=datetime.datetime.now),
        Column('owner_id', types.UnicodeText),
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
    'dataset': orm.relation(Package)
})
meta.mapper(Related, related_table, properties={
'datasets': orm.relation(Package,
    backref=orm.backref('related'),
    secondary=related_dataset_table,
    secondaryjoin=and_(related_dataset_table.c.dataset_id==Package.id,
                          RelatedDataset.status=='active'))
})
