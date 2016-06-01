# encoding: utf-8

from sqlalchemy import *
from migrate import *

def upgrade(migrate_engine):
    migrate_engine.execute('''
        CREATE TABLE term_translation (
            term text NOT NULL,
            term_translation text NOT NULL,
            lang_code text NOT NULL
        );

        create index term_lang on term_translation(term, lang_code);
        create index term on term_translation(term);
    '''
    )



  

