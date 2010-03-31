import os
import sys

import paste.script

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
        from ckan.config.environment import load_environment
        if not self.options.config:
            msg = 'No config file supplied'
            raise self.BadCommand(msg)
        self.filename = os.path.abspath(self.options.config)
        conf = appconfig('config:' + self.filename)
        load_environment(conf.global_conf, conf.local_conf)

    def _setup_app(self):
        cmd = paste.script.appinstall.SetupCommand('setup-app') 
        cmd.run([self.filename]) 


class ManageDb(CkanCommand):
    '''Perform various tasks on the database.
    
    db create # create
    db init # create and put in default data
    db clean
    db upgrade [{version no.}] # Data migrate
    db dump {file-path} # dump to a file (json)
    db dump-rdf {package-name} {file-path}
    db simple-dump-csv {file-path}
    db simple-dump-json {file-path}
    db send-rdf {talis-store} {username} {password}
    db load {file-path} # load from a file
    db load-data4nr {file-path.csv}
    db load-cospread {file-path.csv}
    db load-esw {file-path.txt} [{host} {api-key}]
    db load-ons [{file-path.csv}|recent|days={num-days}|all]
    db migrate06
    db migrate09a
    db migrate09b
    db migrate09c
    '''
    summary = __doc__.split('\n')[0]
    usage = __doc__
    max_args = None
    min_args = 1

    def command(self):
        self._load_config()
        from ckan import model

        cmd = self.args[0]
        if cmd == 'create':
            model.repo.create_db()
        elif cmd == 'init':
            model.repo.init_db()
        elif cmd == 'clean' or cmd == 'drop':
            model.repo.clean_db()
            if self.verbose:
                print 'Cleaning DB: SUCCESS'
        elif cmd == 'upgrade':
            if len(self.args) > 1:
                model.repo.upgrade_db(self.args[1])
            else:
                model.repo.upgrade_db()
        elif cmd == 'dump' or cmd == 'load':
            self.dump_or_load(cmd)
        elif cmd == 'simple-dump-csv':
            self.simple_dump_csv(cmd)
        elif cmd == 'simple-dump-json':
            self.simple_dump_json(cmd)
        elif cmd == 'dump-rdf':
            self.dump_rdf(cmd)
        elif cmd == 'send-rdf':
            self.send_rdf(cmd)
        elif cmd == 'load-data4nr':
            import ckan.getdata.data4nr as data_getter
            self.load_data(data_getter.Data4Nr)
        elif cmd == 'load-cospread':
            import ckan.getdata.cospread as data_getter
            self.load_data(data_getter.Data)
        elif cmd == 'load-esw':
            self.load_esw(cmd)
        elif cmd == 'load-ons':
            self.load_ons()
        elif cmd == 'migrate06':
            import ckan.lib.converter
            dumper = ckan.lib.converter.Dumper()
            dumper.migrate_06_to_07()
        elif cmd == 'migrate09a':
            import ckan.model as model
            sql = '''ALTER TABLE package ADD version VARCHAR(100)'''
            model.metadata.bind.execute(sql)
            sql = '''ALTER TABLE package_revision ADD version VARCHAR(100)'''
            model.metadata.bind.execute(sql)
            if self.verbose:
                print 'Migrated successfully' 
        elif cmd == 'migrate09b':
            import ckan.model as model
            print 'Re-initting DB to update license list'
            model.repo.init_db()
        elif cmd == 'migrate09c':
            import ckan.model as model
            print 'Creating new db tables (package_extra)'
            model.repo.create_db()
        else:
            print 'Command %s not recognized' % cmd
            sys.exit(1)

    def dump_or_load(self, cmd):
        print 'This functionality is mothballed for now.'
        return
        if len(self.args) < 2:
            print 'Need dump path'
            return
        dump_path = self.args[1]
        import ckan.lib.dumper
        dumper = ckan.lib.dumper.Dumper()
        verbose = (self.verbose >= 2)
        if cmd == 'load':
            dumper.load_json(dump_path, verbose=verbose)
        elif cmd == 'dump':
            dumper.dump_json(dump_path, verbose=verbose)
        else:
            print 'Unknown command', cmd

    def load_data(self, data_getter, extension='csv'):
        if len(self.args) < 2:
            print 'Need %s file path' % extension
            return
        load_path = self.args[1] if len(self.args) == 2 else self.args[1:]
        data = data_getter()
        load_func = getattr(data, 'load_%s_into_db' % extension)
        load_func(load_path)

    def simple_dump_csv(self, cmd):
        from ckan import model
        if len(self.args) < 2:
            print 'Need csv file path'
            return
        dump_filepath = self.args[1]
        import ckan.lib.dumper as dumper
        dump_file = open(dump_filepath, 'w')
        query = model.Session.query(model.Package)
        dumper.SimpleDumper().dump_csv(dump_file, query)

    def simple_dump_json(self, cmd):
        from ckan import model
        if len(self.args) < 2:
            print 'Need json file path'
            return
        dump_filepath = self.args[1]
        import ckan.lib.dumper as dumper
        dump_file = open(dump_filepath, 'w')
        query = model.Session.query(model.Package)
        dumper.SimpleDumper().dump_json(dump_file, query)

    def dump_rdf(self, cmd):
        if len(self.args) < 3:
            print 'Need package name and rdf file path'
            return
        package_name = self.args[1]
        rdf_path = self.args[2]
        import ckan.model as model
        import ckan.lib.rdf as rdf
        pkg = model.Package.by_name(unicode(package_name))
        if not pkg:
            print 'Package name "%s" does not exist' % package_name
            return
        rdf = rdf.RdfExporter().export_package(pkg)
        f = open(rdf_path, 'w')
        f.write(rdf)
        f.close()

    def send_rdf(self, cmd):
        if len(self.args) < 4:
            print 'Need all arguments: {talis-store} {username} {password}'
            return
        talis_store = self.args[1]
        username = self.args[2]
        password = self.args[3]
        import ckan.lib.talis
        talis = ckan.lib.talis.Talis()
        return talis.send_rdf(talis_store, username, password)

    def load_esw(self, cmd):
        if len(self.args) < 2:
            print 'Need ESW data file path'
            return
        load_path = self.args[1]
        if len(self.args) > 3:
            server = self.args[2]
            if server.startswith('http://'):
                server = server.strip('http://').strip('/')
            base_location = 'http://%s/api/rest' % server
            api_key = self.args[3]
        else:
            server = api_key = None
        print 'Loading ESW data\n  Filename: %s\n  Server hostname: %s\n  Api-key: %s' % \
              (load_path, server, api_key)
        import ckan.getdata.esw
        data = ckan.getdata.esw.Esw()
        if server:
            import ckanclient
            ckanclient = ckanclient.CkanClient(base_location=base_location, api_key=api_key)
            data.load_esw_txt_via_rest(load_path, ckanclient)
        else:
            data.load_esw_txt_into_db(load_path)

    def load_ons(self):
        if len(self.args) < 2:
            print 'Need xml file path or "all" or "recent" or "days=x".'
            return
        arg = self.args[1]
        if arg == 'recent' or arg == 'all' or arg.startswith('days'):
            import ckan.getdata.ons_download as ons
            if len(self.args) < 3:
                ons_cache_dir = '~/ons_data'
                print 'Defaulting ONS cache dir: %s' % ons_cache_dir
            else:
                ons_cache_dir = self.args[2]
                print 'ONS cache dir: %s' % ons_cache_dir
        ons_cache_dir = os.path.expanduser(ons_cache_dir)
        if not os.path.exists(ons_cache_dir):
            print 'Creating dir: %s' % ons_cache_dir
            os.makedirs(ons_cache_dir)
        if arg == 'recent':
            new_packages, num_packages_after = ons.import_recent(ons_cache_dir)
        elif arg.startswith('days='):
            days = int(arg.split('=')[1])
            new_packages, num_packages_after = ons.import_recent(ons_cache_dir, days=days)
        elif arg == 'all':
            new_packages, num_packages_after = ons.import_all(ons_cache_dir)
        else:
            # filename given
            import ckan.getdata.ons_hub as data_getter
            self.load_data(data_getter.Data, 'xml')


