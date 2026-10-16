from __future__ import annotations

import logging
from typing import Any, Union

import ckan.lib.dictization
from ckan import model
from ckan.common import _, asbool
from ckan.lib.dictization import model_dictize, model_save
from ckan.lib.navl.dictization_functions import validate as _validate
from ckan.logic import (
    NotFound,
    ValidationError,
    index_update_package,
    side_effect_free,
)
from ckan.logic import check_access as _check_access
from ckan.logic import get_or_bust as _get_or_bust
from ckan.logic import schema as schema_
from ckan.model import misc
from ckan.types import ActionResult, Context, DataDict, Query

_table_dictize = ckan.lib.dictization.table_dictize
log = logging.getLogger("ckan.logic")


def vocabulary_create(
    context: Context, data_dict: DataDict
) -> ActionResult.VocabularyCreate:
    """Create a new tag vocabulary.

    You must be a sysadmin to create vocabularies.

    :param name: the name of the new vocabulary, e.g. ``'Genre'``
    :type name: string
    :param tags: the new tags to add to the new vocabulary, for the format of
        tag dictionaries see :py:func:`tag_create`
    :type tags: list of tag dictionaries

    :returns: the newly-created vocabulary
    :rtype: dictionary

    """
    schema = (
        context.get("schema") or schema_.default_create_vocabulary_schema()
    )

    _check_access("vocabulary_create", context, data_dict)

    data, errors = _validate(data_dict, schema, context)

    if errors:
        model.Session.rollback()
        raise ValidationError(errors)

    vocabulary = model_save.vocabulary_dict_save(data, context)

    if not context.get("defer_commit"):
        model.repo.commit()

    log.debug("Created Vocabulary %s", vocabulary.name)

    return model_dictize.vocabulary_dictize(vocabulary, context)


def tag_create(context: Context, data_dict: DataDict) -> ActionResult.TagCreate:
    """Create a new vocabulary tag.

    You must be a sysadmin to create vocabulary tags.

    You can only use this function to create tags that belong to a vocabulary,
    not to create free tags. (To create a new free tag simply add the tag to
    a package, e.g. using the
    :py:func:`~ckan.logic.action.update.package_update` function.)

    :param name: the name for the new tag, a string between 2 and 100
        characters long containing only alphanumeric characters,
        spaces and the characters ``-``,
        ``_`` and ``.``, e.g. ``'Jazz'``
    :type name: string
    :param vocabulary_id: the id of the vocabulary that the new tag
        should be added to, e.g. the id of vocabulary ``'Genre'``
    :type vocabulary_id: string

    :returns: the newly-created tag
    :rtype: dictionary

    """
    _check_access("tag_create", context, data_dict)

    schema = context.get("schema") or schema_.default_create_tag_schema()
    _data, errors = _validate(data_dict, schema, context)
    if errors:
        raise ValidationError(errors)

    tag = model_save.tag_dict_save(data_dict, context)

    if not context.get("defer_commit"):
        model.repo.commit()

    log.debug("Created tag '%s' ", tag)
    return model_dictize.tag_dictize(tag, context)


@side_effect_free
def tag_list(context: Context, data_dict: DataDict) -> ActionResult.TagList:
    """Return a list of the site's tags.

    By default only free tags (tags that don't belong to a vocabulary) are
    returned. If the ``vocabulary_id`` argument is given then only tags
    belonging to that vocabulary will be returned instead.

    :param query: a tag name query to search for, if given only tags whose
        names contain this string will be returned (optional)
    :type query: string
    :param vocabulary_id: the id or name of a vocabulary, if given only tags
        that belong to this vocabulary will be returned (optional)
    :type vocabulary_id: string
    :param all_fields: return full tag dictionaries instead of just names
        (optional, default: ``False``)
    :type all_fields: bool

    :rtype: list of dictionaries

    """
    vocab_id_or_name = data_dict.get("vocabulary_id")
    query = data_dict.get("query") or data_dict.get("q")
    if query:
        query = query.strip()
    all_fields = data_dict.get("all_fields", None)

    _check_access("tag_list", context, data_dict)

    if query:
        tags, _count = _tag_search(context, data_dict)
    else:
        tags = model.Tag.all(vocab_id_or_name)

    if tags:
        if all_fields:
            tag_list: Union[list[dict[str, Any]], list[str]] = (
                model_dictize.tag_list_dictize(tags, context)
            )
        else:
            tag_list = [tag.name for tag in tags]
    else:
        tag_list = []

    return tag_list


