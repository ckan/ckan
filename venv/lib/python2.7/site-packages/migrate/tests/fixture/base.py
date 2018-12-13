#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import testtools

class Base(testtools.TestCase):

    def assertEqualIgnoreWhitespace(self, v1, v2):
        """Compares two strings that should be\
        identical except for whitespace
        """
        def strip_whitespace(s):
            return re.sub(r'\s', '', s)

        line1 = strip_whitespace(v1)
        line2 = strip_whitespace(v2)

        self.assertEqual(line1, line2, "%s != %s" % (v1, v2))

    def ignoreErrors(self, func, *p,**k):
        """Call a function, ignoring any exceptions"""
        try:
            func(*p,**k)
        except:
            pass
