import warnings

from .api import _, is_validator, FancyValidator, Invalid, NoDefault
from . import declarative
from .exc import FERuntimeWarning

__all__ = ['Schema']


class Schema(FancyValidator):

    """
    A schema validates a dictionary of values, applying different
    validators (be key) to the different values.  If
    allow_extra_fields=True, keys without validators will be allowed;
    otherwise they will raise Invalid. If filter_extra_fields is
    set to true, then extra fields are not passed back in the results.

    Validators are associated with keys either with a class syntax, or
    as keyword arguments (class syntax is usually easier).  Something
    like::

        class MySchema(Schema):
            name = Validators.PlainText()
            phone = Validators.PhoneNumber()

    These will not be available as actual instance variables, but will
    be collected in a dictionary.  To remove a validator in a subclass
    that is present in a superclass, set it to None, like::

        class MySubSchema(MySchema):
            name = None

    Note that missing fields are handled at the Schema level.  Missing
    fields can have the 'missing' message set to specify the error
    message, or if that does not exist the *schema* message
    'missingValue' is used.
    """

    # These validators will be applied before this schema:
    pre_validators = []
    # These validators will be applied after this schema:
    chained_validators = []
    # If true, then it is not an error when keys that aren't
    # associated with a validator are present:
    allow_extra_fields = False
    # If true, then keys that aren't associated with a validator
    # are removed:
    filter_extra_fields = False
    # If this is given, then any keys that aren't available but
    # are expected  will be replaced with this value (and then
    # validated!)  This does not override a present .if_missing
    # attribute on validators:
    if_key_missing = NoDefault
    # If true, then missing keys will be missing in the result,
    # if the validator doesn't have if_missing on it already:
    ignore_key_missing = False
    compound = True
    fields = {}
    order = []
    accept_iterator = True

    messages = dict(
        notExpected=_('The input field %(name)s was not expected.'),
        missingValue=_('Missing value'),
        badDictType=_('The input must be dict-like'
            ' (not a %(type)s: %(value)r)'),
        singleValueExpected=_('Please provide only one value'),)

    __mutableattributes__ = ('fields', 'chained_validators',
                             'pre_validators')

    @staticmethod
    def __classinit__(cls, new_attrs):
        FancyValidator.__classinit__(cls, new_attrs)
        # Don't bother doing anything if this is the most parent
        # Schema class (which is the only class with just
        # FancyValidator as a superclass):
        if cls.__bases__ == (FancyValidator,):
            return cls
        # Scan through the class variables we've defined *just*
        # for this subclass, looking for validators (both classes
        # and instances):
        for key, value in new_attrs.iteritems():
            if key in ('pre_validators', 'chained_validators'):
                if is_validator(value):
                    msg = "Any validator with the name %s will be ignored." % \
                            (key,)
                    warnings.warn(msg, FERuntimeWarning)
                continue
            if is_validator(value):
                cls.fields[key] = value
                delattr(cls, key)
            # This last case means we're overwriting a validator
            # from a superclass:
            elif key in cls.fields:
                del cls.fields[key]

        for name, value in cls.fields.iteritems():
            cls.add_field(name, value)

    def __initargs__(self, new_attrs):
        self.fields = self.fields.copy()
        for key, value in new_attrs.iteritems():
            if key in ('pre_validators', 'chained_validators'):
                if is_validator(value):
                    msg = "Any validator with the name %s will be ignored." % \
                            (key,)
                    warnings.warn(msg, FERuntimeWarning)
                continue
            if is_validator(value):
                self.fields[key] = value
                delattr(self, key)
            # This last case means we're overwriting a validator
            # from a superclass:
            elif key in self.fields:
                del self.fields[key]

    def assert_dict(self, value, state):
        """
        Helper to assure we have proper input
        """
        if not hasattr(value, 'items'):
            # Not a dict or dict-like object
            raise Invalid(
                self.message('badDictType', state,
                    type=type(value), value=value), value, state)

    def _convert_to_python(self, value_dict, state):
        if not value_dict:
            if self.if_empty is not NoDefault:
                return self.if_empty
            value_dict = {}

        for validator in self.pre_validators:
            value_dict = validator.to_python(value_dict, state)

        self.assert_dict(value_dict, state)

        new = {}
        errors = {}
        unused = self.fields.keys()
        if state is not None:
            previous_key = getattr(state, 'key', None)
            previous_full_dict = getattr(state, 'full_dict', None)
            state.full_dict = value_dict
        try:
            for name, value in value_dict.items():
                try:
                    unused.remove(name)
                except ValueError:
                    if not self.allow_extra_fields:
                        raise Invalid(self.message('notExpected',
                            state, name=repr(name)), value_dict, state)
                    if not self.filter_extra_fields:
                        new[name] = value
                    continue
                validator = self.fields[name]

                # are iterators (list, tuple, set, etc) allowed?
                if self._value_is_iterator(value) and not getattr(
                        validator, 'accept_iterator', False):
                    errors[name] = Invalid(self.message(
                        'singleValueExpected', state), value_dict, state)

                if state is not None:
                    state.key = name
                try:
                    new[name] = validator.to_python(value, state)
                except Invalid as e:
                    errors[name] = e

            for name in unused:
                validator = self.fields[name]
                try:
                    if_missing = validator.if_missing
                except AttributeError:
                    if_missing = NoDefault
                if if_missing is NoDefault:
                    if self.ignore_key_missing:
                        continue
                    if self.if_key_missing is NoDefault:
                        try:
                            message = validator.message('missing', state)
                        except KeyError:
                            message = self.message('missingValue', state)
                        errors[name] = Invalid(message, None, state)
                    else:
                        if state is not None:
                            state.key = name
                        try:
                            new[name] = validator.to_python(
                                self.if_key_missing, state)
                        except Invalid as e:
                            errors[name] = e
                else:
                    new[name] = validator.if_missing

            if state is not None:
                state.key = previous_key
            for validator in self.chained_validators:
                if (not hasattr(validator, 'validate_partial') or not getattr(
                        validator, 'validate_partial_form', False)):
                    continue
                try:
                    validator.validate_partial(value_dict, state)
                except Invalid as e:
                    sub_errors = e.unpack_errors()
                    if not isinstance(sub_errors, dict):
                        # Can't do anything here
                        continue
                    merge_dicts(errors, sub_errors)

            if errors:
                raise Invalid(
                    format_compound_error(errors),
                    value_dict, state, error_dict=errors)

            for validator in self.chained_validators:
                new = validator.to_python(new, state)

            return new

        finally:
            if state is not None:
                state.key = previous_key
                state.full_dict = previous_full_dict

    def _convert_from_python(self, value_dict, state):
        chained = self.chained_validators[:]
        chained.reverse()
        finished = []
        for validator in chained:
            __traceback_info__ = (
                'for_python chained_validator %s (finished %s)') % (
                validator, ', '.join(map(repr, finished)) or 'none')
            finished.append(validator)
            value_dict = validator.from_python(value_dict, state)
        self.assert_dict(value_dict, state)
        new = {}
        errors = {}
        unused = self.fields.keys()
        if state is not None:
            previous_key = getattr(state, 'key', None)
            previous_full_dict = getattr(state, 'full_dict', None)
            state.full_dict = value_dict
        try:
            __traceback_info__ = None
            for name, value in value_dict.iteritems():
                __traceback_info__ = 'for_python in %s' % name
                try:
                    unused.remove(name)
                except ValueError:
                    if not self.allow_extra_fields:
                        raise Invalid(self.message('notExpected',
                            state, name=repr(name)), value_dict, state)
                    if not self.filter_extra_fields:
                        new[name] = value
                else:
                    if state is not None:
                        state.key = name
                    try:
                        new[name] = self.fields[name].from_python(value, state)
                    except Invalid as e:
                        errors[name] = e

            del __traceback_info__

            for name in unused:
                validator = self.fields[name]
                if state is not None:
                    state.key = name
                try:
                    new[name] = validator.from_python(None, state)
                except Invalid as e:
                    errors[name] = e

            if errors:
                raise Invalid(
                    format_compound_error(errors),
                    value_dict, state, error_dict=errors)

            pre = self.pre_validators[:]
            pre.reverse()
            if state is not None:
                state.key = previous_key

            for validator in pre:
                __traceback_info__ = 'for_python pre_validator %s' % validator
                new = validator.from_python(new, state)

            return new

        finally:
            if state is not None:
                state.key = previous_key
                state.full_dict = previous_full_dict

    @declarative.classinstancemethod
    def add_chained_validator(self, cls, validator):
        if self is not None:
            if self.chained_validators is cls.chained_validators:
                self.chained_validators = cls.chained_validators[:]
            self.chained_validators.append(validator)
        else:
            cls.chained_validators.append(validator)

    @declarative.classinstancemethod
    def add_field(self, cls, name, validator):
        if self is not None:
            if self.fields is cls.fields:
                self.fields = cls.fields.copy()
            self.fields[name] = validator
        else:
            cls.fields[name] = validator

    @declarative.classinstancemethod
    def add_pre_validator(self, cls, validator):
        if self is not None:
            if self.pre_validators is cls.pre_validators:
                self.pre_validators = cls.pre_validators[:]
            self.pre_validators.append(validator)
        else:
            cls.pre_validators.append(validator)

    def subvalidators(self):
        result = []
        result.extend(self.pre_validators)
        result.extend(self.chained_validators)
        result.extend(self.fields.itervalues())
        return result

    def is_empty(self, value):
        ## Generally nothing is empty for us
        return False

    def empty_value(self, value):
        return {}

    def _value_is_iterator(self, value):
        if isinstance(value, basestring):
            return False
        elif isinstance(value, (list, tuple)):
            return True

        try:
            for _v in value:
                break
            return True
        ## @@: Should this catch any other errors?:
        except TypeError:
            return False


