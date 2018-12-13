## FormEncode, a  Form processor
## Copyright (C) 2003, Ian Bicking <ianb@colorstudy.com>

"""
Validator/Converters for use with FormEncode.
"""

import cgi
import locale
import re
import warnings
from encodings import idna

try:  # import dnspython
    import dns.resolver
    import dns.exception
except (IOError, ImportError):
    have_dns = False
else:
    have_dns = True


# These are only imported when needed
httplib = None
random = None
sha1 = None
socket = None
urlparse = None

from .api import (FancyValidator, Identity, Invalid, NoDefault, Validator,
    deprecation_warning, is_empty)

assert Identity and Invalid and NoDefault  # silence unused import warnings

# Dummy i18n translation function, nothing is translated here.
# Instead this is actually done in api.message.
# The surrounding _('string') of the strings is only for extracting
# the strings automatically.
# If you run pygettext with this source comment this function out temporarily.
_ = lambda s: s


############################################################
## Utility methods
############################################################

# These all deal with accepting both datetime and mxDateTime modules and types
datetime_module = None
mxDateTime_module = None


def import_datetime(module_type):
    global datetime_module, mxDateTime_module
    module_type = module_type.lower() if module_type else 'datetime'
    if module_type == 'datetime':
        if datetime_module is None:
            import datetime as datetime_module
        return datetime_module
    elif module_type == 'mxdatetime':
        if mxDateTime_module is None:
            from mx import DateTime as mxDateTime_module
        return mxDateTime_module
    else:
        raise ImportError('Invalid datetime module %r' % module_type)


def datetime_now(module):
    if module.__name__ == 'datetime':
        return module.datetime.now()
    else:
        return module.now()


def datetime_makedate(module, year, month, day):
    if module.__name__ == 'datetime':
        return module.date(year, month, day)
    else:
        try:
            return module.DateTime(year, month, day)
        except module.RangeError as e:
            raise ValueError(str(e))


def datetime_time(module):
    if module.__name__ == 'datetime':
        return module.time
    else:
        return module.Time


def datetime_isotime(module):
    if module.__name__ == 'datetime':
        return module.time.isoformat
    else:
        return module.ISO.Time


############################################################
## Wrapper Validators
############################################################

class ConfirmType(FancyValidator):
    """
    Confirms that the input/output is of the proper type.

    Uses the parameters:

    subclass:
        The class or a tuple of classes; the item must be an instance
        of the class or a subclass.
    type:
        A type or tuple of types (or classes); the item must be of
        the exact class or type.  Subclasses are not allowed.

    Examples::

        >>> cint = ConfirmType(subclass=int)
        >>> cint.to_python(True)
        True
        >>> cint.to_python('1')
        Traceback (most recent call last):
            ...
        Invalid: '1' is not a subclass of <type 'int'>
        >>> cintfloat = ConfirmType(subclass=(float, int))
        >>> cintfloat.to_python(1.0), cintfloat.from_python(1.0)
        (1.0, 1.0)
        >>> cintfloat.to_python(1), cintfloat.from_python(1)
        (1, 1)
        >>> cintfloat.to_python(None)
        Traceback (most recent call last):
            ...
        Invalid: None is not a subclass of one of the types <type 'float'>, <type 'int'>
        >>> cint2 = ConfirmType(type=int)
        >>> cint2(accept_python=False).from_python(True)
        Traceback (most recent call last):
            ...
        Invalid: True must be of the type <type 'int'>
    """

    accept_iterator = True

    subclass = None
    type = None

    messages = dict(
        subclass=_('%(object)r is not a subclass of %(subclass)s'),
        inSubclass=_('%(object)r is not a subclass of one of the types %(subclassList)s'),
        inType=_('%(object)r must be one of the types %(typeList)s'),
        type=_('%(object)r must be of the type %(type)s'))

    def __init__(self, *args, **kw):
        FancyValidator.__init__(self, *args, **kw)
        if self.subclass:
            if isinstance(self.subclass, list):
                self.subclass = tuple(self.subclass)
            elif not isinstance(self.subclass, tuple):
                self.subclass = (self.subclass,)
            self._validate_python = self.confirm_subclass
        if self.type:
            if isinstance(self.type, list):
                self.type = tuple(self.type)
            elif not isinstance(self.type, tuple):
                self.type = (self.type,)
            self._validate_python = self.confirm_type

    def confirm_subclass(self, value, state):
        if not isinstance(value, self.subclass):
            if len(self.subclass) == 1:
                msg = self.message('subclass', state, object=value,
                                   subclass=self.subclass[0])
            else:
                subclass_list = ', '.join(map(str, self.subclass))
                msg = self.message('inSubclass', state, object=value,
                                   subclassList=subclass_list)
            raise Invalid(msg, value, state)

    def confirm_type(self, value, state):
        for t in self.type:
            if type(value) is t:
                break
        else:
            if len(self.type) == 1:
                msg = self.message('type', state, object=value,
                                   type=self.type[0])
            else:
                msg = self.message('inType', state, object=value,
                                   typeList=', '.join(map(str, self.type)))
            raise Invalid(msg, value, state)
        return value

    def is_empty(self, value):
        return False


class Wrapper(FancyValidator):
    """
    Used to convert functions to validator/converters.

    You can give a simple function for `_convert_to_python`,
    `_convert_from_python`, `_validate_python` or `_validate_other`.
    If that function raises an exception, the value is considered invalid.
    Whatever value the function returns is considered the converted value.

    Unlike validators, the `state` argument is not used.  Functions
    like `int` can be used here, that take a single argument.

    Note that as Wrapper will generate a FancyValidator, empty
    values (those who pass ``FancyValidator.is_empty)`` will return ``None``.
    To override this behavior you can use ``Wrapper(empty_value=callable)``.
    For example passing ``Wrapper(empty_value=lambda val: val)`` will return
    the value itself when is considered empty.

    Examples::

        >>> def downcase(v):
        ...     return v.lower()
        >>> wrap = Wrapper(convert_to_python=downcase)
        >>> wrap.to_python('This')
        'this'
        >>> wrap.from_python('This')
        'This'
        >>> wrap.to_python('') is None
        True
        >>> wrap2 = Wrapper(
        ...     convert_from_python=downcase, empty_value=lambda value: value)
        >>> wrap2.from_python('This')
        'this'
        >>> wrap2.to_python('')
        ''
        >>> wrap2.from_python(1)
        Traceback (most recent call last):
          ...
        Invalid: 'int' object has no attribute 'lower'
        >>> wrap3 = Wrapper(validate_python=int)
        >>> wrap3.to_python('1')
        '1'
        >>> wrap3.to_python('a') # doctest: +ELLIPSIS
        Traceback (most recent call last):
          ...
        Invalid: invalid literal for int()...
    """

    func_convert_to_python = None
    func_convert_from_python = None
    func_validate_python = None
    func_validate_other = None

    _deprecated_methods = (
        ('func_to_python', 'func_convert_to_python'),
        ('func_from_python', 'func_convert_from_python'))

    def __init__(self, *args, **kw):
        # allow old method names as parameters
        if 'to_python' in kw and 'convert_to_python' not in kw:
            kw['convert_to_python'] = kw.pop('to_python')
        if 'from_python' in kw and 'convert_from_python' not in kw:
            kw['convert_from_python'] = kw.pop('from_python')
        for n in ('convert_to_python', 'convert_from_python',
                  'validate_python', 'validate_other'):
            if n in kw:
                kw['func_%s' % n] = kw.pop(n)
        FancyValidator.__init__(self, *args, **kw)
        self._convert_to_python = self.wrap(self.func_convert_to_python)
        self._convert_from_python = self.wrap(self.func_convert_from_python)
        self._validate_python = self.wrap(self.func_validate_python)
        self._validate_other = self.wrap(self.func_validate_other)

    def wrap(self, func):
        if not func:
            return None

        def result(value, state, func=func):
            try:
                return func(value)
            except Exception as e:
                raise Invalid(str(e), value, state)

        return result


class Constant(FancyValidator):
    """
    This converter converts everything to the same thing.

    I.e., you pass in the constant value when initializing, then all
    values get converted to that constant value.

    This is only really useful for funny situations, like::

      # Any evaluates sub validators in reverse order for to_python
      fromEmailValidator = Any(
                            Constant('unknown@localhost'),
                               Email())

    In this case, the if the email is not valid
    ``'unknown@localhost'`` will be used instead.  Of course, you
    could use ``if_invalid`` instead.

    Examples::

        >>> Constant('X').to_python('y')
        'X'
    """

    __unpackargs__ = ('value',)

    def _convert_to_python(self, value, state):
        return self.value

    _convert_from_python = _convert_to_python


############################################################
## Normal validators
############################################################

class MaxLength(FancyValidator):
    """
    Invalid if the value is longer than `maxLength`.  Uses len(),
    so it can work for strings, lists, or anything with length.

    Examples::

        >>> max5 = MaxLength(5)
        >>> max5.to_python('12345')
        '12345'
        >>> max5.from_python('12345')
        '12345'
        >>> max5.to_python('123456')
        Traceback (most recent call last):
          ...
        Invalid: Enter a value less than 5 characters long
        >>> max5(accept_python=False).from_python('123456')
        Traceback (most recent call last):
          ...
        Invalid: Enter a value less than 5 characters long
        >>> max5.to_python([1, 2, 3])
        [1, 2, 3]
        >>> max5.to_python([1, 2, 3, 4, 5, 6])
        Traceback (most recent call last):
          ...
        Invalid: Enter a value less than 5 characters long
        >>> max5.to_python(5)
        Traceback (most recent call last):
          ...
        Invalid: Invalid value (value with length expected)
    """

    __unpackargs__ = ('maxLength',)

    messages = dict(
        tooLong=_('Enter a value less than %(maxLength)i characters long'),
        invalid=_('Invalid value (value with length expected)'))

    def _validate_python(self, value, state):
        try:
            if value and len(value) > self.maxLength:
                raise Invalid(
                    self.message('tooLong', state,
                        maxLength=self.maxLength), value, state)
            else:
                return None
        except TypeError:
            raise Invalid(
                self.message('invalid', state), value, state)


class MinLength(FancyValidator):
    """
    Invalid if the value is shorter than `minlength`.  Uses len(), so
    it can work for strings, lists, or anything with length.  Note
    that you **must** use ``not_empty=True`` if you don't want to
    accept empty values -- empty values are not tested for length.

    Examples::

        >>> min5 = MinLength(5)
        >>> min5.to_python('12345')
        '12345'
        >>> min5.from_python('12345')
        '12345'
        >>> min5.to_python('1234')
        Traceback (most recent call last):
          ...
        Invalid: Enter a value at least 5 characters long
        >>> min5(accept_python=False).from_python('1234')
        Traceback (most recent call last):
          ...
        Invalid: Enter a value at least 5 characters long
        >>> min5.to_python([1, 2, 3, 4, 5])
        [1, 2, 3, 4, 5]
        >>> min5.to_python([1, 2, 3])
        Traceback (most recent call last):
          ...
        Invalid: Enter a value at least 5 characters long
        >>> min5.to_python(5)
        Traceback (most recent call last):
          ...
        Invalid: Invalid value (value with length expected)

    """

    __unpackargs__ = ('minLength',)

    messages = dict(
        tooShort=_('Enter a value at least %(minLength)i characters long'),
        invalid=_('Invalid value (value with length expected)'))

    def _validate_python(self, value, state):
        try:
            if len(value) < self.minLength:
                raise Invalid(
                    self.message('tooShort', state,
                        minLength=self.minLength), value, state)
        except TypeError:
            raise Invalid(
                self.message('invalid', state), value, state)


