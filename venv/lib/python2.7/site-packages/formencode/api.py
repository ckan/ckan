"""
Core classes for validation.
"""

from . import declarative
import gettext
import os
import re
import textwrap
import warnings

try:
    from pkg_resources import resource_filename
except ImportError:
    resource_filename = None

__all__ = ['NoDefault', 'Invalid', 'Validator', 'Identity',
           'FancyValidator', 'is_empty', 'is_validator']


def get_localedir():
    """Retrieve the location of locales.

    If we're built as an egg, we need to find the resource within the egg.
    Otherwise, we need to look for the locales on the filesystem or in the
    system message catalog.

    """
    locale_dir = ''
    # Check the egg first
    if resource_filename is not None:
        try:
            locale_dir = resource_filename(__name__, "/i18n")
        except NotImplementedError:
            # resource_filename doesn't work with non-egg zip files
            pass
    if not hasattr(os, 'access'):
        # This happens on Google App Engine
        return os.path.join(os.path.dirname(__file__), 'i18n')
    if os.access(locale_dir, os.R_OK | os.X_OK):
        # If the resource is present in the egg, use it
        return locale_dir

    # Otherwise, search the filesystem
    locale_dir = os.path.join(os.path.dirname(__file__), 'i18n')
    if not os.access(locale_dir, os.R_OK | os.X_OK):
        # Fallback on the system catalog
        locale_dir = os.path.normpath('/usr/share/locale')

    return locale_dir


def set_stdtranslation(domain="FormEncode", languages=None,
                       localedir=get_localedir()):

    t = gettext.translation(domain=domain,
                            languages=languages,
                            localedir=localedir, fallback=True)
    global _stdtrans
    try:
        _stdtrans = t.ugettext
    except AttributeError:  # Python 3
        _stdtrans = t.gettext

set_stdtranslation()

# Dummy i18n translation function, nothing is translated here.
# Instead this is actually done in api.Validator.message.
# The surrounding _('string') of the strings is only for extracting
# the strings automatically.
# If you run pygettext with this source comment this function out temporarily.
_ = lambda s: s


def deprecation_warning(old, new=None, stacklevel=3):
    """Show a deprecation warning."""
    msg = '%s is deprecated' % old
    if new:
        msg += '; use %s instead' % new
    warnings.warn(msg, DeprecationWarning, stacklevel=stacklevel)


def deprecated(old=None, new=None):
    """A decorator which can be used to mark functions as deprecated."""
    def outer(func):
        def inner(*args, **kwargs):
            deprecation_warning(old or func.__name__, new)
            return func(*args, **kwargs)
        return inner
    return outer


class NoDefault(object):
    """A dummy value used for parameters with no default."""


def is_empty(value):
    """Check whether the given value should be considered "empty"."""
    return value is None or value == '' or (
        isinstance(value, (list, tuple, dict)) and not value)


def is_validator(obj):
    """Check whether obj is a Validator instance or class."""
    return (isinstance(obj, Validator) or
        (isinstance(obj, type) and issubclass(obj, Validator)))