@side_effect_free
def tag_show(context: Context, data_dict: DataDict) -> ActionResult.TagShow:
    """Return the details of a tag and all its datasets.

    :param id: the name or id of the tag
    :type id: string
    :param vocabulary_id: the id or name of the tag vocabulary that the tag is
        in - if it is not specified it will assume it is a free tag.
        (optional)
    :type vocabulary_id: string
    :param include_datasets: include a list of the tag's datasets. (Up to a
        limit of 1000 - for more flexibility, use package_search - see
        :py:func:`package_search` for an example.)
        (optional, default: ``False``)
    :type include_datasets: bool

    :returns: the details of the tag, including a list of all of the tag's
        datasets and their details
    :rtype: dictionary
    """
    id = _get_or_bust(data_dict, "id")
    include_datasets = asbool(data_dict.get("include_datasets", False))

    tag = model.Tag.get(id, vocab_id_or_name=data_dict.get("vocabulary_id"))
    if tag is None:
        raise NotFound

    context["tag"] = tag

    _check_access("tag_show", context, data_dict)
    return model_dictize.tag_dictize(tag, context, include_datasets=include_datasets)


def _tag_search(context: Context, data_dict: DataDict) -> tuple[list[model.Tag], int]:

    terms = data_dict.get("query") or data_dict.get("q") or []
    if isinstance(terms, str):
        terms = [terms]
    terms = [t.strip() for t in terms if t.strip()]

    if "fields" in data_dict:
        log.warning(
            '"fields" parameter is deprecated.  Use the "query" parameter instead'
        )

    fields = data_dict.get("fields", {})
    offset = data_dict.get("offset")
    limit = data_dict.get("limit")

    # TODO: should we check for user authentication first?
    q = model.Session.query(model.Tag)

    if "vocabulary_id" in data_dict:
        # Filter by vocabulary.
        vocab = model.Vocabulary.get(_get_or_bust(data_dict, "vocabulary_id"))
        if not vocab:
            return [], 0
        q = q.filter(model.Tag.vocabulary_id == vocab.id)
    else:
        # If no vocabulary_name in data dict then show free tags only.
        q = q.filter(model.Tag.vocabulary_id.is_(None))
        # If we're searching free tags, limit results to tags that are
        # currently applied to a package.
        q: Query[model.Tag] = q.distinct().join(model.Tag.package_tags)

    for field, value in fields.items():
        if field in ("tag", "tags"):
            terms.append(value)

    if not len(terms):
        return [], 0

    for term in terms:
        escaped_term = misc.escape_sql_like_special_characters(term, escape="\\")
        q = q.filter(model.Tag.name.ilike("%" + escaped_term + "%"))

    count = q.count()
    q = q.offset(offset)
    q = q.limit(limit)
    return q.all(), count


@side_effect_free
def tag_search(context: Context, data_dict: DataDict) -> ActionResult.TagSearch:
    """Return a list of tags whose names contain a given string.

    By default only free tags (tags that don't belong to any vocabulary) are
    searched. If the ``vocabulary_id`` argument is given then only tags
    belonging to that vocabulary will be searched instead.

    :param query: the string(s) to search for
    :type query: string or list of strings
    :param vocabulary_id: the id or name of the tag vocabulary to search in
      (optional)
    :type vocabulary_id: string
    :param fields: deprecated
    :type fields: dictionary
    :param limit: the maximum number of tags to return
    :type limit: int
    :param offset: when ``limit`` is given, the offset to start returning tags
        from
    :type offset: int

    :returns: A dictionary with the following keys:

      ``'count'``
        The number of tags in the result.

      ``'results'``
        The list of tags whose names contain the given string, a list of
        dictionaries.

    :rtype: dictionary

    """
    _check_access("tag_search", context, data_dict)

    tags, count = _tag_search(context, data_dict)
    return {"count": count, "results": [_table_dictize(tag, context) for tag in tags]}


@side_effect_free
def tag_autocomplete(
    context: Context, data_dict: DataDict
) -> ActionResult.TagAutocomplete:
    """Return a list of tag names that contain a given string.

    By default only free tags (tags that don't belong to any vocabulary) are
    searched. If the ``vocabulary_id`` argument is given then only tags
    belonging to that vocabulary will be searched instead.

    :param query: the string to search for
    :type query: string
    :param vocabulary_id: the id or name of the tag vocabulary to search in
      (optional)
    :type vocabulary_id: string
    :param fields: deprecated
    :type fields: dictionary
    :param limit: the maximum number of tags to return
    :type limit: int
    :param offset: when ``limit`` is given, the offset to start returning tags
        from
    :type offset: int

    :rtype: list of strings

    """
    _check_access("tag_autocomplete", context, data_dict)
    matching_tags, _count = _tag_search(context, data_dict)
    if matching_tags:
        return [tag.name for tag in matching_tags]
    else:
        return []


