import cli
from collections import defaultdict
import datetime

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
    user_refs = []
    
    pkg_core_fields = ['name', 'title', 'version', 'url', 'notes',
                       'author', 'author_email',
                       'maintainer', 'maintainer_email',
                       ]

    def command(self):
        from ckan import plugins
        self._load_config()
        self._setup_app()
        plugins.load('synchronous_search') # so packages get indexed
        if self.args:
            cmd = self.args[0]
        else:
            cmd = 'basic'
        if self.verbose:
            print 'Creating %s test data' % cmd
        if cmd == 'basic':
            self.create_basic_test_data()
        elif cmd == 'user':
            self.create_test_user()
            print 'Created user %r with password %r and apikey %r' % ('tester',
                    'tester', 'tester')
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
    def create_basic_test_data(cls):
        cls.create()

    @classmethod
    def create_search_test_data(cls):
        cls.create_arbitrary(search_items)

    @classmethod
    def create_gov_test_data(cls, extra_users=[]):
        cls.create_arbitrary(gov_items, extra_user_names=extra_users)

    @classmethod
    def create_family_test_data(cls, extra_users=[]):
        cls.create_arbitrary(family_items,
                              relationships=family_relationships,
                              extra_user_names=extra_users)

    @classmethod
    def create_test_user(cls):
        import ckan.model as model
        tester = model.User.by_name(u'tester')
        if tester is None:
            tester = model.User(name=u'tester', apikey=u'tester',
                password=u'tester')
            model.Session.add(tester)
            model.Session.commit()
        model.Session.remove()
        cls.user_refs.append(u'tester')

    @classmethod
    def create_arbitrary(cls, package_dicts, relationships=[],
            extra_user_names=[], extra_group_names=[], 
            admins=[]):
        '''Creates packages and a few extra objects as well at the
        same time if required.
        @param package_dicts - a list of dictionaries with the package
                               properties.
                               Extra keys allowed:
                               "admins" - list of user names to make admin
                                          for this package.
        @param extra_group_names - a list of group names to create. No
                               properties get set though.
        @param admins - a list of user names to make admins of all the
                               packages created.                           
        '''
        assert isinstance(relationships, (list, tuple))
        assert isinstance(extra_user_names, (list, tuple))
        assert isinstance(extra_group_names, (list, tuple))
        import ckan.model as model
        model.Session.remove()
        new_user_names = extra_user_names
        new_group_names = set()
        new_groups = {}
        
        rev = model.repo.new_revision() 
        rev.author = cls.author
        rev.message = u'Creating test packages.'
        
        admins_list = defaultdict(list) # package_name: admin_names
        if package_dicts:
            if isinstance(package_dicts, dict):
                package_dicts = [package_dicts]
            for item in package_dicts:
                pkg_dict = {}
                for field in cls.pkg_core_fields:
                    if item.has_key(field):
                        pkg_dict[field] = unicode(item[field])
                pkg = model.Package(**pkg_dict)
                model.Session.add(pkg)
                for attr, val in item.items():
                    if isinstance(val, str):
                        val = unicode(val)
                    if attr=='name':
                        continue                
                    if attr in cls.pkg_core_fields:
                        pass
                    elif attr == 'download_url':
                        pkg.add_resource(unicode(val))
                    elif attr == 'resources':
                        assert isinstance(val, (list, tuple))
                        for res_dict in val:
                            non_extras = {}
                            for k, v in res_dict.items():
                                if k != 'extras':
                                    if not isinstance(v, datetime.datetime):
                                        v = unicode(v)
                                    non_extras[str(k)] = v
                            extras = dict([(str(k), unicode(v)) for k, v in res_dict.get('extras', {}).items()])
                            pkg.add_resource(extras=extras, **non_extras)
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
                                cls.tag_names.append(tag_name)
                                model.Session.add(tag)    
                            pkg.tags.append(tag)
                            model.Session.flush()
                    elif attr == 'groups':
                        model.Session.flush()
                        if isinstance(val, (str, unicode)):
                            group_names = val.split()
                        elif isinstance(val, list):
                            group_names = val
                        else:
                            raise NotImplementedError
                        for group_name in group_names:
                            group = model.Group.by_name(unicode(group_name))
                            if not group:
                                if not group_name in new_groups:
                                    group = model.Group(name=unicode(group_name))
                                    model.Session.add(group)
                                    new_group_names.add(group_name)
                                    new_groups[group_name] = group
                                else:
                                    # If adding multiple packages with the same group name,
                                    # model.Group.by_name will not find the group as the
                                    # session has not yet been committed at this point.
                                    # Fetch from the new_groups dict instead.
                                    group = new_groups[group_name]
                            member = model.Member(group=group, table_id=pkg.id, table_name='package')
                            model.Session.add(member)
                    elif attr == 'license':
                        pkg.license_id = val
                    elif attr == 'license_id':
                        pkg.license_id = val
                    elif attr == 'extras':
                        pkg.extras = val
                    elif attr == 'admins':
                        assert isinstance(val, list)
                        admins_list[item['name']].extend(val)
                        for user_name in val:
                            if user_name not in new_user_names:
                                new_user_names.append(user_name)
                    else:
                        raise NotImplementedError(attr)
                cls.pkg_names.append(item['name'])
                model.setup_default_user_roles(pkg, admins=[])
                for admin in admins:
                    admins_list[item['name']].append(admin)
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
                cls.user_refs.append(user_name)
                needs_commit = True

        if needs_commit:
            model.repo.commit_and_remove()
            needs_commit = False

        # setup authz for admins
        for pkg_name, admins in admins_list.items():
            pkg = model.Package.by_name(unicode(pkg_name))
            admins_obj_list = []
            for admin in admins:
                if isinstance(admin, model.User):
                    admin_obj = admin
                else:
                    admin_obj = model.User.by_name(unicode(admin))
                assert admin_obj, admin
                admins_obj_list.append(admin_obj)
            model.setup_default_user_roles(pkg, admins_obj_list)
            needs_commit = True

        # setup authz for groups just created
        for group_name in new_group_names:
            group = model.Group.by_name(unicode(group_name))
            model.setup_default_user_roles(group)
            cls.group_names.add(group_name)
            needs_commit = True

        if needs_commit:
            model.repo.commit_and_remove()
            needs_commit = False

        if relationships:
            rev = model.repo.new_revision() 
            rev.author = cls.author
            rev.message = u'Creating package relationships.'

            def pkg(pkg_name):
                return model.Package.by_name(unicode(pkg_name))
            for subject_name, relationship, object_name in relationships:
                pkg(subject_name).add_relationship(
                    unicode(relationship), pkg(object_name))
                needs_commit = True

            model.repo.commit_and_remove()
        

    @classmethod
    def create_groups(cls, group_dicts, admin_user_name=None):
        '''A more featured interface for creating groups.
        All group fields can be filled, packages added and they can
        have an admin user.'''
        import ckan.model as model
        rev = model.repo.new_revision()
        # same name as user we create below
        rev.author = cls.author
        if admin_user_name:
            admin_users = [model.User.by_name(admin_user_name)]
        else:
            admin_users = []
        assert isinstance(group_dicts, (list, tuple))
        group_attributes = set(('name', 'title', 'description', 'parent_id'))
        for group_dict in group_dicts:
            group = model.Group(name=unicode(group_dict['name']))
            for key in group_dict:
                if key in group_attributes:
                    setattr(group, key, group_dict[key])
                else:
                    group.extras[key] = group_dict[key]
            pkg_names = group_dict.get('packages', [])
            assert isinstance(pkg_names, (list, tuple))
            for pkg_name in pkg_names:
                pkg = model.Package.by_name(unicode(pkg_name))
                assert pkg, pkg_name
                member = model.Member(group=group, table_id=pkg.id, table_name='package')
                model.Session.add(member)
            model.Session.add(group)
            model.setup_default_user_roles(group, admin_users)
            cls.group_names.add(group_dict['name'])
        model.repo.commit_and_remove()

    @classmethod
    def create(cls):
        import ckan.model as model
        model.Session.remove()
        rev = model.repo.new_revision()
        # same name as user we create below
        rev.author = cls.author
        rev.message = u'''Creating test data.
 * Package: annakarenina
 * Package: warandpeace
 * Associated tags, etc etc
'''
        cls.pkg_names = [u'annakarenina', u'warandpeace']
        pkg1 = model.Package(name=cls.pkg_names[0])
        model.Session.add(pkg1)
        pkg1.title = u'A Novel By Tolstoy'
        pkg1.version = u'0.7a'
        pkg1.url = u'http://www.annakarenina.com'
        # put an & in the url string to test escaping
        if 'alt_url' in model.Resource.get_extra_columns():
            configured_extras = ({'alt_url': u'alt123'},
                                 {'alt_url': u'alt345'})
        else:
            configured_extras = ({}, {})
        pr1 = model.Resource(
            url=u'http://www.annakarenina.com/download/x=1&y=2',
            format=u'plain text',
            description=u'Full text. Needs escaping: " Umlaut: \xfc',
            hash=u'abc123',
            extras={'size_extra': u'123'},
            **configured_extras[0]
            )
        pr2 = model.Resource(
            url=u'http://www.annakarenina.com/index.json',
            format=u'json',
            description=u'Index of the novel',
            hash=u'def456',
            extras={'size_extra': u'345'},
            **configured_extras[1]
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
        pkg2 = model.Package(name=cls.pkg_names[1])
        tag1 = model.Tag(name=u'russian')
        tag2 = model.Tag(name=u'tolstoy')

        # Flexible tag, allows spaces, upper-case,
        # and all punctuation except commas
        tag3 = model.Tag(name=u'Flexible \u30a1')

        for obj in [pkg2, tag1, tag2, tag3]:
            model.Session.add(obj)
        pkg1.tags = [tag1, tag2, tag3]
        pkg2.tags = [ tag1, tag3 ]
        cls.tag_names = [ t.name for t in (tag1, tag2, tag3) ]
        pkg1.license_id = u'other-open'
        pkg2.license_id = u'cc-nc' # closed license
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
        
        cls.group_names.add(u'david')
        cls.group_names.add(u'roger')

        model.Session.flush()
        
        model.Session.add(model.Member(table_id=pkg1.id, table_name='package', group=david))
        model.Session.add(model.Member(table_id=pkg2.id, table_name='package', group=david))
        model.Session.add(model.Member(table_id=pkg1.id, table_name='package', group=roger))
        # authz
        model.Session.add_all([
            model.User(name=u'tester', apikey=u'tester', password=u'tester'),
            model.User(name=u'joeadmin', password=u'joeadmin'),
            model.User(name=u'annafan', about=u'I love reading Annakarenina. My site: <a href="http://anna.com">anna.com</a>', password=u'annafan'),
            model.User(name=u'russianfan', password=u'russianfan'),
            model.User(name=u'testsysadmin', password=u'testsysadmin'),
            ])
        cls.user_refs.extend([u'tester', u'joeadmin', u'annafan', u'russianfan', u'testsysadmin'])
        model.repo.commit_and_remove()

        visitor = model.User.by_name(model.PSEUDO_USER__VISITOR)
        anna = model.Package.by_name(u'annakarenina')
        war = model.Package.by_name(u'warandpeace')
        annafan = model.User.by_name(u'annafan')
        russianfan = model.User.by_name(u'russianfan')
        model.setup_default_user_roles(anna, [annafan])
        model.setup_default_user_roles(war, [russianfan])
        model.add_user_to_role(visitor, model.Role.ADMIN, war)
        david = model.Group.by_name(u'david')
        roger = model.Group.by_name(u'roger')
        model.setup_default_user_roles(david, [russianfan])
        model.setup_default_user_roles(roger, [russianfan])
        model.add_user_to_role(visitor, model.Role.ADMIN, roger)
        testsysadmin = model.User.by_name(u'testsysadmin')
        model.add_user_to_role(testsysadmin, model.Role.ADMIN, model.System())

        model.repo.commit_and_remove()

        # Create a couple of authorization groups
        for ag_name in [u'anauthzgroup', u'anotherauthzgroup']:
            ag=model.AuthorizationGroup.by_name(ag_name) 
            if not ag: #may already exist, if not create
                ag=model.AuthorizationGroup(name=ag_name)
                model.Session.add(ag)

        model.repo.commit_and_remove()

        # and give them a range of roles on various things
        ag = model.AuthorizationGroup.by_name(u'anauthzgroup')
        aag = model.AuthorizationGroup.by_name(u'anotherauthzgroup')
        pkg = model.Package.by_name(u'warandpeace')
        g = model.Group.by_name('david')

        model.add_authorization_group_to_role(ag, u'editor', model.System())
        model.add_authorization_group_to_role(ag, u'reader', pkg)
        model.add_authorization_group_to_role(ag, u'admin', aag)
        model.add_authorization_group_to_role(aag, u'editor', ag)
        model.add_authorization_group_to_role(ag, u'editor', g)

        model.repo.commit_and_remove()





    @classmethod
    def create_user(cls, name='', **kwargs):
        import ckan.model as model
        # User objects are not revisioned
        user_ref = name or kwargs['openid']
        assert user_ref
        for k, v in kwargs.items():
            if v:
                # avoid unicode warnings
                kwargs[k] = unicode(v)
        user = model.User(name=unicode(name), **kwargs)
        model.Session.add(user)
        model.Session.commit()
        cls.user_refs.append(user_ref)

    @classmethod
    def flag_for_deletion(cls, pkg_names=[], tag_names=[], group_names=[],
                          user_names=[]):
        '''If you create a domain object manually in your test then you
        can name it here (flag it up) and it will be deleted when you next
        call CreateTestData.delete().'''
        if isinstance(pkg_names, basestring):
            pkg_names = [pkg_names]
        cls.pkg_names.extend(pkg_names)
        cls.tag_names.extend(tag_names)
        cls.group_names = cls.group_names.union(set(group_names))
        cls.user_refs.extend(user_names)

    @classmethod
    def delete(cls):
        '''Purges packages etc. that were created by this class.'''
        import ckan.model as model
        for pkg_name in cls.pkg_names:
            model.Session().autoflush = False
            pkg = model.Package.by_name(unicode(pkg_name))
            if pkg:
                pkg.purge()
        for tag_name in cls.tag_names:
            tag = model.Tag.by_name(unicode(tag_name))
            if tag:
                tag.purge()
        for group_name in cls.group_names:
            group = model.Group.by_name(unicode(group_name))
            if group:
                model.Session.delete(group)
        revs = model.Session.query(model.Revision).filter_by(author=cls.author)
        for rev in revs:
            for pkg in rev.packages:
                pkg.purge()
            for grp in rev.groups:
                grp.purge()
            model.Session.commit()
            model.Session.delete(rev)
        for user_name in cls.user_refs:
            user = model.User.get(unicode(user_name))
            if user:
                user.purge()
        model.Session.commit()
        model.Session.remove()
        cls.reset()

    @classmethod
    def reset(cls):
        cls.pkg_names = []
        cls.group_names = set()
        cls.tag_names = []
        cls.user_refs = []

    @classmethod
    def get_all_data(cls):
        return cls.pkg_names + list(cls.group_names) + cls.tag_names + cls.user_refs


search_items = [{'name':'gils',
              'title':'Government Information Locator Service',
              'url':'',
              'tags':'registry,country-usa,government,federal,gov,workshop-20081101,penguin'.split(','),
              'resources':[{'url':'http://www.dcsf.gov.uk/rsgateway/DB/SFR/s000859/SFR17_2009_tables.xls',
                          'format':'XLS',
                          'last_modified': datetime.datetime(2005,10,01),
                          'description':'December 2009 | http://www.statistics.gov.uk/hub/id/119-36345'},
                          {'url':'http://www.dcsf.gov.uk/rsgateway/DB/SFR/s000860/SFR17_2009_key.doc',
                          'format':'DOC',
                          'description':'http://www.statistics.gov.uk/hub/id/119-34565'}],
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
              'tags':'images,graphics,photographs,photos,pictures,us,usa,america,history,wildlife,nature,war,military,todo split,gov,penguin'.split(','),
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
              'tags':'us,courts,case-law,us,courts,case-law,gov,legal,law,access-bulk,penguins,penguin'.split(','),
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
              'tags':'workshop-20081101,uk,gov,expenditure,finance,public,funding,penguin'.split(','),
              'groups':'ukgov penguin',              
              'notes':'''Discussed at [Workshop on Public Information, 2008-11-02](http://okfn.org/wiki/PublicInformation).

Overview is available in Red Book, or Financial Statement and Budget Report (FSBR), [published by the Treasury](http://www.hm-treasury.gov.uk/budget.htm).''',
              'extras':{'date_released':'2007-10'},
              },
             {'name':'se-publications',
              'title':'Sweden - Government Offices of Sweden - Publications',
              'url':'http://www.sweden.gov.se/sb/d/574',
              'groups':'penguin',              
              'tags':u'country-sweden,format-pdf,access-www,documents,publications,government,eutransparency,penguin,CAPITALS,surprise.,greek omega \u03a9,japanese katakana \u30a1'.split(','),
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
              'tags':'country-sweden,government,data,penguin'.split(','),
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
                {'name':u'marge', 'title':u'Marge'},
                ]
family_relationships = [('abraham', 'parent_of', 'homer'),
                        ('homer', 'parent_of', 'bart'),
                        ('homer', 'parent_of', 'lisa'),
                        ('marge', 'parent_of', 'lisa'),
                        ('marge', 'parent_of', 'bart'),
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
        'department':'Department for Education',
        'published_by':'Department for Education [3]',
        'published_via':'',
        'temporal_granularity':'years',
        'temporal_coverage-from':'2008-6',
        'temporal_coverage-to':'2009-6',
        'mandate':'',
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
     'resources':[{'url':'http://www.decc.gov.uk/en/content/cms/statistics/prices.xls', 'format':'XLS', 'description':''}],
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
        'published_by':'Department of Energy and Climate Change [4]',
        'published_via':'',
         'mandate':'',
        'temporal_granularity':'weeks',
        'temporal_coverage-from':'2008-11-24',
        'temporal_coverage-to':'2009-11-24',
        'national_statistic':'no',
        'import_source':'DECC-Jan-09',
        }
     }
    ]