class NotEmpty(FancyValidator):
    """
    Invalid if value is empty (empty string, empty list, etc).

    Generally for objects that Python considers false, except zero
    which is not considered invalid.

    Examples::

        >>> ne = NotEmpty(messages=dict(empty='enter something'))
        >>> ne.to_python('')
        Traceback (most recent call last):
          ...
        Invalid: enter something
        >>> ne.to_python(0)
        0
    """
    not_empty = True

    messages = dict(
        empty=_('Please enter a value'))

    def _validate_python(self, value, state):
        if value == 0:
            # This isn't "empty" for this definition.
            return value
        if not value:
            raise Invalid(self.message('empty', state), value, state)


class Empty(FancyValidator):
    """
    Invalid unless the value is empty.  Use cleverly, if at all.

    Examples::

        >>> Empty.to_python(0)
        Traceback (most recent call last):
          ...
        Invalid: You cannot enter a value here
    """

    messages = dict(
        notEmpty=_('You cannot enter a value here'))

    def _validate_python(self, value, state):
        if value or value == 0:
            raise Invalid(self.message('notEmpty', state), value, state)


class Regex(FancyValidator):
    """
    Invalid if the value doesn't match the regular expression `regex`.

    The regular expression can be a compiled re object, or a string
    which will be compiled for you.

    Use strip=True if you want to strip the value before validation,
    and as a form of conversion (often useful).

    Examples::

        >>> cap = Regex(r'^[A-Z]+$')
        >>> cap.to_python('ABC')
        'ABC'

    Note that ``.from_python()`` calls (in general) do not validate
    the input::

        >>> cap.from_python('abc')
        'abc'
        >>> cap(accept_python=False).from_python('abc')
        Traceback (most recent call last):
          ...
        Invalid: The input is not valid
        >>> cap.to_python(1)
        Traceback (most recent call last):
          ...
        Invalid: The input must be a string (not a <type 'int'>: 1)
        >>> Regex(r'^[A-Z]+$', strip=True).to_python('  ABC  ')
        'ABC'
        >>> Regex(r'this', regexOps=('I',)).to_python('THIS')
        'THIS'
    """

    regexOps = ()
    strip = False
    regex = None

    __unpackargs__ = ('regex',)

    messages = dict(
        invalid=_('The input is not valid'))

    def __init__(self, *args, **kw):
        FancyValidator.__init__(self, *args, **kw)
        if isinstance(self.regex, basestring):
            ops = 0
            assert not isinstance(self.regexOps, basestring), (
                "regexOps should be a list of options from the re module "
                "(names, or actual values)")
            for op in self.regexOps:
                if isinstance(op, basestring):
                    ops |= getattr(re, op)
                else:
                    ops |= op
            self.regex = re.compile(self.regex, ops)

    def _validate_python(self, value, state):
        self.assert_string(value, state)
        if self.strip and isinstance(value, basestring):
            value = value.strip()
        if not self.regex.search(value):
            raise Invalid(self.message('invalid', state), value, state)

    def _convert_to_python(self, value, state):
        if self.strip and isinstance(value, basestring):
            return value.strip()
        return value


class PlainText(Regex):
    """
    Test that the field contains only letters, numbers, underscore,
    and the hyphen.  Subclasses Regex.

    Examples::

        >>> PlainText.to_python('_this9_')
        '_this9_'
        >>> PlainText.from_python('  this  ')
        '  this  '
        >>> PlainText(accept_python=False).from_python('  this  ')
        Traceback (most recent call last):
          ...
        Invalid: Enter only letters, numbers, or _ (underscore)
        >>> PlainText(strip=True).to_python('  this  ')
        'this'
        >>> PlainText(strip=True).from_python('  this  ')
        'this'
    """

    regex = r"^[a-zA-Z_\-0-9]*$"

    messages = dict(
        invalid=_('Enter only letters, numbers, or _ (underscore)'))


class OneOf(FancyValidator):
    """
    Tests that the value is one of the members of a given list.

    If ``testValueList=True``, then if the input value is a list or
    tuple, all the members of the sequence will be checked (i.e., the
    input must be a subset of the allowed values).

    Use ``hideList=True`` to keep the list of valid values out of the
    error message in exceptions.

    Examples::

        >>> oneof = OneOf([1, 2, 3])
        >>> oneof.to_python(1)
        1
        >>> oneof.to_python(4)
        Traceback (most recent call last):
          ...
        Invalid: Value must be one of: 1; 2; 3 (not 4)
        >>> oneof(testValueList=True).to_python([2, 3, [1, 2, 3]])
        [2, 3, [1, 2, 3]]
        >>> oneof.to_python([2, 3, [1, 2, 3]])
        Traceback (most recent call last):
          ...
        Invalid: Value must be one of: 1; 2; 3 (not [2, 3, [1, 2, 3]])
    """

    list = None
    testValueList = False
    hideList = False

    __unpackargs__ = ('list',)

    messages = dict(
        invalid=_('Invalid value'),
        notIn=_('Value must be one of: %(items)s (not %(value)r)'))

    def _validate_python(self, value, state):
        if self.testValueList and isinstance(value, (list, tuple)):
            for v in value:
                self._validate_python(v, state)
        else:
            if not value in self.list:
                if self.hideList:
                    raise Invalid(self.message('invalid', state), value, state)
                else:
                    try:
                        items = '; '.join(map(str, self.list))
                    except UnicodeError:
                        items = '; '.join(map(unicode, self.list))
                    raise Invalid(
                        self.message('notIn', state,
                            items=items, value=value), value, state)

    @property
    def accept_iterator(self):
        return self.testValueList


class DictConverter(FancyValidator):
    """
    Converts values based on a dictionary which has values as keys for
    the resultant values.

    If ``allowNull`` is passed, it will not balk if a false value
    (e.g., '' or None) is given (it will return None in these cases).

    to_python takes keys and gives values, from_python takes values and
    gives keys.

    If you give hideDict=True, then the contents of the dictionary
    will not show up in error messages.

    Examples::

        >>> dc = DictConverter({1: 'one', 2: 'two'})
        >>> dc.to_python(1)
        'one'
        >>> dc.from_python('one')
        1
        >>> dc.to_python(3)
        Traceback (most recent call last):
            ....
        Invalid: Enter a value from: 1; 2
        >>> dc2 = dc(hideDict=True)
        >>> dc2.hideDict
        True
        >>> dc2.dict
        {1: 'one', 2: 'two'}
        >>> dc2.to_python(3)
        Traceback (most recent call last):
            ....
        Invalid: Choose something
        >>> dc.from_python('three')
        Traceback (most recent call last):
            ....
        Invalid: Nothing in my dictionary goes by the value 'three'.  Choose one of: 'one'; 'two'
    """

    messages = dict(
        keyNotFound=_('Choose something'),
        chooseKey=_('Enter a value from: %(items)s'),
        valueNotFound=_('That value is not known'),
        chooseValue=_('Nothing in my dictionary goes by the value %(value)s.'
            '  Choose one of: %(items)s'))

    dict = None
    hideDict = False

    __unpackargs__ = ('dict',)

    def _convert_to_python(self, value, state):
        try:
            return self.dict[value]
        except KeyError:
            if self.hideDict:
                raise Invalid(self.message('keyNotFound', state), value, state)
            else:
                items = sorted(self.dict)
                items = '; '.join(map(repr, items))
                raise Invalid(self.message('chooseKey',
                    state, items=items), value, state)

    def _convert_from_python(self, value, state):
        for k, v in self.dict.iteritems():
            if value == v:
                return k
        if self.hideDict:
            raise Invalid(self.message('valueNotFound', state), value, state)
        else:
            items = '; '.join(map(repr, self.dict.itervalues()))
            raise Invalid(
                self.message('chooseValue', state,
                    value=repr(value), items=items), value, state)


class IndexListConverter(FancyValidator):
    """
    Converts a index (which may be a string like '2') to the value in
    the given list.

    Examples::

        >>> index = IndexListConverter(['zero', 'one', 'two'])
        >>> index.to_python(0)
        'zero'
        >>> index.from_python('zero')
        0
        >>> index.to_python('1')
        'one'
        >>> index.to_python(5)
        Traceback (most recent call last):
        Invalid: Index out of range
        >>> index(not_empty=True).to_python(None)
        Traceback (most recent call last):
        Invalid: Please enter a value
        >>> index.from_python('five')
        Traceback (most recent call last):
        Invalid: Item 'five' was not found in the list
    """

    list = None

    __unpackargs__ = ('list',)

    messages = dict(
        integer=_('Must be an integer index'),
        outOfRange=_('Index out of range'),
        notFound=_('Item %(value)s was not found in the list'))

    def _convert_to_python(self, value, state):
        try:
            value = int(value)
        except (ValueError, TypeError):
            raise Invalid(self.message('integer', state), value, state)
        try:
            return self.list[value]
        except IndexError:
            raise Invalid(self.message('outOfRange', state), value, state)

    def _convert_from_python(self, value, state):
        for i, v in enumerate(self.list):
            if v == value:
                return i
        raise Invalid(
            self.message('notFound', state, value=repr(value)), value, state)


class DateValidator(FancyValidator):
    """
    Validates that a date is within the given range.  Be sure to call
    DateConverter first if you aren't expecting mxDateTime input.

    ``earliest_date`` and ``latest_date`` may be functions; if so,
    they will be called each time before validating.

    ``after_now`` means a time after the current timestamp; note that
    just a few milliseconds before now is invalid!  ``today_or_after``
    is more permissive, and ignores hours and minutes.

    Examples::

        >>> from datetime import datetime, timedelta
        >>> d = DateValidator(earliest_date=datetime(2003, 1, 1))
        >>> d.to_python(datetime(2004, 1, 1))
        datetime.datetime(2004, 1, 1, 0, 0)
        >>> d.to_python(datetime(2002, 1, 1))
        Traceback (most recent call last):
            ...
        Invalid: Date must be after Wednesday, 01 January 2003
        >>> d.to_python(datetime(2003, 1, 1))
        datetime.datetime(2003, 1, 1, 0, 0)
        >>> d = DateValidator(after_now=True)
        >>> now = datetime.now()
        >>> d.to_python(now+timedelta(seconds=5)) == now+timedelta(seconds=5)
        True
        >>> d.to_python(now-timedelta(days=1))
        Traceback (most recent call last):
            ...
        Invalid: The date must be sometime in the future
        >>> d.to_python(now+timedelta(days=1)) > now
        True
        >>> d = DateValidator(today_or_after=True)
        >>> d.to_python(now) == now
        True

    """

    earliest_date = None
    latest_date = None
    after_now = False
    # Like after_now, but just after this morning:
    today_or_after = False
    # Use None or 'datetime' for the datetime module in the standard lib,
    # or 'mxDateTime' to force the mxDateTime module
    datetime_module = None

    messages = dict(
        after=_('Date must be after %(date)s'),
        before=_('Date must be before %(date)s'),
        # Double %'s, because this will be substituted twice:
        date_format=_('%%A, %%d %%B %%Y'),
        future=_('The date must be sometime in the future'))

    def _validate_python(self, value, state):
        date_format = self.message('date_format', state)
        if (str is not unicode  # Python 2
                and isinstance(date_format, unicode)):
            # strftime uses the locale encoding, not Unicode
            encoding = locale.getlocale(locale.LC_TIME)[1] or 'utf-8'
            date_format = date_format.encode(encoding)
        else:
            encoding = None
        if self.earliest_date:
            if callable(self.earliest_date):
                earliest_date = self.earliest_date()
            else:
                earliest_date = self.earliest_date
            if value < earliest_date:
                date_formatted = earliest_date.strftime(date_format)
                if encoding:
                    date_formatted = date_formatted.decode(encoding)
                raise Invalid(
                    self.message('after', state, date=date_formatted),
                    value, state)
        if self.latest_date:
            if callable(self.latest_date):
                latest_date = self.latest_date()
            else:
                latest_date = self.latest_date
            if value > latest_date:
                date_formatted = latest_date.strftime(date_format)
                if encoding:
                    date_formatted = date_formatted.decode(encoding)
                raise Invalid(
                    self.message('before', state, date=date_formatted),
                    value, state)
        if self.after_now:
            dt_mod = import_datetime(self.datetime_module)
            now = datetime_now(dt_mod)
            if value < now:
                date_formatted = now.strftime(date_format)
                if encoding:
                    date_formatted = date_formatted.decode(encoding)
                raise Invalid(
                    self.message('future', state, date=date_formatted),
                    value, state)
        if self.today_or_after:
            dt_mod = import_datetime(self.datetime_module)
            now = datetime_now(dt_mod)
            today = datetime_makedate(dt_mod,
                                      now.year, now.month, now.day)
            value_as_date = datetime_makedate(
                dt_mod, value.year, value.month, value.day)
            if value_as_date < today:
                date_formatted = now.strftime(date_format)
                if encoding:
                    date_formatted = date_formatted.decode(encoding)
                raise Invalid(
                    self.message('future', state, date=date_formatted),
                    value, state)