class Invalid(Exception):

    """
    This is raised in response to invalid input.  It has several
    public attributes:

    ``msg``:
        The message, *without* values substituted.  For instance, if
        you want HTML quoting of values, you can apply that.
    ``substituteArgs``:
        The arguments (a dictionary) to go with ``msg``.
    ``str(self)``:
        The message describing the error, with values substituted.
    ``value``:
        The offending (invalid) value.
    ``state``:
        The state that went with this validator.  This is an
        application-specific object.
    ``error_list``:
        If this was a compound validator that takes a repeating value,
        and sub-validator(s) had errors, then this is a list of those
        exceptions.  The list will be the same length as the number of
        values -- valid values will have None instead of an exception.
    ``error_dict``:
        Like ``error_list``, but for dictionary compound validators.
    """

    def __init__(self, msg,
                 value, state, error_list=None, error_dict=None):
        Exception.__init__(self, msg, value, state, error_list, error_dict)
        self.msg = msg
        self.value = value
        self.state = state
        self.error_list = error_list
        self.error_dict = error_dict
        assert (not self.error_list or not self.error_dict), (
                "Errors shouldn't have both error dicts and lists "
                "(error %s has %s and %s)"
                % (self, self.error_list, self.error_dict))

    def __str__(self):
        val = self.msg
        return val

    if unicode is not str:  # Python 2

        def __unicode__(self):
            if isinstance(self.msg, unicode):
                return self.msg
            elif isinstance(self.msg, str):
                return self.msg.decode('utf8')
            else:
                return unicode(self.msg)

    def unpack_errors(self, encode_variables=False, dict_char='.',
                      list_char='-'):
        """
        Returns the error as a simple data structure -- lists,
        dictionaries, and strings.

        If ``encode_variables`` is true, then this will return a flat
        dictionary, encoded with variable_encode
        """
        if self.error_list:
            assert not encode_variables, (
                "You can only encode dictionary errors")
            assert not self.error_dict
            return [item.unpack_errors() if item else item
                for item in self.error_list]
        if self.error_dict:
            result = {}
            for name, item in self.error_dict.iteritems():
                result[name] = item if isinstance(
                    item, basestring) else item.unpack_errors()
            if encode_variables:
                from . import variabledecode
                result = variabledecode.variable_encode(
                    result, add_repetitions=False,
                    dict_char=dict_char, list_char=list_char)
                for key in result.keys():
                    if not result[key]:
                        del result[key]
            return result
        assert not encode_variables, (
            "You can only encode dictionary errors")
        return self.msg


############################################################
## Base Classes
############################################################

class Validator(declarative.Declarative):

    """
    The base class of most validators.  See ``IValidator`` for more, and
    ``FancyValidator`` for the more common (and more featureful) class.
    """

    _messages = {}
    if_missing = NoDefault
    repeating = False
    compound = False
    accept_iterator = False
    gettextargs = {}
    # In case you don't want to use __builtins__._
    # although it may be defined, set use_builtins_gettext to False:
    use_builtins_gettext = True

    __singletonmethods__ = (
        'to_python', 'from_python', 'message', 'all_messages', 'subvalidators')

    @staticmethod
    def __classinit__(cls, new_attrs):
        if 'messages' in new_attrs:
            cls._messages = cls._messages.copy()
            cls._messages.update(cls.messages)
            del cls.messages
        cls._initialize_docstring()

    def __init__(self, *args, **kw):
        if 'messages' in kw:
            self._messages = self._messages.copy()
            self._messages.update(kw.pop('messages'))
        declarative.Declarative.__init__(self, *args, **kw)

    def to_python(self, value, state=None):
        return value

    def from_python(self, value, state=None):
        return value

    def message(self, msgName, state, **kw):
        # determine translation function
        try:
            trans = state._
        except AttributeError:
            try:
                if self.use_builtins_gettext:
                    import __builtin__
                    trans = __builtin__._
                else:
                    trans = _stdtrans
            except AttributeError:
                trans = _stdtrans

        if not callable(trans):
            trans = _stdtrans

        msg = self._messages[msgName]
        msg = trans(msg, **self.gettextargs)

        try:
            return msg % kw
        except KeyError as e:
            raise KeyError(
                "Key not found (%s) for %r=%r %% %r (from: %s)"
                % (e, msgName, self._messages.get(msgName), kw,
                   ', '.join(self._messages)))

    def all_messages(self):
        """
        Return a dictionary of all the messages of this validator, and
        any subvalidators if present.  Keys are message names, values
        may be a message or list of messages.  This is really just
        intended for documentation purposes, to show someone all the
        messages that a validator or compound validator (like Schemas)
        can produce.

        @@: Should this produce a more structured set of messages, so
        that messages could be unpacked into a rendered form to see
        the placement of all the messages?  Well, probably so.
        """
        msgs = self._messages.copy()
        for v in self.subvalidators():
            inner = v.all_messages()
            for key, msg in inner:
                if key in msgs:
                    if msgs[key] == msg:
                        continue
                    if isinstance(msgs[key], list):
                        msgs[key].append(msg)
                    else:
                        msgs[key] = [msgs[key], msg]
                else:
                    msgs[key] = msg
        return msgs

    def subvalidators(self):
        """
        Return any validators that this validator contains.  This is
        not useful for functional, except to inspect what values are
        available.  Specifically the ``.all_messages()`` method uses
        this to accumulate all possible messages.
        """
        return []

    @classmethod
    def _initialize_docstring(cls):
        """
        This changes the class's docstring to include information
        about all the messages this validator uses.
        """
        doc = cls.__doc__ or ''
        doc = [textwrap.dedent(doc).rstrip()]
        messages = sorted(cls._messages.iteritems())
        doc.append('\n\n**Messages**\n\n')
        for name, default in messages:
            default = re.sub(r'(%\(.*?\)[rsifcx])', r'``\1``', default)
            doc.append('``' + name + '``:\n')
            doc.append('  ' + default + '\n\n')
        cls.__doc__ = ''.join(doc)


