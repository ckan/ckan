import sqlalchemy
import vdm.sqlalchemy

from types import make_uuid
from meta import *
from domain_object import DomainObject
from package import Package
from core import *
import vocabulary
from vocabulary import Vocabulary

__all__ = ['tag_table', 'package_tag_table', 'Tag', 'PackageTag',
           'PackageTagRevision', 'package_tag_revision_table',
           'MAX_TAG_LENGTH', 'MIN_TAG_LENGTH']

MAX_TAG_LENGTH = 100
MIN_TAG_LENGTH = 2

tag_table = Table('tag', metadata,
        Column('id', types.UnicodeText, primary_key=True, default=make_uuid),
        Column('name', types.Unicode(MAX_TAG_LENGTH), nullable=False),
        Column('vocabulary_id',
            types.Unicode(vocabulary.VOCABULARY_NAME_MAX_LENGTH),
            ForeignKey('vocabulary.id')),
        sqlalchemy.UniqueConstraint('name', 'vocabulary_id')
)

package_tag_table = Table('package_tag', metadata,
        Column('id', types.UnicodeText, primary_key=True, default=make_uuid),
        Column('package_id', types.UnicodeText, ForeignKey('package.id')),
        Column('tag_id', types.UnicodeText, ForeignKey('tag.id')),
        )

vdm.sqlalchemy.make_table_stateful(package_tag_table)
# TODO: this has a composite primary key ...
package_tag_revision_table = make_revisioned_table(package_tag_table)

class Tag(DomainObject):
    def __init__(self, name='', vocabulary_id=None):
        self.name = name
        self.vocabulary_id = vocabulary_id

    # not stateful so same as purge
    def delete(self):
        self.purge()

    @classmethod
    def by_id(cls, tag_id, autoflush=True, vocab=None):
        """Return the tag object with the given id, or None if there is no
        tag with that id.

        By default only free tags (tags which do not belong to any vocabulary)
        are returned. If the optional argument vocab is given then only tags
        from that vocabulary are returned, or None if there is no tag with that
        id in that vocabulary.

        Arguments:
        tag_id -- The id of the tag to return.
        vocab -- A Vocabulary object for the vocabulary to look in (optional).

        """
        if vocab:
            query = Session.query(Tag).filter(Tag.id==tag_id).filter(
                Tag.vocabulary_id==vocab.id)
        else:
            query = Session.query(Tag).filter(Tag.id==tag_id).filter(
                Tag.vocabulary_id==None)
        query = query.autoflush(autoflush)
        tag = query.first()
        return tag

    @classmethod
    def by_name(cls, name, autoflush=True, vocab=None):
        """Return the tag object with the given name, or None if there is no
        tag with that name.

        By default only free tags (tags which do not belong to any vocabulary)
        are returned. If the optional argument vocab is given then only tags
        from that vocabulary are returned, or None if there is no tag with that
        name in that vocabulary.

        Arguments:
        name -- The name of the tag to return.
        vocab -- A Vocabulary object for the vocabulary to look in (optional).

        """
        if vocab:
            query = Session.query(Tag).filter(Tag.name==name).filter(
                Tag.vocabulary_id==vocab.id)
        else:
            query = Session.query(Tag).filter(Tag.name==name).filter(
                Tag.vocabulary_id==None)
        query = query.autoflush(autoflush)
        tag = query.first()
        return tag

    @classmethod
    def get(cls, tag_id_or_name, vocab_id_or_name=None):
        """Return the tag object with the given id or name, or None if there is
        no tag with that id or name.

        By default only free tags (tags which do not belong to any vocabulary)
        are returned. If the optional argument vocab_id_or_name is given then
        only tags that belong to that vocabulary will be returned, and None
        will be returned if there is no vocabulary with that vocabulary id or
        name or if there is no tag with that tag id or name in that vocabulary.

        Arguments:
        tag_id_or_name -- The id or name of the tag to return.
        vocab_id_or_name -- The id or name of the vocabulary to look in.

        """
        if vocab_id_or_name:
            vocab = Vocabulary.get(vocab_id_or_name)
            if vocab is None:
                # The user specified an invalid vocab.
                return None
        else:
            vocab = None
        tag = Tag.by_id(tag_id_or_name, vocab=vocab)
        if not tag:
            tag = Tag.by_name(tag_id_or_name, vocab=vocab)
        return tag
        # Todo: Make sure tag names can't be changed to look like tag IDs?

    @classmethod
    def search_by_name(cls, text_query):
        text_query = text_query.strip().lower()
        q = Session.query(cls).filter(cls.name.contains(text_query))
        q = q.distinct().join(cls.package_tags)
        return q
        
    @classmethod
    def all(cls):
        q = Session.query(cls)
        q = q.distinct().join(PackageTagRevision)
        q = q.filter(sqlalchemy.and_(
            PackageTagRevision.state == 'active', PackageTagRevision.current == True
        ))
        return q

    @property
    def packages_ordered(self):
        q = Session.query(Package)
        q = q.join(PackageTagRevision)
        q = q.filter(PackageTagRevision.tag_id == self.id)
        q = q.filter(sqlalchemy.and_(
            PackageTagRevision.state == 'active', PackageTagRevision.current == True
        ))
        packages = [p for p in q]
        ourcmp = lambda pkg1, pkg2: cmp(pkg1.name, pkg2.name)
        return sorted(packages, cmp=ourcmp)

    def __repr__(self):
        return '<Tag %s>' % self.name


class PackageTag(vdm.sqlalchemy.RevisionedObjectMixin,
        vdm.sqlalchemy.StatefulObjectMixin,
        DomainObject):
    def __init__(self, package=None, tag=None, state=None, **kwargs):
        self.package = package
        self.tag = tag
        self.state = state
        for k,v in kwargs.items():
            setattr(self, k, v)

    def __repr__(self):
        return '<PackageTag package=%s tag=%s>' % (self.package.name, self.tag.name)

    @classmethod
    def by_name(self, package_name, tag_name, autoflush=True):
        q = Session.query(self).autoflush(autoflush).\
            join('package').filter(Package.name==package_name).\
            join('tag').filter(Tag.name==tag_name)
        assert q.count() <= 1, q.all()
        return q.first()

    def related_packages(self):
        return [self.package]

mapper(Tag, tag_table, properties={
    'package_tags':relation(PackageTag, backref='tag',
        cascade='all, delete, delete-orphan',
        ),
    },
    order_by=tag_table.c.name,
    )

mapper(PackageTag, package_tag_table, properties={
    'pkg':relation(Package, backref='package_tag_all',
        cascade='none',
        )
    },
    order_by=package_tag_table.c.id,
    extension=[vdm.sqlalchemy.Revisioner(package_tag_revision_table),
               extension.PluginMapperExtension(),
               ],
    )

from package_mapping import *

vdm.sqlalchemy.modify_base_object_mapper(PackageTag, Revision, State)
PackageTagRevision = vdm.sqlalchemy.create_object_version(mapper, PackageTag,
        package_tag_revision_table)

PackageTagRevision.related_packages = lambda self: [self.continuity.package]

from vdm.sqlalchemy.base import add_stateful_versioned_m2m 
vdm.sqlalchemy.add_stateful_versioned_m2m(Package, PackageTag, 'tags', 'tag',
        'package_tags')
vdm.sqlalchemy.add_stateful_versioned_m2m_on_version(PackageRevision, 'tags')
vdm.sqlalchemy.add_stateful_versioned_m2m(Tag, PackageTag, 'packages', 'package',
        'package_tags')
