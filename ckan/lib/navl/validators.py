import ckan.lib.navl.dictization_functions as df

from ckan.common import _

missing = df.missing
StopOnError = df.StopOnError
Invalid = df.Invalid


def identity_converter(key, data, errors, context):
    return

def keep_extras(key, data, errors, context):

    extras = data.pop(key, {})
    for extras_key, value in extras.iteritems():
        data[key[:-1] + (extras_key,)] = value

def not_missing(key, data, errors, context):

    value = data.get(key)
    if value is missing:
        errors[key].append(_('Missing value'))
        raise StopOnError

def not_empty(key, data, errors, context):

    value = data.get(key)
    if not value or value is missing:
        errors[key].append(_('Missing value'))
        raise StopOnError

def if_empty_same_as(other_key):

    def callable(key, data, errors, context):
        value = data.get(key)
        if not value or value is missing:
            data[key] = data[key[:-1] + (other_key,)]

    return callable


def both_not_empty(other_key):

    def callable(key, data, errors, context):
        value = data.get(key)
        other_value = data.get(key[:-1] + (other_key,))
        if (not value or value is missing and
            not other_value or other_value is missing):
            errors[key].append(_('Missing value'))
            raise StopOnError

    return callable

def empty(key, data, errors, context):

    value = data.pop(key, None)
    
    if value and value is not missing:
        errors[key].append(_(
            'The input field %(name)s was not expected.') % {"name": key[-1]})

def ignore(key, data, errors, context):

    value = data.pop(key, None)
    raise StopOnError

def default(defalult_value):

    def callable(key, data, errors, context):

        value = data.get(key)
        if not value or value is missing:
            data[key] = defalult_value

    return callable

def ignore_missing(key, data, errors, context):
    '''If the key is missing from the data, ignore the rest of the key's
    schema.

    By putting ignore_missing at the start of the schema list for a key,
    you can allow users to post a dict without the key and the dict will pass
    validation. But if they post a dict that does contain the key, then any
    validators after ignore_missing in the key's schema list will be applied.

    :raises ckan.lib.navl.dictization_functions.StopOnError: if ``data[key]``
        is :py:data:`ckan.lib.navl.dictization_functions.missing` or ``None``

    :returns: ``None``

    '''
    value = data.get(key)

    if value is missing or value is None:
        data.pop(key, None)
        raise StopOnError

def ignore_empty(key, data, errors, context):

    value = data.get(key)

    if value is missing or not value:
        data.pop(key, None)
        raise StopOnError

def convert_int(value, context):

    try:
        return int(value)
    except ValueError:
        raise Invalid(_('Please enter an integer value'))

