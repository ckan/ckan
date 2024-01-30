from __future__ import annotations

from ckan.types import Context, FlattenErrorDict, FlattenDataDict, FlattenKey
from ckan.plugins.toolkit import _, missing, Invalid, StopOnError
from ckanext.datastore.backend.postgres import (
    identifier, literal_string, get_read_engine,
)

import sqlalchemy as sa
from sqlalchemy.exc import ProgrammingError


def tabledesigner_ignore(
        key: FlattenKey, data: FlattenDataDict,
        errors: FlattenErrorDict, context: Context):
    '''ignore if resource url_type is not tabledesigner'''
    # existing resources
    if 'resource' in context:
        if context['resource'].url_type != 'tabledesigner':
            del data[key]
            raise StopOnError
    # resource passed as parameter to datastore_create
    elif data.get(('resource',), {}).get('url_type') != 'tabledesigner':
        del data[key]
        raise StopOnError


def tabledesigner_newline_list(value: str | list[str]):
    if isinstance(value, list):
        return value
    try:
        return value.split('\n')
    except AttributeError:
        raise Invalid(_('Must be a list or newline-separated string'))


def tabledesigner_clean_list(value: list[str]):
    "strip whitespace and remove dups"
    return list(dict.fromkeys(v.strip() for v in value))


def tabledesigner_check_pattern(value: str):
    """
    Check that this value is a valid regular expression for the
    datastore regexp_match function
    """
    engine = get_read_engine()
    try:
        with engine.begin() as conn:
            conn.execute(sa.text(
                "SELECT regexp_match('', {pattern})".format(
                    pattern=literal_string(value),
                ).replace(':', r'\:')  # no bind params
            ))
    except ProgrammingError:
        raise Invalid(_('Invalid regular expression'))


def tabledesigner_check_type(
        key: FlattenKey, data: FlattenDataDict,
        errors: FlattenErrorDict, context: Context):
    """
    Check that the type of this value can be cast to the datastore
    column type
    """
    type_ = data[key[:-1] + ('type',)]
    engine = get_read_engine()
    try:
        with engine.begin() as conn:
            conn.execute(sa.text(
                'SELECT {value}::{type_}'.format(
                    value=literal_string(data[key]),
                    type_=identifier(type_),
                ).replace(':', r'\:')  # no bind params
            ))
    except ProgrammingError:
        errors[key].append(
            _('Invalid constraint for type: %s') % type_)
        raise StopOnError


def tabledesigner_compare_minimum(
        key: FlattenKey, data: FlattenDataDict,
        errors: FlattenErrorDict, context: Context):
    """
    Check that this value is not less than the tdminimum value,
    if defined, using the correct datastore column type comparison
    """
    type_ = data[key[:-1] + ('type',)]
    min_ = data[key[:-1] + ('tdminimum',)]
    if min_ is None or min_ is missing:
        return
    max_ = data[key]
    engine = get_read_engine()
    with engine.begin() as conn:
        bad_range = conn.scalar(sa.text(
            'SELECT {min_}::{type_} > {max_}::{type_}'.format(
                min_=literal_string(min_),
                max_=literal_string(max_),
                type_=identifier(type_),
            ).replace(':', r'\:')  # no bind params
        ))
    if bad_range:
        errors[key].append(_('Less than minumum'))
        raise StopOnError
