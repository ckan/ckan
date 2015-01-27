import multiprocessing as mp
from pprint import pprint
import sqlalchemy as sa

from ckan.lib.commands import CkanCommand


class SearchIndexCommand(CkanCommand):
    '''Creates a search index for all datasets

    Usage:
      search-index [-i] [-o] [-r] [-e] rebuild [dataset_name]  - reindex dataset_name if given, if not then rebuild
                                                                 full search index (all datasets)
      search-index rebuild_fast                                - reindex using multiprocessing using all cores.
                                                                 This acts in the same way as rubuild -r [EXPERIMENTAL]
      search-index check                                       - checks for datasets not indexed
      search-index show DATASET_NAME                           - shows index of a dataset
      search-index clear [dataset_name]                        - clears the search index for the provided dataset or
                                                                 for the whole ckan instance
    '''

    summary = __doc__.split('\n')[0]
    usage = __doc__
    max_args = 2
    min_args = 0

    def __init__(self, name):

        super(SearchIndexCommand, self).__init__(name)

        self.parser.add_option('-i', '--force', dest='force',
            action='store_true', default=False, help='Ignore exceptions when rebuilding the index')

        self.parser.add_option('-o', '--only-missing', dest='only_missing',
            action='store_true', default=False, help='Index non indexed datasets only')

        self.parser.add_option('-r', '--refresh', dest='refresh',
            action='store_true', default=False, help='Refresh current index (does not clear the existing one)')

        self.parser.add_option('-e', '--commit-each', dest='commit_each',
            action='store_true', default=False, help=
'''Perform a commit after indexing each dataset. This ensures that changes are
immediately available on the search, but slows significantly the process.
Default is false.'''
                    )

    def command(self):
        if not self.args:
            # default to printing help
            print self.usage
            return

        cmd = self.args[0]
        # Do not run load_config yet
        if cmd == 'rebuild_fast':
            self.rebuild_fast()
            return

        self._load_config()
        if cmd == 'rebuild':
            self.rebuild()
        elif cmd == 'check':
            self.check()
        elif cmd == 'show':
            self.show()
        elif cmd == 'clear':
            self.clear()
        else:
            print 'Command %s not recognized' % cmd

    def rebuild(self):
        from ckan.lib.search import rebuild, commit

        # BY default we don't commit after each request to Solr, as it is
        # a really heavy operation and slows things a lot

        if len(self.args) > 1:
            rebuild(self.args[1])
        else:
            rebuild(only_missing=self.options.only_missing,
                    force=self.options.force,
                    refresh=self.options.refresh,
                    defer_commit=(not self.options.commit_each))

        if not self.options.commit_each:
            commit()

    def check(self):
        from ckan.lib.search import check

        check()

    def show(self):
        from ckan.lib.search import show

        if not len(self.args) == 2:
            print 'Missing parameter: dataset-name'
            return
        index = show(self.args[1])
        pprint(index)

    def clear(self):
        from ckan.lib.search import clear

        package_id =self.args[1] if len(self.args) > 1 else None
        clear(package_id)

    def rebuild_fast(self):
        """ Get out config but without starting pylons environment """
        conf = self._get_config()

        # Get ids using own engine, otherwise multiprocess will balk
        db_url = conf['sqlalchemy.url']
        engine = sa.create_engine(db_url)
        package_ids = []
        result = engine.execute("select id from package where state = 'active';")
        for row in result:
            package_ids.append(row[0])

        def start(ids):
            """ load actual enviroment for each subprocess, so each have thier own
                sa session
            """
            self._load_config()
            from ckan.lib.search import rebuild, commit
            rebuild(package_ids=ids)
            commit()

        def chunks(l, n):
            """ Yield n successive chunks from l.
            """
            newn = int(len(l) / n)
            for i in xrange(0, n-1):
                yield l[i*newn:i*newn+newn]
            yield l[n*newn-newn:]

        processes = []
        for chunk in chunks(package_ids, mp.cpu_count()):
            process = mp.Process(target=start, args=(chunk,))
            processes.append(process)
            process.daemon = True
            process.start()

        for process in processes:
            process.join()
