import os
import sys

from ckan.lib.commands import CkanCommand


class RDFExport(CkanCommand):
    '''Export active datasets as RDF
    This command dumps out all currently active datasets as RDF into the
    specified folder.

    Usage:
      paster rdf-export /path/to/store/output
    '''
    summary = __doc__.split('\n')[0]
    usage = __doc__

    def command(self):
        self._load_config()

        if not self.args:
            # default to run
            print RDFExport.__doc__
        else:
            self.export_datasets(self.args[0])

    def export_datasets(self, out_folder):
        '''
        Export datasets as RDF to an output folder.
        '''
        import urlparse
        import urllib2
        import pylons.config as config
        import ckan.model as model
        import ckan.logic as logic
        import ckan.lib.helpers as h

        # Create output folder if not exists
        if not os.path.isdir(out_folder):
            os.makedirs(out_folder)

        fetch_url = config['ckan.site_url']
        user = logic.get_action('get_site_user')({'model': model,
                                                  'ignore_auth': True}, {})
        context = {'model': model, 'session': model.Session,
                   'user': user['name']}
        dataset_names = logic.get_action('package_list')(context, {})
        for dataset_name in dataset_names:
            dd = logic.get_action('package_show')(context,
                                                  {'id': dataset_name})
            if not dd['state'] == 'active':
                continue

            url = h.url_for(controller='package', action='read',
                            id=dd['name'])

            url = urlparse.urljoin(fetch_url, url[1:]) + '.rdf'
            try:
                fname = os.path.join(out_folder, dd['name']) + ".rdf"
                r = urllib2.urlopen(url).read()
                with open(fname, 'wb') as f:
                    f.write(r)
            except IOError, ioe:
                sys.stderr.write(str(ioe) + "\n")