@side_effect_free
def vocabulary_list(
    context: Context, data_dict: DataDict
) -> ActionResult.VocabularyList:
    """Return a list of all the site's tag vocabularies.

    :rtype: list of dictionaries

    """
    _check_access("vocabulary_list", context, data_dict)

    vocabulary_objects = model.Session.query(model.Vocabulary).all()
    return model_dictize.vocabulary_list_dictize(vocabulary_objects, context)


@side_effect_free
def vocabulary_show(
    context: Context, data_dict: DataDict
) -> ActionResult.VocabularyShow:
    """Return a single tag vocabulary.

    :param id: the id or name of the vocabulary
    :type id: string
    :return: the vocabulary.
    :rtype: dictionary

    """
    _check_access("vocabulary_show", context, data_dict)

    vocab_id = data_dict.get("id")
    if not vocab_id:
        raise ValidationError({"id": _("id not in data")})
    vocabulary = model.Vocabulary.get(vocab_id)
    if vocabulary is None:
        raise NotFound(_('Could not find vocabulary "%s"') % vocab_id)
    vocabulary_dict = model_dictize.vocabulary_dictize(vocabulary, context)
    return vocabulary_dict


def vocabulary_update(
    context: Context, data_dict: DataDict
) -> ActionResult.VocabularyUpdate:
    """Update a tag vocabulary.

    You must be a sysadmin to update vocabularies.

    For further parameters see
    :py:func:`~ckan.logic.action.create.vocabulary_create`.

    :param id: the id of the vocabulary to update
    :type id: string

    :returns: the updated vocabulary
    :rtype: dictionary

    """
    vocab_id = data_dict.get("id")
    if not vocab_id:
        raise ValidationError({"id": _("id not in data")})

    vocab = model.Vocabulary.get(vocab_id)
    if vocab is None:
        raise NotFound(_('Could not find vocabulary "%s"') % vocab_id)

    data_dict["id"] = vocab.id
    if "name" in data_dict:
        if data_dict["name"] == vocab.name:
            del data_dict["name"]

    _check_access("vocabulary_update", context, data_dict)

    schema = context.get("schema") or schema_.default_update_vocabulary_schema()
    data, errors = _validate(data_dict, schema, context)
    if errors:
        model.Session.rollback()
        raise ValidationError(errors)

    updated_vocab = model_save.vocabulary_dict_update(data, context)

    if not context.get("defer_commit"):
        model.repo.commit()

    return model_dictize.vocabulary_dictize(updated_vocab, context)


def vocabulary_delete(context: Context, data_dict: DataDict) -> None:
    """Delete a tag vocabulary.

    You must be a sysadmin to delete vocabularies.

    :param id: the id of the vocabulary
    :type id: string

    """
    vocab_id = data_dict.get("id")
    if not vocab_id:
        raise ValidationError({"id": _("id not in data")})

    vocab_obj = model.Vocabulary.get(vocab_id)
    if vocab_obj is None:
        raise NotFound(_('Could not find vocabulary "%s"') % vocab_id)

    _check_access("vocabulary_delete", context, data_dict)

    vocab_obj.delete()
    model.repo.commit()


def tag_delete(context: Context, data_dict: DataDict) -> None:
    """Delete a tag.

    You must be a sysadmin to delete tags.

    :param id: the id or name of the tag
    :type id: string
    :param vocabulary_id: the id or name of the vocabulary that the tag belongs
        to (optional, default: None)
    :type vocabulary_id: string

    """
    if "id" not in data_dict or not data_dict["id"]:
        raise ValidationError({"id": _("id not in data")})
    tag_id_or_name = _get_or_bust(data_dict, "id")

    vocab_id_or_name = data_dict.get("vocabulary_id")

    tag_obj = model.Tag.get(tag_id_or_name, vocab_id_or_name)

    if tag_obj is None:
        raise NotFound(_('Could not find tag "%s"') % tag_id_or_name)

    _check_access("tag_delete", context, data_dict)

    update_packages = tag_obj.packages
    tag_obj.delete()
    model.repo.commit()
    for p in update_packages:
        index_update_package(context, p.id)
