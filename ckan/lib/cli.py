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
    
    db create
    db init
    db clean
    db drop  # same as db clean
    '''
    summary = __doc__.split('\n')[0]
    usage = __doc__
    max_args = None
    min_args = 1

    def command(self):
        self._load_config()
        cmd = self.args[0]
        if cmd == 'create':
            self._setup_app()
        elif cmd == 'clean' or cmd == 'drop':
            self.clean()
        elif cmd == 'dump':
            self.dump()
        elif cmd == 'load':
            if len(self.args) < 2:
                print 'Need dump path'
                return
            dump_path = self.args[1]
            import ckan.lib.converter
            ckan.lib.converter.load_from_dump(dump_path)
        else:
            print 'Command %s not recognized' % cmd

    def clean(self):
        from ckan import model
        model.metadata.drop_all()
        if self.verbose:
            print 'Cleaning DB: SUCCESS' 


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
        rev = model.new_revision() 
        rev.author = u'tolstoy'
        rev.message = u'''Creating test data.
 * Package: annakarenina
 * Package: warandpeace
 * Associated tags, etc etc
'''
        pkg1 = model.Package(name=self.pkgname1)
        pkg1.title = u'A Novel By Tolstoy'
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
        pkg2.tags = [ tag1, tag2 ]
        model.Session.commit()
        model.Session.remove()
    
    @classmethod
    def delete(self):
        import ckan.model as model
        pkg = model.Package.by_name(self.pkgname1)
        pkg.purge()
        pkg2 = model.Package.by_name(self.pkgname2)
        pkg2.purge()
        tag1 = model.Tag.by_name(u'russian')
        tag2 = model.Tag.by_name(u'tolstoy')
        tag1.purge()
        tag2.purge()
        model.Session.commit()
        model.Session.remove()