class TestData(CkanCommand):
    '''Perform simple consistency tests on the db and wui.

    Usage:
      test-data <wui url>
    '''

    summary = __doc__.split('\n')[0]
    usage = __doc__
    max_args = 1
    min_args = 1

    def command(self):
        self._load_config()
        from ckan import model

        print 'Database check'
        print '**************'

        num_pkg = model.Session.query(model.Package).count()
        print '* Number of packages: ', num_pkg
        assert num_pkg > 0

        num_tag = model.Session.query(model.Tag).count()
        print '* Number of tags: ', num_tag
        assert num_tag > 0

        pkg = model.Session.query(model.Package).first()
        print u'* A package: %s' % pkg.as_dict()
        expected_attributes = ('name', 'title', 'notes', 'url')
        for ea in expected_attributes:
            print '* Checking for attribute ', ea
            assert ea in pkg.__dict__.keys()

        tag = model.Session.query(model.Tag).first()
        print '* A tag: ', tag.name
        expected_attributes = ['name']
        for ea in expected_attributes:
            print '* Checking for attribute ', ea
            assert ea in tag.__dict__.keys()

        print '\nWUI check'
        print   '========='
        import paste.fixture
        self.wui_address = self.args[0]
        if not self.wui_address.startswith('http://'):
            self.wui_address = 'http://' + self.wui_address
        if not self.wui_address.endswith('/'):
            self.wui_address = self.wui_address + '/'

        import paste.proxy
        wsgiapp = paste.proxy.make_proxy({}, self.wui_address)
        self.app = paste.fixture.TestApp(wsgiapp)

        def check_page(path, required_contents, status=200):
            print "* Checking page '%s%s'" % (self.wui_address, path)
            res = self.app.get(path, status=status)
            if type(required_contents) is type(()):
                for required in required_contents:
                    print '    ...checking for %r' % required
                    assert required in res, res
            else:
                assert required_contents in res, res
            return res


        res = check_page('/', ('Search'))
        form = res.forms[0]
        form['q'] = pkg.name
        res = form.submit()
        print '* Checking search using %r' % pkg.name
        assert ('package found' in res) or ('packages found' in res), res

        res = res.click(pkg.title)
        print '* Checking package page %s' % res.request.url
        assert pkg.title in res, res
        for tag in pkg.tags:
            assert tag.name in res, res
        assert pkg.license.name in res, res

        tag = pkg.tags[0]
        res = check_page('/tag/read/%s' % tag.name, 
                ('Tag: %s' % str(tag.name), str(pkg.name))
            )

        res = check_page('/package/new', 'Register a New Package')
        
        res = check_page('/package/list', 'Packages')



