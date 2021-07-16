# encoding: utf-8

from ckan import plugins
from ckan.lib.plugins import DefaultPermissionLabels
from ckan.plugins.toolkit import get_action


class ExampleIPermissionLabelsPlugin(
        plugins.SingletonPlugin, DefaultPermissionLabels):
    '''
    Example permission labels plugin that makes datasets whose
    notes field starts with "Proposed:" visible only to their
    creator and Admin users in the organization assigned to the
    dataset.
    '''
    plugins.implements(plugins.IPermissionLabels)

    def get_dataset_labels(self, dataset_obj):
        '''
        Use creator-*, admin-* labels for proposed datasets
        '''
        if dataset_obj.notes.startswith('Proposed:'):
            labels = ['creator-%s' % dataset_obj.creator_user_id]
            if dataset_obj.owner_org:
                return labels + ['admin-%s' % dataset_obj.owner_org]
            return labels

        return super(ExampleIPermissionLabelsPlugin, self).get_dataset_labels(
            dataset_obj)

    def get_user_dataset_labels(self, user_obj):
        '''
        Include admin-* labels for users in addition to default labels
        creator-*, member-* and public
        '''
        labels = super(ExampleIPermissionLabelsPlugin, self
                       ).get_user_dataset_labels(user_obj)
        if user_obj:
            orgs = get_action('organization_list_for_user')(
                {'user': user_obj.id}, {'permission': 'admin'})
            labels.extend('admin-%s' % o['id'] for o in orgs)
        return labels
