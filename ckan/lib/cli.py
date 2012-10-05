import os
import datetime
import sys
import logging
from pprint import pprint
import re

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
    parser = paste.script.command.Command.standard_parser(verbose=True)
    parser.add_option('-c', '--config', dest='config',
            default='development.ini', help='Config file to use.')
    parser.add_option('-f', '--file',
        action='store',
        dest='file_path',
        help="File to dump results to (if needed)")
    default_verbosity = 1
    group_name = 'ckan'

    def _load_config(self):
        from paste.deploy import appconfig
        if not self.options.config:
            msg = 'No config file supplied'
            raise self.BadCommand(msg)
        self.filename = os.path.abspath(self.options.config)
        if not os.path.exists(self.filename):
            raise AssertionError('Config filename %r does not exist.' % self.filename)
        fileConfig(self.filename)
        conf = appconfig('config:' + self.filename)
        assert 'ckan' not in dir() # otherwise loggers would be disabled
        # We have now loaded the config. Now we can import ckan for the
        # first time.
        from ckan.config.environment import load_environment
        load_environment(conf.global_conf, conf.local_conf)

        self.registry=Registry()
        self.registry.prepare()
        import pylons
        self.translator_obj = MockTranslator()
        self.registry.register(pylons.translator, self.translator_obj)

    def _setup_app(self):
        cmd = paste.script.appinstall.SetupCommand('setup-app')
        cmd.run([self.filename])


class ManageDb(CkanCommand):
    '''Perform various tasks on the database.

    db create # alias of db upgrade
    db init # create and put in default data
    db clean
    db upgrade [{version no.}] # Data migrate
    db version # returns current version of data schema
    db dump {file-path} # dump to a pg_dump file
    db dump-rdf {dataset-name} {file-path}
    db simple-dump-csv {file-path} # dump just datasets in CSV format
    db simple-dump-json {file-path} # dump just datasets in JSON format
    db user-dump-csv {file-path} # dump user information to a CSV file
    db send-rdf {talis-store} {username} {password}
    db load {file-path} # load a pg_dump from a file
    db load-only {file-path} # load a pg_dump from a file but don\'t do
                             # the schema upgrade or search indexing
    db create-from-model # create database from the model (indexes not made)
    '''
    summary = __doc__.split('\n')[0]
    usage = __doc__
    max_args = None
    min_args = 1

    def command(self):
        self._load_config()
        import ckan.model as model
        import ckan.lib.search as search

        cmd = self.args[0]
        if cmd == 'init':
            model.repo.init_db()
            if self.verbose:
                print 'Initialising DB: SUCCESS'
        elif cmd == 'clean' or cmd == 'drop':
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

    def version(self):
        from ckan.model import Session
        print Session.execute('select version from migrate_version;').fetchall()


