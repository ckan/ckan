# encoding: utf-8

from sqlalchemy.orm import relation
from sqlalchemy import types, Column, Table, ForeignKey, and_, UniqueConstraint

from ckan.model import (
    core,
    meta,
    types as _types,
    domain_object,
    vocabulary,
    extension as _extension,
)
import ckan  # this import is needed
import ckan.model
import ckan.lib.dictization
import ckan.lib.maintain as maintain

__all__ = ['tag_table', 'package_tag_table', 'Tag', 'PackageTag',
           'MAX_TAG_LENGTH', 'MIN_TAG_LENGTH']

MAX_TAG_LENGTH = 100
MIN_TAG_LENGTH = 2

tag_table = Table('tag', meta.metadata,
        Column('id', types.UnicodeText, primary_key=True, default=_types.make_uuid),
        Column('name', types.Unicode(MAX_TAG_LENGTH), nullable=False),
        Column('vocabulary_id',
            types.Unicode(vocabulary.VOCABULARY_NAME_MAX_LENGTH),
            ForeignKey('vocabulary.id')),
        UniqueConstraint('name', 'vocabulary_id')
)

package_tag_table = Table('package_tag', meta.metadata,
        Column('id', types.UnicodeText, primary_key=True, default=_types.make_uuid),
        Column('package_id', types.UnicodeText, ForeignKey('package.id')),
        Column('tag_id', types.UnicodeText, ForeignKey('tag.id')),
        Column('state', types.UnicodeText, default=core.State.ACTIVE),
        )


class Tag(domain_object.DomainObject):
    def __init__(self, name='', vocabulary_id=None):
        self.name = name
        self.vocabulary_id = vocabulary_id

    # not stateful so same as purge
    def delete(self):
        self.purge()

    @classmethod
    def by_id(cls, tag_id, autoflush=True):
        '''Return the tag with the given id, or None.

        :param tag_id: the id of the tag to return
        :type tag_id: string

        :returns: the tag with the given id, or None if there is no tag with
            that id
        :rtype: ckan.model.tag.Tag

        '''
        query = meta.Session.query(Tag).filter(Tag.id==tag_id)
        query = query.autoflush(autoflush)
        tag = query.first()
        return tag

    @classmethod
    def by_name(cls, name, vocab=None, autoflush=True):
        '''Return the tag with the given name, or None.

        By default only free tags (tags which do not belong to any vocabulary)
        are returned.

        If the optional argument ``vocab`` is given then only tags from that
        vocabulary are returned, or ``None`` if there is no tag with that name
        in that vocabulary.

        :param name: the name of the tag to return
        :type name: string
        :param vocab: the vocabulary to look in (optional, default: None)
        :type vocab: ckan.model.vocabulary.Vocabulary

        :returns: the tag object with the given id or name, or None if there is
            no tag with that id or name
        :rtype: ckan.model.tag.Tag

        '''
        if vocab:
            query = meta.Session.query(Tag).filter(Tag.name==name).filter(
                Tag.vocabulary_id==vocab.id)
        else:
            query = meta.Session.query(Tag).filter(Tag.name==name).filter(
                Tag.vocabulary_id==None)
        query = query.autoflush(autoflush)
        tag = query.first()
        return tag

    @classmethod
    def get(cls, tag_id_or_name, vocab_id_or_name=None):
        '''Return the tag with the given id or name, or None.

        By default only free tags (tags which do not belong to any vocabulary)
        are returned.

        If the optional argument ``vocab_id_or_name`` is given then only tags
        that belong to that vocabulary will be returned, and ``None`` will be
        returned if there is no vocabulary with that vocabulary id or name or
        if there is no tag with that tag id or name in that vocabulary.

        :param tag_id_or_name: the id or name of the tag to return
        :type tag_id_or_name: string
        :param vocab_id_or_name: the id or name of the vocabulary to look for
            the tag in
        :type vocab_id_or_name: string

        :returns: the tag object with the given id or name, or None if there is
            no tag with that id or name
        :rtype: ckan.model.tag.Tag

        '''
        # First try to get the tag by ID.
        tag = Tag.by_id(tag_id_or_name)
        if tag:
            return tag
        else:
            # If that didn't work, try to get the tag by name and vocabulary.
            if vocab_id_or_name:
                vocab = vocabulary.Vocabulary.get(vocab_id_or_name)
                if vocab is None:
                    # The user specified an invalid vocab.
                    raise ckan.logic.NotFound("could not find vocabulary '%s'"
                            % vocab_id_or_name)
            else:
                vocab = None
            tag = Tag.by_name(tag_id_or_name, vocab=vocab)
            return tag
        # Todo: Make sure tag names can't be changed to look like tag IDs?

    @classmethod
    @maintain.deprecated()
    def search_by_name(cls, search_term, vocab_id_or_name=None):
        '''DEPRECATED

        Return all tags whose names contain a given string.

        By default only free tags (tags which do not belong to any vocabulary)
        are returned. If the optional argument ``vocab_id_or_name`` is given
        then only tags from that vocabulary are returned.

        :param search_term: the string to search for in the tag names
        :type search_term: string
        :param vocab_id_or_name: the id or name of the vocabulary to look in
            (optional, default: None)
        :type vocab_id_or_name: string

        :returns: a list of tags that match the search term
        :rtype: list of ckan.model.tag.Tag objects

        '''
        if vocab_id_or_name:
            vocab = vocabulary.Vocabulary.get(vocab_id_or_name)
            if vocab is None:
                # The user specified an invalid vocab.
                return None
            query = meta.Session.query(Tag).filter(Tag.vocabulary_id==vocab.id)
        else:
            query = meta.Session.query(Tag)
        search_term = search_term.strip().lower()
        query = query.filter(Tag.name.contains(search_term))
        query = query.distinct().join(Tag.package_tags)
        return query

    @classmethod
    def all(cls, vocab_id_or_name=None):
        '''Return all tags that are currently applied to any dataset.

        By default only free tags (tags which do not belong to any vocabulary)
        are returned. If the optional argument ``vocab_id_or_name`` is given
        then only tags from that vocabulary are returned.

        :param vocab_id_or_name: the id or name of the vocabulary to look in
            (optional, default: None)
        :type vocab_id_or_name: string

        :returns: a list of all tags that are currently applied to any dataset
        :rtype: list of ckan.model.tag.Tag objects

        '''
        if vocab_id_or_name:
            vocab = vocabulary.Vocabulary.get(vocab_id_or_name)
            if vocab is None:
                # The user specified an invalid vocab.
                raise ckan.logic.NotFound("could not find vocabulary '%s'"
                        % vocab_id_or_name)
            query = meta.Session.query(Tag).filter(Tag.vocabulary_id==vocab.id)
        else:
            query = meta.Session.query(Tag).filter(Tag.vocabulary_id == None)
            query = query.distinct().join(PackageTag)
            query = query.filter_by(state='active')
        return query

    @property
    def packages(self):
        '''Return a list of all packages that have this tag, sorted by name.

        :rtype: list of ckan.model.package.Package objects

        '''
        q = meta.Session.query(ckan.model.package.Package)
        q = q.join(PackageTag)
        q = q.filter_by(tag_id=self.id)
        q = q.filter_by(state='active')
        q = q.order_by(ckan.model.package.Package.name)
        packages = q.all()
        return packages

    def __repr__(self):
        return '<Tag %s>' % self.name

