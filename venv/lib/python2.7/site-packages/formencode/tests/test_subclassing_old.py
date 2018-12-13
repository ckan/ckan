# -*- coding: utf-8 -*-

import unittest
import warnings

from formencode.api import is_validator, FancyValidator, Invalid
from formencode.compound import CompoundValidator, All
from formencode.validators import Int


with warnings.catch_warnings(record=True) as custom_warnings:
    warnings.simplefilter('default')

    class DeprecatedCustomValidator(FancyValidator):
        """A custom validator based directly on FancyValidator."""

        messages = {
            'custom': "%(number)s is invalid",
        }

        def _to_python(self, value, state):
            if value == '1':
                raise Invalid(self.message(
                    'custom', state, number='one'), value, state)
            return int(value)

        def _from_python(self, value, state):
            if value == 2:
                raise Invalid(self.message(
                    'custom', state, number='two'), value, state)
            return str(value)

        def validate_other(self, value, state):
            if value == '3':
                raise Invalid(self.message(
                    'custom', state, number='three'), value, state)

        def validate_python(self, value, state):
            if value == 4:
                raise Invalid(self.message(
                    'custom', state, number='four'), value, state)


class TestDeprecatedCustomValidator(unittest.TestCase):

    def test_1_warnings(self):
        deprecated = (
            ('_to_python', '_convert_to_python'),
            ('_from_python', '_convert_from_python'),
            ('validate_other', '_validate_other'),
            ('validate_python', '_validate_python'))
        output = '\n'.join(map(str, custom_warnings))
        for old, new in deprecated:
            msg = '%s is deprecated; use %s instead' % (old, new)
            self.assertTrue(msg in output, output or 'no warnings')

    def test_is_validator(self):
        self.assertTrue(is_validator(DeprecatedCustomValidator))
        self.assertTrue(is_validator(DeprecatedCustomValidator()))

    def test_to_python(self):
        cv = DeprecatedCustomValidator()
        self.assertEqual(cv.to_python('0'), 0)
        try:
            cv.to_python('1')
        except Invalid as e:
            self.assertTrue(
                'one is invalid' in str(e), e)
        else:
            self.fail("one should be invalid")
        self.assertEqual(cv.to_python('2'), 2)
        try:
            cv.to_python('3')
        except Invalid as e:
            self.assertTrue(
                'three is invalid' in str(e), e)
        else:
            self.fail("three should be invalid")
        try:
            cv.to_python('4')
        except Invalid as e:
            self.assertTrue(
                'four is invalid' in str(e), e)
        else:
            self.fail("four should be invalid")
        self.assertEqual(cv.to_python('5'), 5)

    def test_from_python(self):
        cv = DeprecatedCustomValidator()
        self.assertEqual(cv.from_python(0), '0')
        self.assertEqual(cv.from_python(1), '1')
        try:
            cv.from_python(2)
        except Invalid as e:
            self.assertTrue(
                'two is invalid' in str(e), e)
        else:
            self.fail("two should be invalid")
        self.assertEqual(cv.from_python(3), '3')
        self.assertEqual(cv.from_python(4), '4')
        self.assertEqual(cv.from_python(5), '5')

    def test_from_python_no_accept(self):
        cv = DeprecatedCustomValidator(accept_python=False)
        self.assertEqual(cv.from_python(0), '0')
        self.assertEqual(cv.from_python(1), '1')
        try:
            cv.from_python(2)
        except Invalid as e:
            self.assertTrue(
                'two is invalid' in str(e), e)
        else:
            self.fail("two should be invalid")
        try:
            cv.from_python(3)
        except Invalid as e:
            self.assertTrue(
                'three is invalid' in str(e), e)
        else:
            self.fail("three should be invalid")
        try:
            cv.from_python(4)
        except Invalid as e:
            self.assertTrue(
                'four is invalid' in str(e), e)
        else:
            self.fail("four should be invalid")
        self.assertEqual(cv.from_python(5), '5')


with warnings.catch_warnings(record=True) as not_one_warnings:
    warnings.simplefilter('default')

    class DeprecatedNotOneValidator(Int):
        """A custom validator based on an existing validator."""

        messages = {
            'custom': "must not be %(number)d",
        }

        number = 1

        def _to_python(self, value, state):
            value = super(DeprecatedNotOneValidator, self)._to_python(
                value, state)
            if value == self.number:
                raise Invalid(self.message(
                    'custom', state, number=self.number), value, state)
            return value


