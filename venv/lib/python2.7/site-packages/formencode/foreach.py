"""
Validator for repeating items.
"""

from .api import NoDefault, Invalid
from .compound import CompoundValidator, from_python

__all__ = ['ForEach']


class ForEach(CompoundValidator):
    """
    Use this to apply a validator/converter to each item in a list.

    For instance::

        ForEach(AsInt(), InList([1, 2, 3]))

    Will take a list of values and try to convert each of them to
    an integer, and then check if each integer is 1, 2, or 3.  Using
    multiple arguments is equivalent to::

        ForEach(All(AsInt(), InList([1, 2, 3])))

    Use convert_to_list=True if you want to force the input to be a
    list.  This will turn non-lists into one-element lists, and None
    into the empty list.  This tries to detect sequences by iterating
    over them (except strings, which aren't considered sequences).

    ForEach will try to convert the entire list, even if errors are
    encountered.  If errors are encountered, they will be collected
    and a single Invalid exception will be raised at the end (with
    error_list set).

    If the incoming value is a set, then we return a set.
    """

    convert_to_list = True
    if_empty = NoDefault
    accept_iterator = True
    repeating = True
    _if_missing = ()

    def _attempt_convert(self, value, state, validate):
        if self.convert_to_list:
            value = self._convert_to_list(value)
        if self.if_empty is not NoDefault and not value:
            return self.if_empty
        if self.not_empty and not value:
            if validate is from_python and self.accept_python:
                return []
            raise Invalid(
                self.message('empty', state),
                value, state)
        new_list = []
        errors = []
        all_good = True
        is_set = isinstance(value, set)
        if state is not None:
            previous_index = getattr(state, 'index', NoDefault)
            previous_full_list = getattr(state, 'full_list', NoDefault)
            index = 0
            state.full_list = value
        try:
            for sub_value in value:
                if state:
                    state.index = index
                    index += 1
                good_pass = True
                for validator in self.validators:
                    try:
                        sub_value = validate(validator, sub_value, state)
                    except Invalid as e:
                        errors.append(e)
                        all_good = False
                        good_pass = False
                        break
                if good_pass:
                    errors.append(None)
                new_list.append(sub_value)
            if all_good:
                if is_set:
                    new_list = set(new_list)
                return new_list
            else:
                raise Invalid('Errors:\n%s' % '\n'.join(unicode(e)
                    for e in errors if e), value, state, error_list=errors)
        finally:
            if state is not None:
                if previous_index is NoDefault:
                    try:
                        del state.index
                    except AttributeError:
                        pass
                else:
                    state.index = previous_index
                if previous_full_list is NoDefault:
                    try:
                        del state.full_list
                    except AttributeError:
                        pass
                else:
                    state.full_list = previous_full_list

    def empty_value(self, value):
        return []

    class _IfMissing(object):

        def __get__(self, obj, cls=None):
            if obj is None:
                return []
            elif obj._if_missing is ForEach._if_missing:
                return []
            else:
                return obj._if_missing

        def __set__(self, obj, value):
            obj._if_missing = value

        def __delete__(self, obj):
            obj._if_missing = NoDefault

    if_missing = _IfMissing()
    del _IfMissing

    def _convert_to_list(self, value):
        if isinstance(value, basestring):
            return [value]
        elif value is None:
            return []
        elif isinstance(value, (list, tuple)):
            return value
        try:
            for _n in value:
                break
            return value
        ## @@: Should this catch any other errors?:
        except TypeError:
            return [value]
