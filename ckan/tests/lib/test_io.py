# encoding: utf-8

import io
import os.path
import shutil
import tempfile
import pytest
import six
from six import text_type

import ckan.lib.io as ckan_io


def test_decode_path_fails_for_unicode():
    with pytest.raises(TypeError):
        ckan_io.decode_path("just_a_unicode")


def test_encode_path_fails_for_str():
    with pytest.raises(TypeError):
        ckan_io.encode_path(b"just_a_str")


def test_decode_path_returns_unicode():
    assert isinstance(ckan_io.decode_path(b"just_a_str"), text_type)


def test_encode_path_returns_str():
    assert isinstance(ckan_io.encode_path("just_a_unicode"), six.binary_type)


def test_decode_encode_path():
    temp_dir = ckan_io.decode_path(six.b(tempfile.mkdtemp()))
    try:
        filename = "\xf6\xe4\xfc.txt"
        path = os.path.join(temp_dir, filename)
        with io.open(ckan_io.encode_path(path), "w", encoding="utf-8") as f:
            f.write("foo")
        # Force str return type
        filenames = os.listdir(ckan_io.encode_path(temp_dir))
        assert ckan_io.decode_path(filenames[0]) == filename
    finally:
        shutil.rmtree(temp_dir)
