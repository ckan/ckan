import cli

class CreateTestData(cli.CkanCommand):
    '''Create test data in the database.
    Tests can also delete the created objects easily with the delete() method.

    create-test-data         - annakarenina and warandpeace
    create-test-data search  - realistic data to test search
    create-test-data gov     - government style data
    create-test-data family  - package relationships data
    create-test-data user    - create a user 'tester' with api key 'tester'
    '''
    summary = __doc__.split('\n')[0]
    usage = __doc__
    max_args = 1
    min_args = 0
    author = u'tester'

    pkg_names = []
    tag_names = []
    group_names = set()
    user_names = []
    
    pkg_core_fields = ['name', 'title', 'version', 'url', 'notes',
                       'author', 'author_email',
                       'maintainer', 'maintainer_email',
                       ]

    def command(self):
        self._load_config()
        self._setup_app()
        if self.args:
            cmd = self.args[0]
        else:
            cmd = 'basic'
        if self.verbose:
            print 'Creating %s test data' % cmd
        if cmd == 'basic':
            self.create_basic_test_data()
        elif cmd == 'user':
            self.create_user()
        elif cmd == 'search':
            self.create_search_test_data()
        elif cmd == 'gov':
            self.create_gov_test_data()
        elif cmd == 'family':
            self.create_family_test_data()
        else:
            print 'Command %s not recognized' % cmd
            raise NotImplementedError
        if self.verbose:
            print 'Creating %s test data: Complete!' % cmd

    @classmethod
    def create_basic_test_data(self):
        self.create()

    @classmethod
    def create_search_test_data(self):
        self.create_arbitrary(search_items)

    @classmethod
    def create_gov_test_data(self, extra_users=[]):
        self.create_arbitrary(gov_items, extra_user_names=extra_users)

    @classmethod
    def create_family_test_data(self, extra_users=[]):
        self.create_arbitrary(family_items,
                              relationships=family_relationships,
                              extra_user_names=extra_users)

    @classmethod
    def create_user(self):
        import ckan.model as model
        tester = model.User.by_name(u'tester')
        if tester is None:
            tester = model.User(name=u'tester', apikey=u'tester')
            model.Session.add(tester)
            model.Session.commit()
        model.Session.remove()
        self.user_names = [u'tester']

    @classmethod
    def create_arbitrary(self, package_dicts, relationships=[],
            extra_user_names=[], extra_group_names=[], 
            commit_changesets=False, admins=[]):
        '''Creates packages and a few extra objects as well at the
        same time if required.
        @param package_dicts - a list of dictionaries with the package
                               properties
        @param extra_group_names - a list of group names to create. No
                               properties get set though.
        '''
        assert isinstance(relationships, (list, tuple))
        assert isinstance(extra_user_names, (list, tuple))
        assert isinstance(extra_group_names, (list, tuple))
        import ckan.model as model
        model.Session.remove()
        new_user_names = extra_user_names
        new_group_names = set()
        
        rev = model.repo.new_revision() 
        rev.author = self.author
        rev.message = u'Creating test packages.'
        
        admins_list = [] # list of (package_name, admin_names)
        if package_dicts:
            if isinstance(package_dicts, dict):
                package_dicts = [package_dicts]
            for item in package_dicts:
                pkg_dict = {}
                for field in self.pkg_core_fields:
                    if item.has_key(field):
                        pkg_dict[field] = unicode(item[field])
                pkg = model.Package(**pkg_dict)
                model.Session.add(pkg)
                for attr, val in item.items():
                    if isinstance(val, str):
                        val = unicode(val)
                    if attr=='name':
                        continue                
                    if attr in self.pkg_core_fields:
                        pass
                    elif attr == 'download_url':
                        pkg.add_resource(unicode(val))
                    elif attr == 'resources':
                        assert isinstance(val, (list, tuple))
                        for res_dict in val:
                            pkg.add_resource(
                                url=unicode(res_dict['url']),
                                format=unicode(res_dict.get('format')),
                                description=unicode(res_dict.get('description')),
                                hash=unicode(res_dict.get('hash')),
                                )
                    elif attr == 'tags':
                        if isinstance(val, (str, unicode)):
                            tags = val.split()
                        elif isinstance(val, list):
                            tags = val
                        else:
                            raise NotImplementedError
                        for tag_name in tags:
                            tag_name = unicode(tag_name)
                            tag = model.Tag.by_name(tag_name)
                            if not tag:
                                tag = model.Tag(name=tag_name)
                                self.tag_names.append(tag_name)
                                model.Session.add(tag)    
                            pkg.tags.append(tag)
                    elif attr == 'groups':
                        if isinstance(val, (str, unicode)):
                            group_names = val.split()
                        elif isinstance(val, list):
                            group_names = val
                        else:
                            raise NotImplementedError
                        for group_name in group_names:
                            group = model.Group.by_name(unicode(group_name))
                            if not group:
                                group = model.Group(name=unicode(group_name))
                                model.Session.add(group)
                                new_group_names.add(group_name)
                            pkg.groups.append(group)
                    elif attr == 'license':
                        pkg.license_id = val
                    elif attr == 'license_id':
                        pkg.license_id = val
                    elif attr == 'extras':
                        pkg.extras = val
                    elif attr == 'admins':
                        # Todo: Use admins parameter to pass in admins (three tests).
                        assert isinstance(val, list)
                        admins_list.append((item['name'], val))
                        for user_name in val:
                            if user_name not in new_user_names:
                                new_user_names.append(user_name)
                    else:
                        raise NotImplementedError(attr)
                self.pkg_names.append(item['name'])
                model.setup_default_user_roles(pkg, admins=admins)
            model.repo.commit_and_remove()

        needs_commit = False
        
        rev = model.repo.new_revision() 
        for group_name in extra_group_names:
            group = model.Group(name=unicode(group_name))
            model.Session.add(group)
            new_group_names.add(group_name)
            needs_commit = True

        if needs_commit:
            model.repo.commit_and_remove()
            needs_commit = False

        # create users that have been identified as being needed
        for user_name in new_user_names:
            if not model.User.by_name(unicode(user_name)):
                user = model.User(name=unicode(user_name))
                model.Session.add(user)
                self.user_names.append(user_name)
                needs_commit = True

        # setup authz for admins
        for pkg_name, admins in admins_list:
            pkg = model.Package.by_name(unicode(pkg_name))
            admins = [model.User.by_name(unicode(user_name)) for user_name in self.user_names]
            model.setup_default_user_roles(pkg, admins)
            needs_commit = True

        # setup authz for groups just created
        for group_name in new_group_names:
            group = model.Group.by_name(unicode(group_name))
            model.setup_default_user_roles(group)
            self.group_names.add(group_name)
            needs_commit = True

        if needs_commit:
            model.repo.commit_and_remove()
            needs_commit = False

        if relationships:
            rev = model.repo.new_revision() 
            rev.author = self.author
            rev.message = u'Creating package relationships.'

            def pkg(pkg_name):
                return model.Package.by_name(unicode(pkg_name))
            for subject_name, relationship, object_name in relationships:
                pkg(subject_name).add_relationship(
                    unicode(relationship), pkg(object_name))
                needs_commit = True

            model.repo.commit_and_remove()
        
        if commit_changesets:
            from ckan.model.changeset import ChangesetRegister
            changeset_ids = ChangesetRegister().commit()

    @classmethod
    def create_groups(self, group_dicts, admin_user_name):
        '''A more featured interface for creating groups.
        All group fields can be filled, packages added and they can
        have an admin user.'''
        import ckan.model as model
        rev = model.repo.new_revision()
        # same name as user we create below
        rev.author = self.author
        admin_user = model.User.by_name(admin_user_name)
        assert isinstance(group_dicts, (list, tuple))
        for group_dict in group_dicts:
            group = model.Group(name=unicode(group_dict['name']))
            for key in ('title', 'description'):
                if group_dict.has_key(key):
                    setattr(group, key, group_dict[key])
            pkg_names = group_dict.get('packages', [])
            assert isinstance(pkg_names, (list, tuple))
            for pkg_name in pkg_names:
                pkg = model.Package.by_name(unicode(pkg_name))
                assert pkg, pkg_name
                pkg.groups.append(group)
            model.Session.add(group)
            model.setup_default_user_roles(group, [admin_user])
            self.group_names.add(group_dict['name'])
        model.repo.commit_and_remove()

    @classmethod
    def create(self, commit_changesets=False):
        import ckan.model as model
        model.Session.remove()
        self.create_user()
        rev = model.repo.new_revision()
        # same name as user we create below
        rev.author = self.author
        rev.message = u'''Creating test data.
 * Package: annakarenina
 * Package: warandpeace
 * Associated tags, etc etc
'''
        self.pkg_names = [u'annakarenina', u'warandpeace']
        pkg1 = model.Package(name=self.pkg_names[0])
        model.Session.add(pkg1)
        pkg1.title = u'A Novel By Tolstoy'
        pkg1.version = u'0.7a'
        pkg1.url = u'http://www.annakarenina.com'
        # put an & in the url string to test escaping
        pr1 = model.PackageResource(
            url=u'http://www.annakarenina.com/download/x=1&y=2',
            format=u'plain text',
            description=u'Full text. Needs escaping: " Umlaut: \xfc',
            hash=u'abc123',
            )
        pr2 = model.PackageResource(
            url=u'http://www.annakarenina.com/index.json',
            format=u'json',
            description=u'Index of the novel',
            hash=u'def456',
            )
        model.Session.add(pr1)
        model.Session.add(pr2)
        pkg1.resources.append(pr1)
        pkg1.resources.append(pr2)
        pkg1.notes = u'''Some test notes

### A 3rd level heading

**Some bolded text.**

*Some italicized text.*

Foreign characters:
u with umlaut \xfc
66-style quote \u201c
foreign word: th\xfcmb
 
Needs escaping:
left arrow <

<http://ckan.net/>

'''
        pkg2 = model.Package(name=self.pkg_names[1])
        tag1 = model.Tag(name=u'russian')
        tag2 = model.Tag(name=u'tolstoy')
        for obj in [pkg2, tag1, tag2]:
            model.Session.add(obj)
        pkg1.tags = [tag1, tag2]
        pkg2.tags = [ tag1 ]
        self.tag_names = [u'russian', u'tolstoy']
        pkg1.license_id = u'other-open'
        pkg2.title = u'A Wonderful Story'
        pkg1.extras = {u'genre':'romantic novel',
                       u'original media':'book'}
        # group
        david = model.Group(name=u'david',
                             title=u'Dave\'s books',
                             description=u'These are books that David likes.')
        roger = model.Group(name=u'roger',
                             title=u'Roger\'s books',
                             description=u'Roger likes these books.')
        for obj in [david, roger]:
            model.Session.add(obj)
        self.group_names.add(u'david')
        self.group_names.add(u'roger')
        david.packages = [pkg1, pkg2]
        roger.packages = [pkg1]
        # authz
        joeadmin = model.User(name=u'joeadmin')
        annafan = model.User(name=u'annafan', about=u'I love reading Annakarenina')
        russianfan = model.User(name=u'russianfan')
        testsysadmin = model.User(name=u'testsysadmin')
        for obj in [joeadmin, annafan, russianfan, testsysadmin]:
            model.Session.add(obj)
        self.user_names.extend([u'joeadmin', u'annafan', u'russianfan', u'testsysadmin'])
        model.repo.commit_and_remove()

        visitor = model.User.by_name(model.PSEUDO_USER__VISITOR)
        anna = model.Package.by_name(u'annakarenina')
        war = model.Package.by_name(u'warandpeace')
        model.setup_default_user_roles(anna, [annafan])
        model.setup_default_user_roles(war, [russianfan])
        model.add_user_to_role(visitor, model.Role.ADMIN, war)
        david = model.Group.by_name(u'david')
        roger = model.Group.by_name(u'roger')
        model.setup_default_user_roles(david, [russianfan])
        model.setup_default_user_roles(roger, [russianfan])
        model.add_user_to_role(visitor, model.Role.ADMIN, roger)

        model.repo.commit_and_remove()

        if commit_changesets:
            from ckan.model.changeset import ChangesetRegister
            changeset_ids = ChangesetRegister().commit()

    @classmethod
    def flag_for_deletion(self, pkg_names=[], tag_names=[], group_names=[],
                          user_names=[]):
        '''If you create a domain object manually in your test then you
        can name it here (flag it up) and it will be deleted when you next
        call CreateTestData.delete().'''
        if isinstance(pkg_names, basestring):
            pkg_names = [pkg_names]
        self.pkg_names.extend(pkg_names)
        self.tag_names.extend(tag_names)
        self.group_names = self.group_names.union(set(group_names))
        self.user_names.extend(user_names)

    @classmethod
    def delete(self):
        '''Purges packages etc. that were created by this class.'''
        import ckan.model as model
        for pkg_name in self.pkg_names:
            pkg = model.Package.by_name(unicode(pkg_name))
            if pkg:
                sql = "DELETE FROM package_search WHERE package_id='%s'" % pkg.id
                model.Session.execute(sql)
        model.repo.commit_and_remove()
        for pkg_name in self.pkg_names:
            pkg = model.Package.by_name(unicode(pkg_name))
            if pkg:
                pkg.purge()
        for tag_name in self.tag_names:
            tag = model.Tag.by_name(unicode(tag_name))
            if tag:
                tag.purge()
        for group_name in self.group_names:
            group = model.Group.by_name(unicode(group_name))
            if group:
                model.Session.delete(group)
        revs = model.Session.query(model.Revision).filter_by(author=self.author)
        for rev in revs:
            for pkg in rev.packages:
                pkg.purge()
            for grp in rev.groups:
                grp.purge()
            model.Session.delete(rev)
        for user_name in self.user_names:
            user = model.User.by_name(unicode(user_name))
            if user:
                user.purge()
        model.Session.commit()
        model.Session.remove()
        self.reset()

    @classmethod
    def reset(cls):
        cls.pkg_names = []
        cls.group_names = set()
        cls.tag_names = []
        cls.user_names = []

    @classmethod
    def get_all_data(cls):
        return cls.pkg_names + list(cls.group_names) + cls.tag_names + cls.user_names


