from sqlalchemy import Column, Table
from sqlalchemy.types import UnicodeText
import meta

__all__ = ['term_translation_table']

term_translation_table = Table('term_translation', meta.metadata,
    Column('term', UnicodeText, nullable=False),
    Column('term_translation', UnicodeText, nullable=False),
    Column('lang_code', UnicodeText, nullable=False),
)

