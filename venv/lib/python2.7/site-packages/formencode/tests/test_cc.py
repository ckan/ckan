# -*- coding: utf-8 -*-

import unittest

from formencode import Invalid
from formencode.validators import CreditCardValidator, CreditCardExpires


class TestCreditCardValidator(unittest.TestCase):

    def setUp(self):
        self.validator = CreditCardValidator()

    def validate(self, cctype, ccnumber):
        try:
            self.validator.to_python(
                dict(ccNumber=ccnumber, ccType=cctype), None)
        except Invalid as e:
            return e.unpack_errors()['ccNumber']

    def message(self, key):
        return self.validator.message(key, None)

    def test_validate(self):
        validate, message = self.validate, self.message
        self.assertTrue(validate('visa', '4' + '1' * 15) is None)
        self.assertEqual(validate('visa', '5' + '1' * 12),
            message('invalidNumber'))
        self.assertEqual(validate('visa', '4' + '1' * 11 + '2'),
            message('invalidNumber'))
        self.assertEqual(validate('visa', 'test'),
            message('notANumber'))
        self.assertEqual(validate('visa', '4' + '1' * 10),
            message('badLength'))


class TestCreditCardExpires(unittest.TestCase):

    def setUp(self):
        self.validator = CreditCardExpires()

    def validate(self, month, year):
        try:
            self.validator.to_python(
                dict(ccExpiresMonth=month, ccExpiresYear=year), None)
        except Invalid as e:
            return e.unpack_errors()['ccExpiresMonth']

    def message(self, key):
        return self.validator.message(key, None)

    def test_validate(self):
        validate, message = self.validate, self.message
        self.assertTrue(validate('11', '2250') is None)
        self.assertEqual(validate('11', 'test'), message('notANumber'))
        self.assertEqual(validate('test', '2250'), message('notANumber'))
        self.assertEqual(validate('10', '2005'), message('invalidNumber'))
        self.assertEqual(validate('10', '05'), message('invalidNumber'))
