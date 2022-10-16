# encoding: utf-8
from __future__ import annotations

from ckan.common import CKANConfig
from typing import Any, Callable
import ckan.plugins as plugins

# Our custom template helper function.
def example_helper():
    '''An example template helper function.'''

    # Just return some example text.
    return 'This is some example text.'


@plugins.toolkit.chained_helper
def dump_json(next_func: Callable[..., Any],
              obj: Any, **kw: Any):
    if 'test_itemplatehelpers' in kw:
        return 'Not today'
    return next_func(obj, **kw)


class ExampleITemplateHelpersPlugin(plugins.SingletonPlugin):
    '''An example that shows how to use the ITemplateHelpers plugin interface.

    '''
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.ITemplateHelpers)

    # Update CKAN's config settings, see the IConfigurer plugin interface.
    def update_config(self, config: CKANConfig):

        # Tell CKAN to use the template files in
        # ckanext/example_itemplatehelpers/templates.
        plugins.toolkit.add_template_directory(config, 'templates')

    # Tell CKAN what custom template helper functions this plugin provides,
    # see the ITemplateHelpers plugin interface.
    def get_helpers(self) -> dict[str, Callable[..., Any]]:
        return {
            'example_helper': example_helper,
            'dump_json': dump_json
        }
