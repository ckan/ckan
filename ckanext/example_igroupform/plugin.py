import ckan.plugins as plugins
import ckan.plugins.toolkit as tk


# I did try unicode in the group_type, but Routes wasn't happy with unicode in
# the route name, so it would require encoding everywhere we do url_for, so
# I've left it.
#group_type = u'gr\xc3\xb6up'  # This is 'group' with an umlaut on the 'o'

group_type = u'grup'
group_type_utf8 = group_type.encode('utf8')


class ExampleIGroupFormPlugin(plugins.SingletonPlugin,
                              tk.DefaultGroupForm):
    '''An example IGroupForm CKAN plugin.

    Doesn't do much yet.
    '''
    plugins.implements(plugins.IGroupForm, inherit=False)

    # IGroupForm

    def group_types(self):
        return (group_type,)

    def is_fallback(self):
        False