class Bool(FancyValidator):
    """
    Always Valid, returns True or False based on the value and the
    existance of the value.

    If you want to convert strings like ``'true'`` to booleans, then
    use ``StringBool``.

    Examples::

        >>> Bool.to_python(0)
        False
        >>> Bool.to_python(1)
        True
        >>> Bool.to_python('')
        False
        >>> Bool.to_python(None)
        False
    """

    if_missing = False

    def _convert_to_python(self, value, state):
        return bool(value)

    _convert_from_python = _convert_to_python

    def empty_value(self, value):
        return False


class RangeValidator(FancyValidator):
    """This is an abstract base class for Int and Number.

    It verifies that a value is within range.  It accepts min and max
    values in the constructor.

    (Since this is an abstract base class, the tests are in Int and Number.)

    """

    messages = dict(
        tooLow=_('Please enter a number that is %(min)s or greater'),
        tooHigh=_('Please enter a number that is %(max)s or smaller'))

    min = None
    max = None

    def _validate_python(self, value, state):
        if self.min is not None:
            if value < self.min:
                msg = self.message('tooLow', state, min=self.min)
                raise Invalid(msg, value, state)
        if self.max is not None:
            if value > self.max:
                msg = self.message('tooHigh', state, max=self.max)
                raise Invalid(msg, value, state)


class Int(RangeValidator):
    """Convert a value to an integer.

    Example::

        >>> Int.to_python('10')
        10
        >>> Int.to_python('ten')
        Traceback (most recent call last):
            ...
        Invalid: Please enter an integer value
        >>> Int(min=5).to_python('6')
        6
        >>> Int(max=10).to_python('11')
        Traceback (most recent call last):
            ...
        Invalid: Please enter a number that is 10 or smaller

    """

    messages = dict(
        integer=_('Please enter an integer value'))

    def _convert_to_python(self, value, state):
        try:
            return int(value)
        except (ValueError, TypeError):
            raise Invalid(self.message('integer', state), value, state)

    _convert_from_python = _convert_to_python


class Number(RangeValidator):
    """Convert a value to a float or integer.

    Tries to convert it to an integer if no information is lost.

    Example::

        >>> Number.to_python('10')
        10
        >>> Number.to_python('10.5')
        10.5
        >>> Number.to_python('ten')
        Traceback (most recent call last):
            ...
        Invalid: Please enter a number
        >>> Number.to_python([1.2])
        Traceback (most recent call last):
            ...
        Invalid: Please enter a number
        >>> Number(min=5).to_python('6.5')
        6.5
        >>> Number(max=10.5).to_python('11.5')
        Traceback (most recent call last):
            ...
        Invalid: Please enter a number that is 10.5 or smaller

    """

    messages = dict(
        number=_('Please enter a number'))

    def _convert_to_python(self, value, state):
        try:
            value = float(value)
            try:
                int_value = int(value)
            except OverflowError:
                int_value = None
            if value == int_value:
                return int_value
            return value
        except (ValueError, TypeError):
            raise Invalid(self.message('number', state), value, state)


class ByteString(FancyValidator):
    """Convert to byte string, treating empty things as the empty string.

    Under Python 2.x you can also use the alias `String` for this validator.

    Also takes a `max` and `min` argument, and the string length must fall
    in that range.

    Also you may give an `encoding` argument, which will encode any unicode
    that is found.  Lists and tuples are joined with `list_joiner`
    (default ``', '``) in ``from_python``.

    ::

        >>> ByteString(min=2).to_python('a')
        Traceback (most recent call last):
            ...
        Invalid: Enter a value 2 characters long or more
        >>> ByteString(max=10).to_python('xxxxxxxxxxx')
        Traceback (most recent call last):
            ...
        Invalid: Enter a value not more than 10 characters long
        >>> ByteString().from_python(None)
        ''
        >>> ByteString().from_python([])
        ''
        >>> ByteString().to_python(None)
        ''
        >>> ByteString(min=3).to_python(None)
        Traceback (most recent call last):
            ...
        Invalid: Please enter a value
        >>> ByteString(min=1).to_python('')
        Traceback (most recent call last):
            ...
        Invalid: Please enter a value

    """

    min = None
    max = None
    not_empty = None
    encoding = None
    list_joiner = ', '

    messages = dict(
        tooLong=_('Enter a value not more than %(max)i characters long'),
        tooShort=_('Enter a value %(min)i characters long or more'))

    def __initargs__(self, new_attrs):
        if self.not_empty is None and self.min:
            self.not_empty = True

    def _convert_to_python(self, value, state):
        if value is None:
            value = ''
        elif not isinstance(value, basestring):
            try:
                value = bytes(value)
            except UnicodeEncodeError:
                value = unicode(value)
        if self.encoding is not None and isinstance(value, unicode):
            value = value.encode(self.encoding)
        return value

    def _convert_from_python(self, value, state):
        if value is None:
            value = ''
        elif not isinstance(value, basestring):
            if isinstance(value, (list, tuple)):
                value = self.list_joiner.join(
                    self._convert_from_python(v, state) for v in value)
            try:
                value = str(value)
            except UnicodeEncodeError:
                value = unicode(value)
        if self.encoding is not None and isinstance(value, unicode):
            value = value.encode(self.encoding)
        if self.strip:
            value = value.strip()
        return value

    def _validate_other(self, value, state):
        if self.max is None and self.min is None:
            return
        if value is None:
            value = ''
        elif not isinstance(value, basestring):
            try:
                value = str(value)
            except UnicodeEncodeError:
                value = unicode(value)
        if self.max is not None and len(value) > self.max:
            raise Invalid(
                self.message('tooLong', state, max=self.max), value, state)
        if self.min is not None and len(value) < self.min:
            raise Invalid(
                self.message('tooShort', state, min=self.min), value, state)

    def empty_value(self, value):
        return ''


class UnicodeString(ByteString):
    """Convert things to unicode string.

    This is implemented as a specialization of the ByteString class.

    Under Python 3.x you can also use the alias `String` for this validator.

    In addition to the String arguments, an encoding argument is also
    accepted. By default the encoding will be utf-8. You can overwrite
    this using the encoding parameter. You can also set inputEncoding
    and outputEncoding differently. An inputEncoding of None means
    "do not decode", an outputEncoding of None means "do not encode".

    All converted strings are returned as Unicode strings.

    ::

        >>> UnicodeString().to_python(None)
        u''
        >>> UnicodeString().to_python([])
        u''
        >>> UnicodeString(encoding='utf-7').to_python('Ni Ni Ni')
        u'Ni Ni Ni'

    """
    encoding = 'utf-8'
    inputEncoding = NoDefault
    outputEncoding = NoDefault
    messages = dict(
        badEncoding=_('Invalid data or incorrect encoding'))

    def __init__(self, **kw):
        ByteString.__init__(self, **kw)
        if self.inputEncoding is NoDefault:
            self.inputEncoding = self.encoding
        if self.outputEncoding is NoDefault:
            self.outputEncoding = self.encoding

    def _convert_to_python(self, value, state):
        if not value:
            return u''
        if isinstance(value, unicode):
            return value
        if not isinstance(value, unicode):
            if hasattr(value, '__unicode__'):
                value = unicode(value)
                return value
            if not (unicode is str  # Python 3
                    and isinstance(value, bytes) and self.inputEncoding):
                value = str(value)
        if self.inputEncoding and not isinstance(value, unicode):
            try:
                value = unicode(value, self.inputEncoding)
            except UnicodeDecodeError:
                raise Invalid(self.message('badEncoding', state), value, state)
            except TypeError:
                raise Invalid(
                    self.message('badType', state,
                        type=type(value), value=value), value, state)
        return value

    def _convert_from_python(self, value, state):
        if not isinstance(value, unicode):
            if hasattr(value, '__unicode__'):
                value = unicode(value)
            else:
                value = str(value)
        if self.outputEncoding and isinstance(value, unicode):
            value = value.encode(self.outputEncoding)
        return value

    def empty_value(self, value):
        return u''


# Provide proper alias for native strings

String = UnicodeString if str is unicode else ByteString


class Set(FancyValidator):
    """
    This is for when you think you may return multiple values for a
    certain field.

    This way the result will always be a list, even if there's only
    one result.  It's equivalent to ForEach(convert_to_list=True).

    If you give ``use_set=True``, then it will return an actual
    ``set`` object.

    ::

       >>> Set.to_python(None)
       []
       >>> Set.to_python('this')
       ['this']
       >>> Set.to_python(('this', 'that'))
       ['this', 'that']
       >>> s = Set(use_set=True)
       >>> s.to_python(None)
       set([])
       >>> s.to_python('this')
       set(['this'])
       >>> s.to_python(('this',))
       set(['this'])
    """

    use_set = False

    if_missing = ()
    accept_iterator = True

    def _convert_to_python(self, value, state):
        if self.use_set:
            if isinstance(value, set):
                return value
            elif isinstance(value, (list, tuple)):
                return set(value)
            elif value is None:
                return set()
            else:
                return set([value])
        else:
            if isinstance(value, list):
                return value
            elif isinstance(value, set):
                return list(value)
            elif isinstance(value, tuple):
                return list(value)
            elif value is None:
                return []
            else:
                return [value]

    def empty_value(self, value):
        if self.use_set:
            return set()
        else:
            return []


