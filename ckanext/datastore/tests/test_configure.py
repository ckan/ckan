# encoding: utf-8

import unittest

import ckan.plugins
import nose.tools
import pyutilib.component.core


import ckanext.datastore.plugin as plugin

class InvalidUrlsOrPermissionsException(Exception):
    pass
