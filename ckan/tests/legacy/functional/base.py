# encoding: utf-8

from ckan.tests.legacy.html_check import HtmlCheckMethods
from ckan.tests.legacy import TestController as ControllerTestCase


class FunctionalTestCase(ControllerTestCase, HtmlCheckMethods):
    pass
