import os
import sys
import logging
from pprint import pprint

import paste.script
from paste.registry import Registry
from paste.script.util.logging_config import fileConfig
import re

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
        # Avoids vdm logging warning
        logging.basicConfig(level=logging.ERROR)

        from paste.deploy import appconfig
        from ckan.config.environment import load_environment
        if not self.options.config:
            msg = 'No config file supplied'
            raise self.BadCommand(msg)
        self.filename = os.path.abspath(self.options.config)
        if not os.path.exists(self.filename):
            raise AssertionError('Config filename %r does not exist.' % self.filename)
        fileConfig(self.filename)
        conf = appconfig('config:' + self.filename)
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
        from ckan import model
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
        from pylons import config
        url = config['sqlalchemy.url']
        # e.g. 'postgres://tester:pass@localhost/ckantest3'
        db_details_match = re.match('^\s*(?P<db_type>\w*)://(?P<db_user>[^:]*):?(?P<db_pass>[^@]*)@(?P<db_host>[^/:]*):?(?P<db_port>[^/]*)/(?P<db_name>[\w.-]*)', url)
        if not db_details_match:
            raise Exception('Could not extract db details from url: %r' % url)
        db_details = db_details_match.groupdict()
        return db_details

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

    def _postgres_load(self, filepath):
        from ckan import model
        assert not model.repo.are_tables_created(), "Tables already found. You need to 'db clean' before a load."
        pg_cmd = self._get_psql_cmd() + ' -f %s' % filepath
        self._run_cmd(pg_cmd)

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
            from ckan import model
            model.repo.upgrade_db()
            
            print 'Rebuilding search index'
            import ckan.lib.search
            ckan.lib.search.rebuild()
        else:
            print 'Now remember you have to call \'db upgrade\' and then \'search-index rebuild\'.'
        print 'Done'

    def simple_dump_csv(self):
        from ckan import model
        if len(self.args) < 2:
            print 'Need csv file path'
            return
        dump_filepath = self.args[1]
        import ckan.lib.dumper as dumper
        dump_file = open(dump_filepath, 'w')
        dumper.SimpleDumper().dump(dump_file, format='csv')

    def simple_dump_json(self):
        from ckan import model
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
      search-index rebuild [package-name]  - reindex package-name if given, if not then rebuild full search index (all packages)
      search-index check                   - checks for packages not indexed
      search-index show {package-name}     - shows index of a package
      search-index clear                   - clears the search index for this ckan instance
    '''

    summary = __doc__.split('\n')[0]
    usage = __doc__
    max_args = 2
    min_args = 0

    def command(self):
        self._load_config()
        from ckan.lib.search import rebuild, check, show, clear

        if not self.args:
            # default to printing help
            print self.usage
            return

        cmd = self.args[0]        
        if cmd == 'rebuild':
            if len(self.args) > 1:
                rebuild(self.args[1])
            else:
                rebuild()
        elif cmd == 'check':
            check()
        elif cmd == 'show':
            if not len(self.args) == 2:
                import pdb; pdb.set_trace()
                self.args
            show(self.args[1])
        elif cmd == 'clear':
            clear()
        else:
            print 'Command %s not recognized' % cmd

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
        from ckan import model

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
        from ckan import model
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
        from ckan import model

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
        from ckan import model

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
        from ckan import model

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
        from ckan import model
        print 'Users:'
        users = model.Session.query(model.User)
        print 'count = %i' % users.count()        
        for user in users:
            print self.get_user_str(user)

    def show(self):
        from ckan import model

        username = self.args[0]
        user = model.User.get(unicode(username))
        print 'User: \n', user

    def setpass(self):
        from ckan import model
        
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
        from ckan import model

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
        from ckan import model
        
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
        from ckan import model

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
        from ckan import model

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
        from ckan import model
        print 'Datasets:'
        datasets = model.Session.query(model.Package)
        print 'count = %i' % datasets.count()
        for dataset in datasets:
            state = ('(%s)' % dataset.state) if dataset.state != 'active' \
                    else ''
            print '%s %s %s' % (dataset.id, dataset.name, state)

    def _get_dataset(self, dataset_ref):
        from ckan import model
        dataset = model.Package.get(unicode(dataset_ref))
        assert dataset, 'Could not find dataset matching reference: %r' % dataset_ref
        return dataset
            
    def show(self, dataset_ref):
        from ckan import model
        import pprint
        dataset = self._get_dataset(dataset_ref)
        pprint.pprint(dataset.as_dict())

    def delete(self, dataset_ref):
        from ckan import model, plugins
        dataset = self._get_dataset(dataset_ref)
        old_state = dataset.state

        plugins.load('synchronous_search')
        rev = model.repo.new_revision()
        dataset.delete()
        model.repo.commit_and_remove()
        dataset = self._get_dataset(dataset_ref)
        print '%s %s -> %s' % (dataset.name, old_state, dataset.state)

    def purge(self, dataset_ref):
        from ckan import model, plugins
        dataset = self._get_dataset(dataset_ref)
        name = dataset.name

        plugins.load('synchronous_search')
        rev = model.repo.new_revision()
        dataset.purge()
        model.repo.commit_and_remove()
        print '%s purged' % name
        

class Celery(CkanCommand):
    '''Run celery daemon

    Usage:
        celeryd
    '''
    min_args = 0
    summary = __doc__.split('\n')[0]
    usage = __doc__

    def command(self):
        os.environ['CKAN_CONFIG'] = os.path.abspath(self.options.config)
        from ckan.lib.celery_app import celery
        celery.worker_main(argv=['celeryd', '--loglevel=INFO'])
        

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
        from ckan import model

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
        from ckan import model
        q = model.Session.query(model.Rating)
        print "%i ratings" % q.count()
        q = q.filter(model.Rating.user_id == None)
        print "of which %i are anonymous ratings" % q.count()        

    def clean(self, user_ratings=True):
        from ckan import model
        q = model.Session.query(model.Rating)
        print "%i ratings" % q.count()
        if not user_ratings:
            q = q.filter(model.Rating.user_id == None)
            print "of which %i are anonymous ratings" % q.count()
        ratings = q.all()
        for rating in ratings:
            rating.purge()
        model.repo.commit_and_remove()

