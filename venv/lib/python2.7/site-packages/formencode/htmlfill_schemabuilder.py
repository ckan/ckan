"""
Extension to ``htmlfill`` that can parse out schema-defining
statements.

You can either pass ``SchemaBuilder`` to ``htmlfill.render`` (the
``listen`` argument), or call ``parse_schema`` to just parse out a
``Schema`` object.
"""

from . import validators
from . import schema
from . import compound
from . import htmlfill

__all__ = ['parse_schema', 'SchemaBuilder']


def parse_schema(form):
    """
    Given an HTML form, parse out the schema defined in it and return
    that schema.
    """
    listener = SchemaBuilder()
    p = htmlfill.FillingParser(
        defaults={}, listener=listener)
    p.feed(form)
    p.close()
    return listener.schema()


default_validators = dict(
    [(name.lower(), getattr(validators, name))
     for name in dir(validators)])


def get_messages(cls, message):
    if not message:
        return {}
    else:
        return dict([(k, message) for k in cls._messages])


def to_bool(value):
    value = value.strip().lower()
    if value in ('true', 't', 'yes', 'y', 'on', '1'):
        return True
    elif value in ('false', 'f', 'no', 'n', 'off', '0'):
        return False
    else:
        raise ValueError("Not a boolean value: %r (use 'true'/'false')")


def force_list(v):
    """
    Force single items into a list. This is useful for checkboxes.
    """
    if isinstance(v, list):
        return v
    elif isinstance(v, tuple):
        return list(v)
    else:
        return [v]


class SchemaBuilder(object):

    def __init__(self, validators=default_validators):
        self.validators = validators
        self._schema = None

    def reset(self):
        self._schema = schema.Schema()

    def schema(self):
        return self._schema

    def listen_input(self, parser, tag, attrs):
        get_attr = parser.get_attr
        name = get_attr(attrs, 'name')
        if not name:
            # @@: should warn if you try to validate unnamed fields
            return
        v = compound.All(validators.Identity())
        add_to_end = None
        # for checkboxes, we must set if_missing = False
        if tag.lower() == "input":
            type_attr = get_attr(attrs, "type").lower().strip()
            if type_attr == "submit":
                v.validators.append(validators.Bool())
            elif type_attr == "checkbox":
                v.validators.append(validators.Wrapper(to_python=force_list))
            elif type_attr == "file":
                add_to_end = validators.FieldStorageUploadConverter()
        message = get_attr(attrs, 'form:message')
        required = to_bool(get_attr(attrs, 'form:required', 'false'))
        if required:
            v.validators.append(
                validators.NotEmpty(
                messages=get_messages(validators.NotEmpty, message)))
        else:
            v.validators[0].if_missing = False
        if add_to_end:
            v.validators.append(add_to_end)
        v_type = get_attr(attrs, 'form:validate', None)
        if v_type:
            pos = v_type.find(':')
            if pos != -1:
                # @@: should parse args
                args = (v_type[pos + 1:],)
                v_type = v_type[:pos]
            else:
                args = ()
            v_type = v_type.lower()
            v_class = self.validators.get(v_type)
            if not v_class:
                raise ValueError("Invalid validation type: %r" % v_type)
            kw_args = {'messages': get_messages(v_class, message)}
            v_inst = v_class(
                *args, **kw_args)
            v.validators.append(v_inst)
        self._schema.add_field(name, v)