class Email(FancyValidator):
    r"""
    Validate an email address.

    If you pass ``resolve_domain=True``, then it will try to resolve
    the domain name to make sure it's valid.  This takes longer, of
    course. You must have the `dnspython <http://www.dnspython.org/>`__ modules
    installed to look up DNS (MX and A) records.

    ::

        >>> e = Email()
        >>> e.to_python(' test@foo.com ')
        'test@foo.com'
        >>> e.to_python('test')
        Traceback (most recent call last):
            ...
        Invalid: An email address must contain a single @
        >>> e.to_python('test@foobar')
        Traceback (most recent call last):
            ...
        Invalid: The domain portion of the email address is invalid (the portion after the @: foobar)
        >>> e.to_python('test@foobar.com.5')
        Traceback (most recent call last):
            ...
        Invalid: The domain portion of the email address is invalid (the portion after the @: foobar.com.5)
        >>> e.to_python('test@foo..bar.com')
        Traceback (most recent call last):
            ...
        Invalid: The domain portion of the email address is invalid (the portion after the @: foo..bar.com)
        >>> e.to_python('test@.foo.bar.com')
        Traceback (most recent call last):
            ...
        Invalid: The domain portion of the email address is invalid (the portion after the @: .foo.bar.com)
        >>> e.to_python('nobody@xn--m7r7ml7t24h.com')
        'nobody@xn--m7r7ml7t24h.com'
        >>> e.to_python('o*reilly@test.com')
        'o*reilly@test.com'
        >>> e = Email(resolve_domain=True)
        >>> e.resolve_domain
        True
        >>> e.to_python('doesnotexist@colorstudy.com')
        'doesnotexist@colorstudy.com'
        >>> e.to_python('test@nyu.edu')
        'test@nyu.edu'
        >>> # NOTE: If you do not have dnspython installed this example won't work:
        >>> e.to_python('test@thisdomaindoesnotexistithinkforsure.com')
        Traceback (most recent call last):
            ...
        Invalid: The domain of the email address does not exist (the portion after the @: thisdomaindoesnotexistithinkforsure.com)
        >>> e.to_python(u'test@google.com')
        u'test@google.com'
        >>> e = Email(not_empty=False)
        >>> e.to_python('')

    """

    resolve_domain = False
    resolve_timeout = 10  # timeout in seconds when resolving domains

    usernameRE = re.compile(r"^[\w!#$%&'*+\-/=?^`{|}~.]+$")
    domainRE = re.compile(r'''
        ^(?:[a-z0-9][a-z0-9\-]{,62}\.)+        # subdomain
        (?:[a-z]{2,63}|xn--[a-z0-9\-]{2,59})$  # top level domain
    ''', re.I | re.VERBOSE)

    messages = dict(
        empty=_('Please enter an email address'),
        noAt=_('An email address must contain a single @'),
        badUsername=_('The username portion of the email address is invalid'
            ' (the portion before the @: %(username)s)'),
        socketError=_('An error occured when trying to connect to the server:'
            ' %(error)s'),
        badDomain=_('The domain portion of the email address is invalid'
            ' (the portion after the @: %(domain)s)'),
        domainDoesNotExist=_('The domain of the email address does not exist'
            ' (the portion after the @: %(domain)s)'))

    def __init__(self, *args, **kw):
        FancyValidator.__init__(self, *args, **kw)
        if self.resolve_domain:
            if not have_dns:
                warnings.warn(
                    "dnspython <http://www.dnspython.org/> is not installed on"
                    " your system (or the dns.resolver package cannot be found)."
                    " I cannot resolve domain names in addresses")
                raise ImportError("no module named dns.resolver")

    def _validate_python(self, value, state):
        if not value:
            raise Invalid(self.message('empty', state), value, state)
        value = value.strip()
        splitted = value.split('@', 1)
        try:
            username, domain = splitted
        except ValueError:
            raise Invalid(self.message('noAt', state), value, state)
        if not self.usernameRE.search(username):
            raise Invalid(
                self.message('badUsername', state, username=username),
                value, state)
        try:
            idna_domain = [idna.ToASCII(p) for p in domain.split('.')]
            if unicode is str:  # Python 3
                idna_domain = [p.decode('ascii') for p in idna_domain]
            idna_domain = '.'.join(idna_domain)
        except UnicodeError:
            # UnicodeError: label empty or too long
            # This exception might happen if we have an invalid domain name part
            # (for example test@.foo.bar.com)
            raise Invalid(
                self.message('badDomain', state, domain=domain),
                value, state)
        if not self.domainRE.search(idna_domain):
            raise Invalid(
                self.message('badDomain', state, domain=domain),
                value, state)
        if self.resolve_domain:
            assert have_dns, "dnspython should be available"
            global socket
            if socket is None:
                import socket
            try:
                try:
                    dns.resolver.query(domain, 'MX')
                except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer) as e:
                    try:
                        dns.resolver.query(domain, 'A')
                    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer) as e:
                        raise Invalid(
                            self.message('domainDoesNotExist',
                                state, domain=domain), value, state)
            except (socket.error, dns.exception.DNSException) as e:
                raise Invalid(
                    self.message('socketError', state, error=e), value, state)

    def _convert_to_python(self, value, state):
        return value.strip()


class URL(FancyValidator):
    """
    Validate a URL, either http://... or https://.  If check_exists
    is true, then we'll actually make a request for the page.

    If add_http is true, then if no scheme is present we'll add
    http://

    ::

        >>> u = URL(add_http=True)
        >>> u.to_python('foo.com')
        'http://foo.com'
        >>> u.to_python('http://hahaha.ha/bar.html')
        'http://hahaha.ha/bar.html'
        >>> u.to_python('http://xn--m7r7ml7t24h.com')
        'http://xn--m7r7ml7t24h.com'
        >>> u.to_python('http://xn--c1aay4a.xn--p1ai')
        'http://xn--c1aay4a.xn--p1ai'
        >>> u.to_python('http://foo.com/test?bar=baz&fleem=morx')
        'http://foo.com/test?bar=baz&fleem=morx'
        >>> u.to_python('http://foo.com/login?came_from=http%3A%2F%2Ffoo.com%2Ftest')
        'http://foo.com/login?came_from=http%3A%2F%2Ffoo.com%2Ftest'
        >>> u.to_python('http://foo.com:8000/test.html')
        'http://foo.com:8000/test.html'
        >>> u.to_python('http://foo.com/something\\nelse')
        Traceback (most recent call last):
            ...
        Invalid: That is not a valid URL
        >>> u.to_python('https://test.com')
        'https://test.com'
        >>> u.to_python('http://test')
        Traceback (most recent call last):
            ...
        Invalid: You must provide a full domain name (like test.com)
        >>> u.to_python('http://test..com')
        Traceback (most recent call last):
            ...
        Invalid: That is not a valid URL
        >>> u = URL(add_http=False, check_exists=True)
        >>> u.to_python('http://google.com')
        'http://google.com'
        >>> u.to_python('google.com')
        Traceback (most recent call last):
            ...
        Invalid: You must start your URL with http://, https://, etc
        >>> u.to_python('http://www.formencode.org/does/not/exist/page.html')
        Traceback (most recent call last):
            ...
        Invalid: The server responded that the page could not be found
        >>> u.to_python('http://this.domain.does.not.exist.example.org/test.html')
        ... # doctest: +ELLIPSIS
        Traceback (most recent call last):
            ...
        Invalid: An error occured when trying to connect to the server: ...

    If you want to allow addresses without a TLD (e.g., ``localhost``) you can do::

        >>> URL(require_tld=False).to_python('http://localhost')
        'http://localhost'

    By default, internationalized domain names (IDNA) in Unicode will be
    accepted and encoded to ASCII using Punycode (as described in RFC 3490).
    You may set allow_idna to False to change this behavior::

        >>> URL(allow_idna=True).to_python(
        ... u'http://\u0433\u0443\u0433\u043b.\u0440\u0444')
        'http://xn--c1aay4a.xn--p1ai'
        >>> URL(allow_idna=True, add_http=True).to_python(
        ... u'\u0433\u0443\u0433\u043b.\u0440\u0444')
        'http://xn--c1aay4a.xn--p1ai'
        >>> URL(allow_idna=False).to_python(
        ... u'http://\u0433\u0443\u0433\u043b.\u0440\u0444')
        Traceback (most recent call last):
        ...
        Invalid: That is not a valid URL

    """

    add_http = True
    allow_idna = True
    check_exists = False
    require_tld = True

    url_re = re.compile(r'''
        ^(http|https)://
        (?:[%:\w]*@)?                              # authenticator
        (?:                                        # ip or domain
        (?P<ip>(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?))|
        (?P<domain>[a-z0-9][a-z0-9\-]{,62}\.)*     # subdomain
        (?P<tld>[a-z]{2,63}|xn--[a-z0-9\-]{2,59})  # top level domain
        )
        (?::[0-9]{1,5})?                           # port
        # files/delims/etc
        (?P<path>/[a-z0-9\-\._~:/\?#\[\]@!%\$&\'\(\)\*\+,;=]*)?
        $
    ''', re.I | re.VERBOSE)

    scheme_re = re.compile(r'^[a-zA-Z]+:')

    messages = dict(
        noScheme=_('You must start your URL with http://, https://, etc'),
        badURL=_('That is not a valid URL'),
        httpError=_('An error occurred when trying to access the URL:'
            ' %(error)s'),
        socketError=_('An error occured when trying to connect to the server:'
            ' %(error)s'),
        notFound=_('The server responded that the page could not be found'),
        status=_('The server responded with a bad status code (%(status)s)'),
        noTLD=_('You must provide a full domain name (like %(domain)s.com)'))

    def _convert_to_python(self, value, state):
        value = value.strip()
        if self.add_http:
            if not self.scheme_re.search(value):
                value = 'http://' + value
        if self.allow_idna:
            value = self._encode_idna(value)
        match = self.scheme_re.search(value)
        if not match:
            raise Invalid(self.message('noScheme', state), value, state)
        value = match.group(0).lower() + value[len(match.group(0)):]
        match = self.url_re.search(value)
        if not match:
            raise Invalid(self.message('badURL', state), value, state)
        if self.require_tld and not match.group('domain'):
            raise Invalid(
                self.message('noTLD', state, domain=match.group('tld')),
                value, state)
        if self.check_exists and value.startswith(('http://', 'https://')):
            self._check_url_exists(value, state)
        return value

    def _encode_idna(self, url):
        global urlparse
        if urlparse is None:
            import urlparse
        try:
            scheme, netloc, path, params, query, fragment = urlparse.urlparse(
                url)
        except ValueError:
            return url
        try:
            netloc = netloc.encode('idna')
            if unicode is str:  # Python 3
                netloc = netloc.decode('ascii')
            return str(urlparse.urlunparse((scheme, netloc,
                path, params, query, fragment)))
        except UnicodeError:
            return url

    def _check_url_exists(self, url, state):
        global httplib, urlparse, socket
        if httplib is None:
            import httplib
        if urlparse is None:
            import urlparse
        if socket is None:
            import socket
        scheme, netloc, path, params, query, fragment = urlparse.urlparse(
            url, 'http')
        if scheme == 'https':
            ConnClass = httplib.HTTPSConnection
        else:
            ConnClass = httplib.HTTPConnection
        try:
            conn = ConnClass(netloc)
            if params:
                path += ';' + params
            if query:
                path += '?' + query
            conn.request('HEAD', path)
            res = conn.getresponse()
        except httplib.HTTPException as e:
            raise Invalid(
                self.message('httpError', state, error=e), state, url)
        except socket.error as e:
            raise Invalid(
                self.message('socketError', state, error=e), state, url)
        else:
            if res.status == 404:
                raise Invalid(
                    self.message('notFound', state), state, url)
            if not 200 <= res.status < 500:
                raise Invalid(
                    self.message('status', state, status=res.status),
                    state, url)


