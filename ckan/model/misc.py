"""
Contains miscelaneous set of DB-related functions
"""

import re

_special_characters = '%_'
def escape_sql_like_special_characters(term, escape='\\'):
    """
    Escapes characters that are special to the the sql LIKE expression.

    In particular, for both postgres and sqlite this means '%' and '_'.
    """
    for ch in escape + _special_characters:
        term = term.replace(ch, escape+ch)
    return term
    