class SearchIndexCommand(CkanCommand):
    '''Creates a search index for all datasets

    Usage:
      search-index [-i] [-o] [-r] [-e] rebuild [dataset-name]     - reindex dataset-name if given, if not then rebuild full search index (all datasets)
      search-index check                                     - checks for datasets not indexed
      search-index show {dataset-name}                       - shows index of a dataset
      search-index clear [dataset-name]                      - clears the search index for the provided dataset or for the whole ckan instance
    '''

    summary = __doc__.split('\n')[0]
    usage = __doc__
    max_args = 2
    min_args = 0

    def __init__(self,name):

        super(SearchIndexCommand,self).__init__(name)

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
        self._load_config()

        if not self.args:
            # default to printing help
            print self.usage
            return

        cmd = self.args[0]
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
    '''
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
            self.export_datasets( self.args[0] )

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
        if not os.path.isdir( out_folder ):
            os.makedirs( out_folder )

        fetch_url = config['ckan.site_url']
        user = logic.get_action('get_site_user')({'model': model, 'ignore_auth': True}, {})
        context = {'model': model, 'session': model.Session, 'user': user['name']}
        dataset_names = logic.get_action('package_list')(context, {})
        for dataset_name in dataset_names:
            dd = logic.get_action('package_show')(context, {'id':dataset_name })
            if not dd['state'] == 'active':
                continue

            url = h.url_for( controller='package',action='read',
                                                  id=dd['name'])

            url = urlparse.urljoin(fetch_url, url[1:]) + '.rdf'
            try:
                fname = os.path.join( out_folder, dd['name'] ) + ".rdf"
                r = urllib2.urlopen(url).read()
                with open(fname, 'wb') as f:
                    f.write(r)
            except IOError, ioe:
                sys.stderr.write( str(ioe) + "\n" )




class Sysadmin(CkanCommand):
    '''Gives sysadmin rights to a named user

    Usage:
      sysadmin                      - lists sysadmins
      sysadmin list                 - lists sysadmins
      sysadmin add <user-name>      - add a user as a sysadmin
      sysadmin remove <user-name>   - removes user from sysadmins
    '''

    summary = __doc__.split('\n')[0]
    usage = __doc__
    max_args = 2
    min_args = 0

    def command(self):
        self._load_config()
        import ckan.model as model

        cmd = self.args[0] if self.args else None
        if cmd == None or cmd == 'list':
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
        sysadmins = model.Session.query(model.SystemRole).filter_by(role=model.Role.ADMIN)
        print 'count = %i' % sysadmins.count()
        for sysadmin in sysadmins:
            user_or_authgroup = sysadmin.user or sysadmin.authorized_group
            assert user_or_authgroup, 'Could not extract entity with this priviledge from: %r' % sysadmin
            print '%s name=%s id=%s' % (user_or_authgroup.__class__.__name__,
                                        user_or_authgroup.name,
                                        user_or_authgroup.id)

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
        model.add_user_to_role(user, model.Role.ADMIN, model.System())
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
        model.remove_user_from_role(user, model.Role.ADMIN, model.System())
        model.repo.commit_and_remove()


class UserCmd(CkanCommand):
    '''Manage users

    Usage:
      user                            - lists users
      user list                       - lists users
      user <user-name>                - shows user properties
      user add <user-name> [apikey=<apikey>] [password=<password>]
                                      - add a user (prompts for password if
                                        not supplied)
      user setpass <user-name>        - set user password (prompts)
      user remove <user-name>         - removes user from users
      user search <query>             - searches for a user name
    '''
    summary = __doc__.split('\n')[0]
    usage = __doc__
    max_args = 4
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
        users = model.Session.query(model.User)
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
            return
        username = self.args[1]
        user = model.User.by_name(unicode(username))
        if user:
            print 'User "%s" already found' % username
            sys.exit(1)

        # parse args
        apikey = None
        password = None
        args = self.args[2:]
        if len(args) == 1 and not (args[0].startswith('password') or \
                                   args[0].startswith('apikey')):
            # continue to support the old syntax of just supplying
            # the apikey
            apikey = args[0]
        else:
            # new syntax: password=foo apikey=bar
            for arg in args:
                split = arg.find('=')
                if split == -1:
                    split = arg.find(' ')
                    if split == -1:
                        raise ValueError('Could not parse arg: %r (expected "--<option>=<value>)")' % arg)
                key, value = arg[:split], arg[split+1:]
                if key == 'password':
                    password = value
                elif key == 'apikey':
                    apikey = value
                else:
                    raise ValueError('Could not parse arg: %r (expected password/apikey argument)' % arg)

        if not password:
            password = self.password_prompt()

        print('Creating user: %r' % username)


        user_params = {'name': unicode(username),
                       'password': password}
        if apikey:
            user_params['apikey'] = unicode(apikey)
        user = model.User(**user_params)
        model.Session.add(user)
        model.repo.commit_and_remove()
        user = model.User.by_name(unicode(username))
        print user

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
      dataset <dataset-name/id>          - shows dataset properties
      dataset show <dataset-name/id>     - shows dataset properties
      dataset list                       - lists datasets
      dataset delete <dataset-name/id>   - changes dataset state to 'deleted'
      dataset purge <dataset-name/id>    - removes dataset from db entirely
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
            state = ('(%s)' % dataset.state) if dataset.state != 'active' \
                    else ''
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
        from ckan import plugins
        import ckan.model as model
        dataset = self._get_dataset(dataset_ref)
        old_state = dataset.state

        plugins.load('synchronous_search')
        rev = model.repo.new_revision()
        dataset.delete()
        model.repo.commit_and_remove()
        dataset = self._get_dataset(dataset_ref)
        print '%s %s -> %s' % (dataset.name, old_state, dataset.state)

    def purge(self, dataset_ref):
        from ckan import plugins
        import ckan.model as model
        dataset = self._get_dataset(dataset_ref)
        name = dataset.name

        plugins.load('synchronous_search')
        rev = model.repo.new_revision()
        dataset.purge()
        model.repo.commit_and_remove()
        print '%s purged' % name


class Celery(CkanCommand):
    '''Celery daemon

    Usage:
        celeryd                 - run the celery daemon
        celeryd run             - run the celery daemon
        celeryd run concurrency - run the celery daemon with
                                  argument 'concurrency'
        celeryd view            - view all tasks in the queue
        celeryd clean           - delete all tasks in the queue
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
        os.environ['CKAN_CONFIG'] = os.path.abspath(self.options.config)
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
        q = q.filter(model.Rating.user_id == None)
        print "of which %i are anonymous ratings" % q.count()

    def clean(self, user_ratings=True):
        import ckan.model as model
        q = model.Session.query(model.Rating)
        print "%i ratings" % q.count()
        if not user_ratings:
            q = q.filter(model.Rating.user_id == None)
            print "of which %i are anonymous ratings" % q.count()
        ratings = q.all()
        for rating in ratings:
            rating.purge()
        model.repo.commit_and_remove()

class Tracking(CkanCommand):
    '''Update tracking statistics

    Usage:
      tracking   - update tracking stats
    '''

    summary = __doc__.split('\n')[0]
    usage = __doc__
    max_args = 1
    min_args = 0

    def command(self):
        self._load_config()
        import ckan.model as model
        engine = model.meta.engine

        if len(self.args) == 1:
            # Get summeries from specified date
            start_date = datetime.datetime.strptime(self.args[0], '%Y-%m-%d')
        else:
            # No date given. See when we last have data for and get data
            # from 2 days before then in case new data is available.
            # If no date here then use 2010-01-01 as the start date
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
        end_date = datetime.datetime.now()

        while start_date < end_date:
            stop_date = start_date + datetime.timedelta(1)
            self.update_tracking(engine, start_date)
            print 'tracking updated for %s' % start_date
            start_date = stop_date

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
                        WHERE t.url =  %s || p.name)
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

class PluginInfo(CkanCommand):
    ''' Provide info on installed plugins.
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
                    interfaces[item] = {'class' : item}
            except TypeError:
                pass

        for interface in interfaces:
            for plugin in p.PluginImplementations(interface):
                name = plugin.name
                if name not in plugins:
                    plugins[name] = {'doc' : plugin.__doc__,
                                     'class' : plugin,
                                     'implements' : []}
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
    create-test-data vocabs  - annakerenina, warandpeace, and some test
                               vocabularies

    '''
    summary = __doc__.split('\n')[0]
    usage = __doc__
    max_args = 1
    min_args = 0

    def command(self):
        self._load_config()
        self._setup_app()
        from ckan import plugins
        plugins.load('synchronous_search') # so packages get indexed
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
       profile {url}

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