search_items = [{'name':'gils',
              'title':'Government Information Locator Service',
              'url':'',
              'tags':'registry  country-usa  government  federal  gov  workshop-20081101 penguin',
              'groups':'ukgov test1 test2 penguin',
              'license':'gpl-3.0',
              'notes':u'''From <http://www.gpoaccess.gov/gils/about.html>
              
> The Government Information Locator Service (GILS) is an effort to identify, locate, and describe publicly available Federal
> Because this collection is decentralized, the GPO

Foreign word:
u with umlaut th\xfcmb
''',
              'extras':{'date_released':'2008'},
              },
             {'name':'us-gov-images',
              'title':'U.S. Government Photos and Graphics',
              'url':'http://www.usa.gov/Topics/Graphics.shtml',
              'download_url':'http://www.usa.gov/Topics/Graphics.shtml',
              'tags':'images  graphics  photographs  photos  pictures  us  usa  america  history  wildlife  nature  war  military  todo-split  gov penguin',
              'groups':'ukgov test1 penguin',
              'license':'other-open',
              'notes':'''## About

Collection of links to different US image collections in the public domain.

## Openness

> Most of these images and graphics are available for use in the public domain, and''',
              'extras':{'date_released':'2009'},
              },
             {'name':'usa-courts-gov',
              'title':'Text of US Federal Cases',
              'url':'http://bulk.resource.org/courts.gov/',
              'download_url':'http://bulk.resource.org/courts.gov/',
              'tags':'us  courts  case-law  us  courts  case-law  gov  legal  law  access-bulk  penguins penguin',
              'groups':'ukgov test2 penguin',
              'license':'cc-zero',
              'notes':'''### Description

1.8 million pages of U.S. case law available with no restrictions. From the [README](http://bulk.resource.org/courts.gov/0_README.html):

> This file is  http://bulk.resource.org/courts.gov/0_README.html and was last revised.

penguin
''',
              'extras':{'date_released':'2007-06'},
              },
             {'name':'uk-government-expenditure',
              'title':'UK Government Expenditure',
              'tags':'workshop-20081101  uk  gov  expenditure  finance  public  funding penguin',
              'groups':'ukgov penguin',              
              'notes':'''Discussed at [Workshop on Public Information, 2008-11-02](http://okfn.org/wiki/PublicInformation).

Overview is available in Red Book, or Financial Statement and Budget Report (FSBR), [published by the Treasury](http://www.hm-treasury.gov.uk/budget.htm).''',
              'extras':{'date_released':'2007-10'},
              },
             {'name':'se-publications',
              'title':'Sweden - Government Offices of Sweden - Publications',
              'url':'http://www.sweden.gov.se/sb/d/574',
              'groups':'penguin',              
              'tags':'country-sweden  format-pdf  access-www  documents  publications  government  eutransparency penguin',
              'license':'',
              'notes':'''### About

Official documents including "government bills and reports, information material and other publications".

### Reuse

Not clear.''',
              'extras':{'date_released':'2009-10-27'},
              },
             {'name':'se-opengov',
              'title':'Opengov.se',
              'groups':'penguin',              
              'url':'http://www.opengov.se/',
              'download_url':'http://www.opengov.se/data/open/',
              'tags':'country-sweden  government  data penguin',
              'license':'cc-by-sa',
              'notes':'''### About

From [website](http://www.opengov.se/sidor/english/):

> Opengov.se is an initiative to highlight available public datasets in Sweden. It contains a commentable catalog of government datasets, their formats and usage restrictions.

> The goal is to highlight the benefits of open access to government data and explain how this is done in practice.

### Openness

It appears that the website is under a CC-BY-SA license. Legal status of the data varies. Data that is fully open can be viewed at:

 * <http://www.opengov.se/data/open/>'''
              },
             ]