class TestDeprecatedNotOneValidator(unittest.TestCase):

    def test_1_warnings(self):  # must run first
        with warnings.catch_warnings(record=True) as runtime_warnings:
            warnings.simplefilter('default')
            DeprecatedNotOneValidator().to_python('2')
        for output in runtime_warnings, not_one_warnings:
            output = '\n'.join(map(str, output))
            msg = '_to_python is deprecated; use _convert_to_python instead'
            self.assertTrue(msg in output, output or 'no warnings')

    def test_is_validator(self):
        self.assertTrue(is_validator(DeprecatedNotOneValidator))
        self.assertTrue(is_validator(DeprecatedNotOneValidator()))
        self.assertTrue(is_validator(DeprecatedNotOneValidator(one=2)))

    def test_to_python(self):
        nov = DeprecatedNotOneValidator()
        self.assertEqual(nov.to_python('0'), 0)
        try:
            nov.to_python('1')
        except Invalid as e:
            self.assertTrue(
                'must not be 1' in str(e), e)
        else:
            self.fail("1 should be invalid")
        self.assertEqual(nov.to_python('2'), 2)
        self.assertEqual(nov.to_python('42'), 42)

    def test_to_python_number(self):
        nov = DeprecatedNotOneValidator(number=42)
        self.assertEqual(nov.to_python('0'), 0)
        self.assertEqual(nov.to_python('1'), 1)
        self.assertEqual(nov.to_python('2'), 2)
        try:
            nov.to_python('42')
        except Invalid as e:
            self.assertTrue(
                'must not be 42' in str(e), e)
        else:
            self.fail("42 should be invalid")

    def test_to_python_range(self):
        nov = DeprecatedNotOneValidator(min=40, max=49, number=42)
        self.assertRaises(Invalid, nov.to_python, '0')
        self.assertRaises(Invalid, nov.to_python, '1')
        self.assertRaises(Invalid, nov.to_python, '2')
        self.assertRaises(Invalid, nov.to_python, '39')
        self.assertEqual(nov.to_python('40'), 40)
        self.assertEqual(nov.to_python('41'), 41)
        try:
            nov.to_python('42')
        except Invalid as e:
            self.assertTrue(
                'must not be 42' in str(e), e)
        else:
            self.fail("42 should be invalid")
        self.assertEqual(nov.to_python('43'), 43)
        self.assertEqual(nov.to_python('49'), 49)
        self.assertRaises(Invalid, nov.to_python, '50')


with warnings.catch_warnings(record=True) as custom_compound_warnings:
    warnings.simplefilter('default')

    class DeprecatedCustomCompoundValidator(CompoundValidator):
        """A custom validator based directly on CompoundValidator."""

        def attempt_convert(self, value, state, validate):
            return validate(self.validators[1], value, state)


class TestDeprecatedCustomCompoundValidator(unittest.TestCase):

    def setUp(self):
        self.validator = DeprecatedCustomCompoundValidator(
            validators=[Int(min=3), Int(max=5)])

    def test_1_warnings(self):
        output = '\n'.join(map(str, custom_compound_warnings))
        msg = 'attempt_convert is deprecated; use _attempt_convert instead'
        self.assertTrue(msg in output, output or 'no warnings')

    def test_is_validator(self):
        self.assertTrue(is_validator(DeprecatedCustomCompoundValidator))
        self.assertTrue(is_validator(self.validator))

    def test_to_python(self):
        with warnings.catch_warnings(record=True) as _ignore:
            ccv = self.validator
            self.assertEqual(ccv.to_python('2'), 2)
            self.assertEqual(ccv.to_python('4'), 4)
            self.assertRaises(Invalid, ccv.to_python, '6')


with warnings.catch_warnings(record=True) as all_and_not_one_warnings:
    warnings.simplefilter('default')

    class DeprecatedAllAndNotOneValidator(All):
        """A custom validator based on an existing CompoundValidator."""

        messages = {
            'custom': "must not be %(number)d",
        }

        number = 1

        def attempt_convert(self, value, state, validate):
            value = super(DeprecatedAllAndNotOneValidator,
                self).attempt_convert(value, state, validate)
            if value == self.number:
                raise Invalid(self.message(
                    'custom', state, number=self.number), value, state)
            return value


class TestDeprecatedAllAndNotOneValidator(unittest.TestCase):

    def setUp(self):
        self.validator = DeprecatedAllAndNotOneValidator(
            validators=[Int(min=3), Int(max=5)], number=4)

    def test_1_warnings(self):  # must run first
        with warnings.catch_warnings(record=True) as runtime_warnings:
            warnings.simplefilter('default')
            self.validator.to_python('3')
        for output in runtime_warnings, all_and_not_one_warnings:
            output = '\n'.join(map(str, output))
            msg = 'attempt_convert is deprecated; use _attempt_convert instead'
            self.assertTrue(msg in output, output or 'no warnings')

    def test_is_validator(self):
        self.assertTrue(is_validator(DeprecatedAllAndNotOneValidator))
        self.assertTrue(is_validator(self.validator))

    def test_to_python(self):
        cav = self.validator
        self.assertRaises(Invalid, cav.to_python, '1')
        self.assertRaises(Invalid, cav.to_python, '2')
        self.assertEqual(cav.to_python('3'), 3)
        try:
            cav.to_python('4')
        except Invalid as e:
            self.assertTrue(
                'must not be 4' in str(e), e)
        else:
            self.fail("4 should be invalid")
        self.assertEqual(cav.to_python('5'), 5)
        self.assertRaises(Invalid, cav.to_python, '6')
        self.assertRaises(Invalid, cav.to_python, '7')