class Sysadmin(CkanCommand):
    '''Gives sysadmin rights to a named 

    Usage:
      sysadmin list                 - lists sysadmins
      sysadmin create <user-name>   - creates sysadmin user
    '''

    summary = __doc__.split('\n')[0]
    usage = __doc__
    max_args = 2
    min_args = 1

    def command(self):
        self._load_config()
        from ckan import model

        cmd = self.args[0]
        if cmd == 'list':
            self.list()
        elif cmd == 'create':
            self.create()
        elif cmd == 'remove':
            self.create()
        else:
            print 'Command %s not recognized' % cmd

    def list(self):
        from ckan import model
        print 'Sysadmins:'
        sysadmins = model.Session.query(model.SystemRole).filter_by(role=model.Role.ADMIN).all()
        for sysadmin in sysadmins:
            print 'name=%s id=%s' % (sysadmin.user.name, sysadmin.user.id)

    def create(self):
        from ckan import model

        if len(self.args) < 2:
            print 'Need name of the user to be made sysadmin.'
            return
        username = self.args[1]

        user = model.User.by_name(unicode(username))
        if not user:
            print 'User "%s" not found - creating' % username
            user = model.User(name=username)
        model.add_user_to_role(user, model.Role.ADMIN, model.System())
        model.repo.commit_and_remove()

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

