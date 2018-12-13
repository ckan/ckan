#!/usr/bin/env python
# -*- coding: utf-8 -*-

import testtools

def main(imports=None):
    if imports:
        global suite
        suite = suite(imports)
        defaultTest='fixture.suite'
    else:
        defaultTest=None
    return testtools.TestProgram(defaultTest=defaultTest)

from .base import Base
from .pathed import Pathed
from .shell import Shell
from .database import DB,usedb
