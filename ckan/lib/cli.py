import collections
import csv
import multiprocessing as mp
import os
import datetime
import sys
from pprint import pprint
import re
import itertools
import json
import logging
import ckan.logic as logic
import ckan.model as model
import ckan.include.rjsmin as rjsmin
import ckan.include.rcssmin as rcssmin
import ckan.lib.fanstatic_resources as fanstatic_resources
import ckan.plugins as p
import sqlalchemy as sa
import urlparse
import routes
from pylons import config

import paste.script
from paste.registry import Registry
from paste.script.util.logging_config import fileConfig

#NB No CKAN imports are allowed until after the config file is loaded.
#   i.e. do the imports in methods, after _load_config is called.
#   Otherwise loggers get disabled.


def parse_db_config(config_key='sqlalchemy.url'):
    ''' Takes a config key for a database connection url and parses it into
    a dictionary. Expects a url like:

    'postgres://tester:pass@localhost/ckantest3'
    '''
    from pylons import config
    url = config[config_key]
    regex = [
        '^\s*(?P<db_type>\w*)',
        '://',
        '(?P<db_user>[^:]*)',
        ':?',
        '(?P<db_pass>[^@]*)',
        '@',
        '(?P<db_host>[^/:]*)',
        ':?',
        '(?P<db_port>[^/]*)',
        '/',
        '(?P<db_name>[\w.-]*)'
    ]
    db_details_match = re.match(''.join(regex), url)
    if not db_details_match:
        raise Exception('Could not extract db details from url: %r' % url)
    db_details = db_details_match.groupdict()
    return db_details


## from http://code.activestate.com/recipes/577058/ MIT licence.
## Written by Trent Mick
def query_yes_no(question, default="yes"):
    """Ask a yes/no question via raw_input() and return their answer.

    "question" is a string that is presented to the user.
    "default" is the presumed answer if the user just hits <Enter>.
        It must be "yes" (the default), "no" or None (meaning
        an answer is required of the user).

    The "answer" return value is one of "yes" or "no".
    """
    valid = {"yes": "yes",   "y": "yes",  "ye": "yes",
             "no": "no",     "n": "no"}
    if default is None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while 1:
        sys.stdout.write(question + prompt)
        choice = raw_input().lower()
        if default is not None and choice == '':
            return default
        elif choice in valid.keys():
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' "\
                             "(or 'y' or 'n').\n")


class MockTranslator(object):
    def gettext(self, value):
        return value

    def ugettext(self, value):
        return value

    def ungettext(self, singular, plural, n):
        if n > 1:
            return plural
        return singular


class CkanCommand(paste.script.command.Command):
    '''Base class for classes that implement CKAN paster commands to inherit.'''
    parser = paste.script.command.Command.standard_parser(verbose=True)
    parser.add_option('-c', '--config', dest='config',
                      default='development.ini', help='Config file to use.')
    parser.add_option('-f', '--file',
                      action='store',
                      dest='file_path',
                      help="File to dump results to (if needed)")
    default_verbosity = 1
    group_name = 'ckan'

    def _get_config(self):
        from paste.deploy import appconfig

        if self.options.config:
            self.filename = os.path.abspath(self.options.config)
            config_source = '-c parameter'
        elif os.environ.get('CKAN_INI'):
            self.filename = os.environ.get('CKAN_INI')
            config_source = '$CKAN_INI'
        else:
            self.filename = os.path.join(os.getcwd(), 'development.ini')
            config_source = 'default value'

        if not os.path.exists(self.filename):
            msg = 'Config file not found: %s' % self.filename
            msg += '\n(Given by: %s)' % config_source
            raise self.BadCommand(msg)

        fileConfig(self.filename)
        return appconfig('config:' + self.filename)

    def _load_config(self, load_site_user=True):
        conf = self._get_config()
        assert 'ckan' not in dir()  # otherwise loggers would be disabled
        # We have now loaded the config. Now we can import ckan for the
        # first time.
        from ckan.config.environment import load_environment
        load_environment(conf.global_conf, conf.local_conf)

        self.registry = Registry()
        self.registry.prepare()
        import pylons
        self.translator_obj = MockTranslator()
        self.registry.register(pylons.translator, self.translator_obj)

        if model.user_table.exists() and load_site_user:
            # If the DB has already been initialized, create and register
            # a pylons context object, and add the site user to it, so the
            # auth works as in a normal web request
            c = pylons.util.AttribSafeContextObj()

            self.registry.register(pylons.c, c)

            self.site_user = logic.get_action('get_site_user')({'ignore_auth': True}, {})

            pylons.c.user = self.site_user['name']
            pylons.c.userobj = model.User.get(self.site_user['name'])

        ## give routes enough information to run url_for
        parsed = urlparse.urlparse(conf.get('ckan.site_url', 'http://0.0.0.0'))
        request_config = routes.request_config()
        request_config.host = parsed.netloc + parsed.path
        request_config.protocol = parsed.scheme

    def _setup_app(self):
        cmd = paste.script.appinstall.SetupCommand('setup-app')
        cmd.run([self.filename])


class ManageDb(CkanCommand):
    '''Perform various tasks on the database.

    db create                      - alias of db upgrade
    db init                        - create and put in default data
    db clean
    db upgrade [version no.]       - Data migrate
    db version                     - returns current version of data schema
    db dump FILE_PATH              - dump to a pg_dump file
    db simple-dump-csv FILE_PATH   - dump just datasets in CSV format
    db simple-dump-json FILE_PATH  - dump just datasets in JSON format
    db user-dump-csv FILE_PATH     - dump user information to a CSV file
    db load FILE_PATH              - load a pg_dump from a file
    db load-only FILE_PATH         - load a pg_dump from a file but don\'t do
                                     the schema upgrade or search indexing
    db create-from-model           - create database from the model (indexes not made)
    db migrate-filestore           - migrate all uploaded data from the 2.1 filesore.
    '''
    summary = __doc__.split('\n')[0]
    usage = __doc__
    max_args = None
    min_args = 1

    def command(self):
        cmd = self.args[0]

        self._load_config(cmd!='upgrade')
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
        elif cmd == 'user-dump-csv':
            self.user_dump_csv()
        elif cmd == 'create-from-model':
            model.repo.create_db()
            if self.verbose:
                print 'Creating DB: SUCCESS'
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
            raise AssertionError('Expected postgres database - not %r' % self.db_details.get('db_type'))
        pg_cmd = command
        pg_cmd += ' -U %(db_user)s' % self.db_details
        if self.db_details.get('db_pass') not in (None, ''):
            pg_cmd = 'export PGPASSWORD=%(db_pass)s && ' % self.db_details + pg_cmd
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
        assert not model.repo.are_tables_created(), "Tables already found. You need to 'db clean' before a load."
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

        psql_cmd = self._get_psql_cmd() + ' -f %s'
        pg_cmd = self._postgres_dump(dump_path)

    def load(self, only_load=False):
        if len(self.args) < 2:
            print 'Need pg_dump filepath'
            return
        dump_path = self.args[1]

        psql_cmd = self._get_psql_cmd() + ' -f %s'
        pg_cmd = self._postgres_load(dump_path)
        if not only_load:
            print 'Upgrading DB'
            import ckan.model as model
            model.repo.upgrade_db()

            print 'Rebuilding search index'
            import ckan.lib.search
            ckan.lib.search.rebuild()
        else:
            print 'Now remember you have to call \'db upgrade\' and then \'search-index rebuild\'.'
        print 'Done'

    def simple_dump_csv(self):
        import ckan.model as model
        if len(self.args) < 2:
            print 'Need csv file path'
            return
        dump_filepath = self.args[1]
        import ckan.lib.dumper as dumper
        dump_file = open(dump_filepath, 'w')
        dumper.SimpleDumper().dump(dump_file, format='csv')

    def simple_dump_json(self):
        import ckan.model as model
        if len(self.args) < 2:
            print 'Need json file path'
            return
        dump_filepath = self.args[1]
        import ckan.lib.dumper as dumper
        dump_file = open(dump_filepath, 'w')
        dumper.SimpleDumper().dump(dump_file, format='json')

    def user_dump_csv(self):
        if len(self.args) < 2:
            print 'Need csv file path'
            return
        dump_filepath = self.args[1]
        import ckan.lib.dumper as dumper
        dump_file = open(dump_filepath, 'w')
        dumper.UserDumper().dump(dump_file)

    def migrate_filestore(self):
        from ckan.model import Session
        import requests
        from ckan.lib.uploader import ResourceUpload
        results = Session.execute("select id, revision_id, url from resource "
                                  "where resource_type = 'file.upload' "
                                  "and (url_type <> 'upload' or url_type is null)"
                                  "and url like '%storage%'")
        for id, revision_id, url in results:
            response = requests.get(url, stream=True)
            if response.status_code != 200:
                print "failed to fetch %s (code %s)" % (url,
                                                        response.status_code)
                continue
            resource_upload = ResourceUpload({'id': id})
            assert resource_upload.storage_path, "no storage configured aborting"

            directory = resource_upload.get_directory(id)
            filepath = resource_upload.get_path(id)
            try:
                os.makedirs(directory)
            except OSError, e:
                ## errno 17 is file already exists
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
        print Session.execute('select version from migrate_version;').fetchall()


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
                               action='store_true', default=False,
                               help='Ignore exceptions when rebuilding the index')

        self.parser.add_option('-o', '--only-missing', dest='only_missing',
                               action='store_true', default=False,
                               help='Index non indexed datasets only')

        self.parser.add_option('-r', '--refresh', dest='refresh',
                               action='store_true', default=False,
                               help='Refresh current index (does not clear the existing one)')

        self.parser.add_option('-e', '--commit-each', dest='commit_each',
                               action='store_true', default=False, help=
'''Perform a commit after indexing each dataset. This ensures that changes are
immediately available on the search, but slows significantly the process.
Default is false.''')

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
        package_id = self.args[1] if len(self.args) > 1 else None
        clear(package_id)

    def rebuild_fast(self):
        ###  Get out config but without starting pylons environment ####
        conf = self._get_config()

        ### Get ids using own engine, otherwise multiprocess will balk
        db_url = conf['sqlalchemy.url']
        engine = sa.create_engine(db_url)
        package_ids = []
        result = engine.execute("select id from package where state = 'active';")
        for row in result:
            package_ids.append(row[0])

        def start(ids):
            ## load actual enviroment for each subprocess, so each have thier own
            ## sa session
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


