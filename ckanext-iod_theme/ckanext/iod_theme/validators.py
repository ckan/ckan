import json
import re

from ckan.plugins.toolkit import missing, _, get_validator, Invalid
from pylons import config

from ckanext.fluent.helpers import fluent_form_languages
from ckanext.scheming.helpers import scheming_language_text

ISO_639_LANGUAGE = u'^[a-z][a-z][a-z]?[a-z]?[_]?[A-Z]?[A-Z]?$'

LANG_SUFFIX = '_translated'

tag_length_validator = get_validator('tag_length_validator')
tag_name_validator = get_validator('tag_name_validator')

try:
    from ckanext.scheming.validation import (
        scheming_validator, validators_from_string)
except ImportError:
    # If scheming can't be imported, return a normal validator instead
    # of the scheming validator
    def scheming_validator(fn):
        def noop(key, data, errors, context):
            return fn(None, None)(key, data, errors, context)
        return noop
    validators_from_string = None

@scheming_validator
def fluent_core_translated_output(field, schema):
    assert field['field_name'].endswith(LANG_SUFFIX), 'Output validator "fluent_core_translated" must only used on a field that ends with "_translated"'

    def validator(key, data, errors, context):
        """
        Return a value for a core field using a multilingual dict.
        """
        data[key] = fluent_text_output(data[key])

        k = key[-1]
        new_key = key[:-1] + (k[:-len(LANG_SUFFIX)],)

        if new_key in data:
            data[new_key] = scheming_language_text(data[key], config.get('ckan.locale_default', 'en'))

    return validator


@scheming_validator
def fluent_text(field, schema):
    """
    Accept multilingual text input in the following forms
    and convert to a json string for storage:

    1. a multilingual dict, eg.

       {"en": "Text", "fr": "texte"}

    2. a JSON encoded version of a multilingual dict, for
       compatibility with old ways of loading data, eg.

       '{"en": "Text", "fr": "texte"}'

    3. separate fields per language (for form submissions):

       fieldname-en = "Text"
       fieldname-fr = "texte"

    When using this validator in a ckanext-scheming schema setting
    "required" to true will make all form languages required to
    pass validation.
    """
    # combining scheming required checks and fluent field processing
    # into a single validator makes this validator more complicated,
    # but should be easier for fluent users and eliminates quite a
    # bit of duplication in handling the different types of input
    required_langs = []
    if field and field.get('required'):
        required_langs = fluent_form_languages(field, schema=schema)

    def validator(key, data, errors, context):
        # just in case there was an error before our validator,
        # bail out here because our errors won't be useful
        if errors[key]:
            return

        value = data[key]
        # 1 or 2. dict or JSON encoded string
        if value is not missing:
            if isinstance(value, basestring):
                try:
                    value = json.loads(value)
                except ValueError:
                    errors[key].append(_('Failed to decode JSON string'))
                    return
                except UnicodeDecodeError:
                    errors[key].append(_('Invalid encoding for JSON string'))
                    return
            if not isinstance(value, dict):
                errors[key].append(_('expecting JSON object'))
                return

            for lang, text in value.iteritems():
                try:
                    m = re.match(ISO_639_LANGUAGE, lang)
                except TypeError:
                    errors[key].append(_('invalid type for language code: %r')
                        % lang)
                    continue
                if not m:
                    errors[key].append(_('invalid language code: "%s"') % lang)
                    continue
                if not isinstance(text, basestring):
                    errors[key].append(_('invalid type for "%s" value') % lang)
                    continue
                if isinstance(text, str):
                    try:
                        value[lang] = text.decode('utf-8')
                    except UnicodeDecodeError:
                        errors[key]. append(_('invalid encoding for "%s" value')
                            % lang)

            for lang in required_langs:
                if value.get(lang):
                    continue
                errors[key].append(_('Required language "%s" missing') % lang)

            if not errors[key]:
                data[key] = json.dumps(value)
            return

        # 3. separate fields
        output = {}
        prefix = key[-1] + '-'
        extras = data.get(key[:-1] + ('__extras',), {})

        for name, text in extras.iteritems():
            if not name.startswith(prefix):
                continue
            lang = name.split('-', 1)[1]
            m = re.match(ISO_639_LANGUAGE, lang)
            if not m:
                errors[name] = [_('invalid language code: "%s"') % lang]
                output = None
                continue

            if output is not None:
                output[lang] = text

        for lang in required_langs:
            if extras.get(prefix + lang):
                continue
            errors[key[:-1] + (key[-1] + '-' + lang,)] = [_('Missing value')]
            output = None

        if output is None:
            return

        for lang in output:
            del extras[prefix + lang]
        data[key] = json.dumps(output)

    return validator