def format_compound_error(v, indent=0):
    if isinstance(v, Exception):
        try:
            return str(v)
        except (UnicodeDecodeError, UnicodeEncodeError):
            # There doesn't seem to be a better way to get a str()
            # version if possible, and unicode() if necessary, because
            # testing for the presence of a __unicode__ method isn't
            # enough
            return unicode(v)
    elif isinstance(v, dict):
        return ('%s\n' % (' ' * indent)).join(
            '%s: %s' % (k, format_compound_error(value, indent=len(k) + 2))
            for k, value in sorted(v.iteritems()) if value is not None)
    elif isinstance(v, list):
        return ('%s\n' % (' ' * indent)).join(
            '%s' % (format_compound_error(value, indent=indent))
            for value in v if value is not None)
    elif isinstance(v, basestring):
        return v
    else:
        assert False, "I didn't expect something like %s" % repr(v)


def merge_dicts(d1, d2):
    for key in d2:
        d1[key] = merge_values(d1[key], d2[key]) if key in d1 else d2[key]
    return d1


def merge_values(v1, v2):
    if isinstance(v1, basestring) and isinstance(v2, basestring):
        return v1 + '\n' + v2
    elif isinstance(v1, (list, tuple)) and isinstance(v2, (list, tuple)):
        return merge_lists(v1, v2)
    elif isinstance(v1, dict) and isinstance(v2, dict):
        return merge_dicts(v1, v2)
    else:
        # @@: Should we just ignore errors?  Seems we do...
        return v1


