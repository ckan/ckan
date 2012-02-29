from meta import Table, types, Session
from core import metadata, Column, DomainObject, mapper
from types import make_uuid
import tag

VOCABULARY_NAME_MIN_LENGTH = 2
VOCABULARY_NAME_MAX_LENGTH = 100

vocabulary_table = Table(
    'vocabulary', metadata,
    Column('id', types.UnicodeText, primary_key=True, default=make_uuid),
    Column('name', types.Unicode(VOCABULARY_NAME_MAX_LENGTH), nullable=False,
        unique=True),
    )

class Vocabulary(DomainObject):

    def __init__(self, name):
        self.id = make_uuid()
        self.name = name

    @classmethod
    def get(cls, id_or_name):
        """Return a Vocabulary object referenced by its id or name, or None if
        there is no vocabulary with the given id or name.
        
        """
        query = Session.query(Vocabulary).filter(Vocabulary.id==id_or_name)
        vocab = query.first()
        if vocab is None:
            vocab = Vocabulary.by_name(id_or_name)
        return vocab

    @property
    def tags(self):
        return Session.query(tag.Tag).filter(tag.Tag.vocabulary_id==self.id)

mapper(Vocabulary, vocabulary_table)
