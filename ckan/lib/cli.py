import os
import sys
import logging

import paste.script
from paste.script.util.logging_config import fileConfig
import re

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
        try:
            fileConfig(self.filename)
        except Exception: pass
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
    db load {file-path} # load a dump from a file
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


class SearchIndexCommand(CkanCommand):
    '''Creates a search index for all packages

    Usage:
      search-index rebuild                 - indexes all packages
    '''

    summary = __doc__.split('\n')[0]
    usage = __doc__
    max_args = 1
    min_args = 0

    def command(self):
        self._load_config()
        from ckan.lib.search import rebuild

        if not self.args:
            # default to run
            cmd = 'rebuild'
        else:
            cmd = self.args[0]
        
        if cmd == 'rebuild':
            rebuild()
        else:
            print 'Command %s not recognized' % cmd


class Sysadmin(CkanCommand):
    '''Gives sysadmin rights to a named 

    Usage:
      sysadmin list                 - lists sysadmins
      sysadmin add <user-name>      - add a user as a sysadmin
      sysadmin remove <user-name>   - removes user from sysadmins
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
        elif cmd == 'add':
            self.add()
        elif cmd == 'remove':
            self.remove()
        else:
            print 'Command %s not recognized' % cmd

    def list(self):
        from ckan import model
        print 'Sysadmins:'
        sysadmins = model.Session.query(model.SystemRole).filter_by(role=model.Role.ADMIN).all()
        for sysadmin in sysadmins:
            print 'name=%s id=%s' % (sysadmin.user.name, sysadmin.user.id)

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
                print('Creating %s user' % username)
                user = model.User(name=unicode(username))
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
      changes update [target]        - updates repository entities to target changeset (defaults to working line\'s head)
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

 
class Notifications(CkanCommand):
    '''Manage notifications

    Usage:
      notifications monitor                 - runs monitor, printing all notifications
    '''

    summary = __doc__.split('\n')[0]
    usage = __doc__
    max_args = 1
    min_args = 1

    def command(self):
        self._load_config()
        from ckan import model
        
        from pylons import config
        if config.get('carrot_messaging_library') != 'pyamqplib':
            print 'Carrot messaging library not configured to AMQP. Currently set to:', config.get('carrot_messaging_library')
            sys.exit(1)
        
        cmd = self.args[0]
        if cmd == 'monitor':
            self.monitor()
        else:
            print 'Command %s not recognized' % cmd

    def monitor(self):
        from ckan.lib import monitor
        monitor = monitor.Monitor()

class Load(CkanCommand):
    '''Load data to a remote CKAN instance.

    load bis {filepath.xls} {ckan-api-url} {api-key}
    load ons {number_of_days_worth} {ckan-api-url} {api-key}
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

        data_type = self.args[0]
        if data_type == 'bis':
            if len(self.args) != 4:
                print 'Error: Wrong number of arguments for data type: %s' % data_type
                print self.usage
                sys.exit(1)
            filepath, api_url, api_key = self.args[1:]
            assert api_url.startswith('http://') and api_url.endswith('/api'), api_url
            # import them
            from ckanext.dgu.bis.bis import BisImporter, BisLoader
            importer = BisImporter(filepath=filepath)
            loader = BisLoader
        elif data_type == 'ons':
            from ckanext.dgu.ons.importer import OnsImporter
            from ckanext.dgu.ons.loader import OnsLoader
            from ckanext.dgu.ons.downloader import OnsData
            if len(self.args) != 4:
                print 'Error: Wrong number of arguments for data type: %s' % data_type
                print self.usage
                sys.exit(1)
            days, api_url, api_key = self.args[1:]
            days = int(days)
            assert api_url.startswith('http://') and api_url.endswith('/api'), api_url
            # download data
            ons_data = OnsData()
            url, url_name = ons_data._get_url_recent(days=days)
            data_filepath = ons_data.download(url, url_name, force_download=True)
            
            # import them
            importer = OnsImporter(filepath=data_filepath)
            loader = OnsLoader
        else:
            print 'Error: Data type %r not recognised' % data_type
            print self.usage
            sys.exit(1)

        pkg_dicts = [pkg_dict for pkg_dict in importer.pkg_dict()]
        print '%i packages' % len(pkg_dicts)
        if pkg_dicts:
            #raw_input('Press return to load packages')
            print 'Loading packages...'
            # load them
            from ckanclient import CkanClient
            client = CkanClient(api_key=api_key, base_location=api_url,
                                is_verbose=False)
            loader = loader(client)
            res = loader.load_packages(pkg_dicts)
            if res['num_errors'] == 0 and res['num_loaded']:
                print 'SUCCESS'
            else:
                print '%i ERRORS' % res['num_errors']
            print '%i package loaded' % res['num_loaded']

            if res['num_loaded']:
                #raw_input('Press return to add them to the ukgov group')

                # add them to the group
                print 'Adding them to the ukgov group...'
                loader.add_pkgs_to_group(res['pkg_names'], 'ukgov')
                print '...SUCCESS'