def fluent_text_output(value):
    """
    Return stored json representation as a multilingual dict, if
    value is already a dict just pass it through.
    """
    if isinstance(value, dict):
        return value
    try:
        return json.loads(value)
    except ValueError:
        # plain string in the db, assume default locale
        return {config.get('ckan.locale_default', 'en'): value}


@scheming_validator
def fluent_tags(field, schema):
    """
    Accept multilingual lists of tags in the following forms
    and convert to a json string for storage.

    1. a multilingual dict of lists of tag strings, eg.

       {"en": ["big", "large"], "fr": ["grande"]}

    2. separate fields per language with comma-separated values
       (for form submissions)

       fieldname-en = "big,large"
       fieldname-fr = "grande"

    Validation of each tag is performed with validators
    tag_length_validator and tag_name_validator. When using
    ckanext-scheming these may be overridden with the
    "tag_validators" field value
    """
    # XXX this validator is too long and should be broken up

    required_langs = []
    if field and field.get('required'):
        required_langs = fluent_form_languages(field, schema=schema)

    tag_validators = [tag_length_validator, tag_name_validator]
    if field and 'tag_validators' in field:
        tag_validators = validators_from_string(
            field['tag_validators'], field, schema)

    def validator(key, data, errors, context):
        if errors[key]:
            return

        value = data[key]
        # 1. dict of lists of tag strings
        if value is not missing:
            if not isinstance(value, dict):
                errors[key].append(_('expecting JSON object'))
                return

            for lang, keys in value.items():
                try:
                    m = re.match(ISO_639_LANGUAGE, lang)
                except TypeError:
                    errors[key].append(_('invalid type for language code: %r')
                        % lang)
                    continue
                if not m:
                    errors[key].append(_('invalid language code: "%s"') % lang)
                    continue
                if not isinstance(keys, list):
                    errors[key].append(_('invalid type for "%s" value') % lang)
                    continue
                out = []
                for i, v in enumerate(keys):
                    if not isinstance(v, basestring):
                        errors[key].append(
                            _('invalid type for "{lang}" value item {num}').format(
                                lang=lang, num=i))
                        continue

                    if isinstance(v, str):
                        try:
                            out.append(v.decode('utf-8'))
                        except UnicodeDecodeError:
                            errors[key]. append(_(
                                'expected UTF-8 encoding for '
                                '"{lang}" value item {num}').format(
                                    lang=lang, num=i))
                    else:
                        out.append(v)

                tags = []
                errs = []
                for tag in out:
                    newtag, tagerrs = _validate_single_tag(tag, tag_validators)
                    errs.extend(tagerrs)
                    tags.append(newtag)
                if errs:
                    errors[key].extend(errs)
                value[lang] = tags

            for lang in required_langs:
                if value.get(lang):
                    continue
                errors[key].append(_('Required language "%s" missing') % lang)

            if not errors[key]:
                data[key] = json.dumps(value)
            return

        # 2. separate fields
        output = {}
        prefix = key[-1] + '-'
        extras = data.get(key[:-1] + ('__extras',), {})

        for name, text in extras.iteritems():
            if not name.startswith(prefix):
                continue
            lang = name.split('-', 1)[1]
            m = re.match(ISO_639_LANGUAGE, lang)
            if not m:
                errors[name] = [_('invalid language code: "%s"') % lang]
                output = None
                continue

            if not isinstance(text, basestring):
                errors[name].append(_('invalid type'))
                continue

            if isinstance(text, str):
                try:
                    text = text.decode('utf-8')
                except UnicodeDecodeError:
                    errors[name].append(_('expected UTF-8 encoding'))
                    continue

            if output is not None and text:
                tags = []
                errs = []
                for tag in text.split(','):
                    newtag, tagerrs = _validate_single_tag(tag, tag_validators)
                    errs.extend(tagerrs)
                    tags.append(newtag)
                output[lang] = tags
                if errs:
                    errors[key[:-1] + (name,)] = errs

        for lang in required_langs:
            if extras.get(prefix + lang):
                continue
            errors[key[:-1] + (key[-1] + '-' + lang,)] = [_('Missing value')]
            output = None

        if output is None:
            return

        for lang in output:
            del extras[prefix + lang]
        data[key] = json.dumps(output)

    return validator


def fluent_tags_output(value):
    """
    Return stored json representation as a multilingual dict, if
    value is already a dict just pass it through.
    """
    if isinstance(value, dict):
        return value
    return json.loads(value)


def _validate_single_tag(name, validators):
    """
    Return (new_name, errors_list) for validators in the form
    validator(value, context)
    """
    errors = []
    for v in validators:
        try:
            name = v(name, {})
        except Invalid as e:
            errors.append(e.error)
    return name, errors
