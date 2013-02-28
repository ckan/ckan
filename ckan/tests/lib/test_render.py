import os
import unittest

import pylons.config as config
import nose.tools as tools

import ckan.lib.render as render


class TestRender(unittest.TestCase):
    def setUp(self):
        template_paths = config['pylons.app_globals'].template_paths
        self._original_template_paths = list(template_paths)
        fixture_templates_path = os.path.join(os.path.dirname(__file__), 'fixtures')
        template_paths.append(fixture_templates_path)

        self._original_find_template = render.find_template

        self.inexistent_template = 'inexistent-template.html'
        self.existent_template = 'existent-template.html'

    def tearDown(self):
        config['pylons.app_globals'].template_paths = self._original_template_paths
        render.find_template = self._original_find_template

    @tools.raises(render.TemplateNotFound)
    def test_template_info_raises_if_couldnt_find_template(self):
        render.template_info(self.inexistent_template)

    def test_template_info_doesnt_raises_if_found_template(self):
        render.template_info(self.existent_template)

    def test_template_info_caches_the_templates(self):
        render.template_info(self.existent_template)

        render.find_template = lambda _: False

        render.template_info(self.existent_template)

    @tools.raises(render.TemplateNotFound)
    def test_reset_template_info_cache_clears_the_cache(self):
        render.template_info(self.existent_template)

        render.find_template = lambda _: False
        render.reset_template_info_cache()

        render.template_info(self.existent_template)
