# encoding: utf-8

import io
import os.path
import shutil
import tempfile

from nose.tools import eq_, ok_, raises

import ckan.lib.io as ckan_io


class TestDecodeEncodePath(object):

    @raises(TypeError)
    def test_decode_path_fails_for_unicode(self):
        ckan_io.decode_path(u'just_a_unicode')

    @raises(TypeError)
    def test_encode_path_fails_for_str(self):
        ckan_io.encode_path(b'just_a_str')

    def test_decode_path_returns_unicode(self):
        ok_(isinstance(ckan_io.decode_path(b'just_a_str'), unicode))

    def test_encode_path_returns_str(self):
        ok_(isinstance(ckan_io.encode_path(u'just_a_unicode'), str))

    def test_decode_encode_path(self):
        temp_dir = ckan_io.decode_path(tempfile.mkdtemp())
        try:
            filename = u'\xf6\xe4\xfc.txt'
            path = os.path.join(temp_dir, filename)
            with io.open(ckan_io.encode_path(path), u'w',
                         encoding=u'utf-8') as f:
                f.write(u'foo')
            # Force str return type
            filenames = os.listdir(ckan_io.encode_path(temp_dir))
            eq_(ckan_io.decode_path(filenames[0]), filename)
        finally:
            shutil.rmtree(temp_dir)
