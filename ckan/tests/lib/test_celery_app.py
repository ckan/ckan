# encoding: utf-8

u'''
Tests for ``ckan.lib.celery_app``.
'''

from nose.tools import raises
import mock


class TestCeleryVersion(object):
    u'''
    Make sure that Celery's version is checked.
    '''
    @mock.patch.dict(u'sys.modules', {u'celery': mock.MagicMock()})
    def check_celery_version(self, version):
        import celery
        celery.__version__ = version
        import ckan.lib.celery_app
        reload(ckan.lib.celery_app)

    def test_3x(self):
        self.check_celery_version(u'3.1.25')

    @raises(ImportError)
    def test_4x(self):
        self.check_celery_version(u'4.0.0')