class XRI(FancyValidator):
    r"""
    Validator for XRIs.

    It supports both i-names and i-numbers, of the first version of the XRI
    standard.

    ::

        >>> inames = XRI(xri_type="i-name")
        >>> inames.to_python("   =John.Smith ")
        '=John.Smith'
        >>> inames.to_python("@Free.Software.Foundation")
        '@Free.Software.Foundation'
        >>> inames.to_python("Python.Software.Foundation")
        Traceback (most recent call last):
            ...
        Invalid: The type of i-name is not defined; it may be either individual or organizational
        >>> inames.to_python("http://example.org")
        Traceback (most recent call last):
            ...
        Invalid: The type of i-name is not defined; it may be either individual or organizational
        >>> inames.to_python("=!2C43.1A9F.B6F6.E8E6")
        Traceback (most recent call last):
            ...
        Invalid: "!2C43.1A9F.B6F6.E8E6" is an invalid i-name
        >>> iname_with_schema = XRI(True, xri_type="i-name")
        >>> iname_with_schema.to_python("=Richard.Stallman")
        'xri://=Richard.Stallman'
        >>> inames.to_python("=John Smith")
        Traceback (most recent call last):
            ...
        Invalid: "John Smith" is an invalid i-name
        >>> inumbers = XRI(xri_type="i-number")
        >>> inumbers.to_python("!!1000!de21.4536.2cb2.8074")
        '!!1000!de21.4536.2cb2.8074'
        >>> inumbers.to_python("@!1000.9554.fabd.129c!2847.df3c")
        '@!1000.9554.fabd.129c!2847.df3c'

    """

    iname_valid_pattern = re.compile(r"""
    ^
    [\w]+                  # A global alphanumeric i-name
    (\.[\w]+)*             # An i-name with dots
    (\*[\w]+(\.[\w]+)*)*   # A community i-name
    $
    """, re.VERBOSE | re.UNICODE)

    iname_invalid_start = re.compile(r"^[\d\.-]", re.UNICODE)
    """@cvar: These characters must not be at the beggining of the i-name"""

    inumber_pattern = re.compile(r"""
    ^
    (
    [=@]!       # It's a personal or organization i-number
    |
    !!          # It's a network i-number
    )
    [\dA-F]{1,4}(\.[\dA-F]{1,4}){0,3}       # A global i-number
    (![\dA-F]{1,4}(\.[\dA-F]{1,4}){0,3})*   # Zero or more sub i-numbers
    $
    """, re.VERBOSE | re.IGNORECASE)

    messages = dict(
        noType=_('The type of i-name is not defined;'
            ' it may be either individual or organizational'),
        repeatedChar=_('Dots and dashes may not be repeated consecutively'),
        badIname=_('"%(iname)s" is an invalid i-name'),
        badInameStart=_('i-names may not start with numbers'
            ' nor punctuation marks'),
        badInumber=_('"%(inumber)s" is an invalid i-number'),
        badType=_('The XRI must be a string (not a %(type)s: %(value)r)'),
        badXri=_('"%(xri_type)s" is not a valid type of XRI'))

    def __init__(self, add_xri=False, xri_type="i-name", **kwargs):
        """Create an XRI validator.

        @param add_xri: Should the schema be added if not present?
            Officially it's optional.
        @type add_xri: C{bool}
        @param xri_type: What type of XRI should be validated?
            Possible values: C{i-name} or C{i-number}.
        @type xri_type: C{str}

        """
        self.add_xri = add_xri
        assert xri_type in ('i-name', 'i-number'), (
            'xri_type must be "i-name" or "i-number"')
        self.xri_type = xri_type
        super(XRI, self).__init__(**kwargs)

    def _convert_to_python(self, value, state):
        """Prepend the 'xri://' schema if needed and remove trailing spaces"""
        value = value.strip()
        if self.add_xri and not value.startswith('xri://'):
            value = 'xri://' + value
        return value

    def _validate_python(self, value, state=None):
        """Validate an XRI

        @raise Invalid: If at least one of the following conditions in met:
            - C{value} is not a string.
            - The XRI is not a personal, organizational or network one.
            - The relevant validator (i-name or i-number) considers the XRI
                is not valid.

        """
        if not isinstance(value, basestring):
            raise Invalid(
                self.message('badType', state,
                    type=str(type(value)), value=value), value, state)

        # Let's remove the schema, if any
        if value.startswith('xri://'):
            value = value[6:]

        if not value[0] in ('@', '=') and not (
                self.xri_type == 'i-number' and value[0] == '!'):
            raise Invalid(self.message('noType', state), value, state)

        if self.xri_type == 'i-name':
            self._validate_iname(value, state)
        else:
            self._validate_inumber(value, state)

    def _validate_iname(self, iname, state):
        """Validate an i-name"""
        # The type is not required here:
        iname = iname[1:]
        if '..' in iname or '--' in iname:
            raise Invalid(self.message('repeatedChar', state), iname, state)
        if self.iname_invalid_start.match(iname):
            raise Invalid(self.message('badInameStart', state), iname, state)
        if not self.iname_valid_pattern.match(iname) or '_' in iname:
            raise Invalid(
                self.message('badIname', state, iname=iname), iname, state)

    def _validate_inumber(self, inumber, state):
        """Validate an i-number"""
        if not self.__class__.inumber_pattern.match(inumber):
            raise Invalid(
                self.message('badInumber', state,
                    inumber=inumber, value=inumber), inumber, state)


class OpenId(FancyValidator):
    r"""
    OpenId validator.

    ::
        >>> v = OpenId(add_schema=True)
        >>> v.to_python(' example.net ')
        'http://example.net'
        >>> v.to_python('@TurboGears')
        'xri://@TurboGears'
        >>> w = OpenId(add_schema=False)
        >>> w.to_python(' example.net ')
        Traceback (most recent call last):
        ...
        Invalid: "example.net" is not a valid OpenId (it is neither an URL nor an XRI)
        >>> w.to_python('!!1000')
        '!!1000'
        >>> w.to_python('look@me.com')
        Traceback (most recent call last):
        ...
        Invalid: "look@me.com" is not a valid OpenId (it is neither an URL nor an XRI)

    """

    messages = dict(
        badId=_('"%(id)s" is not a valid OpenId'
            ' (it is neither an URL nor an XRI)'))

    def __init__(self, add_schema=False, **kwargs):
        """Create an OpenId validator.

        @param add_schema: Should the schema be added if not present?
        @type add_schema: C{bool}

        """
        self.url_validator = URL(add_http=add_schema)
        self.iname_validator = XRI(add_schema, xri_type="i-name")
        self.inumber_validator = XRI(add_schema, xri_type="i-number")

    def _convert_to_python(self, value, state):
        value = value.strip()
        try:
            return self.url_validator.to_python(value, state)
        except Invalid:
            try:
                return self.iname_validator.to_python(value, state)
            except Invalid:
                try:
                    return self.inumber_validator.to_python(value, state)
                except Invalid:
                    pass
        # It's not an OpenId!
        raise Invalid(self.message('badId', state, id=value), value, state)

    def _validate_python(self, value, state):
        self._convert_to_python(value, state)


def StateProvince(*kw, **kwargs):
    deprecation_warning("please use formencode.national.USStateProvince")
    from formencode.national import USStateProvince
    return USStateProvince(*kw, **kwargs)


def PhoneNumber(*kw, **kwargs):
    deprecation_warning("please use formencode.national.USPhoneNumber")
    from formencode.national import USPhoneNumber
    return USPhoneNumber(*kw, **kwargs)


def IPhoneNumberValidator(*kw, **kwargs):
    deprecation_warning(
        "please use formencode.national.InternationalPhoneNumber")
    from formencode.national import InternationalPhoneNumber
    return InternationalPhoneNumber(*kw, **kwargs)


class FieldStorageUploadConverter(FancyValidator):
    """
    Handles cgi.FieldStorage instances that are file uploads.

    This doesn't do any conversion, but it can detect empty upload
    fields (which appear like normal fields, but have no filename when
    no upload was given).
    """
    def _convert_to_python(self, value, state=None):
        if isinstance(value, cgi.FieldStorage):
            if getattr(value, 'filename', None):
                return value
            raise Invalid('invalid', value, state)
        else:
            return value

    def is_empty(self, value):
        if isinstance(value, cgi.FieldStorage):
            return not bool(getattr(value, 'filename', None))
        return FancyValidator.is_empty(self, value)


class FileUploadKeeper(FancyValidator):
    """
    Takes two inputs (a dictionary with keys ``static`` and
    ``upload``) and converts them into one value on the Python side (a
    dictionary with ``filename`` and ``content`` keys).  The upload
    takes priority over the static value.  The filename may be None if
    it can't be discovered.

    Handles uploads of both text and ``cgi.FieldStorage`` upload
    values.

    This is basically for use when you have an upload field, and you
    want to keep the upload around even if the rest of the form
    submission fails.  When converting *back* to the form submission,
    there may be extra values ``'original_filename'`` and
    ``'original_content'``, which may want to use in your form to show
    the user you still have their content around.

    To use this, make sure you are using variabledecode, then use
    something like::

      <input type="file" name="myfield.upload">
      <input type="hidden" name="myfield.static">

    Then in your scheme::

      class MyScheme(Scheme):
          myfield = FileUploadKeeper()

    Note that big file uploads mean big hidden fields, and lots of
    bytes passed back and forth in the case of an error.
    """

    upload_key = 'upload'
    static_key = 'static'

    def _convert_to_python(self, value, state):
        upload = value.get(self.upload_key)
        static = value.get(self.static_key, '').strip()
        filename = content = None
        if isinstance(upload, cgi.FieldStorage):
            filename = upload.filename
            content = upload.value
        elif isinstance(upload, basestring) and upload:
            filename = None
            # @@: Should this encode upload if it is unicode?
            content = upload
        if not content and static:
            filename, content = static.split(None, 1)
            filename = '' if filename == '-' else filename.decode('base64')
            content = content.decode('base64')
        return {'filename': filename, 'content': content}

    def _convert_from_python(self, value, state):
        filename = value.get('filename', '')
        content = value.get('content', '')
        if filename or content:
            result = self.pack_content(filename, content)
            return {self.upload_key: '',
                    self.static_key: result,
                    'original_filename': filename,
                    'original_content': content}
        else:
            return {self.upload_key: '',
                    self.static_key: ''}

    def pack_content(self, filename, content):
        enc_filename = self.base64encode(filename) or '-'
        enc_content = (content or '').encode('base64')
        result = '%s %s' % (enc_filename, enc_content)
        return result


