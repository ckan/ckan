import os
import unittest
import tempfile

import pylons.config as config
import nose.tools as tools

import ckan.lib.render as render


class TestRender(unittest.TestCase):
    def setUp(self):
        self.existent_template = tempfile.NamedTemporaryFile()

        template_paths = config['pylons.app_globals'].template_paths
        self._original_template_paths = list(template_paths)
        template_paths.append(os.path.dirname(self.existent_template.name))

    def tearDown(self):
        config['pylons.app_globals'].template_paths = self._original_template_paths

    @tools.raises(render.TemplateNotFound)
    def test_template_info_raises_if_couldnt_find_template(self):
        render.template_info('inexistent-template.html')

    def test_template_info_doesnt_raises_if_found_template(self):
        render.template_info(self.existent_template.name)

    def test_template_info_caches_the_templates(self):
        render.template_info(self.existent_template.name)

        self.existent_template.close()

        render.template_info(self.existent_template.name)

    @tools.raises(render.TemplateNotFound)
    def test_reset_template_info_cache_clears_the_cache(self):
        render.template_info(self.existent_template.name)

        self.existent_template.close()
        render.reset_template_info_cache()

        render.template_info(self.existent_template.name)
