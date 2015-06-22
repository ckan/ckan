import sys

import ckan.lib.cli as cli
import ckan.plugins as p
import ckanext.datastore.db as datastore_db


class DatapusherCommand(cli.CkanCommand):
    '''Perform commands in the datapusher

    Usage:

        resubmit  - Resubmit all datastore resources to the datapusher,
                    ignoring if their files haven't changed.
        submit <pkgname> - Submits all resources from the package
                         identified by pkgname (either the short name or ID).
    '''

    summary = __doc__.split('\n')[0]
    usage = __doc__

    def command(self):
        if self.args and self.args[0] == 'resubmit':
            self._confirm_or_abort()

            self._load_config()
            self._submit_all()
        elif self.args and self.args[0] == 'submit':
            self._confirm_or_abort()

            if len(self.args) != 2:
                print "This command requires an argument\n"
                print self.usage
                sys.exit(1)

            self._load_config()
            self._submit_package(self.args[1])
        else:
            print self.usage

    def _confirm_or_abort(self):
        question = (
            "Data in any datastore resource that isn't in their source files "
            "(e.g. data added using the datastore API) will be permanently "
            "lost. Are you sure you want to proceed?"
        )
        answer = cli.query_yes_no(question, default=None)
        if not answer == 'yes':
            print "Aborting..."
            sys.exit(0)

    def _submit_all(self):
        resources_ids = datastore_db.get_all_resources_ids_in_datastore()
        self._submit(resource_ids)

    def _submit_package(self, pkg_id):
        import ckan.model as model

        package_show = p.toolkit.get_action('package_show')
        try:
            pkg = package_show({'model': model, 'ignore_auth': True},
                               {'id': pkg_id.strip()})
        except Exception, e:
            print e
            print "Package '{}' was not found".format(pkg_id)
            sys.exit(1)

        resource_ids = [r['id'] for r in pkg['resources']]
        self._submit(resource_ids)

    def _submit(self, resources):
        import ckan.model as model

        print 'Submitting %d datastore resources' % len(resources)
        user = p.toolkit.get_action('get_site_user')(
            {'model': model, 'ignore_auth': True}, {})
        datapusher_submit = p.toolkit.get_action('datapusher_submit')
        for resource_id in resources:
            print ('Submitting %s...' % resource_id),
            data_dict = {
                'resource_id': resource_id,
                'ignore_hash': True,
            }
            if datapusher_submit({'user': user['name']}, data_dict):
                print 'OK'
            else:
                print 'Fail'
