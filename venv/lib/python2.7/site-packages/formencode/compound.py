"""
Validators for applying validations in sequence.
"""

from .api import (FancyValidator, Identity, Invalid, NoDefault, Validator,
    is_validator)

__all__ = ['CompoundValidator', 'Any', 'All', 'Pipe']

############################################################
## Compound Validators
############################################################


def to_python(validator, value, state):
    return validator.to_python(value, state)


def from_python(validator, value, state):
    return validator.from_python(value, state)


class CompoundValidator(FancyValidator):
    """Base class for all compound validators."""

    if_invalid = NoDefault
    accept_iterator = False

    validators = []

    __unpackargs__ = ('*', 'validatorArgs')

    __mutableattributes__ = ('validators',)

    _deprecated_methods = (
        ('attempt_convert', '_attempt_convert'),)

    @staticmethod
    def __classinit__(cls, new_attrs):
        FancyValidator.__classinit__(cls, new_attrs)
        toAdd = []
        for name, value in new_attrs.iteritems():
            if is_validator(value) and value is not Identity:
                toAdd.append((name, value))
                # @@: Should we really delete too?
                delattr(cls, name)
        toAdd.sort()
        cls.validators.extend([value for _name, value in toAdd])

    def __init__(self, *args, **kw):
        Validator.__init__(self, *args, **kw)
        self.validators = self.validators[:]
        self.validators.extend(self.validatorArgs)

    @staticmethod
    def _repr_vars(names):
        return [n for n in Validator._repr_vars(names)
                if n != 'validatorArgs']

    def _attempt_convert(self, value, state, convertFunc):
        raise NotImplementedError("Subclasses must implement _attempt_convert")

    def _convert_to_python(self, value, state=None):
        return self._attempt_convert(value, state,
                                    to_python)

    def _convert_from_python(self, value, state=None):
        return self._attempt_convert(value, state,
                                    from_python)

    def subvalidators(self):
        return self.validators


class Any(CompoundValidator):
    """Check if any of the specified validators is valid.

    This class is like an 'or' operator for validators.  The first
    validator/converter in the order of evaluation that validates the value
    will be used.

    The order of evaluation differs depending on if you are validating to
    Python or from Python as follows:

    The validators are evaluated right to left when validating to Python.

    The validators are evaluated left to right when validating from Python.

    Examples::

        >>> from formencode.validators import DictConverter
        >>> av = Any(validators=[DictConverter({2: 1}),
        ... DictConverter({3: 2}), DictConverter({4: 3})])
        >>> av.to_python(3)
        2
        >>> av.from_python(2)
        3

    """

    def _attempt_convert(self, value, state, validate):
        lastException = None
        validators = self.validators
        if validate is to_python:
            validators = reversed(validators)
        for validator in validators:
            try:
                return validate(validator, value, state)
            except Invalid as e:
                lastException = e
        if self.if_invalid is NoDefault:
            raise lastException
        return self.if_invalid

    @property
    def not_empty(self):
        not_empty = True
        for validator in self.validators:
            not_empty = not_empty and getattr(validator, 'not_empty', False)
        return not_empty

    def is_empty(self, value):
        # sub-validators should handle emptiness.
        return False

    @property
    def accept_iterator(self):
        accept_iterator = False
        for validator in self.validators:
            accept_iterator = accept_iterator or getattr(
                validator, 'accept_iterator', False)
        return accept_iterator


class All(CompoundValidator):
    """Check if all of the specified validators are valid.

    This class is like an 'and' operator for validators.  All
    validators must work, and the results are passed in turn through
    all validators for conversion in the order of evaluation. All
    is the same as `Pipe` but operates in the reverse order.

    The order of evaluation differs depending on if you are validating to
    Python or from Python as follows:

    The validators are evaluated right to left when validating to Python.

    The validators are evaluated left to right when validating from Python.

    `Pipe` is more intuitive when predominantly validating to Python.

    Examples::

        >>> from formencode.validators import DictConverter
        >>> av = All(validators=[DictConverter({2: 1}),
        ... DictConverter({3: 2}), DictConverter({4: 3})])
        >>> av.to_python(4)
        1
        >>> av.from_python(1)
        4

    """

    def __repr__(self):
        return '<All %s>' % self.validators

    def _attempt_convert(self, value, state, validate):
        # To preserve the order of the transformations, we do them
        # differently when we are converting to and from Python.
        validators = self.validators
        if validate is to_python:
            validators = reversed(validators)
        try:
            for validator in validators:
                value = validate(validator, value, state)
        except Invalid:
            if self.if_invalid is NoDefault:
                raise
            return self.if_invalid
        return value

    def with_validator(self, validator):
        """Add another validator.

        Adds the validator (or list of validators) to a copy of
        this validator.
        """
        new = self.validators[:]
        if isinstance(validator, (list, tuple)):
            new.extend(validator)
        else:
            new.append(validator)
        return self.__class__(*new, **dict(if_invalid=self.if_invalid))

    @classmethod
    def join(cls, *validators):
        """Join the specified validators.

        Joins several validators together as a single validator,
        filtering out None and trying to keep `All` validators from
        being nested (which isn't needed).
        """
        validators = filter(lambda v: v and v is not Identity, validators)
        if not validators:
            return Identity
        if len(validators) == 1:
            return validators[0]
        if isinstance(validators[0], All):
            return validators[0].with_validator(validators[1:])
        return cls(*validators)

    @property
    def if_missing(self):
        for validator in self.validators:
            v = validator.if_missing
            if v is not NoDefault:
                return v
        return NoDefault

    @property
    def not_empty(self):
        not_empty = False
        for validator in self.validators:
            not_empty = not_empty or getattr(validator, 'not_empty', False)
        return not_empty

    def is_empty(self, value):
        # sub-validators should handle emptiness.
        return False

    @property
    def accept_iterator(self):
        accept_iterator = True
        for validator in self.validators:
            accept_iterator = accept_iterator and getattr(
                validator, 'accept_iterator', False)
        return accept_iterator


class Pipe(All):
    """Pipe value through all specified validators.

    This class works like `All` but the order of evaluation is opposite. All
    validators must work, and the results are passed in turn through
    each validator for conversion in the order of evaluation.  A behaviour
    known to Unix and GNU users as 'pipe'.

    The order of evaluation differs depending on if you are validating to
    Python or from Python as follows:

    The validators are evaluated left to right when validating to Python.

    The validators are evaluated right to left when validating from Python.

    Examples::

        >>> from formencode.validators import DictConverter
        >>> pv = Pipe(validators=[DictConverter({1: 2}),
        ... DictConverter({2: 3}), DictConverter({3: 4})])
        >>> pv.to_python(1)
        4
        >>> pv.from_python(4)
        1

    """

    def __repr__(self):
        return '<Pipe %s>' % self.validators

    def _attempt_convert(self, value, state, validate):
        # To preserve the order of the transformations, we do them
        # differently when we are converting to and from Python.
        validators = self.validators
        if validate is from_python:
            validators = reversed(self.validators)
        try:
            for validator in validators:
                value = validate(validator, value, state)
        except Invalid:
            if self.if_invalid is NoDefault:
                raise
            return self.if_invalid
        return value
