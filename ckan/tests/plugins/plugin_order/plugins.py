# -*- coding: utf-8 -*-

import ckan.plugins as p

class FirstPlugin(p.SingletonPlugin):
    p.implements(p.IConfigurer)
    p.implements(p.ITemplateHelpers)

    # IConfigurer

    def update_config(self, config_):
        p.toolkit.add_template_directory(config_, "templates_first")


    # ITemplateHelpers

    def get_helpers(self):
        return { "helper": self.helper }


    def helper(self):
        return "First helper"


class SecondPlugin(p.SingletonPlugin):
    p.implements(p.IConfigurer)
    p.implements(p.ITemplateHelpers)

    # IConfigurer

    def update_config(self, config_):
        p.toolkit.add_template_directory(config_, "templates_second")


    # ITemplateHelpers

    def get_helpers(self):
        return { "helper": self.helper }


    def helper(self):
        return "Second helper"

