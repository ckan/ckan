#!/usr/bin/python
# -*- coding: utf-8 -*-

from migrate.tests import fixture
from migrate.versioning.util.keyedinstance import *

class TestKeydInstance(fixture.Base):
    def test_unique(self):
        """UniqueInstance should produce unique object instances"""
        class Uniq1(KeyedInstance):
            @classmethod
            def _key(cls,key):
                return str(key)
            def __init__(self,value):
                self.value=value
        class Uniq2(KeyedInstance):
            @classmethod
            def _key(cls,key):
                return str(key)
            def __init__(self,value):
                self.value=value

        a10 = Uniq1('a')

        # Different key: different instance
        b10 = Uniq1('b')
        self.assertTrue(a10 is not b10)

        # Different class: different instance
        a20 = Uniq2('a')
        self.assertTrue(a10 is not a20)

        # Same key/class: same instance
        a11 = Uniq1('a')
        self.assertTrue(a10 is a11)

        # __init__ is called
        self.assertEqual(a10.value,'a')

        # clear() causes us to forget all existing instances
        Uniq1.clear()
        a12 = Uniq1('a')
        self.assertTrue(a10 is not a12)

        self.assertRaises(NotImplementedError, KeyedInstance._key)
