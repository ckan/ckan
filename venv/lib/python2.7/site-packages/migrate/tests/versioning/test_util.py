#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

from sqlalchemy import *

from migrate.exceptions import MigrateDeprecationWarning
from migrate.tests import fixture
from migrate.tests.fixture.warnings import catch_warnings
from migrate.versioning.util import *
from migrate.versioning import api

import warnings

class TestUtil(fixture.Pathed):

    def test_construct_engine(self):
        """Construct engine the smart way"""
        url = 'sqlite://'

        engine = construct_engine(url)
        self.assertTrue(engine.name == 'sqlite')

        # keyword arg
        engine = construct_engine(url, engine_arg_encoding='utf-8')
        self.assertEqual(engine.dialect.encoding, 'utf-8')

        # dict
        engine = construct_engine(url, engine_dict={'encoding': 'utf-8'})
        self.assertEqual(engine.dialect.encoding, 'utf-8')

        # engine parameter
        engine_orig = create_engine('sqlite://')
        engine = construct_engine(engine_orig)
        self.assertEqual(engine, engine_orig)

        # test precedance
        engine = construct_engine(url, engine_dict={'encoding': 'iso-8859-1'},
            engine_arg_encoding='utf-8')
        self.assertEqual(engine.dialect.encoding, 'utf-8')

        # deprecated echo=True parameter
        try:
            # py 2.4 compatability :-/
            cw = catch_warnings(record=True)
            w = cw.__enter__()

            warnings.simplefilter("always")
            engine = construct_engine(url, echo='True')
            self.assertTrue(engine.echo)

            self.assertEqual(len(w),1)
            self.assertTrue(issubclass(w[-1].category,
                                       MigrateDeprecationWarning))
            self.assertEqual(
                'echo=True parameter is deprecated, pass '
                'engine_arg_echo=True or engine_dict={"echo": True}',
                str(w[-1].message))

        finally:
            cw.__exit__()

        # unsupported argument
        self.assertRaises(ValueError, construct_engine, 1)

    def test_passing_engine(self):
        repo = self.tmp_repos()
        api.create(repo, 'temp')
        api.script('First Version', repo)
        engine = construct_engine('sqlite:///:memory:')

        api.version_control(engine, repo)
        api.upgrade(engine, repo)

    def test_asbool(self):
        """test asbool parsing"""
        result = asbool(True)
        self.assertEqual(result, True)

        result = asbool(False)
        self.assertEqual(result, False)

        result = asbool('y')
        self.assertEqual(result, True)

        result = asbool('n')
        self.assertEqual(result, False)

        self.assertRaises(ValueError, asbool, 'test')
        self.assertRaises(ValueError, asbool, object)


    def test_load_model(self):
        """load model from dotted name"""
        model_path = os.path.join(self.temp_usable_dir, 'test_load_model.py')

        f = open(model_path, 'w')
        f.write("class FakeFloat(int): pass")
        f.close()

        try:
            # py 2.4 compatability :-/
            cw = catch_warnings(record=True)
            w = cw.__enter__()

            warnings.simplefilter("always")

            # deprecated spelling
            FakeFloat = load_model('test_load_model.FakeFloat')
            self.assertTrue(isinstance(FakeFloat(), int))

            self.assertEqual(len(w),1)
            self.assertTrue(issubclass(w[-1].category,
                                       MigrateDeprecationWarning))
            self.assertEqual(
                'model should be in form of module.model:User '
                'and not module.model.User',
                str(w[-1].message))

        finally:
            cw.__exit__()

        FakeFloat = load_model('test_load_model:FakeFloat')
        self.assertTrue(isinstance(FakeFloat(), int))

        FakeFloat = load_model(FakeFloat)
        self.assertTrue(isinstance(FakeFloat(), int))

    def test_guess_obj_type(self):
        """guess object type from string"""
        result = guess_obj_type('7')
        self.assertEqual(result, 7)

        result = guess_obj_type('y')
        self.assertEqual(result, True)

        result = guess_obj_type('test')
        self.assertEqual(result, 'test')
