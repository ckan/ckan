from nose.tools import assert_equals

from ckan.lib.hash import get_message_hash, get_redirect

class TestHash:
    @classmethod
    def setup_class(cls):
        global secret
        secret = '42' # so that these tests are repeatable

    def test_get_message_hash(self):
        assert_equals(len(get_message_hash(u'/tag/country-uk')), len('6f58ff51b42e6b2d2e700abd1a14c9699e115c61'))

    def test_get_message_hash_unicode(self):
        assert_equals(len(get_message_hash(u'/tag/biocombust\xedveis')), len('d748fa890eb6a964cd317e6ff62905fad645b43d'))
    