class PackageTag(core.StatefulObjectMixin,
                 domain_object.DomainObject):
    def __init__(self, package=None, tag=None, state=None, **kwargs):
        self.package = package
        self.tag = tag
        self.state = state
        for k,v in kwargs.items():
            setattr(self, k, v)

    def __repr__(self):
        s = u'<PackageTag package=%s tag=%s>' % (self.package.name, self.tag.name)
        return s.encode('utf8')

    @classmethod
    @maintain.deprecated()
    def by_name(self, package_name, tag_name, vocab_id_or_name=None,
            autoflush=True):
        '''DEPRECATED (and broken - missing the join to Tag)

        Return the PackageTag for the given package and tag names, or None.

        By default only PackageTags for free tags (tags which do not belong to
        any vocabulary) are returned. If the optional argument
        ``vocab_id_or_name`` is given then only PackageTags for tags from that
        vocabulary are returned.

        :param package_name: the name of the package to look for
        :type package_name: string
        :param tag_name: the name of the tag to look for
        :type tag_name: string
        :param vocab_id_or_name: the id or name of the vocabulary to look for
            the tag in
        :type vocab_id_or_name: string

        :returns: the PackageTag for the given package and tag names, or None
            if there is no PackageTag for those package and tag names
        :rtype: ckan.model.tag.PackageTag

        '''
        if vocab_id_or_name:
            vocab = vocabulary.Vocabulary.get(vocab_id_or_name)
            if vocab is None:
                # The user specified an invalid vocab.
                return None
            query = (meta.Session.query(PackageTag, Tag, ckan.model.Package)
                    .filter(Tag.vocabulary_id == vocab.id)
                    .filter(ckan.model.Package.name==package_name)
                    .filter(Tag.name==tag_name))
        else:
            query = (meta.Session.query(PackageTag)
                    .filter(ckan.model.Package.name==package_name)
                    .filter(Tag.name==tag_name))
        query = query.autoflush(autoflush)
        return query.one()[0]

    def related_packages(self):
        return [self.package]

meta.mapper(Tag, tag_table, properties={
    'package_tags': relation(PackageTag, backref='tag',
        cascade='all, delete, delete-orphan',
        ),
    'vocabulary': relation(vocabulary.Vocabulary,
        order_by=tag_table.c.name)
    },
    order_by=tag_table.c.name,
    )

# NB meta.mapper(tag.PackageTag... is found in package.py, because if it was
# here it we'd get circular references
