# -*- coding: utf-8 -*-

import unittest

from formencode.api import is_validator, FancyValidator, Invalid
from formencode.compound import CompoundValidator, All
from formencode.validators import Int


class CustomValidator(FancyValidator):
    """A custom validator based directly on FancyValidator."""

    messages = {
        'custom': "%(number)s is invalid",
    }

    def _convert_to_python(self, value, state):
        if value == '1':
            raise Invalid(self.message(
                'custom', state, number='one'), value, state)
        return int(value)

    def _convert_from_python(self, value, state):
        if value == 2:
            raise Invalid(self.message(
                'custom', state, number='two'), value, state)
        return str(value)

    def _validate_other(self, value, state):
        if value == '3':
            raise Invalid(self.message(
                'custom', state, number='three'), value, state)

    def _validate_python(self, value, state):
        if value == 4:
            raise Invalid(self.message(
                'custom', state, number='four'), value, state)


class TestCustomValidator(unittest.TestCase):

    def test_is_validator(self):
        self.assertTrue(is_validator(CustomValidator))
        self.assertTrue(is_validator(CustomValidator()))

    def test_to_python(self):
        cv = CustomValidator()
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
        cv = CustomValidator()
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
        cv = CustomValidator(accept_python=False)
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


class NotOneValidator(Int):
    """A custom validator based on an existing validator."""

    messages = {
        'custom': "must not be %(number)d",
    }

    number = 1

    def _convert_to_python(self, value, state):
        value = super(NotOneValidator, self)._convert_to_python(value, state)
        if value == self.number:
            raise Invalid(self.message(
                'custom', state, number=self.number), value, state)
        return value


class TestNotOneValidator(unittest.TestCase):

    def test_is_validator(self):
        self.assertTrue(is_validator(NotOneValidator))
        self.assertTrue(is_validator(NotOneValidator()))
        self.assertTrue(is_validator(NotOneValidator(one=2)))

    def test_to_python(self):
        nov = NotOneValidator()
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
        nov = NotOneValidator(number=42)
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
        nov = NotOneValidator(min=40, max=49, number=42)
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


class CustomCompoundValidator(CompoundValidator):
    """A custom validator based directly on CompoundValidator."""

    def _attempt_convert(self, value, state, validate):
        return validate(self.validators[1], value, state)


class TestCustomCompoundValidator(unittest.TestCase):

    def setUp(self):
        self.validator = CustomCompoundValidator(
            validators=[Int(min=3), Int(max=5)])

    def test_is_validator(self):
        self.assertTrue(is_validator(CustomCompoundValidator))
        self.assertTrue(is_validator(self.validator))

    def test_to_python(self):
        ccv = self.validator
        self.assertEqual(ccv.to_python('2'), 2)
        self.assertEqual(ccv.to_python('4'), 4)
        self.assertRaises(Invalid, ccv.to_python, '6')


class AllAndNotOneValidator(All):
    """A custom validator based on an existing CompoundValidator."""

    messages = {
        'custom': "must not be %(number)d",
    }

    number = 1

    def _attempt_convert(self, value, state, validate):
        value = super(AllAndNotOneValidator, self)._attempt_convert(
            value, state, validate)
        if value == self.number:
            raise Invalid(self.message(
                'custom', state, number=self.number), value, state)
        return value


class TestAllAndNotOneValidator(unittest.TestCase):

    def setUp(self):
        self.validator = AllAndNotOneValidator(
            validators=[Int(min=3), Int(max=5)], number=4)

    def test_is_validator(self):
        self.assertTrue(is_validator(AllAndNotOneValidator))
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


class DeclarativeAllValidator(All):
    """A CompoundValidator with subvalidators given as attributes."""

    first_validator = Int(min=3)
    second_validator = Int(max=5)


class TestDeclarativeAllValidator(unittest.TestCase):

    def test_is_validator(self):
        self.assertTrue(is_validator(DeclarativeAllValidator))
        self.assertTrue(is_validator(DeclarativeAllValidator()))

    def test_attrs_deleted(self):
        self.assertFalse(hasattr(DeclarativeAllValidator, 'first_validator'))
        self.assertFalse(hasattr(DeclarativeAllValidator, 'second_validator'))

    def test_to_python(self):
        dav = DeclarativeAllValidator()
        self.assertRaises(Invalid, dav.to_python, '1')
        self.assertRaises(Invalid, dav.to_python, '2')
        self.assertEqual(dav.to_python('3'), 3)
        self.assertEqual(dav.to_python('4'), 4)
        self.assertEqual(dav.to_python('5'), 5)
        self.assertRaises(Invalid, dav.to_python, '6')
        self.assertRaises(Invalid, dav.to_python, '7')