class Notification(CkanCommand):
    '''Send out modification notifications.

    In "replay" mode, an update signal is sent for each dataset in the database.

    Usage:
      notify replay                        - send out modification signals
    '''

    summary = __doc__.split('\n')[0]
    usage = __doc__
    max_args = 1
    min_args = 0

    def command(self):
        self._load_config()
        from ckan.model import Session, Package, DomainObjectOperation
        from ckan.model.modification import DomainObjectModificationExtension

        if not self.args:
            # default to run
            cmd = 'replay'
        else:
            cmd = self.args[0]

        if cmd == 'replay':
            dome = DomainObjectModificationExtension()
            for package in Session.query(Package):
                dome.notify(package, DomainObjectOperation.changed)
        else:
            print 'Command %s not recognized' % cmd


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
        user = logic.get_action('get_site_user')({'model': model, 'ignore_auth': True}, {})
        context = {'model': model, 'session': model.Session, 'user': user['name']}
        dataset_names = logic.get_action('package_list')(context, {})
        for dataset_name in dataset_names:
            dd = logic.get_action('package_show')(context, {'id': dataset_name})
            if not dd['state'] == 'active':
                continue

            url = h.url_for(controller='package', action='read', id=dd['name'])

            url = urlparse.urljoin(fetch_url, url[1:]) + '.rdf'
            try:
                fname = os.path.join(out_folder, dd['name']) + ".rdf"
                try:
                    r = urllib2.urlopen(url).read()
                except urllib2.HTTPError, e:
                    if e.code == 404:
                        print ('Please install ckanext-dcat and enable the ' +
                               '`dcat` plugin to use the RDF serializations')
                        sys.exit(1)
                with open(fname, 'wb') as f:
                    f.write(r)
            except IOError, ioe:
                sys.stderr.write(str(ioe) + "\n")


class Sysadmin(CkanCommand):
    '''Gives sysadmin rights to a named user

    Usage:
      sysadmin                      - lists sysadmins
      sysadmin list                 - lists sysadmins
      sysadmin add USERNAME         - add a user as a sysadmin
      sysadmin remove USERNAME      - removes user from sysadmins
    '''

    summary = __doc__.split('\n')[0]
    usage = __doc__
    max_args = 2
    min_args = 0

    def command(self):
        self._load_config()
        import ckan.model as model

        cmd = self.args[0] if self.args else None
        if cmd is None or cmd == 'list':
            self.list()
        elif cmd == 'add':
            self.add()
        elif cmd == 'remove':
            self.remove()
        else:
            print 'Command %s not recognized' % cmd

    def list(self):
        import ckan.model as model
        print 'Sysadmins:'
        sysadmins = model.Session.query(model.User).filter_by(sysadmin=True)
        print 'count = %i' % sysadmins.count()
        for sysadmin in sysadmins:
            print '%s name=%s id=%s' % (sysadmin.__class__.__name__,
                                        sysadmin.name,
                                        sysadmin.id)

    def add(self):
        import ckan.model as model

        if len(self.args) < 2:
            print 'Need name of the user to be made sysadmin.'
            return
        username = self.args[1]

        user = model.User.by_name(unicode(username))
        if not user:
            print 'User "%s" not found' % username
            makeuser = raw_input('Create new user: %s? [y/n]' % username)
            if makeuser == 'y':
                password = UserCmd.password_prompt()
                print('Creating %s user' % username)
                user = model.User(name=unicode(username),
                                  password=password)
            else:
                print 'Exiting ...'
                return

        user.sysadmin = True
        model.Session.add(user)
        model.repo.commit_and_remove()
        print 'Added %s as sysadmin' % username

    def remove(self):
        import ckan.model as model

        if len(self.args) < 2:
            print 'Need name of the user to be made sysadmin.'
            return
        username = self.args[1]

        user = model.User.by_name(unicode(username))
        if not user:
            print 'Error: user "%s" not found!' % username
            return
        user.sysadmin = False
        model.repo.commit_and_remove()


class UserCmd(CkanCommand):
    '''Manage users

    Usage:
      user                            - lists users
      user list                       - lists users
      user USERNAME                   - shows user properties
      user add USERNAME [FIELD1=VALUE1 FIELD2=VALUE2 ...]
                                      - add a user (prompts for password
                                        if not supplied).
                                        Field can be: apikey
                                                      password
                                                      email
      user setpass USERNAME           - set user password (prompts)
      user remove USERNAME            - removes user from users
      user search QUERY               - searches for a user name
    '''
    summary = __doc__.split('\n')[0]
    usage = __doc__
    max_args = None
    min_args = 0

    def command(self):
        self._load_config()
        import ckan.model as model

        if not self.args:
            self.list()
        else:
            cmd = self.args[0]
            if cmd == 'add':
                self.add()
            elif cmd == 'remove':
                self.remove()
            elif cmd == 'search':
                self.search()
            elif cmd == 'setpass':
                self.setpass()
            elif cmd == 'list':
                self.list()
            else:
                self.show()

    def get_user_str(self, user):
        user_str = 'name=%s' % user.name
        if user.name != user.display_name:
            user_str += ' display=%s' % user.display_name
        return user_str

    def list(self):
        import ckan.model as model
        print 'Users:'
        users = model.Session.query(model.User).filter_by(state='active')
        print 'count = %i' % users.count()
        for user in users:
            print self.get_user_str(user)

    def show(self):
        import ckan.model as model

        username = self.args[0]
        user = model.User.get(unicode(username))
        print 'User: \n', user

    def setpass(self):
        import ckan.model as model

        if len(self.args) < 2:
            print 'Need name of the user.'
            return
        username = self.args[1]
        user = model.User.get(username)
        print('Editing user: %r' % user.name)

        password = self.password_prompt()
        user.password = password
        model.repo.commit_and_remove()
        print 'Done'

    def search(self):
        import ckan.model as model

        if len(self.args) < 2:
            print 'Need user name query string.'
            return
        query_str = self.args[1]

        query = model.User.search(query_str)
        print '%i users matching %r:' % (query.count(), query_str)
        for user in query.all():
            print self.get_user_str(user)

    @classmethod
    def password_prompt(cls):
        import getpass
        password1 = None
        while not password1:
            password1 = getpass.getpass('Password: ')
        password2 = getpass.getpass('Confirm password: ')
        if password1 != password2:
            print 'Passwords do not match'
            sys.exit(1)
        return password1

    def add(self):
        import ckan.model as model

        if len(self.args) < 2:
            print 'Need name of the user.'
            sys.exit(1)
        username = self.args[1]

        # parse args into data_dict
        data_dict = {'name': username}
        for arg in self.args[2:]:
            try:
                field, value = arg.split('=', 1)
                data_dict[field] = value
            except ValueError:
                raise ValueError('Could not parse arg: %r (expected "<option>=<value>)"' % arg)

        if 'password' not in data_dict:
            data_dict['password'] = self.password_prompt()

        if 'fullname' in data_dict:
            data_dict['fullname'] = data_dict['fullname'].decode(sys.getfilesystemencoding())

        print('Creating user: %r' % username)

        try:
            import ckan.logic as logic
            site_user = logic.get_action('get_site_user')({'model': model, 'ignore_auth': True}, {})
            context = {
                'model': model,
                'session': model.Session,
                'ignore_auth': True,
                'user': site_user['name'],
            }
            user_dict = logic.get_action('user_create')(context, data_dict)
            pprint(user_dict)
        except logic.ValidationError, e:
            print e
            sys.exit(1)

    def remove(self):
        import ckan.model as model

        if len(self.args) < 2:
            print 'Need name of the user.'
            return
        username = self.args[1]

        user = model.User.by_name(unicode(username))
        if not user:
            print 'Error: user "%s" not found!' % username
            return
        user.delete()
        model.repo.commit_and_remove()
        print('Deleted user: %s' % username)


