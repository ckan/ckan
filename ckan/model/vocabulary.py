from meta import Table, types, Session
from core import metadata, Column, DomainObject, mapper
from types import make_uuid

MAX_VOCAB_NAME_LENGTH = 100

vocabulary_table = Table(
    'vocabulary', metadata,
    Column('id', types.UnicodeText, primary_key=True, default=make_uuid),
    Column('name', types.Unicode(MAX_VOCAB_NAME_LENGTH), nullable=False, unique=True),
    )

class Vocabulary(DomainObject):

    def __init__(self, name):
        self.id = make_uuid()
        self.name = name

    @classmethod
    def get(cls, reference):
        """Return a Vocabulary object referenced by its id or name."""

        query = Session.query(cls).filter(cls.id==reference)
        vocab = query.first()
        if vocab is None:
            vocab = cls.by_name(reference)            
        return vocab

mapper(Vocabulary, vocabulary_table)
