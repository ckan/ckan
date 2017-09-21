# encoding: utf-8

from __future__ import absolute_import
from .base import FunctionalTestCase

class TestError(FunctionalTestCase):
    def test_without_redirect(self):
        # this is what a web bot might do
        res = self.app.get('/error/document')
        assert 'There is no error.' in str(res), str(res)