class DatasetCmd(CkanCommand):
    '''Manage datasets

    Usage:
      dataset DATASET_NAME|ID            - shows dataset properties
      dataset show DATASET_NAME|ID       - shows dataset properties
      dataset list                       - lists datasets
      dataset delete [DATASET_NAME|ID]   - changes dataset state to 'deleted'
      dataset purge [DATASET_NAME|ID]    - removes dataset from db entirely
    '''
    summary = __doc__.split('\n')[0]
    usage = __doc__
    max_args = 3
    min_args = 0

    def command(self):
        self._load_config()
        import ckan.model as model

        if not self.args:
            print self.usage
        else:
            cmd = self.args[0]
            if cmd == 'delete':
                self.delete(self.args[1])
            elif cmd == 'purge':
                self.purge(self.args[1])
            elif cmd == 'list':
                self.list()
            elif cmd == 'show':
                self.show(self.args[1])
            else:
                self.show(self.args[0])

    def list(self):
        import ckan.model as model
        print 'Datasets:'
        datasets = model.Session.query(model.Package)
        print 'count = %i' % datasets.count()
        for dataset in datasets:
            state = ('(%s)' % dataset.state) if dataset.state != 'active' else ''
            print '%s %s %s' % (dataset.id, dataset.name, state)

    def _get_dataset(self, dataset_ref):
        import ckan.model as model
        dataset = model.Package.get(unicode(dataset_ref))
        assert dataset, 'Could not find dataset matching reference: %r' % dataset_ref
        return dataset

    def show(self, dataset_ref):
        import pprint
        dataset = self._get_dataset(dataset_ref)
        pprint.pprint(dataset.as_dict())

    def delete(self, dataset_ref):
        import ckan.model as model
        dataset = self._get_dataset(dataset_ref)
        old_state = dataset.state

        rev = model.repo.new_revision()
        dataset.delete()
        model.repo.commit_and_remove()
        dataset = self._get_dataset(dataset_ref)
        print '%s %s -> %s' % (dataset.name, old_state, dataset.state)

    def purge(self, dataset_ref):
        import ckan.model as model
        dataset = self._get_dataset(dataset_ref)
        name = dataset.name

        rev = model.repo.new_revision()
        dataset.purge()
        model.repo.commit_and_remove()
        print '%s purged' % name


class Celery(CkanCommand):
    '''Celery daemon

    Usage:
        celeryd <run>            - run the celery daemon
        celeryd run concurrency  - run the celery daemon with
                                   argument 'concurrency'
        celeryd view             - view all tasks in the queue
        celeryd clean            - delete all tasks in the queue
    '''
    min_args = 0
    max_args = 2
    summary = __doc__.split('\n')[0]
    usage = __doc__

    def command(self):
        if not self.args:
            self.run_()
        else:
            cmd = self.args[0]
            if cmd == 'run':
                self.run_()
            elif cmd == 'view':
                self.view()
            elif cmd == 'clean':
                self.clean()
            else:
                print 'Command %s not recognized' % cmd
                sys.exit(1)

    def run_(self):
        default_ini = os.path.join(os.getcwd(), 'development.ini')

        if self.options.config:
            os.environ['CKAN_CONFIG'] = os.path.abspath(self.options.config)
        elif os.path.isfile(default_ini):
            os.environ['CKAN_CONFIG'] = default_ini
        else:
            print 'No .ini specified and none was found in current directory'
            sys.exit(1)

        from ckan.lib.celery_app import celery
        celery_args = []
        if len(self.args) == 2 and self.args[1] == 'concurrency':
            celery_args.append['--concurrency=1']
        celery.worker_main(argv=['celeryd', '--loglevel=INFO'] + celery_args)

    def view(self):
        self._load_config()
        import ckan.model as model
        from kombu.transport.sqlalchemy.models import Message
        q = model.Session.query(Message)
        q_visible = q.filter_by(visible=True)
        print '%i messages (total)' % q.count()
        print '%i visible messages' % q_visible.count()
        for message in q:
            if message.visible:
                print '%i: Visible' % (message.id)
            else:
                print '%i: Invisible Sent:%s' % (message.id, message.sent_at)

    def clean(self):
        self._load_config()
        import ckan.model as model
        query = model.Session.execute("select * from kombu_message")
        tasks_initially = query.rowcount
        if not tasks_initially:
            print 'No tasks to delete'
            sys.exit(0)
        query = model.Session.execute("delete from kombu_message")
        query = model.Session.execute("select * from kombu_message")
        tasks_afterwards = query.rowcount
        print '%i of %i tasks deleted' % (tasks_initially - tasks_afterwards,
                                          tasks_initially)
        if tasks_afterwards:
            print 'ERROR: Failed to delete all tasks'
            sys.exit(1)
        model.repo.commit_and_remove()


class Ratings(CkanCommand):
    '''Manage the ratings stored in the db

    Usage:
      ratings count                 - counts ratings
      ratings clean                 - remove all ratings
      ratings clean-anonymous       - remove only anonymous ratings
    '''

    summary = __doc__.split('\n')[0]
    usage = __doc__
    max_args = 1
    min_args = 1

    def command(self):
        self._load_config()
        import ckan.model as model

        cmd = self.args[0]
        if cmd == 'count':
            self.count()
        elif cmd == 'clean':
            self.clean()
        elif cmd == 'clean-anonymous':
            self.clean(user_ratings=False)
        else:
            print 'Command %s not recognized' % cmd

    def count(self):
        import ckan.model as model
        q = model.Session.query(model.Rating)
        print "%i ratings" % q.count()
        q = q.filter(model.Rating.user_id is None)
        print "of which %i are anonymous ratings" % q.count()

    def clean(self, user_ratings=True):
        import ckan.model as model
        q = model.Session.query(model.Rating)
        print "%i ratings" % q.count()
        if not user_ratings:
            q = q.filter(model.Rating.user_id is None)
            print "of which %i are anonymous ratings" % q.count()
        ratings = q.all()
        for rating in ratings:
            rating.purge()
        model.repo.commit_and_remove()


## Used by the Tracking class
_ViewCount = collections.namedtuple("ViewCount", "id name count")


