import logging

import ckan.plugins as p
import ckan.model as model

log = logging.getLogger(__name__)

class HomepagePlugin(p.SingletonPlugin):
    p.implements(p.IConfigurer, inherit=True)
    p.implements(p.ITemplateHelpers, inherit=True)
    p.implements(p.IConfigurable, inherit=True)

    def configure(self, config):
        groups = config.get('ckan.featured_groups', '')
        if groups:
            log.warning('Config setting `ckan.featured_groups` is deprecated '
                        'please use `ckanext.homepage.groups`')
        self.groups = config.get('ckanext.homepage.groups', groups).split()
        self.orgs = config.get('ckanext.homepage.orgs', '').split()

    def update_config(self, config):
        p.toolkit.add_template_directory(config, 'theme/templates')

    def get_featured_organizations(self, count=1):
        orgs = self.featured_group_org(get_action='organization_show',
                                       list_action='organization_list',
                                       count=count,
                                       items=self.orgs)
        return orgs

    def get_featured_groups(self, count=1):
        groups = self.featured_group_org(get_action='group_show',
                                         list_action='group_list',
                                         count=count,
                                         items=self.groups)
        return groups

    def featured_group_org(self, items, get_action, list_action, count):
        def get_group(id):
            context = {'ignore_auth': True,
                       'limits': {'packages': 2},
                       'for_view': True}
            data_dict = {'id': id}

            try:
                out = p.toolkit.get_action(get_action)(context, data_dict)
            except p.toolkit.ObjectNotFound:
                return None
            return out

        groups_data = []

        extras = p.toolkit.get_action(list_action)({}, {})

        # list of found ids to prevent duplicates
        found = []
        for group_name in items + extras:
            group = get_group(group_name)
            if not group:
                continue
            # ckeck if duplicate
            if group['id'] in found:
                continue
            found.append(group['id'])
            groups_data.append(group)
            if len(groups_data) == count:
                break

        return groups_data

    def get_site_statistics(self):
        stats = {}
        stats['dataset_count'] = p.toolkit.get_action('package_search')({}, {"rows": 1})['count']
        stats['group_count'] = len(p.toolkit.get_action('group_list')({}, {}))
        stats['organization_count'] = len(p.toolkit.get_action('organization_list')({}, {}))
        result =model.Session.execute(
            '''select count(*) from related r
               left join related_dataset rd on r.id = rd.related_id
               where rd.status = 'active' or rd.id is null''').first()[0]
        stats['related_count'] = len(p.toolkit.get_action('organization_list')({}, {}))

        return stats

    def get_helpers(self):
        return {
            'get_featured_organizations': self.get_featured_organizations,
            'get_featured_groups': self.get_featured_groups,
            'get_site_statistics': self.get_site_statistics,
        }
