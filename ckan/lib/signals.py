# -*- coding: utf-8 -*-

from blinker import Namespace

ckan = Namespace()
ckanext = Namespace()

before_action = ckan.signal(u'before_get_action', doc=u'''
Action is about to be called.
''')