class Tracking(CkanCommand):
    '''Update tracking statistics

    Usage:
      tracking update [start_date]       - update tracking stats
      tracking export FILE [start_date]  - export tracking stats to a csv file
    '''

    summary = __doc__.split('\n')[0]
    usage = __doc__
    max_args = 3
    min_args = 1

    def command(self):
        self._load_config()
        import ckan.model as model
        engine = model.meta.engine

        cmd = self.args[0]
        if cmd == 'update':
            start_date = self.args[1] if len(self.args) > 1 else None
            self.update_all(engine, start_date)
        elif cmd == 'export':
            if len(self.args) <= 1:
                print self.__class__.__doc__
                sys.exit(1)
            output_file = self.args[1]
            start_date = self.args[2] if len(self.args) > 2 else None
            self.update_all(engine, start_date)
            self.export_tracking(engine, output_file)
        else:
            print self.__class__.__doc__
            sys.exit(1)

    def update_all(self, engine, start_date=None):
        if start_date:
            start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d')
        else:
            # No date given. See when we last have data for and get data
            # from 2 days before then in case new data is available.
            # If no date here then use 2011-01-01 as the start date
            sql = '''SELECT tracking_date from tracking_summary
                     ORDER BY tracking_date DESC LIMIT 1;'''
            result = engine.execute(sql).fetchall()
            if result:
                start_date = result[0]['tracking_date']
                start_date += datetime.timedelta(-2)
                # convert date to datetime
                combine = datetime.datetime.combine
                start_date = combine(start_date, datetime.time(0))
            else:
                start_date = datetime.datetime(2011, 1, 1)
        start_date_solrsync = start_date
        end_date = datetime.datetime.now()

        while start_date < end_date:
            stop_date = start_date + datetime.timedelta(1)
            self.update_tracking(engine, start_date)
            print 'tracking updated for %s' % start_date
            start_date = stop_date

        self.update_tracking_solr(engine, start_date_solrsync)

    def _total_views(self, engine):
        sql = '''
            SELECT p.id,
                   p.name,
                   COALESCE(SUM(s.count), 0) AS total_views
               FROM package AS p
               LEFT OUTER JOIN tracking_summary AS s ON s.package_id = p.id
               GROUP BY p.id, p.name
               ORDER BY total_views DESC
        '''
        return [_ViewCount(*t) for t in engine.execute(sql).fetchall()]

    def _recent_views(self, engine, measure_from):
        sql = '''
            SELECT p.id,
                   p.name,
                   COALESCE(SUM(s.count), 0) AS total_views
               FROM package AS p
               LEFT OUTER JOIN tracking_summary AS s ON s.package_id = p.id
               WHERE s.tracking_date >= %(measure_from)s
               GROUP BY p.id, p.name
               ORDER BY total_views DESC
        '''
        return [_ViewCount(*t) for t in engine.execute(sql, measure_from=str(measure_from)).fetchall()]

    def export_tracking(self, engine, output_filename):
        '''Write tracking summary to a csv file.'''
        HEADINGS = [
            "dataset id",
            "dataset name",
            "total views",
            "recent views (last 2 weeks)",
        ]

        measure_from = datetime.date.today() - datetime.timedelta(days=14)
        recent_views = self._recent_views(engine, measure_from)
        total_views = self._total_views(engine)

        with open(output_filename, 'w') as fh:
            f_out = csv.writer(fh)
            f_out.writerow(HEADINGS)
            recent_views_for_id = dict((r.id, r.count) for r in recent_views)
            f_out.writerows([(r.id,
                              r.name,
                              r.count,
                              recent_views_for_id.get(r.id, 0))
                              for r in total_views])

    def update_tracking(self, engine, summary_date):
        PACKAGE_URL = '/dataset/'
        # clear out existing data before adding new
        sql = '''DELETE FROM tracking_summary
                 WHERE tracking_date='%s'; ''' % summary_date
        engine.execute(sql)

        sql = '''SELECT DISTINCT url, user_key,
                     CAST(access_timestamp AS Date) AS tracking_date,
                     tracking_type INTO tracking_tmp
                 FROM tracking_raw
                 WHERE CAST(access_timestamp as Date)='%s';

                 INSERT INTO tracking_summary
                   (url, count, tracking_date, tracking_type)
                 SELECT url, count(user_key), tracking_date, tracking_type
                 FROM tracking_tmp
                 GROUP BY url, tracking_date, tracking_type;

                 DROP TABLE tracking_tmp;
                 COMMIT;''' % summary_date
        engine.execute(sql)

        # get ids for dataset urls
        sql = '''UPDATE tracking_summary t
                 SET package_id = COALESCE(
                        (SELECT id FROM package p
                        WHERE p.name = regexp_replace(' ' || t.url, '^[ ]{1}(/\w{2}){0,1}' || %s, ''))
                     ,'~~not~found~~')
                 WHERE t.package_id IS NULL
                 AND tracking_type = 'page';'''
        engine.execute(sql, PACKAGE_URL)

        # update summary totals for resources
        sql = '''UPDATE tracking_summary t1
                 SET running_total = (
                    SELECT sum(count)
                    FROM tracking_summary t2
                    WHERE t1.url = t2.url
                    AND t2.tracking_date <= t1.tracking_date
                 )
                 ,recent_views = (
                    SELECT sum(count)
                    FROM tracking_summary t2
                    WHERE t1.url = t2.url
                    AND t2.tracking_date <= t1.tracking_date AND t2.tracking_date >= t1.tracking_date - 14
                 )
                 WHERE t1.running_total = 0 AND tracking_type = 'resource';'''
        engine.execute(sql)

        # update summary totals for pages
        sql = '''UPDATE tracking_summary t1
                 SET running_total = (
                    SELECT sum(count)
                    FROM tracking_summary t2
                    WHERE t1.package_id = t2.package_id
                    AND t2.tracking_date <= t1.tracking_date
                 )
                 ,recent_views = (
                    SELECT sum(count)
                    FROM tracking_summary t2
                    WHERE t1.package_id = t2.package_id
                    AND t2.tracking_date <= t1.tracking_date AND t2.tracking_date >= t1.tracking_date - 14
                 )
                 WHERE t1.running_total = 0 AND tracking_type = 'page'
                 AND t1.package_id IS NOT NULL
                 AND t1.package_id != '~~not~found~~';'''
        engine.execute(sql)

    def update_tracking_solr(self, engine, start_date):
        sql = '''SELECT package_id FROM tracking_summary
                where package_id!='~~not~found~~'
                and tracking_date >= %s;'''
        results = engine.execute(sql, start_date)

        package_ids = set()
        for row in results:
            package_ids.add(row['package_id'])

        total = len(package_ids)
        not_found = 0
        print '%i package index%s to be rebuilt starting from %s' % (total, '' if total < 2 else 'es', start_date)

        from ckan.lib.search import rebuild
        for package_id in package_ids:
            try:
                rebuild(package_id)
            except logic.NotFound:
                print "Error: package %s not found." % (package_id)
                not_found += 1
            except KeyboardInterrupt:
                print "Stopped."
                return
            except:
                raise
        print 'search index rebuilding done.' + (' %i not found.' % (not_found) if not_found else "")


class PluginInfo(CkanCommand):
    '''Provide info on installed plugins.
    '''

    summary = __doc__.split('\n')[0]
    usage = __doc__
    max_args = 0
    min_args = 0

    def command(self):
        self.get_info()

    def get_info(self):
        ''' print info about current plugins from the .ini file'''
        import ckan.plugins as p
        self._load_config()
        interfaces = {}
        plugins = {}
        for name in dir(p):
            item = getattr(p, name)
            try:
                if issubclass(item, p.Interface):
                    interfaces[item] = {'class': item}
            except TypeError:
                pass

        for interface in interfaces:
            for plugin in p.PluginImplementations(interface):
                name = plugin.name
                if name not in plugins:
                    plugins[name] = {'doc': plugin.__doc__,
                                     'class': plugin,
                                     'implements': []}
                plugins[name]['implements'].append(interface.__name__)

        for plugin in plugins:
            p = plugins[plugin]
            print plugin + ':'
            print '-' * (len(plugin) + 1)
            if p['doc']:
                print p['doc']
            print 'Implements:'
            for i in p['implements']:
                extra = None
                if i == 'ITemplateHelpers':
                    extra = self.template_helpers(p['class'])
                if i == 'IActions':
                    extra = self.actions(p['class'])
                print '    %s' % i
                if extra:
                    print extra
            print

    def actions(self, cls):
        ''' Return readable action function info. '''
        actions = cls.get_actions()
        return self.function_info(actions)

    def template_helpers(self, cls):
        ''' Return readable helper function info. '''
        helpers = cls.get_helpers()
        return self.function_info(helpers)

    def function_info(self, functions):
        ''' Take a dict of functions and output readable info '''
        import inspect
        output = []
        for function_name in functions:
            fn = functions[function_name]
            args_info = inspect.getargspec(fn)
            params = args_info.args
            num_params = len(params)
            if args_info.varargs:
                params.append('*' + args_info.varargs)
            if args_info.keywords:
                params.append('**' + args_info.keywords)
            if args_info.defaults:
                offset = num_params - len(args_info.defaults)
                for i, v in enumerate(args_info.defaults):
                    params[i + offset] = params[i + offset] + '=' + repr(v)
            # is this a classmethod if so remove the first parameter
            if inspect.ismethod(fn) and inspect.isclass(fn.__self__):
                params = params[1:]
            params = ', '.join(params)
            output.append('        %s(%s)' % (function_name, params))
            # doc string
            if fn.__doc__:
                bits = fn.__doc__.split('\n')
                for bit in bits:
                    output.append('            %s' % bit)
        return ('\n').join(output)