def merge_lists(l1, l2):
    if len(l1) < len(l2):
        l1 = l1 + [None] * (len(l2) - len(l1))
    elif len(l2) < len(l1):
        l2 = l2 + [None] * (len(l1) - len(l2))
    result = []
    for l1item, l2item in zip(l1, l2):
        item = None
        if l1item is None:
            item = l2item
        elif l2item is None:
            item = l1item
        else:
            item = merge_values(l1item, l2item)
        result.append(item)
    return result


class SimpleFormValidator(FancyValidator):
    """
    This validator wraps a simple function that validates the form.

    The function looks something like this::

      >>> def validate(form_values, state, validator):
      ...     if form_values.get('country', 'US') == 'US':
      ...         if not form_values.get('state'):
      ...             return dict(state='You must enter a state')
      ...     if not form_values.get('country'):
      ...         form_values['country'] = 'US'

    This tests that the field 'state' must be filled in if the country
    is US, and defaults that country value to 'US'.  The ``validator``
    argument is the SimpleFormValidator instance, which you can use to
    format messages or keep configuration state in if you like (for
    simple ad hoc validation you are unlikely to need it).

    To create a validator from that function, you would do::

      >>> from formencode.schema import SimpleFormValidator
      >>> validator = SimpleFormValidator(validate)
      >>> validator.to_python({'country': 'US', 'state': ''}, None)
      Traceback (most recent call last):
          ...
      Invalid: state: You must enter a state
      >>> sorted(validator.to_python({'state': 'IL'}, None).items())
      [('country', 'US'), ('state', 'IL')]

    The validate function can either return a single error message
    (that applies to the whole form), a dictionary that applies to the
    fields, None which means the form is valid, or it can raise
    Invalid.

    Note that you may update the value_dict *in place*, but you cannot
    return a new value.

    Another way to instantiate a validator is like this::

      >>> @SimpleFormValidator.decorate()
      ... def MyValidator(value_dict, state):
      ...     return None # or some more useful validation

    After this ``MyValidator`` will be a ``SimpleFormValidator``
    instance (it won't be your function).
    """

    __unpackargs__ = ('func',)

    validate_partial_form = False

    def __initargs__(self, new_attrs):
        self.__doc__ = getattr(self.func, '__doc__', None)

    def to_python(self, value_dict, state):
        # Since we aren't really supposed to modify things in-place,
        # we'll give the validation function a copy:
        value_dict = value_dict.copy()
        errors = self.func(value_dict, state, self)
        if not errors:
            return value_dict
        if isinstance(errors, basestring):
            raise Invalid(errors, value_dict, state)
        elif isinstance(errors, dict):
            raise Invalid(
                format_compound_error(errors),
                value_dict, state, error_dict=errors)
        elif isinstance(errors, Invalid):
            raise errors
        else:
            raise TypeError(
                "Invalid error value: %r" % errors)
        return value_dict

    validate_partial = to_python

    @classmethod
    def decorate(cls, **kw):
        def decorator(func):
            return cls(func, **kw)
        return decorator