class _Identity(Validator):

    def __repr__(self):
        return 'validators.Identity'

Identity = _Identity()


class FancyValidator(Validator):

    """
    FancyValidator is the (abstract) superclass for various validators
    and converters.  A subclass can validate, convert, or do both.
    There is no formal distinction made here.

    Validators have two important external methods:

    ``.to_python(value, state)``:
      Attempts to convert the value.  If there is a problem, or the
      value is not valid, an Invalid exception is raised.  The
      argument for this exception is the (potentially HTML-formatted)
      error message to give the user.

    ``.from_python(value, state)``:
      Reverses ``.to_python()``.

    These two external methods make use of the following four
    important internal methods that can be overridden.  However,
    none of these *have* to be overridden, only the ones that
    are appropriate for the validator.

    ``._convert_to_python(value, state)``:
      This method converts the source to a Python value.  It returns
      the converted value, or raises an Invalid exception if the
      conversion cannot be done.  The argument to this exception
      should be the error message.  Contrary to ``.to_python()`` it is
      only meant to convert the value, not to fully validate it.

    ``._convert_from_python(value, state)``:
      Should undo ``._convert_to_python()`` in some reasonable way, returning
      a string.

    ``._validate_other(value, state)``:
      Validates the source, before ``._convert_to_python()``, or after
      ``._convert_from_python()``.  It's usually more convenient to use
      ``._validate_python()`` however.

    ``._validate_python(value, state)``:
      Validates a Python value, either the result of ``._convert_to_python()``,
      or the input to ``._convert_from_python()``.

    You should make sure that all possible validation errors are
    raised in at least one these four methods, not matter which.

    Subclasses can also override the ``__init__()`` method
    if the ``declarative.Declarative`` model doesn't work for this.

    Validators should have no internal state besides the
    values given at instantiation.  They should be reusable and
    reentrant.

    All subclasses can take the arguments/instance variables:

    ``if_empty``:
      If set, then this value will be returned if the input evaluates
      to false (empty list, empty string, None, etc), but not the 0 or
      False objects.  This only applies to ``.to_python()``.

    ``not_empty``:
      If true, then if an empty value is given raise an error.
      (Both with ``.to_python()`` and also ``.from_python()``
      if ``._validate_python`` is true).

    ``strip``:
      If true and the input is a string, strip it (occurs before empty
      tests).

    ``if_invalid``:
      If set, then when this validator would raise Invalid during
      ``.to_python()``, instead return this value.

    ``if_invalid_python``:
      If set, when the Python value (converted with
      ``.from_python()``) is invalid, this value will be returned.

    ``accept_python``:
      If True (the default), then ``._validate_python()`` and
      ``._validate_other()`` will not be called when
      ``.from_python()`` is used.

    These parameters are handled at the level of the external
    methods ``.to_python()`` and ``.from_python`` already;
    if you overwrite one of the internal methods, you usually
    don't need to care about them.

    """

    if_invalid = NoDefault
    if_invalid_python = NoDefault
    if_empty = NoDefault
    not_empty = False
    accept_python = True
    strip = False

    messages = dict(
        empty=_("Please enter a value"),
        badType=_("The input must be a string (not a %(type)s: %(value)r)"),
        noneType=_("The input must be a string (not None)"))

    _inheritance_level = 0
    _deprecated_methods = (
        ('_to_python', '_convert_to_python'),
        ('_from_python', '_convert_from_python'),
        ('validate_python', '_validate_python'),
        ('validate_other', '_validate_other'))

    @staticmethod
    def __classinit__(cls, new_attrs):
        Validator.__classinit__(cls, new_attrs)
        # account for deprecated methods
        cls._inheritance_level += 1
        if '_deprecated_methods' in new_attrs:
            cls._deprecated_methods = cls._deprecated_methods + new_attrs[
                '_deprecated_methods']
        for old, new in cls._deprecated_methods:
            if old in new_attrs:
                if new not in new_attrs:
                    deprecation_warning(old, new,
                        stacklevel=cls._inheritance_level + 2)
                    setattr(cls, new, new_attrs[old])
            elif new in new_attrs:
                    setattr(cls, old, deprecated(old=old, new=new)(
                        new_attrs[new]))

    def to_python(self, value, state=None):
        try:
            if self.strip and isinstance(value, basestring):
                value = value.strip()
            elif hasattr(value, 'mixed'):
                # Support Paste's MultiDict
                value = value.mixed()
            if self.is_empty(value):
                if self.not_empty:
                    raise Invalid(self.message('empty', state), value, state)
                if self.if_empty is not NoDefault:
                    return self.if_empty
                return self.empty_value(value)
            vo = self._validate_other
            if vo and vo is not self._validate_noop:
                vo(value, state)
            tp = self._convert_to_python
            if tp:
                value = tp(value, state)
            vp = self._validate_python
            if vp and vp is not self._validate_noop:
                vp(value, state)
        except Invalid:
            value = self.if_invalid
            if value is NoDefault:
                raise
        return value

    def from_python(self, value, state=None):
        try:
            if self.strip and isinstance(value, basestring):
                value = value.strip()
            if not self.accept_python:
                if self.is_empty(value):
                    if self.not_empty:
                        raise Invalid(self.message('empty', state),
                                      value, state)
                    return self.empty_value(value)
                vp = self._validate_python
                if vp and vp is not self._validate_noop:
                    vp(value, state)
                fp = self._convert_from_python
                if fp:
                    value = fp(value, state)
                vo = self._validate_other
                if vo and vo is not self._validate_noop:
                    vo(value, state)
            else:
                if self.is_empty(value):
                    return self.empty_value(value)
                fp = self._convert_from_python
                if fp:
                    value = fp(value, state)
        except Invalid:
            value = self.if_invalid_python
            if value is NoDefault:
                raise
        return value

    def is_empty(self, value):
        return is_empty(value)

    def empty_value(self, value):
        return None

    def assert_string(self, value, state):
        if not isinstance(value, basestring):
            raise Invalid(self.message('badType', state,
                                       type=type(value), value=value),
                          value, state)

    def base64encode(self, value):
        """
        Encode a string in base64, stripping whitespace and removing
        newlines.
        """
        return value.encode('base64').strip().replace('\n', '')

    def _validate_noop(self, value, state=None):
        """
        A validation method that doesn't do anything.
        """
        pass

    _validate_python = _validate_other = _validate_noop
    _convert_to_python = _convert_from_python = None