class DateConverter(FancyValidator):
    """
    Validates and converts a string date, like mm/yy, dd/mm/yy,
    dd-mm-yy, etc.  Using ``month_style`` you can support
    the three general styles ``mdy`` = ``us`` = ``mm/dd/yyyy``,
    ``dmy`` = ``euro`` = ``dd/mm/yyyy`` and
    ``ymd`` = ``iso`` = ``yyyy/mm/dd``.

    Accepts English month names, also abbreviated.  Returns value as a
    datetime object (you can get mx.DateTime objects if you use
    ``datetime_module='mxDateTime'``).  Two year dates are assumed to
    be within 1950-2020, with dates from 21-49 being ambiguous and
    signaling an error.

    Use accept_day=False if you just want a month/year (like for a
    credit card expiration date).

    ::

        >>> d = DateConverter()
        >>> d.to_python('12/3/09')
        datetime.date(2009, 12, 3)
        >>> d.to_python('12/3/2009')
        datetime.date(2009, 12, 3)
        >>> d.to_python('2/30/04')
        Traceback (most recent call last):
            ...
        Invalid: That month only has 29 days
        >>> d.to_python('13/2/05')
        Traceback (most recent call last):
            ...
        Invalid: Please enter a month from 1 to 12
        >>> d.to_python('1/1/200')
        Traceback (most recent call last):
            ...
        Invalid: Please enter a four-digit year after 1899

    If you change ``month_style`` you can get European-style dates::

        >>> d = DateConverter(month_style='dd/mm/yyyy')
        >>> date = d.to_python('12/3/09')
        >>> date
        datetime.date(2009, 3, 12)
        >>> d.from_python(date)
        '12/03/2009'
    """

    # set to False if you want only month and year
    accept_day = True
    # allowed month styles: 'mdy' = 'us', 'dmy' = 'euro', 'ymd' = 'iso'
    # also allowed: 'mm/dd/yyyy', 'dd/mm/yyyy', 'yyyy/mm/dd'
    month_style = 'mdy'
    # preferred separator for reverse conversion: '/', '.' or '-'
    separator = '/'

    # Use 'datetime' to force the Python datetime module, or
    # 'mxDateTime' to force the mxDateTime module (None means use
    # datetime, or if not present mxDateTime)
    datetime_module = None

    _month_names = {
        'jan': 1, 'january': 1,
        'feb': 2, 'febuary': 2,
        'mar': 3, 'march': 3,
        'apr': 4, 'april': 4,
        'may': 5,
        'jun': 6, 'june': 6,
        'jul': 7, 'july': 7,
        'aug': 8, 'august': 8,
        'sep': 9, 'sept': 9, 'september': 9,
        'oct': 10, 'october': 10,
        'nov': 11, 'november': 11,
        'dec': 12, 'december': 12,
        }

    _date_re = dict(
        dmy=re.compile(
            r'^\s*(\d\d?)[\-\./\\](\d\d?|%s)[\-\./\\](\d\d\d?\d?)\s*$'
                % '|'.join(_month_names), re.I),
        mdy=re.compile(
            r'^\s*(\d\d?|%s)[\-\./\\](\d\d?)[\-\./\\](\d\d\d?\d?)\s*$'
                % '|'.join(_month_names), re.I),
        ymd=re.compile(
            r'^\s*(\d\d\d?\d?)[\-\./\\](\d\d?|%s)[\-\./\\](\d\d?)\s*$'
                % '|'.join(_month_names), re.I),
        my=re.compile(
            r'^\s*(\d\d?|%s)[\-\./\\](\d\d\d?\d?)\s*$'
                % '|'.join(_month_names), re.I),
        ym=re.compile(
            r'^\s*(\d\d\d?\d?)[\-\./\\](\d\d?|%s)\s*$'
                % '|'.join(_month_names), re.I))

    _formats = dict(d='%d', m='%m', y='%Y')

    _human_formats = dict(d=_('DD'), m=_('MM'), y=_('YYYY'))

    # Feb. should be leap-year aware (but mxDateTime does catch that)
    _monthDays = {
        1: 31, 2: 29, 3: 31, 4: 30, 5: 31, 6: 30, 7: 31, 8: 31,
        9: 30, 10: 31, 11: 30, 12: 31}

    messages = dict(
        badFormat=_('Please enter the date in the form %(format)s'),
        monthRange=_('Please enter a month from 1 to 12'),
        invalidDay=_('Please enter a valid day'),
        dayRange=_('That month only has %(days)i days'),
        invalidDate=_('That is not a valid day (%(exception)s)'),
        unknownMonthName=_('Unknown month name: %(month)s'),
        invalidYear=_('Please enter a number for the year'),
        fourDigitYear=_('Please enter a four-digit year after 1899'),
        wrongFormat=_('Please enter the date in the form %(format)s'))

    def __init__(self, *args, **kw):
        super(DateConverter, self).__init__(*args, **kw)
        month_style = (self.month_style or DateConverter.month_style).lower()
        accept_day = bool(self.accept_day)
        self.accept_day = self.accept_day
        if month_style in ('mdy',
                'md', 'mm/dd/yyyy', 'mm/dd', 'us', 'american'):
            month_style = 'mdy'
        elif month_style in ('dmy',
                'dm', 'dd/mm/yyyy', 'dd/mm', 'euro', 'european'):
            month_style = 'dmy'
        elif month_style in ('ymd',
                'ym', 'yyyy/mm/dd', 'yyyy/mm', 'iso', 'china', 'chinese'):
            month_style = 'ymd'
        else:
            raise TypeError('Bad month_style: %r' % month_style)
        self.month_style = month_style
        separator = self.separator
        if not separator or separator == 'auto':
            separator = dict(mdy='/', dmy='.', ymd='-')[month_style]
        elif separator not in ('-', '.', '/', '\\'):
            raise TypeError('Bad separator: %r' % separator)
        self.separator = separator
        self.format = separator.join(self._formats[part]
            for part in month_style if part != 'd' or accept_day)
        self.human_format = separator.join(self._human_formats[part]
            for part in month_style if part != 'd' or accept_day)

    def _convert_to_python(self, value, state):
        self.assert_string(value, state)
        month_style = self.month_style
        if not self.accept_day:
            month_style = 'ym' if month_style == 'ymd' else 'my'
        match = self._date_re[month_style].search(value)
        if not match:
            raise Invalid(
                self.message('badFormat', state,
                    format=self.human_format), value, state)
        groups = match.groups()
        if self.accept_day:
            if month_style == 'mdy':
                month, day, year = groups
            elif month_style == 'dmy':
                day, month, year = groups
            else:
                year, month, day = groups
            day = int(day)
            if not 1 <= day <= 31:
                raise Invalid(self.message('invalidDay', state), value, state)
        else:
            day = 1
            if month_style == 'my':
                month, year = groups
            else:
                year, month = groups
        month = self.make_month(month, state)
        if not 1 <= month <= 12:
            raise Invalid(self.message('monthRange', state), value, state)
        if self._monthDays[month] < day:
            raise Invalid(
                self.message('dayRange', state,
                    days=self._monthDays[month]), value, state)
        year = self.make_year(year, state)
        dt_mod = import_datetime(self.datetime_module)
        try:
            return datetime_makedate(dt_mod, year, month, day)
        except ValueError as v:
            raise Invalid(
                self.message('invalidDate', state,
                    exception=str(v)), value, state)

    def make_month(self, value, state):
        try:
            return int(value)
        except ValueError:
            try:
                return self._month_names[value.lower().strip()]
            except KeyError:
                raise Invalid(
                    self.message('unknownMonthName', state,
                        month=value), value, state)

    def make_year(self, year, state):
        try:
            year = int(year)
        except ValueError:
            raise Invalid(self.message('invalidYear', state), year, state)
        if year <= 20:
            year += 2000
        elif 50 <= year < 100:
            year += 1900
        if 20 < year < 50 or 99 < year < 1900:
            raise Invalid(self.message('fourDigitYear', state), year, state)
        return year

    def _convert_from_python(self, value, state):
        if self.if_empty is not NoDefault and not value:
            return ''
        return value.strftime(self.format)


class TimeConverter(FancyValidator):
    """
    Converts times in the format HH:MM:SSampm to (h, m, s).
    Seconds are optional.

    For ampm, set use_ampm = True.  For seconds, use_seconds = True.
    Use 'optional' for either of these to make them optional.

    Examples::

        >>> tim = TimeConverter()
        >>> tim.to_python('8:30')
        (8, 30)
        >>> tim.to_python('20:30')
        (20, 30)
        >>> tim.to_python('30:00')
        Traceback (most recent call last):
            ...
        Invalid: You must enter an hour in the range 0-23
        >>> tim.to_python('13:00pm')
        Traceback (most recent call last):
            ...
        Invalid: You must enter an hour in the range 1-12
        >>> tim.to_python('12:-1')
        Traceback (most recent call last):
            ...
        Invalid: You must enter a minute in the range 0-59
        >>> tim.to_python('12:02pm')
        (12, 2)
        >>> tim.to_python('12:02am')
        (0, 2)
        >>> tim.to_python('1:00PM')
        (13, 0)
        >>> tim.from_python((13, 0))
        '13:00:00'
        >>> tim2 = tim(use_ampm=True, use_seconds=False)
        >>> tim2.from_python((13, 0))
        '1:00pm'
        >>> tim2.from_python((0, 0))
        '12:00am'
        >>> tim2.from_python((12, 0))
        '12:00pm'

    Examples with ``datetime.time``::

        >>> v = TimeConverter(use_datetime=True)
        >>> a = v.to_python('18:00')
        >>> a
        datetime.time(18, 0)
        >>> b = v.to_python('30:00')
        Traceback (most recent call last):
            ...
        Invalid: You must enter an hour in the range 0-23
        >>> v2 = TimeConverter(prefer_ampm=True, use_datetime=True)
        >>> v2.from_python(a)
        '6:00:00pm'
        >>> v3 = TimeConverter(prefer_ampm=True,
        ...                    use_seconds=False, use_datetime=True)
        >>> a = v3.to_python('18:00')
        >>> a
        datetime.time(18, 0)
        >>> v3.from_python(a)
        '6:00pm'
        >>> a = v3.to_python('18:00:00')
        Traceback (most recent call last):
            ...
        Invalid: You may not enter seconds
    """

    use_ampm = 'optional'
    prefer_ampm = False
    use_seconds = 'optional'
    use_datetime = False
    # This can be set to make it prefer mxDateTime:
    datetime_module = None

    messages = dict(
        noAMPM=_('You must indicate AM or PM'),
        tooManyColon=_('There are too many :\'s'),
        noSeconds=_('You may not enter seconds'),
        secondsRequired=_('You must enter seconds'),
        minutesRequired=_('You must enter minutes (after a :)'),
        badNumber=_('The %(part)s value you gave is not a number: %(number)r'),
        badHour=_('You must enter an hour in the range %(range)s'),
        badMinute=_('You must enter a minute in the range 0-59'),
        badSecond=_('You must enter a second in the range 0-59'))

    def _convert_to_python(self, value, state):
        result = self._to_python_tuple(value, state)
        if self.use_datetime:
            dt_mod = import_datetime(self.datetime_module)
            time_class = datetime_time(dt_mod)
            return time_class(*result)
        else:
            return result

    def _to_python_tuple(self, value, state):
        time = value.strip()
        explicit_ampm = False
        if self.use_ampm:
            last_two = time[-2:].lower()
            if last_two not in ('am', 'pm'):
                if self.use_ampm != 'optional':
                    raise Invalid(self.message('noAMPM', state), value, state)
                offset = 0
            else:
                explicit_ampm = True
                offset = 12 if last_two == 'pm' else 0
                time = time[:-2]
        else:
            offset = 0
        parts = time.split(':', 3)
        if len(parts) > 3:
            raise Invalid(self.message('tooManyColon', state), value, state)
        if len(parts) == 3 and not self.use_seconds:
            raise Invalid(self.message('noSeconds', state), value, state)
        if (len(parts) == 2
                and self.use_seconds and self.use_seconds != 'optional'):
            raise Invalid(self.message('secondsRequired', state), value, state)
        if len(parts) == 1:
            raise Invalid(self.message('minutesRequired', state), value, state)
        try:
            hour = int(parts[0])
        except ValueError:
            raise Invalid(
                self.message('badNumber', state,
                    number=parts[0], part='hour'), value, state)
        if explicit_ampm:
            if not 1 <= hour <= 12:
                raise Invalid(
                    self.message('badHour', state,
                        number=hour, range='1-12'), value, state)
            if hour == 12 and offset == 12:
                # 12pm == 12
                pass
            elif hour == 12 and offset == 0:
                # 12am == 0
                hour = 0
            else:
                hour += offset
        else:
            if not 0 <= hour < 24:
                raise Invalid(
                    self.message('badHour', state,
                        number=hour, range='0-23'), value, state)
        try:
            minute = int(parts[1])
        except ValueError:
            raise Invalid(
                self.message('badNumber', state,
                    number=parts[1], part='minute'), value, state)
        if not 0 <= minute < 60:
            raise Invalid(
                self.message('badMinute', state, number=minute),
                value, state)
        if len(parts) == 3:
            try:
                second = int(parts[2])
            except ValueError:
                raise Invalid(
                    self.message('badNumber', state,
                        number=parts[2], part='second'), value, state)
            if not 0 <= second < 60:
                raise Invalid(
                    self.message('badSecond', state, number=second),
                    value, state)
        else:
            second = None
        if second is None:
            return (hour, minute)
        else:
            return (hour, minute, second)

    def _convert_from_python(self, value, state):
        if isinstance(value, basestring):
            return value
        if hasattr(value, 'hour'):
            hour, minute = value.hour, value.minute
            second = value.second
        elif len(value) == 3:
            hour, minute, second = value
        elif len(value) == 2:
            hour, minute = value
            second = 0
        ampm = ''
        if (self.use_ampm == 'optional' and self.prefer_ampm) or (
                self.use_ampm and self.use_ampm != 'optional'):
            ampm = 'am'
            if hour > 12:
                hour -= 12
                ampm = 'pm'
            elif hour == 12:
                ampm = 'pm'
            elif hour == 0:
                hour = 12
        if self.use_seconds:
            return '%i:%02i:%02i%s' % (hour, minute, second, ampm)
        else:
            return '%i:%02i%s' % (hour, minute, ampm)


def PostalCode(*kw, **kwargs):
    deprecation_warning("please use formencode.national.USPostalCode")
    from formencode.national import USPostalCode
    return USPostalCode(*kw, **kwargs)


