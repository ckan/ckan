import os
import sys
import logging

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
        # Avoids vdm logging warning
        logging.basicConfig(level=logging.ERROR)
        
        self._load_config()
        from ckan import model

        cmd = self.args[0]
        if cmd == 'create':
            model.repo.create_db()
            if self.verbose:
                print 'Creating DB: SUCCESS'
        elif cmd == 'init':
            model.repo.init_db()
            if self.verbose:
                print 'Initialising DB: SUCCESS'
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
        assert pkg.license in res, res

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
            user = model.User(name=unicode(username))
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


class Changes(CkanCommand):
    '''Distribute changes

    Usage:
      changes commit                 - creates changesets for any outstanding revisions
      changes diff [[start] stop]    - prints sum of changes for any outstanding revisions
      changes heads                  - display the last changeset of all active lines
      changes log [changeset]        - display summary of changeset(s)
      changes merge [target] [mode]  - creates mergeset to follow target changeset and to close the working changeset
      changes update [target]        - updates repository entities to target changeset (defaults to working line's head)
      changes moderate [target]      - updates repository entities whilst allowing for changes to be ignored
      changes pull [sources]         - pulls unseen changesets from changeset sources
      changes working                - display working changeset
    '''
      # Todo:
      #changes branch [name]          - sets or displays the current branch
      #changes branches               - displays all known branches
      #changes push [sinks]           - pushes new changesets to changeset sinks
      #changes status                 - prints sum of changes for any outstanding revisions

    summary = __doc__.split('\n')[0]
    usage = __doc__
    max_args = 3
    min_args = 1
    CkanCommand.parser.add_option('-i', '--interactive',
        action='store_true',
        dest='is_interactive',
        default=False,
        help="Prompt for confirmation of actions.")


    def command(self):
        self._load_config()
        from ckan import model
        cmd = self.args[0]
        if cmd == 'pull':
            self.pull()
        elif cmd == 'heads':
            self.heads()
        elif cmd == 'update':
            self.update()
        elif cmd == 'moderate':
            self.moderate()
        elif cmd == 'commit':
            self.commit()
        elif cmd == 'merge':
            self.merge()
        elif cmd == 'working':
            self.working()
        elif cmd == 'log':
            self.log()
        elif cmd == 'diff':
            self.diff()
        else:
            print 'Command %s not recognized' % cmd

    def _load_config(self):
        super(Changes, self)._load_config()
        import logging
        logging.basicConfig()
        logger_vdm = logging.getLogger('vdm')
        logger_vdm.setLevel(logging.ERROR)


    def pull(self):
        if len(self.args) > 1:
            sources = [unicode(self.args[1])]
        else:
            from pylons import config
            sources = config.get('changeset.sources', '').strip().split(',')
        sources = [s.strip() for s in sources if s.strip()]
        if not sources:
            print "No changes source to pull (set 'changeset.sources' in config)."
            return
        from ckan.model.changeset import ChangesetRegister
        from ckan.model.changeset import ChangesSourceException
        changeset_register = ChangesetRegister()
        is_error = False
        for source in sources:
            try:
                changesets = changeset_register.pull(source)
            except ChangesSourceException, inst:
                print "%s" % inst
            else:
                print "Pulled %s changeset%s from '%s'." % (
                    len(changesets), 
                    (len(changesets) == 1 and "" or "s"),
                    source
                )
        if is_error:
            sys.exit(1)

    def heads(self):
        from ckan.model.changeset import Heads
        from ckan.model.changeset import ChangesetRegister
        print "Most recent changeset for each active line:"
        ids = Heads().ids()
        ids.reverse()  # Ordered by timestamp.
        changeset_register = ChangesetRegister()
        for id in ids:
            head = changeset_register.get(id)
            print ""
            self.log_changeset(head)

    def update(self):
        if len(self.args) > 1:
            changeset_id = unicode(self.args[1])
        else:
            changeset_id = None
        self.update_repository(changeset_id)

    def moderate(self):
        if len(self.args) > 1:
            changeset_id = unicode(self.args[1])
        else:
            changeset_id = None
        self.options.is_interactive = True
        self.update_repository(changeset_id)

    def update_repository(self, changeset_id):
        from ckan.model.changeset import ChangesetRegister
        from ckan.model.changeset import EmptyChangesetRegisterException
        from ckan.model.changeset import UncommittedChangesException
        from ckan.model.changeset import WorkingAtHeadException
        from ckan.model.changeset import ConflictException
        changeset_register = ChangesetRegister()
        report = {
            'created': [],
            'updated': [],
            'deleted': [],
        }
        try:
            changeset_register.update(
                target_id=changeset_id,
                report=report, 
                moderator=self.options.is_interactive and self or None,
            )
        except ConflictException, inst:
            print "Update aborted due to conflict with the working model."
            print inst
            sys.exit(1)
        except EmptyChangesetRegisterException, inst:
            print "Nothing to update (changeset register is empty)."
            sys.exit(0)
        except WorkingAtHeadException, inst:
            print inst
            sys.exit(0)
        except UncommittedChangesException, inst:
            print "There are uncommitted revisions (run 'changes commit')."
            sys.exit(1)
        print ", ".join(["%s %s packages" % (key, len(val)) for (key, val) in report.items()])
        if report['created']:
            print ""
            print "The following packages have been created:"
            names = []
            for entity in report['created']:
                if not entity:
                    continue
                if entity.name in names:
                    continue
                print "package:    %s" % entity.name
                names.append(entity.name)
        if report['updated']:
            print ""
            print "The following packages have been updated:"
            names = []
            for entity in report['updated']:
                if not entity:
                    continue
                if entity.name in names:
                    continue
                print "package:    %s" % entity.name
                names.append(entity.name)
        if report['deleted']:
            print ""
            print "The following packages have been deleted:"
            names = []
            for entity in report['deleted']:
                if not entity:
                    continue
                if entity.name in names:
                    continue
                print "package:    %s" % entity.name
                names.append(entity.name)

    def moderate_changeset_apply(self, changeset):
        self.log_changeset(changeset)
        answer = None
        while answer not in ['y', 'n']:
            print ""
            question = "Do you want to apply this changeset? [Y/n/d] "
            try:
                answer = raw_input(question).strip() or 'y'
            except KeyboardInterrupt:
                print ""
                print ""
                return False
            print ""
            answer = answer[0].lower()
            if answer == 'd':
                print "Change summary:"
                print ""
                print "diff %s %s" % (changeset.follows_id, changeset.id)
                self.print_changes(changeset.changes)
        return answer == 'y'

    def moderate_change_apply(self, change):
        print "Change summary:"
        self.print_changes([change])
        print ""
        answer = raw_input("Do you want to apply this change? [Y/n] ").strip() or "y"
        answer = answer[0].lower()
        print ""
        if answer == 'y':
            return True
        else:
            print 
            answer = raw_input("Do you want to mask changes to this ref? [Y/n] ").strip() or "y"
            answer = answer[0].lower()
            print ""
            if answer == 'y':
                from ckan.model.changeset import ChangemaskRegister, Session
                register = ChangemaskRegister()
                mask = register.create_entity(change.ref)
                Session.add(mask)
                Session.commit()
                print "Mask has been set for ref: %s" % change.ref
                print ""
            else:
                print "Warning: Not setting a mask after not applying changes may lead to conflicts."
                import time
                time.sleep(5)
                print ""

    def commit(self):
        from ckan.model.changeset import ChangesetRegister
        changeset_register = ChangesetRegister()
        changeset_ids = changeset_register.commit()
        print "Committed %s revision%s." % (len(changeset_ids), (len(changeset_ids) != 1) and "s" or "")

    def merge(self):
        if len(self.args) == 3:
            closing_id = unicode(self.args[1])
            continuing_id = unicode(self.args[2])
        elif len(self.args) == 2:
            working_changeset = self.get_working_changeset()
            if not working_changeset:
                print "There is no working changeset to merge into '%s'." % continuing_id
                sys.exit(1)
            closing_id = working_changeset.id
            continuing_id = unicode(self.args[1])
        else:
            print "Need a target changeset to merge into."
            sys.exit(1)
        from ckan.model.changeset import ChangesetRegister
        from ckan.model.changeset import ConflictException
        from ckan.model.changeset import Heads
        from ckan.model.changeset import Resolve, CliResolve
        changeset_register = ChangesetRegister()
        if not len(changeset_register):
            print "There are zero changesets in the changeset register."
            sys.exit(1)
        try:
            resolve_class = self.options.is_interactive and CliResolve or Resolve
            mergeset = changeset_register.merge(
                closing_id=closing_id,
                continuing_id=continuing_id,
                resolve_class=resolve_class,
            )
            # Todo: Update repository before commiting changeset?
            self.update_repository(mergeset.id)
            print ""
        except ConflictException, inst:
            print inst
            sys.exit(1)
        else:
            self.log_changeset(mergeset)
        # Todo: Better merge report.

    def working(self):
        working_changeset = self.get_working_changeset()
        if working_changeset:
            print "Last updated or committed changeset:"
            print ""
            self.log_changeset(working_changeset)
        else:
            print "There is no working changeset."

    def get_working_changeset(self):
        from ckan.model.changeset import ChangesetRegister
        changeset_register = ChangesetRegister()
        return changeset_register.get_working()

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
            self.print_changes(changeset.changes)
        else:
            changesets = changeset_register.values()
            changesets.reverse()  # Ordered by timestamp.
            for changeset in changesets:
                self.log_changeset(changeset)
                print ""

    def log_changeset(self, changeset):
        print "Changeset:    %s %s" % (changeset.is_working and "@" or " ", changeset.id)
        if changeset.branch and changeset.branch != 'default':
            print "branch:         %s" % changeset.branch
        if changeset.follows_id:
            print "follows:        %s" % changeset.follows_id
        if changeset.closes_id:
            print "closes:         %s" % changeset.closes_id
        user = str(changeset.get_meta().get('author', ''))
        if user:
            print "user:           %s" % user
        print "date:           %s +0000" % changeset.timestamp.strftime('%c')
        if changeset.revision_id:
            print "revision:       %s" % changeset.revision_id
        summary = str(changeset.get_meta().get('log_message', ''))
        if summary:
            print "summary:        %s" % summary.split('\n')[0]

    def diff(self):
        if len(self.args) > 2:
            changeset_id1 = unicode(self.args[1])
            changeset_id2 = unicode(self.args[2])
        elif len(self.args) > 1:
            working_changeset = self.get_working_changeset()
            if not working_changeset:
                print "There is no working changeset."
                sys.exit(1)
            print "Displaying changes from the working changeset (without any outstanding revisions)..."
            changeset_id1 = working_changeset.id 
            changeset_id2 = unicode(self.args[1])
        else:
            # Todo: Calc changes for outstanding revisions.
            print "Sorry, displaying changes of uncommitted revisions is not yet supported."
            print ""
            print "Providing one target changeset will display the changes from the working changeset. Providing two target changesets will display the sum of changes between the first and the second target."
            sys.exit(1)
        from ckan.model.changeset import NoIntersectionException
        from ckan.model.changeset import ChangesetRegister, Route, Reduce
        register = ChangesetRegister()
        changeset1 = register.get(changeset_id1, None)
        if not changeset1:
            print "Changeset '%s' not found." % changeset_id1
            sys.exit(1)
        changeset2 = register.get(changeset_id2, None)
        if not changeset2:
            print "Changeset '%s' not found." % changeset_id2
            sys.exit(1)
        route = Route(changeset1, changeset2)
        try:
            changes = route.calc_changes()
            # Todo: Calc and sum with changes for outstanding revisions.
            changes = Reduce(changes).calc_changes()
        except NoIntersectionException:
            print "The changesets '%s' and '%s' are not on intersecting lines." % (
                changeset_id1, changeset_id2
            )
        else:
   
            print "diff %s %s" % (changeset_id1, changeset_id2) 
            self.print_changes(changes)
        
    def print_changes(self, changes):
        deleting = []
        updating = []
        creating = []
        # Todo: Refactor with identical ordering routine in apply_changes().
        for change in changes:
            if change.old == None and change.new != None:
                creating.append(change)
            elif change.old != None and change.new != None:
                updating.append(change)
            elif change.old != None and change.new == None:
                deleting.append(change)
        # Todo: Also sort changes by ref before printing, so they always appear in the same way. 
        for change in deleting:
            print ""
            print "D %s" % change.ref
            attr_names = change.old.keys()
            attr_names.sort()
            for attr_name in attr_names:
                old_value = change.old[attr_name]
                if old_value:
                    msg = "D @%s:  %s" % (attr_name, repr(old_value))
                    print msg.encode('utf8')
        for change in updating:
            print ""
            print "M %s" % change.ref
            attr_names = change.old.keys()
            attr_names.sort()
            for attr_name in attr_names:
                if attr_name in change.new:
                    old_value = change.old[attr_name]
                    new_value = change.new[attr_name]
                    msg = "M @%s:  %s  ----->>>   %s" % (attr_name, repr(old_value), repr(new_value))
                    print msg.encode('utf8')
        for change in creating:
            print ""
            print "A %s" % change.ref
            attr_names = change.new.keys()
            attr_names.sort()
            for attr_name in attr_names:
                new_value = change.new[attr_name]
                if new_value:
                    msg = "A @%s:  %s" % (attr_name, repr(new_value))
                    print msg.encode('utf8')

 