class CreateTestDataCommand(CkanCommand):
    '''Create test data in the database.
    Tests can also delete the created objects easily with the delete() method.

    create-test-data              - annakarenina and warandpeace
    create-test-data search       - realistic data to test search
    create-test-data gov          - government style data
    create-test-data family       - package relationships data
    create-test-data user         - create a user 'tester' with api key 'tester'
    create-test-data translations - annakarenina, warandpeace, and some test
                                    translations of terms
    create-test-data vocabs       - annakerenina, warandpeace, and some test
                                    vocabularies
    create-test-data hierarchy    - hierarchy of groups
    '''
    summary = __doc__.split('\n')[0]
    usage = __doc__
    max_args = 1
    min_args = 0

    def command(self):
        self._load_config()
        self._setup_app()
        from ckan import plugins
        from create_test_data import CreateTestData

        if self.args:
            cmd = self.args[0]
        else:
            cmd = 'basic'
        if self.verbose:
            print 'Creating %s test data' % cmd
        if cmd == 'basic':
            CreateTestData.create_basic_test_data()
        elif cmd == 'user':
            CreateTestData.create_test_user()
            print 'Created user %r with password %r and apikey %r' % ('tester',
                                                                      'tester', 'tester')
        elif cmd == 'search':
            CreateTestData.create_search_test_data()
        elif cmd == 'gov':
            CreateTestData.create_gov_test_data()
        elif cmd == 'family':
            CreateTestData.create_family_test_data()
        elif cmd == 'translations':
            CreateTestData.create_translations_test_data()
        elif cmd == 'vocabs':
            CreateTestData.create_vocabs_test_data()
        elif cmd == 'hierarchy':
            CreateTestData.create_group_hierarchy_test_data()
        else:
            print 'Command %s not recognized' % cmd
            raise NotImplementedError
        if self.verbose:
            print 'Creating %s test data: Complete!' % cmd


class Profile(CkanCommand):
    '''Code speed profiler
    Provide a ckan url and it will make the request and record
    how long each function call took in a file that can be read
    by runsnakerun.

    Usage:
       profile URL

    e.g. profile /data/search

    The result is saved in profile.data.search
    To view the profile in runsnakerun:
       runsnakerun ckan.data.search.profile

    You may need to install python module: cProfile
    '''
    summary = __doc__.split('\n')[0]
    usage = __doc__
    max_args = 1
    min_args = 1

    def _load_config_into_test_app(self):
        from paste.deploy import loadapp
        import paste.fixture
        if not self.options.config:
            msg = 'No config file supplied'
            raise self.BadCommand(msg)
        self.filename = os.path.abspath(self.options.config)
        if not os.path.exists(self.filename):
            raise AssertionError('Config filename %r does not exist.' % self.filename)
        fileConfig(self.filename)

        wsgiapp = loadapp('config:' + self.filename)
        self.app = paste.fixture.TestApp(wsgiapp)

    def command(self):
        self._load_config_into_test_app()

        import paste.fixture
        import cProfile
        import re

        url = self.args[0]

        def profile_url(url):
            try:
                res = self.app.get(url, status=[200], extra_environ={'REMOTE_USER': 'visitor'})
            except paste.fixture.AppError:
                print 'App error: ', url.strip()
            except KeyboardInterrupt:
                raise
            except:
                import traceback
                traceback.print_exc()
                print 'Unknown error: ', url.strip()

        output_filename = 'ckan%s.profile' % re.sub('[/?]', '.', url.replace('/', '.'))
        profile_command = "profile_url('%s')" % url
        cProfile.runctx(profile_command, globals(), locals(), filename=output_filename)
        print 'Written profile to: %s' % output_filename


class CreateColorSchemeCommand(CkanCommand):
    '''Create or remove a color scheme.

    After running this, you'll need to regenerate the css files. See paster's less command for details.

    color               - creates a random color scheme
    color clear         - clears any color scheme
    color <'HEX'>       - uses as base color eg '#ff00ff' must be quoted.
    color <VALUE>       - a float between 0.0 and 1.0 used as base hue
    color <COLOR_NAME>  - html color name used for base color eg lightblue
    '''

    summary = __doc__.split('\n')[0]
    usage = __doc__
    max_args = 1
    min_args = 0

    rules = [
        '@layoutLinkColor',
        '@mastheadBackgroundColor',
        '@btnPrimaryBackground',
        '@btnPrimaryBackgroundHighlight',
    ]

    # list of predefined colors
    color_list = {
        'aliceblue': '#f0fff8',
        'antiquewhite': '#faebd7',
        'aqua': '#00ffff',
        'aquamarine': '#7fffd4',
        'azure': '#f0ffff',
        'beige': '#f5f5dc',
        'bisque': '#ffe4c4',
        'black': '#000000',
        'blanchedalmond': '#ffebcd',
        'blue': '#0000ff',
        'blueviolet': '#8a2be2',
        'brown': '#a52a2a',
        'burlywood': '#deb887',
        'cadetblue': '#5f9ea0',
        'chartreuse': '#7fff00',
        'chocolate': '#d2691e',
        'coral': '#ff7f50',
        'cornflowerblue': '#6495ed',
        'cornsilk': '#fff8dc',
        'crimson': '#dc143c',
        'cyan': '#00ffff',
        'darkblue': '#00008b',
        'darkcyan': '#008b8b',
        'darkgoldenrod': '#b8860b',
        'darkgray': '#a9a9a9',
        'darkgrey': '#a9a9a9',
        'darkgreen': '#006400',
        'darkkhaki': '#bdb76b',
        'darkmagenta': '#8b008b',
        'darkolivegreen': '#556b2f',
        'darkorange': '#ff8c00',
        'darkorchid': '#9932cc',
        'darkred': '#8b0000',
        'darksalmon': '#e9967a',
        'darkseagreen': '#8fbc8f',
        'darkslateblue': '#483d8b',
        'darkslategray': '#2f4f4f',
        'darkslategrey': '#2f4f4f',
        'darkturquoise': '#00ced1',
        'darkviolet': '#9400d3',
        'deeppink': '#ff1493',
        'deepskyblue': '#00bfff',
        'dimgray': '#696969',
        'dimgrey': '#696969',
        'dodgerblue': '#1e90ff',
        'firebrick': '#b22222',
        'floralwhite': '#fffaf0',
        'forestgreen': '#228b22',
        'fuchsia': '#ff00ff',
        'gainsboro': '#dcdcdc',
        'ghostwhite': '#f8f8ff',
        'gold': '#ffd700',
        'goldenrod': '#daa520',
        'gray': '#808080',
        'grey': '#808080',
        'green': '#008000',
        'greenyellow': '#adff2f',
        'honeydew': '#f0fff0',
        'hotpink': '#ff69b4',
        'indianred ': '#cd5c5c',
        'indigo ': '#4b0082',
        'ivory': '#fffff0',
        'khaki': '#f0e68c',
        'lavender': '#e6e6fa',
        'lavenderblush': '#fff0f5',
        'lawngreen': '#7cfc00',
        'lemonchiffon': '#fffacd',
        'lightblue': '#add8e6',
        'lightcoral': '#f08080',
        'lightcyan': '#e0ffff',
        'lightgoldenrodyellow': '#fafad2',
        'lightgray': '#d3d3d3',
        'lightgrey': '#d3d3d3',
        'lightgreen': '#90ee90',
        'lightpink': '#ffb6c1',
        'lightsalmon': '#ffa07a',
        'lightseagreen': '#20b2aa',
        'lightskyblue': '#87cefa',
        'lightslategray': '#778899',
        'lightslategrey': '#778899',
        'lightsteelblue': '#b0c4de',
        'lightyellow': '#ffffe0',
        'lime': '#00ff00',
        'limegreen': '#32cd32',
        'linen': '#faf0e6',
        'magenta': '#ff00ff',
        'maroon': '#800000',
        'mediumaquamarine': '#66cdaa',
        'mediumblue': '#0000cd',
        'mediumorchid': '#ba55d3',
        'mediumpurple': '#9370d8',
        'mediumseagreen': '#3cb371',
        'mediumslateblue': '#7b68ee',
        'mediumspringgreen': '#00fa9a',
        'mediumturquoise': '#48d1cc',
        'mediumvioletred': '#c71585',
        'midnightblue': '#191970',
        'mintcream': '#f5fffa',
        'mistyrose': '#ffe4e1',
        'moccasin': '#ffe4b5',
        'navajowhite': '#ffdead',
        'navy': '#000080',
        'oldlace': '#fdf5e6',
        'olive': '#808000',
        'olivedrab': '#6b8e23',
        'orange': '#ffa500',
        'orangered': '#ff4500',
        'orchid': '#da70d6',
        'palegoldenrod': '#eee8aa',
        'palegreen': '#98fb98',
        'paleturquoise': '#afeeee',
        'palevioletred': '#d87093',
        'papayawhip': '#ffefd5',
        'peachpuff': '#ffdab9',
        'peru': '#cd853f',
        'pink': '#ffc0cb',
        'plum': '#dda0dd',
        'powderblue': '#b0e0e6',
        'purple': '#800080',
        'red': '#ff0000',
        'rosybrown': '#bc8f8f',
        'royalblue': '#4169e1',
        'saddlebrown': '#8b4513',
        'salmon': '#fa8072',
        'sandybrown': '#f4a460',
        'seagreen': '#2e8b57',
        'seashell': '#fff5ee',
        'sienna': '#a0522d',
        'silver': '#c0c0c0',
        'skyblue': '#87ceeb',
        'slateblue': '#6a5acd',
        'slategray': '#708090',
        'slategrey': '#708090',
        'snow': '#fffafa',
        'springgreen': '#00ff7f',
        'steelblue': '#4682b4',
        'tan': '#d2b48c',
        'teal': '#008080',
        'thistle': '#d8bfd8',
        'tomato': '#ff6347',
        'turquoise': '#40e0d0',
        'violet': '#ee82ee',
        'wheat': '#f5deb3',
        'white': '#ffffff',
        'whitesmoke': '#f5f5f5',
        'yellow': '#ffff00',
        'yellowgreen': '#9acd32',
    }

    def create_colors(self, hue, num_colors=5, saturation=None, lightness=None):
        if saturation is None:
            saturation = 0.9
        if lightness is None:
            lightness = 40
        else:
            lightness *= 100

        import math
        saturation -= math.trunc(saturation)

        print hue, saturation
        import colorsys
        ''' Create n related colours '''
        colors = []
        for i in xrange(num_colors):
            ix = i * (1.0/num_colors)
            _lightness = (lightness + (ix * 40))/100.
            if _lightness > 1.0:
                _lightness = 1.0
            color = colorsys.hls_to_rgb(hue, _lightness, saturation)
            hex_color = '#'
            for part in color:
                hex_color += '%02x' % int(part * 255)
            # check and remove any bad values
            if not re.match('^\#[0-9a-f]{6}$', hex_color):
                hex_color = '#FFFFFF'
            colors.append(hex_color)
        return colors

    def command(self):

        hue = None
        saturation = None
        lightness = None

        path = os.path.dirname(__file__)
        path = os.path.join(path, '..', 'public', 'base', 'less', 'custom.less')

        if self.args:
            arg = self.args[0]
            rgb = None
            if arg == 'clear':
                os.remove(path)
                print 'custom colors removed.'
            elif arg.startswith('#'):
                color = arg[1:]
                if len(color) == 3:
                    rgb = [int(x, 16) * 16 for x in color]
                elif len(color) == 6:
                    rgb = [int(x, 16) for x in re.findall('..', color)]
                else:
                    print 'ERROR: invalid color'
            elif arg.lower() in self.color_list:
                color = self.color_list[arg.lower()][1:]
                rgb = [int(x, 16) for x in re.findall('..', color)]
            else:
                try:
                    hue = float(self.args[0])
                except ValueError:
                    print 'ERROR argument `%s` not recognised' % arg
            if rgb:
                import colorsys
                hue, lightness, saturation = colorsys.rgb_to_hls(*rgb)
                lightness = lightness / 340
                # deal with greys
                if not (hue == 0.0 and saturation == 0.0):
                    saturation = None
        else:
            import random
            hue = random.random()
        if hue is not None:
            f = open(path, 'w')
            colors = self.create_colors(hue, saturation=saturation, lightness=lightness)
            for i in xrange(len(self.rules)):
                f.write('%s: %s;\n' % (self.rules[i], colors[i]))
                print '%s: %s;\n' % (self.rules[i], colors[i])
            f.close
            print 'Color scheme has been created.'
        print 'Make sure less is run for changes to take effect.'


