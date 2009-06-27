import os

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
    db drop  # same as db clean
    db migrate06
    db migrate09a
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
        elif cmd == 'dump' or cmd == 'load':
            self.dump_or_load(cmd)
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
        else:
            print 'Command %s not recognized' % cmd

    def dump_or_load(self, cmd):
        if len(self.args) < 2:
            print 'Need dump path'
            return
        dump_path = self.args[1]
        import ckan.lib.converter
        dumper = ckan.lib.converter.Dumper()
        if cmd == 'load':
            dumper.load(dump_path, verbose=self.verbose)
        elif cmd == 'dump':
            dumper.dump(dump_path, verbose=self.verbose)
        else:
            print 'Unknown command', cmd


class CreateTestData(CkanCommand):
    '''Create test data in the DB.
    '''
    summary = __doc__.split('\n')[0]
    usage = __doc__


    def command(self):
        self._load_config()
        self._setup_app()
        if self.verbose:
            print 'Creating test data'
        self.create()
        if self.verbose:
            print 'Creating test data: Complete!'

    pkgname1 = u'annakarenina'
    pkgname2 = u'warandpeace'

    @classmethod
    def create(self):
        import ckan.model as model
        model.Session.remove()
        rev = model.repo.new_revision() 
        rev.author = u'tolstoy'
        rev.message = u'''Creating test data.
 * Package: annakarenina
 * Package: warandpeace
 * Associated tags, etc etc
'''
        pkg1 = model.Package(name=self.pkgname1)
        pkg1.title = u'A Novel By Tolstoy'
        pkg1.version = u'0.7a'
        pkg1.url = u'http://www.annakarenina.com'
        # put an & in the url string to test escaping
        pkg1.download_url = u'http://www.annakarenina.com/download/x=1&y=2'
        pkg1.notes = u'''Some test notes

### A 3rd level heading

**Some bolded text.**

*Some italicized text.*
'''
        pkg2 = model.Package(name=self.pkgname2)
        tag1 = model.Tag(name=u'russian')
        tag2 = model.Tag(name=u'tolstoy')
        license1 = model.License.byName(u'OKD Compliant::Other')
        pkg1.tags = [tag1, tag2]
        pkg1.license = license1
        pkg2.tags = [ tag1 ]
        # api key
        model.ApiKey(name=u'tester', key=u'tester')
        model.Session.commit()
        model.Session.remove()
    
    @classmethod
    def delete(self):
        import ckan.model as model
        pkg = model.Package.by_name(self.pkgname1)
        if pkg:
            pkg.purge()
        pkg2 = model.Package.by_name(self.pkgname2)
        if pkg2:
            pkg2.purge()
        tag1 = model.Tag.by_name(u'russian')
        tag2 = model.Tag.by_name(u'tolstoy')
        if tag1:
            tag1.purge()
        if tag2:
            tag2.purge()
        revs = model.Revision.query.filter_by(author=u'tolstoy')
        for rev in revs:
            model.Session.delete(rev)
        for key in model.ApiKey.query.filter_by(name=u'tester').all():
            key.purge()
        model.Session.commit()
        model.Session.remove()