class StripField(FancyValidator):
    """
    Take a field from a dictionary, removing the key from the dictionary.

    ``name`` is the key.  The field value and a new copy of the dictionary
    with that field removed are returned.

    >>> StripField('test').to_python({'a': 1, 'test': 2})
    (2, {'a': 1})
    >>> StripField('test').to_python({})
    Traceback (most recent call last):
        ...
    Invalid: The name 'test' is missing

    """

    __unpackargs__ = ('name',)

    messages = dict(
        missing=_('The name %(name)s is missing'))

    def _convert_to_python(self, valueDict, state):
        v = valueDict.copy()
        try:
            field = v.pop(self.name)
        except KeyError:
            raise Invalid(
                self.message('missing', state, name=repr(self.name)),
                valueDict, state)
        return field, v

    def is_empty(self, value):
        # empty dictionaries don't really apply here
        return False


class StringBool(FancyValidator):  # originally from TurboGears 1
    """
    Converts a string to a boolean.

    Values like 'true' and 'false' are considered True and False,
    respectively; anything in ``true_values`` is true, anything in
    ``false_values`` is false, case-insensitive).  The first item of
    those lists is considered the preferred form.

    ::

        >>> s = StringBool()
        >>> s.to_python('yes'), s.to_python('no')
        (True, False)
        >>> s.to_python(1), s.to_python('N')
        (True, False)
        >>> s.to_python('ye')
        Traceback (most recent call last):
            ...
        Invalid: Value should be 'true' or 'false'
    """

    true_values = ['true', 't', 'yes', 'y', 'on', '1']
    false_values = ['false', 'f', 'no', 'n', 'off', '0']

    messages = dict(
        string=_('Value should be %(true)r or %(false)r'))

    def _convert_to_python(self, value, state):
        if isinstance(value, basestring):
            value = value.strip().lower()
            if value in self.true_values:
                return True
            if not value or value in self.false_values:
                return False
            raise Invalid(
                self.message('string', state,
                    true=self.true_values[0], false=self.false_values[0]),
                value, state)
        return bool(value)

    def _convert_from_python(self, value, state):
        return (self.true_values if value else self.false_values)[0]

# Should deprecate:
StringBoolean = StringBool


class SignedString(FancyValidator):
    """
    Encodes a string into a signed string, and base64 encodes both the
    signature string and a random nonce.

    It is up to you to provide a secret, and to keep the secret handy
    and consistent.
    """

    messages = dict(
        malformed=_('Value does not contain a signature'),
        badsig=_('Signature is not correct'))

    secret = None
    nonce_length = 4

    def _convert_to_python(self, value, state):
        global sha1
        if not sha1:
            from hashlib import sha1
        assert self.secret is not None, "You must give a secret"
        parts = value.split(None, 1)
        if not parts or len(parts) == 1:
            raise Invalid(self.message('malformed', state), value, state)
        sig, rest = parts
        sig = sig.decode('base64')
        rest = rest.decode('base64')
        nonce = rest[:self.nonce_length]
        rest = rest[self.nonce_length:]
        expected = sha1(str(self.secret) + nonce + rest).digest()
        if expected != sig:
            raise Invalid(self.message('badsig', state), value, state)
        return rest

    def _convert_from_python(self, value, state):
        global sha1
        if not sha1:
            from hashlib import sha1
        nonce = self.make_nonce()
        value = str(value)
        digest = sha1(self.secret + nonce + value).digest()
        return self.encode(digest) + ' ' + self.encode(nonce + value)

    def encode(self, value):
        return value.encode('base64').strip().replace('\n', '')

    def make_nonce(self):
        global random
        if not random:
            import random
        return ''.join(chr(random.randrange(256))
            for _i in xrange(self.nonce_length))


class IPAddress(FancyValidator):
    """
    Formencode validator to check whether a string is a correct IP address.

    Examples::

        >>> ip = IPAddress()
        >>> ip.to_python('127.0.0.1')
        '127.0.0.1'
        >>> ip.to_python('299.0.0.1')
        Traceback (most recent call last):
            ...
        Invalid: The octets must be within the range of 0-255 (not '299')
        >>> ip.to_python('192.168.0.1/1')
        Traceback (most recent call last):
            ...
        Invalid: Please enter a valid IP address (a.b.c.d)
        >>> ip.to_python('asdf')
        Traceback (most recent call last):
            ...
        Invalid: Please enter a valid IP address (a.b.c.d)
    """

    messages = dict(
        badFormat=_('Please enter a valid IP address (a.b.c.d)'),
        leadingZeros=_('The octets must not have leading zeros'),
        illegalOctets=_('The octets must be within the range of 0-255'
            ' (not %(octet)r)'))

    leading_zeros = False

    def _validate_python(self, value, state=None):
        try:
            if not value:
                raise ValueError
            octets = value.split('.', 5)
            # Only 4 octets?
            if len(octets) != 4:
                raise ValueError
            # Correct octets?
            for octet in octets:
                if octet.startswith('0') and octet != '0':
                    if not self.leading_zeros:
                        raise Invalid(
                            self.message('leadingZeros', state), value, state)
                    # strip zeros so this won't be an octal number
                    octet = octet.lstrip('0')
                if not 0 <= int(octet) < 256:
                    raise Invalid(
                        self.message('illegalOctets', state, octet=octet),
                        value, state)
        # Splitting faild: wrong syntax
        except ValueError:
            raise Invalid(self.message('badFormat', state), value, state)


class CIDR(IPAddress):
    """
    Formencode validator to check whether a string is in correct CIDR
    notation (IP address, or IP address plus /mask).

    Examples::

        >>> cidr = CIDR()
        >>> cidr.to_python('127.0.0.1')
        '127.0.0.1'
        >>> cidr.to_python('299.0.0.1')
        Traceback (most recent call last):
            ...
        Invalid: The octets must be within the range of 0-255 (not '299')
        >>> cidr.to_python('192.168.0.1/1')
        Traceback (most recent call last):
            ...
        Invalid: The network size (bits) must be within the range of 8-32 (not '1')
        >>> cidr.to_python('asdf')
        Traceback (most recent call last):
            ...
        Invalid: Please enter a valid IP address (a.b.c.d) or IP network (a.b.c.d/e)
    """

    messages = dict(IPAddress._messages,
        badFormat=_('Please enter a valid IP address (a.b.c.d)'
            ' or IP network (a.b.c.d/e)'),
        illegalBits=_('The network size (bits) must be within the range'
            ' of 8-32 (not %(bits)r)'))

    def _validate_python(self, value, state):
        try:
            # Split into octets and bits
            if '/' in value:  # a.b.c.d/e
                addr, bits = value.split('/')
            else:  # a.b.c.d
                addr, bits = value, 32
            # Use IPAddress validator to validate the IP part
            IPAddress._validate_python(self, addr, state)
            # Bits (netmask) correct?
            if not 8 <= int(bits) <= 32:
                raise Invalid(
                    self.message('illegalBits', state, bits=bits),
                    value, state)
        # Splitting faild: wrong syntax
        except ValueError:
            raise Invalid(self.message('badFormat', state), value, state)


class MACAddress(FancyValidator):
    """
    Formencode validator to check whether a string is a correct hardware
    (MAC) address.

    Examples::

        >>> mac = MACAddress()
        >>> mac.to_python('aa:bb:cc:dd:ee:ff')
        'aabbccddeeff'
        >>> mac.to_python('aa:bb:cc:dd:ee:ff:e')
        Traceback (most recent call last):
            ...
        Invalid: A MAC address must contain 12 digits and A-F; the value you gave has 13 characters
        >>> mac.to_python('aa:bb:cc:dd:ee:fx')
        Traceback (most recent call last):
            ...
        Invalid: MAC addresses may only contain 0-9 and A-F (and optionally :), not 'x'
        >>> MACAddress(add_colons=True).to_python('aabbccddeeff')
        'aa:bb:cc:dd:ee:ff'
    """

    strip = True
    valid_characters = '0123456789abcdefABCDEF'
    add_colons = False

    messages = dict(
        badLength=_('A MAC address must contain 12 digits and A-F;'
            ' the value you gave has %(length)s characters'),
        badCharacter=_('MAC addresses may only contain 0-9 and A-F'
            ' (and optionally :), not %(char)r'))

    def _convert_to_python(self, value, state):
        address = value.replace(':', '').lower()  # remove colons
        if len(address) != 12:
            raise Invalid(
                self.message('badLength', state,
                    length=len(address)), address, state)
        for char in address:
            if char not in self.valid_characters:
                raise Invalid(
                    self.message('badCharacter', state,
                        char=char), address, state)
        if self.add_colons:
            address = '%s:%s:%s:%s:%s:%s' % (
                address[0:2], address[2:4], address[4:6],
                address[6:8], address[8:10], address[10:12])
        return address

    _convert_from_python = _convert_to_python


class FormValidator(FancyValidator):
    """
    A FormValidator is something that can be chained with a Schema.

    Unlike normal chaining the FormValidator can validate forms that
    aren't entirely valid.

    The important method is .validate(), of course.  It gets passed a
    dictionary of the (processed) values from the form.  If you have
    .validate_partial_form set to True, then it will get the incomplete
    values as well -- check with the "in" operator if the form was able
    to process any particular field.

    Anyway, .validate() should return a string or a dictionary.  If a
    string, it's an error message that applies to the whole form.  If
    not, then it should be a dictionary of fieldName: errorMessage.
    The special key "form" is the error message for the form as a whole
    (i.e., a string is equivalent to {"form": string}).

    Returns None on no errors.
    """

    validate_partial_form = False

    validate_partial_python = None
    validate_partial_other = None

    def is_empty(self, value):
        return False

    def field_is_empty(self, value):
        return is_empty(value)


class RequireIfMissing(FormValidator):
    """
    Require one field based on another field being present or missing.

    This validator is applied to a form, not an individual field (usually
    using a Schema's ``pre_validators`` or ``chained_validators``) and is
    available under both names ``RequireIfMissing`` and ``RequireIfPresent``.

    If you provide a ``missing`` value (a string key name) then
    if that field is missing the field must be entered.
    This gives you an either/or situation.

    If you provide a ``present`` value (another string key name) then
    if that field is present, the required field must also be present.

    ::

        >>> from formencode import validators
        >>> v = validators.RequireIfPresent('phone_type', present='phone')
        >>> v.to_python(dict(phone_type='', phone='510 420  4577'))
        Traceback (most recent call last):
            ...
        Invalid: You must give a value for phone_type
        >>> v.to_python(dict(phone=''))
        {'phone': ''}

    Note that if you have a validator on the optionally-required
    field, you should probably use ``if_missing=None``.  This way you
    won't get an error from the Schema about a missing value.  For example::

        class PhoneInput(Schema):
            phone = PhoneNumber()
            phone_type = String(if_missing=None)
            chained_validators = [RequireIfPresent('phone_type', present='phone')]
    """

    # Field that potentially is required:
    required = None
    # If this field is missing, then it is required:
    missing = None
    # If this field is present, then it is required:
    present = None

    __unpackargs__ = ('required',)

    def _convert_to_python(self, value_dict, state):
        is_empty = self.field_is_empty
        if is_empty(value_dict.get(self.required)) and (
                (self.missing and is_empty(value_dict.get(self.missing))) or
                (self.present and not is_empty(value_dict.get(self.present)))):
            raise Invalid(
                _('You must give a value for %s') % self.required,
                value_dict, state,
                error_dict={self.required:
                    Invalid(self.message('empty', state),
                        value_dict.get(self.required), state)})
        return value_dict

RequireIfPresent = RequireIfMissing

