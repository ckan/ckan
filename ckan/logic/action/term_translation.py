from __future__ import annotations

from typing import Any

import ckan.lib.navl.validators as validators
import ckan.model as model
from ckan.common import _
from ckan.lib.dictization import table_dictize as _table_dictize
from ckan.lib.navl.dictization_functions import validate as _validate
from ckan.logic import (
    ValidationError,
    check_access as _check_access,
    get_action as _get_action,
    get_or_bust as _get_or_bust,
    side_effect_free,
)
from ckan.types import ActionResult, Context, DataDict
from sqlalchemy.sql import select as _select


@side_effect_free
def term_translation_show(
    context: Context, data_dict: DataDict
) -> ActionResult.TermTranslationShow:
    """Return the translations for the given term(s) and language(s).

    :param terms: the terms to search for translations of, e.g. ``'Russian'``,
        ``'romantic novel'``
    :type terms: list of strings
    :param lang_codes: the language codes of the languages to search for
        translations into, e.g. ``'en'``, ``'de'`` (optional, default is to
        search for translations into any language)
    :type lang_codes: list of language code strings

    :rtype: a list of term translation dictionaries each with keys ``'term'``
        (the term searched for, in the source language), ``'term_translation'``
        (the translation of the term into the target language) and
        ``'lang_code'`` (the language code of the target language)
    """
    _check_access("term_translation_show", context, data_dict)

    trans_table = model.term_translation_table

    q = _select(trans_table)

    if "terms" not in data_dict:
        raise ValidationError({"terms": "terms not in data"})

    # This action accepts `terms` as either a list of strings, or a single
    # string.
    terms = _get_or_bust(data_dict, "terms")
    if isinstance(terms, str):
        terms = [terms]
    if terms:
        q = q.where(trans_table.c["term"].in_(terms))

    # This action accepts `lang_codes` as either a list of strings, or a single
    # string.
    if "lang_codes" in data_dict:
        lang_codes = _get_or_bust(data_dict, "lang_codes")
        if isinstance(lang_codes, str):
            lang_codes = [lang_codes]
        q = q.where(trans_table.c["lang_code"].in_(lang_codes))

    conn: Any = model.Session.connection()
    cursor = conn.execute(q)

    results: ActionResult.TermTranslationShow = []

    for row in cursor:
        results.append(_table_dictize(row, context))

    return results


def term_translation_update(
    context: Context, data_dict: DataDict
) -> ActionResult.TermTranslationUpdate:
    """Create or update a term translation.

    You must be a sysadmin to create or update term translations.

    :param term: the term to be translated, in the original language, e.g.
        ``'romantic novel'``
    :type term: string
    :param term_translation: the translation of the term, e.g.
        ``'Liebesroman'``
    :type term_translation: string
    :param lang_code: the language code of the translation, e.g. ``'de'``
    :type lang_code: string

    :returns: the newly created or updated term translation
    :rtype: dictionary

    """
    _check_access("term_translation_update", context, data_dict)

    schema = {
        "term": [validators.not_empty, validators.unicode_safe],
        "term_translation": [validators.not_empty, validators.unicode_safe],
        "lang_code": [validators.not_empty, validators.unicode_safe],
    }

    data, errors = _validate(data_dict, schema, context)
    if errors:
        model.Session.rollback()
        raise ValidationError(errors)

    trans_table = model.term_translation_table

    update = trans_table.update()
    update = update.where(trans_table.c["term"] == data["term"])
    update = update.where(trans_table.c["lang_code"] == data["lang_code"])
    update = update.values(term_translation=data["term_translation"])

    conn = model.Session.connection()
    result = conn.execute(update)

    # insert if not updated
    if not result.rowcount:
        conn.execute(trans_table.insert().values(**data))

    if not context.get("defer_commit"):
        model.Session.commit()

    return data


def term_translation_update_many(
    context: Context, data_dict: DataDict
) -> ActionResult.TermTranslationUpdateMany:
    """Create or update many term translations at once.

    :param data: the term translation dictionaries to create or update,
        for the format of term translation dictionaries see
        :py:func:`~term_translation_update`
    :type data: list of dictionaries

    :returns: a dictionary with key ``'success'`` whose value is a string
        stating how many term translations were updated
    :rtype: string

    """
    if not (data_dict.get("data") and isinstance(data_dict.get("data"), list)):
        raise ValidationError({"error": _("Must be a list of dicts")})

    context["defer_commit"] = True

    action = _get_action("term_translation_update")
    num = 0
    for num, row in enumerate(data_dict["data"]):
        action(context, row)

    model.Session.commit()

    return {"success": _("%s rows updated") % (num + 1)}
