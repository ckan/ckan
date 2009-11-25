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
    db upgrade [{version no.}] # Data migrate
    db dump {file-path} # dump to a file (json)
    db dump-rdf {package-name} {file-path}
    db simple-dump-csv {file-path}
    db simple-dump-json {file-path}
    db send-rdf {talis-store} {username} {password}
    db load {file-path} # load from a file
    db load-data4nr {file-path.csv}
    db load-esw {file-path.txt} [{host} {api-key}]
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
            self.load_data4nr(cmd)
        elif cmd == 'load-esw':
            self.load_esw(cmd)
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

    def dump_or_load(self, cmd):
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

    def load_data4nr(self, cmd):
        if len(self.args) < 2:
            print 'Need csv file path'
            return
        load_path = self.args[1]
        import ckan.getdata.data4nr
        data = ckan.getdata.data4nr.Data4Nr()
        data.load_csv_into_db(load_path)

    def simple_dump_csv(self, cmd):
        if len(self.args) < 2:
            print 'Need csv file path'
            return
        dump_filepath = self.args[1]
        import ckan.lib.dumper as dumper
        dump_file = open(dump_filepath, 'w')
        dumper.SimpleDumper().dump_csv(dump_file)

    def simple_dump_json(self, cmd):
        if len(self.args) < 2:
            print 'Need json file path'
            return
        dump_filepath = self.args[1]
        import ckan.lib.dumper as dumper
        dump_file = open(dump_filepath, 'w')
        dumper.SimpleDumper().dump_json(dump_file)

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
        # same name as user we create below
        rev.author = u'tester'
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

<http://ckan.net/>

'''
        pkg2 = model.Package(name=self.pkgname2)
        tag1 = model.Tag(name=u'russian')
        tag2 = model.Tag(name=u'tolstoy')
        pkg1.tags = [tag1, tag2]
        pkg2.tags = [ tag1 ]
        license1 = model.License.byName(u'OKD Compliant::Other')
        pkg1.license = license1
        pkg2.title = u'A Wonderful Story'
        pkg1._extras = {'genre':model.PackageExtra(key=u'genre', value='romantic novel'),
                        'original media':model.PackageExtra(key=u'original media', value='book')
                        }
        # api key
        model.User(name=u'tester', apikey=u'tester')
        # group
        david = model.Group(name=u'david',
                             title=u'Dave\'s books',
                             description=u'These are books that David likes.')
        roger = model.Group(name=u'roger',
                             title=u'Roger\'s books',
                             description=u'Roger likes these books.')
        david.packages = [pkg1, pkg2]
        roger.packages = [pkg1]
        # authz
        joeadmin = model.User(name=u'joeadmin')
        annafan = model.User(name=u'annafan', about=u'I love reading Annakarenina')
        russianfan = model.User(name=u'russianfan')
        testsysadmin = model.User(name=u'testsysadmin')
        model.repo.commit_and_remove()

        visitor = model.User.by_name(model.PSEUDO_USER__VISITOR)
        anna = model.Package.by_name(u'annakarenina')
        war = model.Package.by_name(u'warandpeace')
        model.setup_default_user_roles(anna, [annafan])
        model.setup_default_user_roles(war, [russianfan])
        model.add_user_to_role(visitor, model.Role.ADMIN, war)
        model.setup_default_user_roles(david, [russianfan])
        model.setup_default_user_roles(roger, [russianfan])
        model.add_user_to_role(visitor, model.Role.ADMIN, roger)

        model.repo.commit_and_remove()
    
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
        groups = (model.Group.by_name(u'david'), model.Group.by_name(u'roger'))
        for group in groups:
            if group:
                model.Session.delete(group)
        for key in model.User.query.filter_by(name=u'tester').all():
            key.purge()
        model.Session.commit()
        model.Session.remove()


class CreateSearchTestData(CkanCommand):
    '''Create searching test data in the DB.
    '''
    summary = __doc__.split('\n')[0]
    usage = __doc__
    
    items = [{'name':'gils',
              'title':'Government Information Locator Service',
              'url':'',
              'tags':'registry  country-usa  government  federal  gov  workshop-20081101',
              'groups':'ukgov test1 test2 penguin',
              'license':'OKD Compliant::Other',
              'notes':'''From <http://www.gpoaccess.gov/gils/about.html>
              
> The Government Information Locator Service (GILS) is an effort to identify, locate, and describe publicly available Federal
> Because this collection is decentralized, the GPO''',
              },
             {'name':'us-gov-images',
              'title':'U.S. Government Photos and Graphics',
              'url':'http://www.usa.gov/Topics/Graphics.shtml',
              'download_url':'http://www.usa.gov/Topics/Graphics.shtml',
              'tags':'images  graphics  photographs  photos  pictures  us  usa  america  history  wildlife  nature  war  military  todo-split  gov',
              'groups':'ukgov test1 penguin',
              'license':'OKD Compliant::Other',
              'notes':'''## About

Collection of links to different US image collections in the public domain.

## Openness

> Most of these images and graphics are available for use in the public domain, and''',
              },
             {'name':'usa-courts-gov',
              'title':'Text of US Federal Cases',
              'url':'http://bulk.resource.org/courts.gov/',
              'download_url':'http://bulk.resource.org/courts.gov/',
              'tags':'us  courts  case-law  us  courts  case-law  gov  legal  law  access-bulk  penguins penguin',
              'groups':'ukgov test2 penguin',
              'license':'OKD Compliant::Creative Commons CCZero',
              'notes':'''### Description

