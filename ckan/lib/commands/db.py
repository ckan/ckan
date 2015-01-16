import os
import sys

from ckan.lib.commands import parse_db_config, CkanCommand


class ManageDb(CkanCommand):
    '''Perform various tasks on the database.

    db create                      - alias of db upgrade
    db init                        - create and put in default data
    db clean
    db upgrade [version no.]       - Data migrate
    db version                     - returns current version of data schema
    db dump FILE_PATH              - dump to a pg_dump file
    db dump-rdf DATASET_NAME FILE_PATH
    db simple-dump-csv FILE_PATH   - dump just datasets in CSV format
    db simple-dump-json FILE_PATH  - dump just datasets in JSON format
    db user-dump-csv FILE_PATH     - dump user information to a CSV file
    db send-rdf TALIS_STORE USERNAME PASSWORD
    db load FILE_PATH              - load a pg_dump from a file
    db load-only FILE_PATH         - load a pg_dump from a file but don\'t do
                                     the schema upgrade or search indexing
    db create-from-model           - create database from the model (indexes
                                     not made)
    db migrate-filestore           - migrate all uploaded data from the 2.1
                                     filestore.
    '''
    summary = __doc__.split('\n')[0]
    usage = __doc__
    max_args = None
    min_args = 1

    def command(self):
        cmd = self.args[0]

        self._load_config(cmd != 'upgrade')

        import ckan.model as model
        import ckan.lib.search as search

        if cmd == 'init':

            model.repo.init_db()
            if self.verbose:
                print 'Initialising DB: SUCCESS'
        elif cmd == 'clean' or cmd == 'drop':

            # remove any *.pyc version files to prevent conflicts
            v_path = os.path.join(os.path.dirname(__file__),
                                  '..', 'migration', 'versions', '*.pyc')
            import glob
            filelist = glob.glob(v_path)
            for f in filelist:
                os.remove(f)

            model.repo.clean_db()
            search.clear()
            if self.verbose:
                print 'Cleaning DB: SUCCESS'
        elif cmd == 'upgrade':
            if len(self.args) > 1:
                model.repo.upgrade_db(self.args[1])
            else:
                model.repo.upgrade_db()
        elif cmd == 'version':
            self.version()
        elif cmd == 'dump':
            self.dump()
        elif cmd == 'load':
            self.load()
        elif cmd == 'load-only':
            self.load(only_load=True)
        elif cmd == 'simple-dump-csv':
            self.simple_dump_csv()
        elif cmd == 'simple-dump-json':
            self.simple_dump_json()
        elif cmd == 'dump-rdf':
            self.dump_rdf()
        elif cmd == 'user-dump-csv':
            self.user_dump_csv()
        elif cmd == 'create-from-model':
            model.repo.create_db()
            if self.verbose:
                print 'Creating DB: SUCCESS'
        elif cmd == 'send-rdf':
            self.send_rdf()
        elif cmd == 'migrate-filestore':
            self.migrate_filestore()
        else:
            print 'Command %s not recognized' % cmd
            sys.exit(1)

    def _get_db_config(self):
        return parse_db_config()

    def _get_postgres_cmd(self, command):
        self.db_details = self._get_db_config()
        if self.db_details.get('db_type') not in ('postgres', 'postgresql'):
            raise AssertionError('Expected postgres database - not %r' %
                                 self.db_details.get('db_type'))
        pg_cmd = command
        pg_cmd += ' -U %(db_user)s' % self.db_details
        if self.db_details.get('db_pass') not in (None, ''):
            pg_cmd = 'export PGPASSWORD=%(db_pass)s && ' % self.db_details \
                + pg_cmd
        if self.db_details.get('db_host') not in (None, ''):
            pg_cmd += ' -h %(db_host)s' % self.db_details
        if self.db_details.get('db_port') not in (None, ''):
            pg_cmd += ' -p %(db_port)s' % self.db_details
        return pg_cmd

    def _get_psql_cmd(self):
        psql_cmd = self._get_postgres_cmd('psql')
        psql_cmd += ' -d %(db_name)s' % self.db_details
        return psql_cmd

    def _postgres_dump(self, filepath):
        pg_dump_cmd = self._get_postgres_cmd('pg_dump')
        pg_dump_cmd += ' %(db_name)s' % self.db_details
        pg_dump_cmd += ' > %s' % filepath
        self._run_cmd(pg_dump_cmd)
        print 'Dumped database to: %s' % filepath

    def _postgres_load(self, filepath):
        import ckan.model as model
        assert not model.repo.are_tables_created(),\
            "Tables already found. You need to 'db clean' before a load."
        pg_cmd = self._get_psql_cmd() + ' -f %s' % filepath
        self._run_cmd(pg_cmd)
        print 'Loaded CKAN database: %s' % filepath

    def _run_cmd(self, command_line):
        import subprocess
        retcode = subprocess.call(command_line, shell=True)
        if retcode != 0:
            raise SystemError('Command exited with errorcode: %i' % retcode)

    def dump(self):
        if len(self.args) < 2:
            print 'Need pg_dump filepath'
            return
        dump_path = self.args[1]
        self._postgres_dump(dump_path)

    def load(self, only_load=False):
        if len(self.args) < 2:
            print 'Need pg_dump filepath'
            return
        dump_path = self.args[1]

        self._postgres_load(dump_path)
        if not only_load:
            print 'Upgrading DB'
            import ckan.model as model
            model.repo.upgrade_db()

            print 'Rebuilding search index'
            import ckan.lib.search
            ckan.lib.search.rebuild()
        else:
            print 'Now remember you have to call \'db upgrade\' and '\
                  'then \'search-index rebuild\'.'
        print 'Done'

    def simple_dump_csv(self):
        if len(self.args) < 2:
            print 'Need csv file path'
            return

        dump_filepath = self.args[1]
        import ckan.lib.dumper as dumper
        dump_file = open(dump_filepath, 'w')
        dumper.SimpleDumper().dump(dump_file, format='csv')

    def simple_dump_json(self):
        if len(self.args) < 2:
            print 'Need json file path'
            return

        dump_filepath = self.args[1]
        import ckan.lib.dumper as dumper
        dump_file = open(dump_filepath, 'w')
        dumper.SimpleDumper().dump(dump_file, format='json')

    def dump_rdf(self):
        if len(self.args) < 3:
            print 'Need dataset name and rdf file path'
            return
        package_name = self.args[1]
        rdf_path = self.args[2]
        import ckan.model as model
        import ckan.lib.rdf as rdf
        pkg = model.Package.by_name(unicode(package_name))
        if not pkg:
            print 'Dataset name "%s" does not exist' % package_name
            return
        rdf = rdf.RdfExporter().export_package(pkg)
        f = open(rdf_path, 'w')
        f.write(rdf)
        f.close()

    def user_dump_csv(self):
        if len(self.args) < 2:
            print 'Need csv file path'
            return
        dump_filepath = self.args[1]
        import ckan.lib.dumper as dumper
        dump_file = open(dump_filepath, 'w')
        dumper.UserDumper().dump(dump_file)

    def send_rdf(self):
        if len(self.args) < 4:
            print 'Need all arguments: {talis-store} {username} {password}'
            return
        talis_store = self.args[1]
        username = self.args[2]
        password = self.args[3]
        import ckan.lib.talis
        talis = ckan.lib.talis.Talis()
        return talis.send_rdf(talis_store, username, password)

    def migrate_filestore(self):
        from ckan.model import Session
        import requests
        from ckan.lib.uploader import ResourceUpload
        results = Session.execute("select id, revision_id, url from resource "
                                  "where resource_type = 'file.upload' "
                                  "and (url_type <> 'upload' or url_type is "
                                  "null) and url like '%storage%'")
        for id, revision_id, url in results:
            response = requests.get(url, stream=True)
            if response.status_code != 200:
                print "failed to fetch %s (code %s)" % (url,
                                                        response.status_code)
                continue
            resource_upload = ResourceUpload({'id': id})
            assert resource_upload.storage_path, \
                "no storage configured aborting"

            directory = resource_upload.get_directory(id)
            filepath = resource_upload.get_path(id)
            try:
                os.makedirs(directory)
            except OSError, e:
                # errno 17 is file already exists
                if e.errno != 17:
                    raise

            with open(filepath, 'wb+') as out:
                for chunk in response.iter_content(1024):
                    if chunk:
                        out.write(chunk)

            Session.execute("update resource set url_type = 'upload'"
                            "where id = '%s'" % id)
            Session.execute("update resource_revision set url_type = 'upload'"
                            "where id = '%s' and "
                            "revision_id = '%s'" % (id, revision_id))
            Session.commit()
            print "Saved url %s" % url

    def version(self):
        from ckan.model import Session
        print Session.execute('select version from migrate_version;')\
            .fetchall()