family_items = [{'name':u'abraham', 'title':u'Abraham'},
                {'name':u'homer', 'title':u'Homer'},
                {'name':u'homer_derived', 'title':u'Homer Derived'},
                {'name':u'beer', 'title':u'Beer'},
                {'name':u'bart', 'title':u'Bart'},
                {'name':u'lisa', 'title':u'Lisa'},
                ]
family_relationships = [('abraham', 'parent_of', 'homer'),
                        ('homer', 'parent_of', 'bart'),
                        ('homer', 'parent_of', 'lisa'),
                        ('homer_derived', 'derives_from', 'homer'),
                        ('homer', 'depends_on', 'beer'),
                        ]

gov_items = [
    {'name':'private-fostering-england-2009',
     'title':'Private Fostering',
     'notes':'Figures on children cared for and accommodated in private fostering arrangements, England, Year ending 31 March 2009',
     'resources':[{'url':'http://www.dcsf.gov.uk/rsgateway/DB/SFR/s000859/SFR17_2009_tables.xls',
                  'format':'XLS',
                  'description':'December 2009 | http://www.statistics.gov.uk/hub/id/119-36345'},
                  {'url':'http://www.dcsf.gov.uk/rsgateway/DB/SFR/s000860/SFR17_2009_key.doc',
                  'format':'DOC',
                  'description':'http://www.statistics.gov.uk/hub/id/119-34565'}],
     'url':'http://www.dcsf.gov.uk/rsgateway/DB/SFR/s000859/index.shtml',
     'author':'DCSF Data Services Group',
     'author_email':'statistics@dcsf.gsi.gov.uk',
     'license':'ukcrown',
     'tags':'children fostering',
     'extras':{
        'external_reference':'DCSF-DCSF-0024',
        'date_released':'2009-07-30',
        'date_updated':'2009-07-30',
        'update_frequency':'annually',
        'geographic_granularity':'regional',
        'geographic_coverage':'100000: England',
        'department':'Department for Children, Schools and Families',
        'temporal_granularity':'years',
        'temporal_coverage-from':'2008-6',
        'temporal_coverage-to':'2009-6',
        'categories':'Health, well-being and Care',
        'national_statistic':'yes',
        'precision':'Numbers to nearest 10, percentage to nearest whole number',
        'taxonomy_url':'',
        'agency':'',
        'import_source':'ONS-Jan-09',
        }
     },
    {'name':'weekly-fuel-prices',
     'title':'Weekly fuel prices',
     'notes':'Latest price as at start of week of unleaded petrol and diesel.',
     'resources':[{'url':'', 'format':'XLS', 'description':''}],
     'url':'http://www.decc.gov.uk/en/content/cms/statistics/source/prices/prices.aspx',
     'author':'DECC Energy Statistics Team',
     'author_email':'energy.stats@decc.gsi.gov.uk',
     'license':'ukcrown',
     'tags':'fuel prices',
     'extras':{
        'external_reference':'DECC-DECC-0001',
        'date_released':'2009-11-24',
        'date_updated':'2009-11-24',
        'update_frequency':'weekly',
        'geographic_granularity':'national',
        'geographic_coverage':'111100: United Kingdom (England, Scotland, Wales, Northern Ireland)',
        'department':'Department of Energy and Climate Change',
        'temporal_granularity':'weeks',
        'temporal_coverage-from':'2008-11-24',
        'temporal_coverage-to':'2009-11-24',
        'national_statistic':'yes',
        'import_source':'DECC-Jan-09',
        }
     }
    ]
