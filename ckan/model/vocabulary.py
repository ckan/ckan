from meta import Table, types, Session
from core import metadata, Column, DomainObject, mapper
from types import make_uuid

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
        """Return a Vocabulary object referenced by its id or name."""

        query = Session.query(cls).filter(cls.id==id_or_name)
        vocab = query.first()
        if vocab is None:
            vocab = cls.by_name(id_or_name)
        return vocab

mapper(Vocabulary, vocabulary_table)