class TranslationsCommand(CkanCommand):
    '''Translation helper functions

    trans js      - generate the javascript translations
    trans mangle  - mangle the zh_TW translations for testing
    '''

    summary = __doc__.split('\n')[0]
    usage = __doc__
    max_args = 1
    min_args = 1

    def command(self):
        self._load_config()
        from pylons import config
        self.ckan_path = os.path.join(os.path.dirname(__file__), '..')
        i18n_path = os.path.join(self.ckan_path, 'i18n')
        self.i18n_path = config.get('ckan.i18n_directory', i18n_path)
        command = self.args[0]
        if command == 'mangle':
            self.mangle_po()
        elif command == 'js':
            self.build_js_translations()
        else:
            print 'command not recognised'

    def po2dict(self, po, lang):
        '''Convert po object to dictionary data structure (ready for JSON).

        This function is from pojson
        https://bitbucket.org/obviel/pojson

Copyright (c) 2010, Fanstatic Developers
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of the <organization> nor the
      names of its contributors may be used to endorse or promote products
      derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL FANSTATIC DEVELOPERS BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
'''
        result = {}

        result[''] = {}
        result['']['plural-forms'] = po.metadata['Plural-Forms']
        result['']['lang'] = lang
        result['']['domain'] = 'ckan'

        for entry in po:
            if entry.obsolete:
                continue
            # check if used in js file we only include these
            occurrences = entry.occurrences
            js_use = False
            for occurrence in occurrences:
                if occurrence[0].endswith('.js'):
                    js_use = True
                    continue
            if not js_use:
                continue
            if entry.msgstr:
                result[entry.msgid] = [None, entry.msgstr]
            elif entry.msgstr_plural:
                plural = [entry.msgid_plural]
                result[entry.msgid] = plural
                ordered_plural = sorted(entry.msgstr_plural.items())
                for order, msgstr in ordered_plural:
                    plural.append(msgstr)
        return result

    def build_js_translations(self):
        import polib
        import simplejson as json

        def create_js(source, lang):
            print 'Generating', lang
            po = polib.pofile(source)
            data = self.po2dict(po, lang)
            data = json.dumps(data, sort_keys=True,
                              ensure_ascii=False, indent=2 * ' ')
            out_dir = os.path.abspath(os.path.join(self.ckan_path, 'public',
                                                   'base', 'i18n'))
            out_file = open(os.path.join(out_dir, '%s.js' % lang), 'w')
            out_file.write(data.encode('utf-8'))
            out_file.close()

        for l in os.listdir(self.i18n_path):
            if os.path.isdir(os.path.join(self.i18n_path, l)):
                f = os.path.join(self.i18n_path, l, 'LC_MESSAGES', 'ckan.po')
                create_js(f, l)
        print 'Completed generating JavaScript translations'

    def mangle_po(self):
        ''' This will mangle the zh_TW translations for translation coverage
        testing.

        NOTE: This will destroy the current translations fot zh_TW
        '''
        import polib
        pot_path = os.path.join(self.i18n_path, 'ckan.pot')
        po = polib.pofile(pot_path)
        # we don't want to mangle the following items in strings
        # %(...)s  %s %0.3f %1$s %2$0.3f [1:...] {...} etc

        # sprintf bit after %
        spf_reg_ex = "\+?(0|'.)?-?\d*(.\d*)?[\%bcdeufosxX]"

        extract_reg_ex = '(\%\([^\)]*\)' + spf_reg_ex + \
                         '|\[\d*\:[^\]]*\]' + \
                         '|\{[^\}]*\}' + \
                         '|<[^>}]*>' + \
                         '|\%((\d)*\$)?' + spf_reg_ex + ')'

        for entry in po:
            msg = entry.msgid.encode('utf-8')
            matches = re.finditer(extract_reg_ex, msg)
            length = len(msg)
            position = 0
            translation = u''
            for match in matches:
                translation += '-' * (match.start() - position)
                position = match.end()
                translation += match.group(0)
            translation += '-' * (length - position)
            entry.msgstr = translation
        out_dir = os.path.join(self.i18n_path, 'zh_TW', 'LC_MESSAGES')
        try:
            os.makedirs(out_dir)
        except OSError:
            pass
        po.metadata['Plural-Forms'] = "nplurals=1; plural=0\n"
        out_po = os.path.join(out_dir, 'ckan.po')
        out_mo = os.path.join(out_dir, 'ckan.mo')
        po.save(out_po)
        po.save_as_mofile(out_mo)
        print 'zh_TW has been mangled'