class CreateSearchIndex(CkanCommand):
    '''Creates a search index for all packages
    '''

    summary = __doc__.split('\n')[0]
    usage = __doc__
    max_args = 0
    min_args = 0

    def command(self):
        self._load_config()
        self.index()

    def index(self):
        from ckan import model
        from ckan.model.full_search import SearchVectorTrigger
        engine = model.metadata.bind
        for pkg in model.Session.query(model.Package).all():
            pkg_dict = pkg.as_dict()
            SearchVectorTrigger().update_package_vector(pkg_dict, engine)

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

class ChangesSourceException(Exception): pass

class Changes(CkanCommand):
    '''Distribute changes

    Usage:
      changes pull [source]          - pulls unseen changesets from changeset sources
      changes update [target]        - updates repository entities to target changeset (defaults to tip's line's head)
      changes commit                 - creates changesets for all outstanding changes (revisions)
      changes merge [follow]         - creates mergeset to follow changeset and close tip
      changes log [changeset]        - display changeset summary
      changes tip                    - display tip changeset
    '''

    summary = __doc__.split('\n')[0]
    usage = __doc__
    max_args = 2
    min_args = 1

    def command(self):
        self._load_config()
        from ckan import model
        cmd = self.args[0]
        if cmd == 'pull':
            self.pull()
        elif cmd == 'update':
            self.update()
        elif cmd == 'commit':
            self.commit()
        elif cmd == 'merge':
            self.merge()
        elif cmd == 'tip':
            self.tip()
        elif cmd == 'log':
            self.log()
        else:
            print 'Command %s not recognized' % cmd

    def pull(self):
        from pylons import config
        sources = config.get('changes_source', '').strip()
        if not sources:
            print "No changes sources are configured here (try "
            print "setting 'changes_source' in your config file)."
            return
        sources = [source.strip() for source in sources.split(',')]
        for source in sources:
            print "Pulling changes from: %s" % source
            try:
                self.pull_source(source)
            except ChangesSourceException, inst:
                print inst
                sys.exit(1)
            
    def pull_source(self, source):
        # Get foreign register of changes.
        api_location = source.split('/api')[0] + '/api'
        from ckanclient import CkanClient
        ckan_service = CkanClient(base_location=api_location)
        foreign_ids = ckan_service.changeset_register_get()
        if foreign_ids == None:
            msg = "Error pulling changes from: %s (CKAN service error: %s: %s)" % (source, ckan_service.last_url_error or "%s: %s" % (ckan_service.last_status, ckan_service.last_http_error), ckan_service.last_location)
            raise ChangesSourceException, msg
        # Get local register of changes.
        from ckan.model.changeset import ChangesetRegister
        changeset_register = ChangesetRegister()
        local_ids = changeset_register.keys()
        # Get list of unseen changes.
        unseen_ids = []
        for changeset_id in foreign_ids:
            if changeset_id not in local_ids:
                unseen_ids.append(changeset_id)
        print "There are %d new changesets." % len(unseen_ids)
        # Pull unseen changes from foreign register.
        unseen_changesets = []
        for unseen_id in unseen_ids:
            print "Pulling changeset %s..." % unseen_id
            unseen_data = ckan_service.changeset_entity_get(unseen_id)
            print "unseen changeset data: %s" % changeset_register.dumps(unseen_data)
            changeset_id = changeset_register.queue_incoming(unseen_data)
            if not changeset_id:
                msg = "Error: Couldn't add changeset %s to the queue." % changeset_id
                raise Exception, msg
            if unseen_id != changeset_id:
                msg = "Error: Queued changeset id mismatch (%s, %s)." % (unseen_id, changeset_id)
                raise Exception, msg

    def update(self):
        if len(self.args) > 1:
            changeset_id = unicode(self.args[1])
        else:
            changeset_id = None
        from ckan.model.changeset import ChangesetRegister
        from ckan.model.changeset import EmptyChangesetRegisterException
        from ckan.model.changeset import TipAtHeadException
        changeset_register = ChangesetRegister()
        updated_entities = []
        try:
            updated_entities = changeset_register.update(changeset_id)
        except EmptyChangesetRegisterException, inst:
            print "There are zero changesets in the changeset register."
            sys.exit(1)
        except TipAtHeadException, inst:
            print "The tip changeset is already at the head of its line."
            sys.exit(1)
        if updated_entities:
            print "The following entities were updated:"
        for entity in updated_entities:
            # Assume all are CKAN packages.
            print "package:    %s" % entity.name
            # Todo: Better update report.

    def commit(self):
        from ckan.model.changeset import ChangesetRegister
        changeset_register = ChangesetRegister()
        changesets = changeset_register.commit()
        for changeset in changesets:
            self.log_changeset(changeset)
            print ""

    def merge(self):
        if len(self.args) > 1:
            changeset_id = unicode(self.args[1])
        else:
            print "Need a target changeset to merge with tip."
            sys.exit(1)
        from ckan.model.changeset import ChangesetRegister
        from ckan.model.changeset import ConflictException
        from ckan.model.changeset import Heads
        changeset_register = ChangesetRegister()
        if not len(changeset_register):
            print "There are zero changesets in the changeset register."
            sys.exit(1)
        try:
            mergeset = changeset_register.merge(changeset_id)
        except ConflictException, inst:
            print inst
            sys.exit(1)
        print mergeset
        # Todo: Better merge report.

    def tip(self):
        from ckan.model.changeset import ChangesetRegister
        changeset_register = ChangesetRegister()
        changeset = changeset_register.get_tip()
        self.log_changeset(changeset)

    def log(self):
        if len(self.args) > 1:
            changeset_id = unicode(self.args[1])
        else:
            changeset_id = None
        from ckan.model.changeset import ChangesetRegister
        changeset_register = ChangesetRegister()
        if changeset_id:
            changeset = changeset_register[changeset_id]
            self.log_changeset(changeset)
            for change in changeset.changes:
                print change.ref
                print change.dumps(change.load_diff())
        else:
            changesets = changeset_register.values()
            changesets.reverse()  # Ordered by timestamp.
            for changeset in changesets:
                self.log_changeset(changeset)
                print ""

    def log_changeset(self, changeset):
        print "changeset:      %s" % changeset.id
        if changeset.is_tip:
            print "tag:            %s" % 'tip'
        if changeset.follows_id:
            print "follows:        %s" % changeset.follows_id
        if changeset.closes_id:
            print "closes:         %s" % changeset.closes_id
        user = str(changeset.get_meta().get('author', ''))
        if user:
            print "user:           %s" % user
        print "date:           %s" % changeset.timestamp.strftime('%c')
        summary = str(changeset.get_meta().get('log_message', ''))
        if summary:
            print "summary:        %s" % summary

    def apply_queue(self):
        from ckan.model.changeset import ChangesetRegister
        changeset_register = ChangesetRegister()
        queue = self.get_queue()
        if not queue:
            return
        print "Applying queued changesets..."
        for changeset in queue:
            if not changeset.is_conflicting():
                changeset.apply()
                print "applied changeset '%s' OK" % changeset.id
            else:
                print "held back (conflicting) '%s'" % changeset.id

    def get_queue(self):
        from ckan.model.changeset import ChangesetRegister
        register = ChangesetRegister()
        return [c for c in register.values() if not c.revision_id]

#    def print_status(self):
#        from ckan.model.changeset import ChangesetRegister
#        changeset_register = ChangesetRegister()
#        for changeset in self.get_queue():
#            status_flag = ' '
#            if changeset.status:
#                status_flag = changeset.status[0].upper()
#            if status_flag == 'Q' and not changeset.is_conflicting():
#                status_flag = 'R'
#            if status_flag == 'A' and not changeset.revision_id:
#                status_flag = 'E'
#            changes_flag = ''
#            for change in changeset.changes:
#                diff = change.get_diff()
#                if diff.new:
#                    changes_flag = '+'*len(diff.new) + changes_flag
#                if diff.old:
#                    changes_flag = changes_flag + "-"*len(diff.old)
#            print '%s  %s  %s' % (status_flag, changeset.id, changes_flag)
#
                
