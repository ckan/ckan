import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit

import ckanext.tabledesigner.views as views

@toolkit.blanket.actions
@toolkit.blanket.blueprints(views.tabledesigner)
class TableDesignerPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)

    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, "templates")
        toolkit.add_resource('assets', 'ckanext-tabledesigner')
