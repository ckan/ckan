import unittest

from urlparse import parse_qsl

from formencode import Invalid, Validator, compound, foreach, validators
from formencode.schema import Schema, merge_dicts, SimpleFormValidator
from formencode.variabledecode import NestedVariables


def _notranslation(s):
    return s


def setup_module(module):
    """Disable i18n translation"""

    import __builtin__
    __builtin__._ = _notranslation


def teardown_module(module):
    """Remove translation function"""
    import __builtin__
    del __builtin__._


def d(**kw):
    return kw


def cgi_parse(qs):
    """Parse a query string and returns the usually dictionary."""
    d = {}
    for key, value in parse_qsl(qs, True):
        if key in d:
            if isinstance(d[key], list):
                d[key].append(value)
            else:
                d[key] = [d[key], value]
        else:
            d[key] = value
    return d


class DecodeCase(object):

    error_expected = False

    def __init__(self, schema, input, **output):
        self.raw_input = input
        self.schema = schema
        if isinstance(input, str):
            input = cgi_parse(input)
        self.input = input
        self.output = output
        all_cases.append(self)

    def test(self):
        print 'input', repr(self.input)
        actual = self.schema.to_python(self.input)
        print 'output', repr(actual)
        assert actual == self.output


class BadCase(DecodeCase):

    error_expected = True

    def __init__(self, *args, **kw):
        DecodeCase.__init__(self, *args, **kw)
        if len(self.output) == 1 and 'text' in self.output:
            self.output = self.output['text']

    def test(self):
        print repr(self.raw_input)
        try:
            print repr(self.schema.to_python(self.input))
        except Invalid as e:
            actual = e.unpack_errors()
            assert actual == self.output
        else:
            assert False, "Exception expected"


class Name(Schema):
    fname = validators.String(not_empty=True)
    mi = validators.String(max=1, if_missing=None, if_empty=None)
    lname = validators.String(not_empty=True)


all_cases = []

DecodeCase(Name, 'fname=Ian&mi=S&lname=Bicking',
           fname='Ian', mi='S', lname='Bicking')

DecodeCase(Name, 'fname=Ian&lname=Bicking',
           fname='Ian', mi=None, lname='Bicking')

BadCase(Name, 'fname=&lname=',
        fname='Please enter a value',
        lname='Please enter a value')

BadCase(Name, 'fname=Franklin&mi=Delano&lname=Roosevelt',
        mi="Enter a value not more than 1 characters long")

BadCase(Name, '',
        fname='Missing value',
        lname='Missing value')


class AddressesForm(Schema):

    pre_validators = [NestedVariables()]

    class addresses(foreach.ForEach):

        class schema(Schema):
            name = Name()
            email = validators.Email()


DecodeCase(AddressesForm,
           'addresses-2.name.fname=Jill&addresses-1.name.fname=Bob&'
           'addresses-1.name.lname=Briscoe&'
           'addresses-1.email=bob@bobcom.com&'
           'addresses-2.name.lname=Hill&addresses-2.email=jill@hill.com&'
           'addresses-2.name.mi=J',
           addresses=[d(name=d(fname='Bob', mi=None, lname='Briscoe'),
                        email='bob@bobcom.com'),
                      d(name=d(fname='Jill', mi='J', lname='Hill'),
                        email='jill@hill.com')])

DecodeCase(AddressesForm,
           '',
           addresses=[])

BadCase(AddressesForm,
        'addresses-1.name.fname=&addresses-1.name.lname=x&'
        'addresses-1.email=x@domain.com',
        addresses=[d(name=d(fname="Please enter a value"))])

BadCase(AddressesForm,
        'whatever=nothing',
        text="The input field 'whatever' was not expected.")


def test_this():

    for case in all_cases:
        yield (case.test,)


def test_merge():
    assert (merge_dicts(dict(a='a'), dict(b='b'))
            == dict(a='a', b='b'))
    assert (merge_dicts(dict(a='a', c='c'), dict(a='a', b='b'))
            == dict(a='a\na', b='b', c='c'))
    assert (merge_dicts(dict(a=['a1', 'a2'], b=['b'], c=['c']),
                        dict(a=['aa1'],
                             b=['bb', 'bbb'],
                             c='foo'))
            == dict(a=['a1\naa1', 'a2'], b=['b\nbb', 'bbb'],
                    c=['c']))


class ChainedTest(Schema):
    a = validators.String()
    a_confirm = validators.String()

    b = validators.String()
    b_confirm = validators.String()

    chained_validators = [validators.FieldsMatch('a', 'a_confirm'),
                            validators.FieldsMatch('b', 'b_confirm')]


def test_multiple_chained_validators_errors():
    s = ChainedTest()
    try:
        s.to_python({'a': '1', 'a_confirm': '2', 'b': '3', 'b_confirm': '4'})
    except Invalid as e:
        assert 'a_confirm' in e.error_dict and 'b_confirm' in e.error_dict
    try:
        s.to_python({})
    except Invalid:
        pass
    else:
        assert False


def test_SimpleFormValidator_doc():
    """
    Verify SimpleFormValidator preserves the decorated function's docstring.
    """

    BOGUS_DOCSTRING = "blah blah blah"

    def f(value_dict, state, validator):
        value_dict['f'] = 99

    f.__doc__ = BOGUS_DOCSTRING
    g = SimpleFormValidator(f)

    assert f.__doc__ == g.__doc__, "Docstrings don't match!"


