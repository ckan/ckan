# -*- coding: utf-8 -*-

import ckan.plugins as p
from ckanext.example_iclick.cli import get_commands


class ExampleIClickPlugin(p.SingletonPlugin):
    p.implements(p.IClick)

    # IClick

    def get_commands(self):
        return get_commands()
