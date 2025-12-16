# encoding: utf-8

from sqlalchemy import Column, Table, Index
from sqlalchemy.types import UnicodeText
import ckan.model.meta as meta

__all__ = ['term_translation_table']

term_translation_table = Table(
    'term_translation', meta.metadata,
    Column('term', UnicodeText, nullable=False),
    Column('term_translation', UnicodeText, nullable=False),
    Column('lang_code', UnicodeText, nullable=False),
    Index('term_lang', 'term', 'lang_code'),
)