class MinifyCommand(CkanCommand):
    '''Create minified versions of the given Javascript and CSS files.

    Usage:

        paster minify [--clean] PATH

    for example:

        paster minify ckan/public/base
        paster minify ckan/public/base/css/*.css
        paster minify ckan/public/base/css/red.css

    if the --clean option is provided any minified files will be removed.

    '''
    summary = __doc__.split('\n')[0]
    usage = __doc__
    min_args = 1

    exclude_dirs = ['vendor']

    def __init__(self, name):

        super(MinifyCommand, self).__init__(name)

        self.parser.add_option('--clean', dest='clean',
                               action='store_true', default=False,
                               help='remove any minified files in the path')

    def command(self):
        clean = getattr(self.options, 'clean', False)
        self._load_config()
        for base_path in self.args:
            if os.path.isfile(base_path):
                if clean:
                    self.clear_minifyed(base_path)
                else:
                    self.minify_file(base_path)
            elif os.path.isdir(base_path):
                for root, dirs, files in os.walk(base_path):
                    dirs[:] = [d for d in dirs if not d in self.exclude_dirs]
                    for filename in files:
                        path = os.path.join(root, filename)
                        if clean:
                            self.clear_minifyed(path)
                        else:
                            self.minify_file(path)
            else:
                # Path is neither a file or a dir?
                continue

    def clear_minifyed(self, path):
        path_only, extension = os.path.splitext(path)

        if extension not in ('.css', '.js'):
            # This is not a js or css file.
            return

        if path_only.endswith('.min'):
            print 'removing %s' % path
            os.remove(path)

    def minify_file(self, path):
        '''Create the minified version of the given file.

        If the file is not a .js or .css file (e.g. it's a .min.js or .min.css
        file, or it's some other type of file entirely) it will not be
        minifed.

        :param path: The path to the .js or .css file to minify

        '''
        path_only, extension = os.path.splitext(path)

        if path_only.endswith('.min'):
            # This is already a minified file.
            return

        if extension not in ('.css', '.js'):
            # This is not a js or css file.
            return

        path_min = fanstatic_resources.min_path(path)

        source = open(path, 'r').read()
        f = open(path_min, 'w')
        if path.endswith('.css'):
            f.write(rcssmin.cssmin(source))
        elif path.endswith('.js'):
            f.write(rjsmin.jsmin(source))
        f.close()
        print "Minified file '{0}'".format(path)


class LessCommand(CkanCommand):
    '''Compile all root less documents into their CSS counterparts

    Usage:

        paster less

    '''
    summary = __doc__.split('\n')[0]
    usage = __doc__
    min_args = 0

    def command(self):
        self.less()

    custom_css = {
        'fuchsia': '''
            @layoutLinkColor: #E73892;
            @footerTextColor: mix(#FFF, @layoutLinkColor, 60%);
            @footerLinkColor: @footerTextColor;
            @mastheadBackgroundColor: @layoutLinkColor;
            @btnPrimaryBackground: lighten(@layoutLinkColor, 10%);
            @btnPrimaryBackgroundHighlight: @layoutLinkColor;
            ''',

        'green': '''
            @layoutLinkColor: #2F9B45;
            @footerTextColor: mix(#FFF, @layoutLinkColor, 60%);
            @footerLinkColor: @footerTextColor;
            @mastheadBackgroundColor: @layoutLinkColor;
            @btnPrimaryBackground: lighten(@layoutLinkColor, 10%);
            @btnPrimaryBackgroundHighlight: @layoutLinkColor;
            ''',

        'red': '''
            @layoutLinkColor: #C14531;
            @footerTextColor: mix(#FFF, @layoutLinkColor, 60%);
            @footerLinkColor: @footerTextColor;
            @mastheadBackgroundColor: @layoutLinkColor;
            @btnPrimaryBackground: lighten(@layoutLinkColor, 10%);
            @btnPrimaryBackgroundHighlight: @layoutLinkColor;
            ''',

        'maroon': '''
            @layoutLinkColor: #810606;
            @footerTextColor: mix(#FFF, @layoutLinkColor, 60%);
            @footerLinkColor: @footerTextColor;
            @mastheadBackgroundColor: @layoutLinkColor;
            @btnPrimaryBackground: lighten(@layoutLinkColor, 10%);
            @btnPrimaryBackgroundHighlight: @layoutLinkColor;
            ''',
    }

    def less(self):
        ''' Compile less files '''
        import subprocess
        command = 'npm bin'
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        output = process.communicate()
        directory = output[0].strip()
        less_bin = os.path.join(directory, 'lessc')

        root = os.path.join(os.path.dirname(__file__), '..', 'public', 'base')
        root = os.path.abspath(root)
        custom_less = os.path.join(root, 'less', 'custom.less')
        for color in self.custom_css:
            f = open(custom_less, 'w')
            f.write(self.custom_css[color])
            f.close()
            self.compile_less(root, less_bin, color)
        f = open(custom_less, 'w')
        f.write('// This file is needed in order for ./bin/less to compile in less 1.3.1+\n')
        f.close()
        self.compile_less(root, less_bin, 'main')

    def compile_less(self, root, less_bin, color):
        print 'compile %s.css' % color
        import subprocess
        main_less = os.path.join(root, 'less', 'main.less')
        main_css = os.path.join(root, 'css', '%s.css' % color)

        command = '%s %s %s' % (less_bin, main_less, main_css)

        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        output = process.communicate()


class FrontEndBuildCommand(CkanCommand):
    '''Creates and minifies css and JavaScript files

    Usage:

        paster front-end-build
    '''

    summary = __doc__.split('\n')[0]
    usage = __doc__
    min_args = 0

    def command(self):
        self._load_config()

        # Less css
        cmd = LessCommand('less')
        cmd.command()

        # js translation strings
        cmd = TranslationsCommand('trans')
        cmd.options = self.options
        cmd.args = ('js',)
        cmd.command()

        # minification
        cmd = MinifyCommand('minify')
        cmd.options = self.options
        root = os.path.join(os.path.dirname(__file__), '..', 'public', 'base')
        root = os.path.abspath(root)
        ckanext = os.path.join(os.path.dirname(__file__), '..', '..', 'ckanext')
        ckanext = os.path.abspath(ckanext)
        cmd.args = (root, ckanext)
        cmd.command()


