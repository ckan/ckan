from sqlalchemy import types, Column, Table

import meta
import types as _types
import tag
import domain_object

VOCABULARY_NAME_MIN_LENGTH = 2
VOCABULARY_NAME_MAX_LENGTH = 100

vocabulary_table = Table(
    'vocabulary', meta.metadata,
    Column('id', types.UnicodeText, primary_key=True,
           default=_types.make_uuid),
    Column('name', types.Unicode(VOCABULARY_NAME_MAX_LENGTH), nullable=False,
        unique=True),
    )


class Vocabulary(domain_object.DomainObject):

    def __init__(self, name):
        self.id = _types.make_uuid()
        self.name = name

    @classmethod
    def get(cls, id_or_name):
        '''Return a Vocabulary object referenced by its id or name, or
        None if there is no vocabulary with the given id or name. '''
        query = meta.Session.query(Vocabulary)
        query = query.filter(Vocabulary.id == id_or_name)
        vocab = query.first()
        if vocab is None:
            vocab = Vocabulary.by_name(id_or_name)
        return vocab

    @property
    def tags(self):
        query = meta.Session.query(tag.Tag)
        return query.filter(tag.Tag.vocabulary_id == self.id)

meta.mapper(Vocabulary, vocabulary_table)
