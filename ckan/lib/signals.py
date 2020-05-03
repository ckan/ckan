# -*- coding: utf-8 -*-

from blinker import Namespace

ckan = Namespace()
ckanext = Namespace()


before_action = ckan.signal(u'before_action')
"""Action is about to be called.
"""

after_action = ckan.signal(u'after_action')
"""Action was successfully completed.
"""

register_blueprint = ckan.signal(u'register_blueprint')
"""Blueprint for dataset/resoruce/group/organization is going to be
registered inside application.
"""

resource_download = ckan.signal(u'resource_download')
"""File from uploaded resource will be sent to user.
"""