class ViewsCommand(CkanCommand):
    '''Manage resource views.

    Usage:

        paster views create [options] [type1] [type2] ...

            Create views on relevant resources. You can optionally provide
            specific view types (eg `recline_view`, `image_view`). If no types
            are provided, the default ones will be used. These are generally
            the ones defined in the `ckan.views.default_views` config option.
            Note that on either case, plugins must be loaded (ie added to
            `ckan.plugins`), otherwise the command will stop.

        paster views clear [options] [type1] [type2] ...

            Permanently delete all views or the ones with the provided types.

        paster views clean

            Permanently delete views for all types no longer present in the
            `ckan.plugins` configuration option.

    '''

    summary = __doc__.split('\n')[0]
    usage = __doc__
    min_args = 1

    def __init__(self, name):

        super(ViewsCommand, self).__init__(name)

        self.parser.add_option('-y', '--yes', dest='assume_yes',
                               action='store_true',
                               default=False,
                               help='''Automatic yes to prompts. Assume "yes"
as answer to all prompts and run non-interactively''')

        self.parser.add_option('-d', '--dataset', dest='dataset_id',
                               action='append',
                               help='''Create views on a particular dataset.
You can use the dataset id or name, and it can be defined multiple times.''')

        self.parser.add_option('--no-default-filters',
                               dest='no_default_filters',
                               action='store_true',
                               default=False,
                               help='''Do not add default filters for relevant
resource formats for the view types provided. Note that filters are not added
by default anyway if an unsupported view type is provided or when using the
`-s` or `-d` options.''')

        self.parser.add_option('-s', '--search', dest='search_params',
                               action='store',
                               default=False,
                               help='''Extra search parameters that will be
used for getting the datasets to create the resource views on. It must be a
JSON object like the one used by the `package_search` API call. Supported
fields are `q`, `fq` and `fq_list`. Check the documentation for examples.
Not used when using the `-d` option.''')

    def command(self):
        self._load_config()
        if not self.args:
            print self.usage
        elif self.args[0] == 'create':
            view_plugin_types = self.args[1:]
            self.create_views(view_plugin_types)
        elif self.args[0] == 'clear':
            view_plugin_types = self.args[1:]
            self.clear_views(view_plugin_types)
        elif self.args[0] == 'clean':
            self.clean_views()
        else:
            print self.usage

    _page_size = 100

    def _get_view_plugins(self, view_plugin_types,
                          get_datastore_views=False):
        '''
        Returns the view plugins that were succesfully loaded

        Views are provided as a list of ``view_plugin_types``. If no types are
        provided, the default views defined in the ``ckan.views.default_views``
        will be created. Only in this case (when the default view plugins are
        used) the `get_datastore_views` parameter can be used to get also view
        plugins that require data to be in the DataStore.

        If any of the provided plugins could not be loaded (eg it was not added
        to `ckan.plugins`) the command will stop.

        Returns a list of loaded plugin names.
        '''
        from ckan.lib.datapreview import (get_view_plugins,
                                          get_default_view_plugins
                                          )

        log = logging.getLogger(__name__)

        view_plugins = []

        if not view_plugin_types:
            log.info('No view types provided, using default types')
            view_plugins = get_default_view_plugins()
            if get_datastore_views:
                view_plugins.extend(
                    get_default_view_plugins(get_datastore_views=True))
        else:
            view_plugins = get_view_plugins(view_plugin_types)

        loaded_view_plugins = [view_plugin.info()['name']
                               for view_plugin in view_plugins]

        plugins_not_found = list(set(view_plugin_types) -
                                 set(loaded_view_plugins))

        if plugins_not_found:
            msg = ('View plugin(s) not found : {0}. '.format(plugins_not_found)
                   + 'Have they been added to the `ckan.plugins` configuration'
                   + ' option?')
            log.error(msg)
            sys.exit(1)

        return loaded_view_plugins

    def _add_default_filters(self, search_data_dict, view_types):
        '''
        Adds extra filters to the `package_search` dict for common view types

        It basically adds `fq` parameters that filter relevant resource formats
        for the view types provided. For instance, if one of the view types is
        `pdf_view` the following will be added to the final query:

            fq=res_format:"pdf" OR res_format:"PDF"

        This obviously should only be used if all view types are known and can
        be filtered, otherwise we want all datasets to be returned. If a
        non-filterable view type is provided, the search params are not
        modified.

        Returns the provided data_dict for `package_search`, optionally
        modified with extra filters.
        '''

        from ckanext.imageview.plugin import DEFAULT_IMAGE_FORMATS
        from ckanext.textview.plugin import get_formats as get_text_formats
        from ckanext.datapusher.plugin import DEFAULT_FORMATS as \
            datapusher_formats

        filter_formats = []

        for view_type in view_types:
            if view_type == 'image_view':

                for _format in DEFAULT_IMAGE_FORMATS:
                    filter_formats.extend([_format, _format.upper()])

            elif view_type == 'text_view':
                formats = get_text_formats(config)
                for _format in itertools.chain.from_iterable(formats.values()):
                    filter_formats.extend([_format, _format.upper()])

            elif view_type == 'pdf_view':
                filter_formats.extend(['pdf', 'PDF'])

            elif view_type in ['recline_view', 'recline_grid_view',
                               'recline_graph_view', 'recline_map_view']:

                if datapusher_formats[0] in filter_formats:
                    continue

                for _format in datapusher_formats:
                    if '/' not in _format:
                        filter_formats.extend([_format, _format.upper()])
            else:
                # There is another view type provided so we can't add any
                # filter
                return search_data_dict

        filter_formats_query = ['+res_format:"{0}"'.format(_format)
                                for _format in filter_formats]
        search_data_dict['fq_list'].append(' OR '.join(filter_formats_query))

        return search_data_dict

    def _update_search_params(self, search_data_dict):
        '''
        Update the `package_search` data dict with the user provided parameters

        Supported fields are `q`, `fq` and `fq_list`.

        If the provided JSON object can not be parsed the process stops with
        an error.

        Returns the updated data dict
        '''

        log = logging.getLogger(__name__)

        if not self.options.search_params:
            return search_data_dict

        try:
            user_search_params = json.loads(self.options.search_params)
        except ValueError, e:
            log.error('Unable to parse JSON search parameters: {0}'.format(e))
            sys.exit(1)

        if user_search_params.get('q'):
            search_data_dict['q'] = user_search_params['q']

        if user_search_params.get('fq'):
            if search_data_dict['fq']:
                search_data_dict['fq'] += ' ' + user_search_params['fq']
            else:
                search_data_dict['fq'] = user_search_params['fq']

        if (user_search_params.get('fq_list') and
                isinstance(user_search_params['fq_list'], list)):
            search_data_dict['fq_list'].extend(user_search_params['fq_list'])

    def _search_datasets(self, page=1, view_types=[]):
        '''
        Perform a query with `package_search` and return the result

        Results can be paginated using the `page` parameter
        '''

        n = self._page_size

        search_data_dict = {
            'q': '',
            'fq': '',
            'fq_list': [],
            'rows': n,
            'start': n * (page - 1),
        }

        if self.options.dataset_id:

            search_data_dict['q'] = ' OR '.join(
                ['id:{0} OR name:"{0}"'.format(dataset_id)
                 for dataset_id in self.options.dataset_id]
            )

        elif self.options.search_params:

            self._update_search_params(search_data_dict)

        elif not self.options.no_default_filters:

            self._add_default_filters(search_data_dict, view_types)

        if not search_data_dict.get('q'):
            search_data_dict['q'] = '*:*'

        query = p.toolkit.get_action('package_search')(
            {'ignore_capacity_check': True},
            search_data_dict)

        return query

    def create_views(self, view_plugin_types=[]):

        from ckan.lib.datapreview import add_views_to_dataset_resources

        log = logging.getLogger(__name__)

        datastore_enabled = 'datastore' in config['ckan.plugins'].split()

        loaded_view_plugins = self._get_view_plugins(view_plugin_types,
                                                     datastore_enabled)

        context = {'user': self.site_user['name']}

        page = 1
        while True:
            query = self._search_datasets(page, loaded_view_plugins)

            if page == 1 and query['count'] == 0:
                log.info('No datasets to create resource views on, exiting...')
                sys.exit(1)

            elif page == 1 and not self.options.assume_yes:

                msg = ('\nYou are about to check {0} datasets for the ' +
                       'following view plugins: {1}\n' +
                       ' Do you want to continue?')

                confirm = query_yes_no(msg.format(query['count'],
                                                  loaded_view_plugins))

                if confirm == 'no':
                    log.info('Command aborted by user')
                    sys.exit(1)

            if query['results']:
                for dataset_dict in query['results']:

                    if not dataset_dict.get('resources'):
                        continue

                    views = add_views_to_dataset_resources(
                        context,
                        dataset_dict,
                        view_types=loaded_view_plugins)

                    if views:
                        view_types = list(set([view['view_type']
                                               for view in views]))
                        msg = ('Added {0} view(s) of type(s) {1} to ' +
                               'resources from dataset {2}')
                        log.debug(msg.format(len(views),
                                             ', '.join(view_types),
                                             dataset_dict['name']))

                if len(query['results']) < self._page_size:
                    break

                page += 1
            else:
                break

        log.info('Done')

    def clear_views(self, view_plugin_types=[]):

        log = logging.getLogger(__name__)

        if not self.options.assume_yes:
            if view_plugin_types:
                msg = 'Are you sure you want to delete all resource views ' + \
                      'of type {0}?'.format(', '.join(view_plugin_types))
            else:
                msg = 'Are you sure you want to delete all resource views?'

            result = query_yes_no(msg, default='no')

            if result == 'no':
                log.info('Command aborted by user')
                sys.exit(1)

        context = {'user': self.site_user['name']}
        logic.get_action('resource_view_clear')(
            context, {'view_types': view_plugin_types})

        log.info('Done')

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


class ConfigToolCommand(paste.script.command.Command):
    '''Tool for editing options in a CKAN config file

    paster config-tool <default.ini> <key>=<value> [<key>=<value> ...]
    paster config-tool <default.ini> -f <custom_options.ini>

    Examples:
      paster config-tool default.ini sqlalchemy.url=123 'ckan.site_title=ABC'
      paster config-tool default.ini -s server:main -e port=8080
      paster config-tool default.ini -f custom_options.ini
    '''
    parser = paste.script.command.Command.standard_parser(verbose=True)
    default_verbosity = 1
    group_name = 'ckan'
    usage = __doc__
    summary = usage.split('\n')[0]

    parser.add_option('-s', '--section', dest='section',
                      default='app:main', help='Section of the config file')
    parser.add_option(
        '-e', '--edit', action='store_true', dest='edit', default=False,
        help='Checks the option already exists in the config file')
    parser.add_option(
        '-f', '--file', dest='merge_filepath', metavar='FILE',
        help='Supply an options file to merge in')

    def command(self):
        import config_tool
        if len(self.args) < 1:
            self.parser.error('Not enough arguments (got %i, need at least 1)'
                              % len(self.args))
        config_filepath = self.args[0]
        if not os.path.exists(config_filepath):
            self.parser.error('Config filename %r does not exist.' %
                              config_filepath)
        if self.options.merge_filepath:
            config_tool.config_edit_using_merge_file(
                config_filepath, self.options.merge_filepath)
        options = self.args[1:]
        if not (options or self.options.merge_filepath):
            self.parser.error('No options provided')
        if options:
            for option in options:
                if '=' not in option:
                    sys.stderr.write(
                        'An option does not have an equals sign: %r '
                        'It should be \'key=value\'. If there are spaces '
                        'you\'ll need to quote the option.\n' % option)
                    sys.exit(1)
            try:
                config_tool.config_edit_using_option_strings(
                    config_filepath, options, self.options.section,
                    edit=self.options.edit)
            except config_tool.ConfigToolError, e:
                sys.stderr.write(e.message)
                sys.exit(1)