1.8 million pages of U.S. case law available with no restrictions. From the [README](http://bulk.resource.org/courts.gov/0_README.html):

> This file is  http://bulk.resource.org/courts.gov/0_README.html and was last revised''',
              },
             {'name':'uk-government-expenditure',
              'title':'UK Government Expenditure',
              'tags':'workshop-20081101  uk  gov  expenditure  finance  public  funding',
              'groups':'ukgov penguin',              
              'notes':'''Discussed at [Workshop on Public Information, 2008-11-02](http://okfn.org/wiki/PublicInformation).

Overview is available in Red Book, or Financial Statement and Budget Report (FSBR), [published by the Treasury](http://www.hm-treasury.gov.uk/budget.htm).'''
              },
             {'name':'se-publications',
              'title':'Sweden - Government Offices of Sweden - Publications',
              'url':'http://www.sweden.gov.se/sb/d/574',
              'groups':'penguin',              
              'tags':'country-sweden  format-pdf  access-www  documents  publications  government  eutransparency',
              'license':'Other::License Not Specified',
              'notes':'''### About

Official documents including "government bills and reports, information material and other publications".

### Reuse

Not clear.''',
              },
             {'name':'se-opengov',
              'title':'Opengov.se',
              'groups':'penguin',              
              'url':'http://www.opengov.se/',
              'download_url':'http://www.opengov.se/data/open/',
              'tags':'country-sweden  government  data',
              'licenses':'OKD Compliant::Creative Commons Attribution-ShareAlike',
              'notes':'''### About

From [website](http://www.opengov.se/sidor/english/):

> Opengov.se is an initiative to highlight available public datasets in Sweden. It contains a commentable catalog of government datasets, their formats and usage restrictions.

> The goal is to highlight the benefits of open access to government data and explain how this is done in practice.

### Openness

It appears that the website is under a CC-BY-SA license. Legal status of the data varies. Data that is fully open can be viewed at:

 * <http://www.opengov.se/data/open/>'''
              },
             ]

    def command(self):
        self._load_config()
        self._setup_app()
        if self.verbose:
            print 'Creating search test data'
        self.create()
        if self.verbose:
            print 'Creating search test data: Complete!'

    pkgname1 = u'annakarenina'
    pkgname2 = u'warandpeace'

    @classmethod
    def create(self):
        import ckan.model as model
        model.Session.remove()
        rev = model.repo.new_revision() 
        rev.author = u'tolkein'
        rev.message = u'Creating search test data.'
        self.pkgs = {}
        self.tags = {}
        self.groups = {}
        for item in self.items:
            pkg = model.Package(name=unicode(item['name']))
            for attr, val in item.items():
                if isinstance(val, str):
                    val = unicode(val)
                if attr=='name':
                    continue                
                if attr in ['title', 'version', 'url', 'download_url']:
                    setattr(pkg, attr, unicode(val))
                elif attr == 'tags':
                    for tag_name in val.split():
                        tag = self.tags.get(tag_name)
                        if not tag:
                            tag = model.Tag(name=tag_name)
                            self.tags[tag_name] = tag
                        pkg.tags.append(tag)
                elif attr == 'groups':
                    for group_name in val.split():
                        group = self.groups.get(group_name)
                        if not group:
                            group = model.Group(name=group_name)
                            self.groups[group_name] = group
                        pkg.groups.append(group)
                elif attr == 'license':
                    license = model.License.byName(val)
                    pkg.license = license
            self.pkgs[item['name']] = pkg
            model.setup_default_user_roles(pkg)
            rev = model.repo.new_revision() 
            rev.author = u'tolkein'
            rev.message = u'Creating search test data.'

        model.Session.commit()
        model.Session.remove()
    
    @classmethod
    def delete(self):
        import ckan.model as model
        for pkg_name, pkg in self.pkgs.items():
            pkg.purge()
        for tag_name, tag in self.tags.items():
            tag.purge()

        revs = model.Revision.query.filter_by(author=u'tolkein')
        for rev in revs:
            model.Session.delete(rev)
        model.Session.commit()
        model.Session.remove()

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

        num_pkg = model.Package.query().count()
        print '* Number of packages: ', num_pkg
        assert num_pkg > 0

        num_tag = model.Tag.query().count()
        print '* Number of tags: ', num_tag
        assert num_tag > 0

        pkg = model.Package.query().first()
        print '* A package: ', repr(pkg)
        expected_attributes = ('name', 'title', 'notes', 'url', 'download_url')
        for ea in expected_attributes:
            print '* Checking for attribute ', ea
            assert ea in pkg.__dict__.keys()

        tag = model.Tag.query().first()
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


        res = check_page('/', ('Search', 'New'))
        form = res.forms[0]
        form['q'] = pkg.name
        res = form.submit()
        print '* Checking search'
        assert ('package found' in res) or ('packages found' in res), res

        res = res.click(pkg.name)
        print '* Checking package page %s' % res.request.url
        assert pkg.title in res, res
        for tag in pkg.tags:
            assert tag.name in res, res
        assert pkg.license.name in res, res

        tag = pkg.tags[0]
        res = res.click(tag.name)
        print '* Checking tag %s' % res.request.url
        assert 'Tag: %s' % str(tag.name) in res, res
        assert str(pkg.name) in res, res
        
        res = check_page('/package/new', 'Register a New Package')
        
        res = check_page('/package/list', 'Packages')

        res = check_page('/api/search/package?tags=gov+us+legal', '{"count": 1, "results": ["usa-courts-gov"]}')


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
        sysadmins = model.SystemRole.query.filter_by(role=model.Role.ADMIN).all()
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
        for pkg in model.Package.query.all():
            pkg_dict = pkg.as_dict()
            SearchVectorTrigger().update_package_vector(pkg_dict, engine)
