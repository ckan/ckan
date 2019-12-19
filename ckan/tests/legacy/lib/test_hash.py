# encoding: utf-8


from ckan.lib.hash import get_message_hash


def test_get_message_hash():
    assert len(get_message_hash(u"/tag/country-uk")) == len(
        "6f58ff51b42e6b2d2e700abd1a14c9699e115c61"
    )


def test_get_message_hash_unicode():
    assert len(get_message_hash(u"/tag/biocombust\xedveis")) == len(
        "d748fa890eb6a964cd317e6ff62905fad645b43d"
    )
