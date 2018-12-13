# -*- coding: utf-8 -*-

import unittest

from formencode import Invalid
from formencode.validators import Email


class TestEmail(unittest.TestCase):

    def setUp(self):
        self.validator = Email()

    def validate(self, *args):
        try:
            return self.validator.to_python(*args)
        except Invalid as e:
            return unicode(e)

    def message(self, message_name, username, domain):
        email = '@'.join((username, domain))
        return self.validator.message(
            message_name, email, username=username, domain=domain)

    def test_invalid_email_addresses(self):
        invalid_usernames = [
            # (username, domain, message_name),
            ('foo\tbar', 'formencode.org', 'badUsername'),
            ('foo\nbar', 'formencode.org', 'badUsername'),
            ('test', '', 'noAt'),
            ('test', 'foobar', 'badDomain'),
            ('test', 'foobar.5', 'badDomain'),
            ('test', 'foo..bar.com', 'badDomain'),
            ('test', '.foo.bar.com', 'badDomain'),
            ('foo,bar', 'formencode.org', 'badUsername')]

        for username, domain, message_name in invalid_usernames:
            email = '@'.join(el for el in (username, domain) if el)
            error = self.validate(email)
            expected = self.message(message_name, username, domain)
            self.assertEqual(error, expected)

    def test_valid_email_addresses(self):
        valid_email_addresses = [
            # (email address, expected email address),
            (' test@foo.com ', 'test@foo.com'),
            ('Test@foo.com', 'Test@foo.com'),
            ('nobody@xn--m7r7ml7t24h.com', 'nobody@xn--m7r7ml7t24h.com'),
            ('o*reilly@test.com', 'o*reilly@test.com'),
            ('foo+bar@example.com', 'foo+bar@example.com'),
            ('foo.bar@example.com', 'foo.bar@example.com'),
            ('foo!bar@example.com', 'foo!bar@example.com'),
            ('foo{bar}@example.com', 'foo{bar}@example.com'),
            # examples from RFC 3696
            #   punting on the difficult and extremely uncommon ones
            #('"Abc\@def"@example.com', '"Abc\@def"@example.com'),
            #('"Fred Bloggs"@example.com', '"Fred Bloggs"@example.com'),
            #('"Joe\\Blow"@example.com', '"Joe\\Blow"@example.com'),
            #('"Abc@def"@example.com', '"Abc@def"@example.com'),
            ('customer/department=shipping@example.com',
                'customer/department=shipping@example.com'),
            ('$A12345@example.com', '$A12345@example.com'),
            ('!def!xyz%abc@example.com', '!def!xyz%abc@example.com'),
            ('_somename@example.com', '_somename@example.com')]

        for email, expected in valid_email_addresses:
            self.assertEqual(self.validate(email), expected)


class TestUnicodeEmailWithResolveDomain(unittest.TestCase):

    def setUp(self):
        self.validator = Email(resolve_domain=True)

    def test_unicode_ascii_subgroup(self):
        self.assertEqual(self.validator.to_python(
            u'foo@yandex.com'), 'foo@yandex.com')

    def test_cyrillic_email(self):
        self.assertEqual(self.validator.to_python(
            u'me@письмо.рф'), u'me@письмо.рф')