class RequireIfMatching(FormValidator):
    """
    Require a list of fields based on the value of another field.

    This validator is applied to a form, not an individual field (usually
    using a Schema's ``pre_validators`` or ``chained_validators``).

    You provide a field name, an expected value and a list of required fields
    (a list of string key names). If the value of the field, if present,
    matches the value of ``expected_value``, then the validator will raise an
    ``Invalid`` exception for every field in ``required_fields`` that is
    missing.

    ::

        >>> from formencode import validators
        >>> v = validators.RequireIfMatching('phone_type', expected_value='mobile', required_fields=['mobile'])
        >>> v.to_python(dict(phone_type='mobile'))
        Traceback (most recent call last):
            ...
        formencode.api.Invalid: You must give a value for mobile
        >>> v.to_python(dict(phone_type='someothervalue'))
        {'phone_type': 'someothervalue'}
    """

    # Field that we will check for its value:
    field = None
    # Value that the field shall have
    expected_value = None
    # If this field is present, then these fields are required:
    required_fields = []

    __unpackargs__ = ('field', 'expected_value')

    def _convert_to_python(self, value_dict, state):
        is_empty = self.field_is_empty

        if self.field in value_dict and value_dict.get(self.field) == self.expected_value:
            for required_field in self.required_fields:
                if required_field not in value_dict or is_empty(value_dict.get(required_field)):
                    raise Invalid(
                        _('You must give a value for %s') % required_field,
                        value_dict, state,
                        error_dict={required_field:
                            Invalid(self.message('empty', state),
                                value_dict.get(required_field), state)})
        return value_dict

class FieldsMatch(FormValidator):
    """
    Tests that the given fields match, i.e., are identical.  Useful
    for password+confirmation fields.  Pass the list of field names in
    as `field_names`.

    ::

        >>> f = FieldsMatch('pass', 'conf')
        >>> sorted(f.to_python({'pass': 'xx', 'conf': 'xx'}).items())
        [('conf', 'xx'), ('pass', 'xx')]
        >>> f.to_python({'pass': 'xx', 'conf': 'yy'})
        Traceback (most recent call last):
            ...
        Invalid: conf: Fields do not match
    """

    show_match = False
    field_names = None
    validate_partial_form = True

    __unpackargs__ = ('*', 'field_names')

    messages = dict(
        invalid=_('Fields do not match (should be %(match)s)'),
        invalidNoMatch=_('Fields do not match'),
        notDict=_('Fields should be a dictionary'))

    def __init__(self, *args, **kw):
        super(FieldsMatch, self).__init__(*args, **kw)
        if len(self.field_names) < 2:
            raise TypeError('FieldsMatch() requires at least two field names')

    def validate_partial(self, field_dict, state):
        for name in self.field_names:
            if name not in field_dict:
                return
        self._validate_python(field_dict, state)

    def _validate_python(self, field_dict, state):
        try:
            ref = field_dict[self.field_names[0]]
        except TypeError:
            # Generally because field_dict isn't a dict
            raise Invalid(self.message('notDict', state), field_dict, state)
        except KeyError:
            ref = ''
        errors = {}
        for name in self.field_names[1:]:
            if field_dict.get(name, '') != ref:
                if self.show_match:
                    errors[name] = self.message('invalid', state,
                                                match=ref)
                else:
                    errors[name] = self.message('invalidNoMatch', state)
        if errors:
            error_list = sorted(errors.iteritems())
            error_message = '<br>\n'.join(
                '%s: %s' % (name, value) for name, value in error_list)
            raise Invalid(error_message, field_dict, state, error_dict=errors)


class CreditCardValidator(FormValidator):
    """
    Checks that credit card numbers are valid (if not real).

    You pass in the name of the field that has the credit card
    type and the field with the credit card number.  The credit
    card type should be one of "visa", "mastercard", "amex",
    "dinersclub", "discover", "jcb".

    You must check the expiration date yourself (there is no
    relation between CC number/types and expiration dates).

    ::

        >>> cc = CreditCardValidator()
        >>> sorted(cc.to_python({'ccType': 'visa', 'ccNumber': '4111111111111111'}).items())
        [('ccNumber', '4111111111111111'), ('ccType', 'visa')]
        >>> cc.to_python({'ccType': 'visa', 'ccNumber': '411111111111111'})
        Traceback (most recent call last):
            ...
        Invalid: ccNumber: You did not enter a valid number of digits
        >>> cc.to_python({'ccType': 'visa', 'ccNumber': '411111111111112'})
        Traceback (most recent call last):
            ...
        Invalid: ccNumber: You did not enter a valid number of digits
        >>> cc().to_python({})
        Traceback (most recent call last):
            ...
        Invalid: The field ccType is missing
    """

    validate_partial_form = True

    cc_type_field = 'ccType'
    cc_number_field = 'ccNumber'

    __unpackargs__ = ('cc_type_field', 'cc_number_field')

    messages = dict(
        notANumber=_('Please enter only the number, no other characters'),
        badLength=_('You did not enter a valid number of digits'),
        invalidNumber=_('That number is not valid'),
        missing_key=_('The field %(key)s is missing'))

    def validate_partial(self, field_dict, state):
        if not field_dict.get(self.cc_type_field, None) \
           or not field_dict.get(self.cc_number_field, None):
            return None
        self._validate_python(field_dict, state)

    def _validate_python(self, field_dict, state):
        errors = self._validateReturn(field_dict, state)
        if errors:
            error_list = sorted(errors.iteritems())
            raise Invalid(
                '<br>\n'.join('%s: %s' % (name, value)
                    for name, value in error_list),
                field_dict, state, error_dict=errors)

    def _validateReturn(self, field_dict, state):
        for field in self.cc_type_field, self.cc_number_field:
            if field not in field_dict:
                raise Invalid(
                    self.message('missing_key', state, key=field),
                    field_dict, state)
        ccType = field_dict[self.cc_type_field].lower().strip()
        number = field_dict[self.cc_number_field].strip()
        number = number.replace(' ', '')
        number = number.replace('-', '')
        try:
            long(number)
        except ValueError:
            return {self.cc_number_field: self.message('notANumber', state)}
        assert ccType in self._cardInfo, (
            "I can't validate that type of credit card")
        foundValid = False
        validLength = False
        for prefix, length in self._cardInfo[ccType]:
            if len(number) == length:
                validLength = True
                if number.startswith(prefix):
                    foundValid = True
                    break
        if not validLength:
            return {self.cc_number_field: self.message('badLength', state)}
        if not foundValid:
            return {self.cc_number_field: self.message('invalidNumber', state)}
        if not self._validateMod10(number):
            return {self.cc_number_field: self.message('invalidNumber', state)}
        return None

    def _validateMod10(self, s):
        """Check string with the mod 10 algorithm (aka "Luhn formula")."""
        checksum, factor = 0, 1
        for c in reversed(s):
            for c in str(factor * int(c)):
                checksum += int(c)
            factor = 3 - factor
        return checksum % 10 == 0

    _cardInfo = {
        "visa": [('4', 16),
                 ('4', 13)],
        "mastercard": [('51', 16),
                       ('52', 16),
                       ('53', 16),
                       ('54', 16),
                       ('55', 16)],
        "discover": [('6011', 16)],
        "amex": [('34', 15),
                 ('37', 15)],
        "dinersclub": [('300', 14),
                       ('301', 14),
                       ('302', 14),
                       ('303', 14),
                       ('304', 14),
                       ('305', 14),
                       ('36', 14),
                       ('38', 14)],
        "jcb": [('3', 16),
                ('2131', 15),
                ('1800', 15)],
            }


class CreditCardExpires(FormValidator):
    """
    Checks that credit card expiration date is valid relative to
    the current date.

    You pass in the name of the field that has the credit card
    expiration month and the field with the credit card expiration
    year.

    ::

        >>> ed = CreditCardExpires()
        >>> sorted(ed.to_python({'ccExpiresMonth': '11', 'ccExpiresYear': '2250'}).items())
        [('ccExpiresMonth', '11'), ('ccExpiresYear', '2250')]
        >>> ed.to_python({'ccExpiresMonth': '10', 'ccExpiresYear': '2005'})
        Traceback (most recent call last):
            ...
        Invalid: ccExpiresMonth: Invalid Expiration Date<br>
        ccExpiresYear: Invalid Expiration Date
    """

    validate_partial_form = True

    cc_expires_month_field = 'ccExpiresMonth'
    cc_expires_year_field = 'ccExpiresYear'

    __unpackargs__ = ('cc_expires_month_field', 'cc_expires_year_field')

    datetime_module = None

    messages = dict(
        notANumber=_('Please enter numbers only for month and year'),
        invalidNumber=_('Invalid Expiration Date'))

    def validate_partial(self, field_dict, state):
        if not field_dict.get(self.cc_expires_month_field, None) \
           or not field_dict.get(self.cc_expires_year_field, None):
            return None
        self._validate_python(field_dict, state)

    def _validate_python(self, field_dict, state):
        errors = self._validateReturn(field_dict, state)
        if errors:
            error_list = sorted(errors.iteritems())
            raise Invalid(
                '<br>\n'.join('%s: %s' % (name, value)
                    for name, value in error_list),
                field_dict, state, error_dict=errors)

    def _validateReturn(self, field_dict, state):
        ccExpiresMonth = str(field_dict[self.cc_expires_month_field]).strip()
        ccExpiresYear = str(field_dict[self.cc_expires_year_field]).strip()

        try:
            ccExpiresMonth = int(ccExpiresMonth)
            ccExpiresYear = int(ccExpiresYear)
            dt_mod = import_datetime(self.datetime_module)
            now = datetime_now(dt_mod)
            today = datetime_makedate(dt_mod, now.year, now.month, now.day)
            next_month = ccExpiresMonth % 12 + 1
            next_month_year = ccExpiresYear
            if next_month == 1:
                next_month_year += 1
            expires_date = datetime_makedate(
                dt_mod, next_month_year, next_month, 1)
            assert expires_date > today
        except ValueError:
            return {self.cc_expires_month_field:
                        self.message('notANumber', state),
                    self.cc_expires_year_field:
                        self.message('notANumber', state)}
        except AssertionError:
            return {self.cc_expires_month_field:
                        self.message('invalidNumber', state),
                    self.cc_expires_year_field:
                        self.message('invalidNumber', state)}


class CreditCardSecurityCode(FormValidator):
    """
    Checks that credit card security code has the correct number
    of digits for the given credit card type.

    You pass in the name of the field that has the credit card
    type and the field with the credit card security code.

    ::

        >>> code = CreditCardSecurityCode()
        >>> sorted(code.to_python({'ccType': 'visa', 'ccCode': '111'}).items())
        [('ccCode', '111'), ('ccType', 'visa')]
        >>> code.to_python({'ccType': 'visa', 'ccCode': '1111'})
        Traceback (most recent call last):
            ...
        Invalid: ccCode: Invalid credit card security code length
    """

    validate_partial_form = True

    cc_type_field = 'ccType'
    cc_code_field = 'ccCode'

    __unpackargs__ = ('cc_type_field', 'cc_code_field')

    messages = dict(
        notANumber=_('Please enter numbers only for credit card security code'),
        badLength=_('Invalid credit card security code length'))

    def validate_partial(self, field_dict, state):
        if (not field_dict.get(self.cc_type_field, None)
                or not field_dict.get(self.cc_code_field, None)):
            return None
        self._validate_python(field_dict, state)

    def _validate_python(self, field_dict, state):
        errors = self._validateReturn(field_dict, state)
        if errors:
            error_list = sorted(errors.iteritems())
            raise Invalid(
                '<br>\n'.join('%s: %s' % (name, value)
                    for name, value in error_list),
                field_dict, state, error_dict=errors)

    def _validateReturn(self, field_dict, state):
        ccType = str(field_dict[self.cc_type_field]).strip()
        ccCode = str(field_dict[self.cc_code_field]).strip()
        try:
            int(ccCode)
        except ValueError:
            return {self.cc_code_field: self.message('notANumber', state)}
        length = self._cardInfo[ccType]
        if len(ccCode) != length:
            return {self.cc_code_field: self.message('badLength', state)}

    # key = credit card type, value = length of security code
    _cardInfo = dict(visa=3, mastercard=3, discover=3, amex=4)


def validators():
    """Return the names of all validators in this module."""
    return [name for name, value in globals().iteritems()
        if isinstance(value, type) and issubclass(value, Validator)]

__all__ = ['Invalid'] + validators()