class State(object):
    pass


def test_state_manipulation():
    """
    Verify that full_dict push and pop works
    """
    state = State()
    old_dict = state.full_dict = {'a': 1}
    old_key = state.key = 'a'
    new_dict = {'b': 2}

    class MyValidator(Validator):
        check_key = None
        pre_validator = False
        post_validator = False
        __unpackargs__ = ('check_key',)

        def to_python(self, value, state):
            if not self.pre_validator:
                assert getattr(
                    state, 'full_dict', {}) == new_dict, "full_dict not added"
            assert state.key == self.check_key, "key not updated"

            return value

        def from_python(self, value, state):
            if not self.post_validator:
                assert getattr(
                    state, 'full_dict', {}) == new_dict, "full_dict not added"
            assert state.key == self.check_key, "key not updated"

            return value

    s = Schema(if_key_missing=None, b=MyValidator('b'), c=MyValidator('c'),
               pre_validators=[MyValidator('a', pre_validator=True)],
               chained_validators=[MyValidator('a', post_validator=True)])

    s.to_python(new_dict, state)

    assert state.full_dict == old_dict, "full_dict not restored"
    assert state.key == old_key, "key not restored"

    s.from_python(new_dict, state)

    assert state.full_dict == old_dict, "full_dict not restored"
    assert state.key == old_key, "key not restored"


class TestAtLeastOneCheckboxIsChecked(object):
    """Tests to address SourceForge bug #1777245

    The reporter is trying to enforce agreement to a Terms of Service
    agreement, with failure to check the 'I agree' checkbox handled as
    a validation failure. The tests below illustrate a working approach.

    """

    def setup(self):
        self.not_empty_messages = {'missing': 'a missing value message'}

        class CheckForCheckboxSchema(Schema):
            agree = validators.StringBool(messages=self.not_empty_messages)

        self.schema = CheckForCheckboxSchema()

    def test_Schema_with_input_present(self):
        # <input type="checkbox" name="agree" value="yes" checked="checked">
        result = self.schema.to_python({'agree': 'yes'})
        assert result['agree'] is True

    def test_Schema_with_input_missing(self):
        # <input type="checkbox" name="agree" value="yes">
        try:
            self.schema.to_python({})
        except Invalid as exc:
            error_message = exc.error_dict['agree'].msg
            assert self.not_empty_messages['missing'] == error_message, \
                error_message
        else:
            assert False, 'missing input not detected'


class TestStrictSchemaWithMultipleEqualInputFields(unittest.TestCase):
    """Tests to address github bug #13"""

    def setUp(self):

        class StrictSchema(Schema):
            allow_extra_fields = False

        class IntegerTestSchema(StrictSchema):
            field = validators.Int(not_empty=True)

        class StringTestSchema(StrictSchema):
            field = validators.UnicodeString(not_empty=True)

        class CorrectForEachStringTestSchema(StrictSchema):
            field = foreach.ForEach(validators.UnicodeString(not_empty=True))

        class CorrectSetTestSchema(StrictSchema):
            field = validators.Set(not_empty=True)

        class CorrectSetTestPipeSchema(StrictSchema):
            field = compound.Pipe(validators.Set(not_empty=True),
                foreach.ForEach(validators.UnicodeString(not_empty=True)))

        self.int_schema = IntegerTestSchema()
        self.string_schema = StringTestSchema()
        self.foreach_schema = CorrectForEachStringTestSchema()
        self.set_schema = CorrectSetTestSchema()
        self.pipe_schema = CorrectSetTestPipeSchema()

    def test_single_integer_value(self):
        params = cgi_parse('field=111')
        data = self.int_schema.to_python(params)
        self.assertEqual(data, dict(field=111))

    def test_multiple_integer_value(self):
        params = cgi_parse('field=111&field=222')
        self.assertRaises(Invalid, self.int_schema.to_python, params)

    def test_single_string_value(self):
        params = cgi_parse('field=string')
        data = self.string_schema.to_python(params)
        self.assertEqual(data, dict(field='string'))

    def test_multiple_string_value(self):
        params = cgi_parse('field=string1&field=string2')
        self.assertRaises(Invalid, self.string_schema.to_python, params)

    def test_correct_multiple_string_value_foreach(self):
        params = cgi_parse('field=string1&field=string2')
        data = self.foreach_schema.to_python(params)
        self.assertEqual(data, dict(field=['string1', 'string2']))

    def test_correct_multiple_string_value_set(self):
        params = cgi_parse('field=string1&field=string2')
        data = self.set_schema.to_python(params)
        self.assertEqual(data, dict(field=['string1', 'string2']))

    def test_correct_multiple_string_value_pipe(self):
        params = cgi_parse('field=string1&field=string2')
        data = self.pipe_schema.to_python(params)
        self.assertEqual(data, dict(field=['string1', 'string2']))


def test_copy():
    assert 'mi' in Name.fields
    NoTitleName = Name()
    assert 'mi' in NoTitleName.fields
    TitleName = NoTitleName(title=validators.String())
    assert 'mi' in TitleName.fields
    assert 'title' in TitleName.fields
    assert 'title' not in NoTitleName.fields
