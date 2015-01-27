import ckan.logic as logic
import ckan.model as model
import ckan.plugins as p
import sqlalchemy as sa

from ckan.lib.commands import query_yes_no, CkanCommand


class ViewsCommand(CkanCommand):
    '''Manage resource views.

    Usage:

        paster views create all                 - Create views for all types.
        paster views create [type1] [type2] ... - Create views for specified types.
        paster views clean                      - Permanently delete views for all types no longer in the configuration file.

    Supported types are "pdf", "text", "webpage", "image" and "grid".  Make
    sure the relevant plugins are loaded for the following types, otherwise
    an error will be raised:
        * "grid"-> "recline_grid_view"
        * "pdf" -> "pdf_view"
        * "text -> "text_view"
    '''

    summary = __doc__.split('\n')[0]
    usage = __doc__
    min_args = 1

    def command(self):
        self._load_config()
        if not self.args:
            print self.usage
        elif self.args[0] == 'create':
            self.create_views(self.args[1:])
        elif self.args[0] == 'clean':
            self.clean_views()
        else:
            print self.usage

    def create_views(self, view_types):
        supported_types = ['grid', 'text', 'webpage', 'pdf', 'image']
        if not view_types:
            print self.usage
            return
        if view_types[0] == 'all':
            view_types = supported_types
        else:
            for view_type in view_types:
                if view_type not in supported_types:
                    print 'View type {view} not supported in this command'.format(view=view_type)
                    return

        for view_type in view_types:
            create_function_name = 'create_%s_views' % view_type
            create_function = getattr(self, create_function_name)
            create_function()

    def clean_views(self):
        names = []
        for plugin in p.PluginImplementations(p.IResourceView):
            names.append(str(plugin.info()['name']))

        results = model.ResourceView.get_count_not_in_view_types(names)

        if not results:
            print 'No resource views to delete'
            return

        print 'This command will delete.\n'
        for row in results:
            print '%s of type %s' % (row[1], row[0])

        result = query_yes_no('Do you want to delete these resource views:', default='no')

        if result == 'no':
            print 'Not Deleting.'
            return

        model.ResourceView.delete_not_in_view_types(names)
        model.Session.commit()
        print 'Deleted resource views.'

    def create_text_views(self):
        if not p.plugin_loaded('text_view'):
            print 'Please enable the text_view plugin to make the text views.'
            return

        if not p.plugin_loaded('resource_proxy'):
            print 'Please enable the resource_proxy plugin to make the text views.'
            return

        print 'Text resource views are being created'

        import ckanext.textview.plugin as textplugin

        formats = tuple(textplugin.DEFAULT_TEXT_FORMATS + textplugin.DEFAULT_XML_FORMATS +
                        textplugin.DEFAULT_JSON_FORMATS + textplugin.DEFAULT_JSONP_FORMATS)

        resources = model.Resource.get_all_without_views(formats)

        user = logic.get_action('get_site_user')({'model': model, 'ignore_auth': True}, {})
        context = {'model': model, 'session': model.Session, 'user': user['name']}

        count = 0
        for resource in resources:
            count += 1
            resource_view = {'title': 'Text View',
                             'description': 'View of the {format} file'.format(
                              format=resource.format.upper()),
                             'resource_id': resource.id,
                             'view_type': 'text'}

            logic.get_action('resource_view_create')(context, resource_view)

        print '%s text resource views created!' % count

    def create_image_views(self):
        import ckanext.imageview.plugin as imagevewplugin
        formats = tuple(imagevewplugin.DEFAULT_IMAGE_FORMATS)

        print 'Image resource views are being created'

        resources = model.Resource.get_all_without_views(formats)

        user = logic.get_action('get_site_user')({'model': model, 'ignore_auth': True}, {})
        context = {'model': model, 'session': model.Session, 'user': user['name']}

        count = 0
        for resource in resources:
            count += 1
            resource_view = {'title': 'Resource Image',
                             'description': 'View of the Image',
                             'resource_id': resource.id,
                             'view_type': 'image_view'}

            logic.get_action('resource_view_create')(context, resource_view)

        print '%s image resource views created!' % count

    def create_webpage_views(self):
        formats = tuple(['html', 'htm'])

        print 'Web page resource views are being created'

        resources = model.Resource.get_all_without_views(formats)

        user = logic.get_action('get_site_user')({'model': model, 'ignore_auth': True}, {})
        context = {'model': model, 'session': model.Session, 'user': user['name']}

        count = 0
        for resource in resources:
            count += 1
            resource_view = {'title': 'Web Page View',
                             'description': 'View of the webpage',
                             'resource_id': resource.id,
                             'view_type': 'webpage_view'}

            logic.get_action('resource_view_create')(context, resource_view)

        print '%s webpage resource views created!' % count

    def create_pdf_views(self):
        if not p.plugin_loaded('pdf_view'):
            print 'Please enable the pdf_view plugin to make the PDF views.'
            return

        if not p.plugin_loaded('resource_proxy'):
            print 'Please enable the resource_proxy plugin to make the PDF views.'
            return

        print 'PDF resource views are being created'

        resources = model.Resource.get_all_without_views(['pdf'])

        user = logic.get_action('get_site_user')({'model': model, 'ignore_auth': True}, {})
        context = {'model': model, 'session': model.Session, 'user': user['name']}

        count = 0
        for resource in resources:
            count += 1
            resource_view = {'title': 'PDF View',
                             'description': 'PDF view of the resource.',
                             'resource_id': resource.id,
                             'view_type': 'pdf'}

            logic.get_action('resource_view_create')(context, resource_view)

        print '%s pdf resource views created!' % count

    def create_grid_views(self):
        import ckan.plugins.toolkit as toolkit
        import ckanext.datastore.db as db
        import pylons

        if not p.plugin_loaded('datastore'):
            print 'The datastore plugin needs to be enabled to generate the grid views.'
            return

        if not p.plugin_loaded('recline_grid_view'):
            print 'Please enable the recline_grid_view plugin to make the grid views.'
            return

        print 'Grid resource views are being created'

        user = logic.get_action('get_site_user')({'model': model, 'ignore_auth': True}, {})
        context = {'model': model, 'session': model.Session, 'user': user['name']}

        data_dict = {}
        data_dict['connection_url'] = pylons.config['ckan.datastore.write_url']

        resources_sql = sa.text(u'''SELECT name FROM "_table_metadata"
                                    WHERE alias_of is null''')
        results = db._get_engine(data_dict).execute(resources_sql)

        count = 0
        for row in results:
            try:
                res = logic.get_action('resource_view_list')(context, {'id': row[0]})
            except toolkit.ObjectNotFound:
                continue
            if res:
                continue
            count += 1
            resource_view = {'resource_id': row[0],
                             'view_type': 'recline_grid_view',
                             'title': 'Grid view',
                             'description': 'View of data within the DataStore'}
            logic.get_action('resource_view_create')(context, resource_view)

        print '%s grid resource views created!' % count
