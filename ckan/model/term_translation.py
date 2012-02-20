import sqlalchemy as sa
from meta import *
from core import *
from types import make_uuid
from datetime import datetime

__all__ = ['term_translation_table']

term_translation_table = Table('term_translation', metadata,
    Column('term', UnicodeText, nullable=False),
    Column('term_translation', UnicodeText, nullable=False),
    Column('lang_code', UnicodeText, nullable=False),
)

