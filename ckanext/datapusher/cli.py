import ckan.lib.cli as cli
import ckan.plugins as p
import ckanext.datastore.db as datastore_db


class DatapusherCommand(cli.CkanCommand):
    '''Perform commands in the datapusher

    Usage:

        submit    - Resubmit all datastore resources to the datapusher,
                    ignoring if their files haven't changed.
    '''

    summary = __doc__.split('\n')[0]
    usage = __doc__

    def command(self):
        if self.args and self.args[0] == 'submit':
            self._load_config()
            self._submit_all()
        else:
            print self.usage

    def _submit_all(self):
        question = (
            "Data in any datastore resource that isn't in their source files "
            "(e.g. data added using the datastore API) will be permanently "
            "lost. Are you sure you want to proceed?"
        )
        answer = cli.query_yes_no(question, default=None)
        if answer == 'yes':
            resources_ids = datastore_db.get_all_resources_ids_in_datastore()
            print 'Submitting %d datastore resources' % len(resources_ids)
            datapusher_submit = p.toolkit.get_action('datapusher_submit')
            for resource_id in resources_ids:
                print ('Submitting %s...' % resource_id),
                data_dict = {
                    'resource_id': resource_id,
                    'ignore_hash': True,
                }
                if datapusher_submit(None, data_dict):
                    print 'OK'
                else:
                    print 'Fail'
