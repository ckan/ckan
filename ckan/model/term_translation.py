from meta import *
from core import *

__all__ = ['term_translation_table']

term_translation_table = Table('term_translation', metadata,
    Column('term', UnicodeText, nullable=False),
    Column('term_translation', UnicodeText, nullable=False),
    Column('lang_code', UnicodeText, nullable=False),
)