class Harvester(CkanCommand):
    '''Harvests remotely mastered metadata

    Usage:
      harvester source {url} [{user-ref} [{publisher-ref}]]     
        - create new harvest source

      harvester sources                                 
        - lists harvest sources

      harvester job {source-id} [{user-ref}]
        - create new harvesting job

      harvester jobs
        - lists harvesting jobs

      harvester run
        - runs harvesting jobs
    '''

    summary = __doc__.split('\n')[0]
    usage = __doc__
    max_args = 4
    min_args = 0

    def command(self):
        self._load_config()
        # Clear the 'No handlers could be found for logger "vdm"' warning message.
        print ""
        cmd = self.args[0]
        if cmd == 'source':
            if len(self.args) >= 2:
                url = unicode(self.args[1])
            else:
                print self.usage
                print 'Error, source url is not given.'
                sys.exit(1)
            if len(self.args) >= 3:
                user_ref = unicode(self.args[2])
            else:
                user_ref = u''
            if len(self.args) >= 4:
                publisher_ref = unicode(self.args[3])
            else:
                publisher_ref = u''
            self.register_harvest_source(url, user_ref, publisher_ref)
        elif cmd == 'sources':
            self.list_harvest_sources()
        elif cmd == 'job':
            if len(self.args) >= 2:
                source_id = unicode(self.args[1])
            else:
                print self.usage
                print 'Error, job source is not given.'
                sys.exit(1)
            if len(self.args) >= 3:
                user_ref = unicode(self.args[2])
            else:
                user_ref = u''
            self.register_harvesting_job(source_id, user_ref)
        elif cmd == 'jobs':
            self.list_harvesting_jobs()
        elif cmd == 'run':
            self.run_harvester()
        else:
            print 'Command %s not recognized' % cmd

    def _load_config(self):
        super(Harvester, self)._load_config()
        import logging
        logging.basicConfig()
        logger_vdm = logging.getLogger('vdm')
        logger_vdm.setLevel(logging.ERROR)

    def run_harvester(self, *args, **kwds):
        from pylons.i18n.translation import _get_translator
        import pylons
        pylons.translator._push_object(_get_translator(pylons.config.get('lang')))

        from ckan.model import HarvestingJob
        from ckan.controllers.harvesting import HarvestingJobController
        jobs = HarvestingJob.filter(status=u"New").all()
        jobs_len = len(jobs)
        jobs_count = 0
        if jobs_len:
            print "Running %s harvesting jobs..." % jobs_len
        else:
            print "There are no new harvesting jobs."
        print ""
        for job in jobs:
            jobs_count += 1
            print "Running job %s/%s: %s" % (jobs_count, jobs_len, job.id)
            self.print_harvesting_job(job)
            job_controller = HarvestingJobController(job)
            job_controller.harvest_documents()

    def register_harvesting_job(self, source_id, user_ref):
        from ckan.model import HarvestSource
        from ckan.model import HarvestingJob
        if re.match('(http|file)://', source_id):
            source_url = unicode(source_id)
            source_id = None
            sources = HarvestSource.filter(url=source_url).all()
            if sources:
                source = sources[0]
            else:
                source = self.create_harvest_source(url=source_url, user_ref=user_ref, publisher_ref=u'')
        else:
            source = HarvestSource.get(source_id)

        job = HarvestingJob(
            source=source,
            user_ref=user_ref,
            status=u"New",
        )
        job.save()
        print "Created new harvesting job:"
        self.print_harvesting_job(job)
        status = u"New"
        jobs = HarvestingJob.filter(status=status).all()
        self.print_there_are("harvesting job", jobs, condition=status)

    def register_harvest_source(self, url, user_ref, publisher_ref):
        from ckan.model import HarvestSource
        existing = self.get_harvest_sources(url=url)
        if existing:
            print "Error, there is already a harvesting source for that URL"
            self.print_harvest_sources(existing)
            sys.exit(1)
        else:
            source = self.create_harvest_source(url=url, user_ref=user_ref, publisher_ref=publisher_ref)
            print "Created new harvest source:"
            self.print_harvest_source(source)
            sources = self.get_harvest_sources()
            self.print_there_are("harvest source", sources)

    def list_harvest_sources(self):
        sources = self.get_harvest_sources()
        self.print_harvest_sources(sources)
        self.print_there_are(what="harvest source", sequence=sources)
       
    def list_harvesting_jobs(self):
        jobs = self.get_harvesting_jobs()
        self.print_harvesting_jobs(jobs)
        self.print_there_are(what="harvesting job", sequence=jobs)

    def get_harvest_sources(self, **kwds):
        from ckan.model import HarvestSource
        return HarvestSource.filter(**kwds).all()

    def get_harvesting_jobs(self, **kwds):
        from ckan.model import HarvestingJob
        return HarvestingJob.filter(**kwds).all()

    def create_harvest_source(self, **kwds):
        from ckan.model import HarvestSource
        source = HarvestSource(**kwds)
        source.save()
        return source

    def create_harvesting_job(self, **kwds):
        from ckan.model import HarvestingJob
        job = HarvestingJob(**kwds)
        job.save()
        return job

    def print_harvest_sources(self, sources):
        if sources:
            print ""
        for source in sources:
            self.print_harvest_source(source)

    def print_harvest_source(self, source):
        print "Source id: %s" % source.id
        print "      url: %s" % source.url
        print "     user: %s" % source.user_ref
        print "publisher: %s" % source.publisher_ref
        print "     docs: %s" % len(source.documents)
        print ""

    def print_harvesting_jobs(self, jobs):
        if jobs:
            print ""
        for job in jobs:
            self.print_harvesting_job(job)

    def print_harvesting_job(self, job):
        print "Job id: %s" % job.id
        if job.user_ref:
            print "  user: %s" % job.user_ref
        print "status: %s" % job.status
        print "source: %s" % job.source.id
        print "   url: %s" % job.source.url
        #print "report: %s" % job.report
        if job.report and job.report['packages']:
            for package_id in job.report['packages']:
                print "   doc: %s" % package_id
        if job.report and job.report['errors']:
            for msg in job.report['errors']:
                print " error: %s" % msg
        print ""

    def print_there_are(self, what, sequence, condition=""):
        is_singular = self.is_singular(sequence)
        print "There %s %s %s%s%s" % (
            is_singular and "is" or "are",
            len(sequence),
            condition and ("%s " % condition.lower()) or "",
            what,
            not is_singular and "s" or "",
        )

    def is_singular(self, sequence):
        return len(sequence) == 1
    
