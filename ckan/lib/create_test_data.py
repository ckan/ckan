# encoding: utf-8
from __future__ import annotations

import logging
import datetime
from typing import Any, Optional, Union, cast



import ckan.model as model
from ckan.logic import get_action
from ckan.types import Context


log = logging.getLogger(__name__)

class CreateTestData(object):
    # keep track of the objects created by this class so that
    # tests can easy call delete() method to delete them all again.
    pkg_names: list[str] = []
    tag_names: list[str] = []
    group_names: set[str] = set()
    user_refs: list[str] = []

    author: str = u'tester'

    pkg_core_fields: list[str] = ['name', 'title', 'version', 'url', 'notes',
                       'author', 'author_email',
                       'maintainer', 'maintainer_email',
                       'private',
                       ]
    @classmethod
    def create_basic_test_data(cls):
        cls.create()

    @classmethod
    def create_search_test_data(cls):
        cls.create_arbitrary(search_items)

    @classmethod
    def create_gov_test_data(cls, extra_users: list[str] = []):
        cls.create_arbitrary(gov_items, extra_user_names=extra_users)

    @classmethod
    def create_family_test_data(cls, extra_users: list[str] = []):
        cls.create_arbitrary(family_items,
                              relationships=family_relationships,
                              extra_user_names=extra_users)

    @classmethod
    def create_group_hierarchy_test_data(
            cls, extra_users: list[dict[str, Any]] = []):
        cls.create_users(group_hierarchy_users)
        cls.create_groups(group_hierarchy_groups)
        cls.create_arbitrary(group_hierarchy_datasets)

    @classmethod
    def create_test_user(cls):
        tester = model.User.by_name(u'tester')
        if tester is None:
            tester = model.User(name=u'tester', password=u'tester')
            model.Session.add(tester)
            model.Session.commit()
        model.Session.remove()
        cls.user_refs.append(u'tester')

    @classmethod
    def create_translations_test_data(cls):
        import ckan.model
        package = ckan.model.Package.get('annakarenina')
        if not package:
            CreateTestData.create()
            package = ckan.model.Package.get('annakarenina')

        sysadmin_user = ckan.model.User.get('testsysadmin')
        assert package and sysadmin_user
        # Add some new tags to the package.
        # These tags are codes that are meant to be always translated before
        # display, if not into the user's current language then into the
        # fallback language.
        package.add_tags([ckan.model.Tag('123'), ckan.model.Tag('456'),
                ckan.model.Tag('789')])

        # Add the above translations to CKAN.
        for (lang_code, translations) in (('de', german_translations),
                ('fr', french_translations), ('en', english_translations)):
            for term in terms:
                if term in translations:
                    data_dict = {
                            'term': term,
                            'term_translation': translations[term],
                            'lang_code': lang_code,
                            }
                    context = cast(Context, {
                        'model': ckan.model,
                        'session': ckan.model.Session,
                        'user': sysadmin_user.name,
                    })
                    get_action('term_translation_update')(context,
                            data_dict)

        ckan.model.Session.commit()

    @classmethod
    def create_vocabs_test_data(cls):
        import ckan.model
        warandpeace = ckan.model.Package.get('warandpeace')
        if not warandpeace:
            CreateTestData.create()
            warandpeace = ckan.model.Package.get('warandpeace')

        sysadmin_user = ckan.model.User.get('testsysadmin')
        annakarenina = ckan.model.Package.get('annakarenina')
        assert sysadmin_user and annakarenina and warandpeace

        # Create a couple of vocabularies.
        context = cast(Context, {
                'model': ckan.model,
                'session': ckan.model.Session,
                'user': sysadmin_user.name
                })
        data_dict = {
                'name': 'Genre',
                'tags': [{'name': 'Drama'}, {'name': 'Sci-Fi'},
                    {'name': 'Mystery'}],
                }
        get_action('vocabulary_create')(context, data_dict)

        data_dict = {
                'name': 'Actors',
                'tags': [{'name': 'keira-knightley'}, {'name': 'jude-law'},
                    {'name': 'alessio-boni'}],
                }
        get_action('vocabulary_create')(context, data_dict)

        # Add some vocab tags to some packages.
        genre_vocab = ckan.model.Vocabulary.get('Genre')
        actors_vocab = ckan.model.Vocabulary.get('Actors')
        annakarenina.add_tag_by_name('Drama', vocab=genre_vocab)
        annakarenina.add_tag_by_name('keira-knightley', vocab=actors_vocab)
        annakarenina.add_tag_by_name('jude-law', vocab=actors_vocab)
        warandpeace.add_tag_by_name('Drama', vocab=genre_vocab)
        warandpeace.add_tag_by_name('alessio-boni', vocab=actors_vocab)

    @classmethod
    def create_arbitrary(
            cls, package_dicts: Union[dict[str, Any], list[dict[str, Any]]],
            relationships: list[dict[str, Any]] = [],
            extra_user_names: list[str] = [],
            extra_group_names: list[str] = []):
        '''Creates packages and a few extra objects as well at the
        same time if required.
        @param package_dicts - a list of dictionaries with the package
                               properties.
                               Extra keys allowed:
        @param extra_group_names - a list of group names to create. No
                               properties get set though.
        '''
        assert isinstance(relationships, (list, tuple))
        assert isinstance(extra_user_names, (list, tuple))
        assert isinstance(extra_group_names, (list, tuple))
        model.Session.remove()
        new_user_names = extra_user_names
        new_group_names = set()
        new_groups = {}

        if package_dicts:
            if isinstance(package_dicts, dict):
                package_dicts = [package_dicts]
            for item in package_dicts:
                pkg_dict = {}
                for field in cls.pkg_core_fields:
                    if field in item:
                        pkg_dict[field] = str(item[field])
                if model.Package.by_name(pkg_dict['name']):
                    log.warning('Cannot create package "%s" as it already exists.' % \
                                    (pkg_dict['name']))
                    continue
                pkg = model.Package(**pkg_dict)
                model.Session.add(pkg)
                for attr, val in item.items():
                    if isinstance(val, str):
                        val = str(val)
                    if attr=='name':
                        continue
                    if attr in cls.pkg_core_fields:
                        pass
                    elif attr == 'download_url':
                        pkg.add_resource(str(val))
                    elif attr == 'resources':
                        assert isinstance(val, (list, tuple))
                        for res_dict in val:
                            non_extras = {}
                            for k, v in res_dict.items():
                                if k != 'extras':
                                    if not isinstance(v, datetime.datetime):
                                        v = str(v)
                                    non_extras[str(k)] = v
                            extras = {str(k): str(v) for k, v in res_dict.get('extras', {}).items()}
                            pkg.add_resource(extras=extras, **non_extras)
                    elif attr == 'tags':
                        if isinstance(val, str):
                            tags = val.split()
                        elif isinstance(val, list):
                            tags = val
                        else:
                            raise NotImplementedError
                        for tag_name in tags:
                            tag_name = str(tag_name)
                            tag = model.Tag.by_name(tag_name)
                            if not tag:
                                tag = model.Tag(name=tag_name)
                                cls.tag_names.append(tag_name)
                                model.Session.add(tag)
                            pkg.add_tag(tag)
                            model.Session.flush()
                    elif attr == 'groups':
                        model.Session.flush()
                        if isinstance(val, str):
                            group_names = val.split()
                        elif isinstance(val, list):
                            group_names = val
                        else:
                            raise NotImplementedError
                        for group_name in group_names:
                            group = model.Group.by_name(str(group_name))
                            if not group:
                                if not group_name in new_groups:
                                    group = model.Group(name=
                                                        str(group_name))
                                    model.Session.add(group)
                                    new_group_names.add(group_name)
                                    new_groups[group_name] = group
                                else:
                                    # If adding multiple packages with the same
                                    # group name, model.Group.by_name will not
                                    # find the group as the session has not yet
                                    # been committed at this point.  Fetch from
                                    # the new_groups dict instead.
                                    group = new_groups[group_name]
                            capacity = 'organization' if group.is_organization\
                                       else 'public'
                            member = model.Member(group=group, table_id=pkg.id,
                                                  table_name='package',
                                                  capacity=capacity)
                            model.Session.add(member)
                            if group.is_organization:
                                pkg.owner_org = group.id
                    elif attr == 'license':
                        pkg.license_id = val
                    elif attr == 'license_id':
                        pkg.license_id = val
                    elif attr == 'extras':
                        pkg.extras = val
                    elif attr == 'admins':
                        assert 0, 'Deprecated param "admins"'
                    else:
                        raise NotImplementedError(attr)
                cls.pkg_names.append(item['name'])
                model.repo.commit_and_remove()

        needs_commit = False

        for group_name in extra_group_names:
            group = model.Group(name=str(group_name))
            model.Session.add(group)
            new_group_names.add(group_name)
            needs_commit = True

        if needs_commit:
            model.repo.commit_and_remove()
            needs_commit = False

        # create users that have been identified as being needed
        for user_name in new_user_names:
            if not model.User.by_name(str(user_name)):
                user = model.User(name=str(user_name))
                model.Session.add(user)
                cls.user_refs.append(user_name)
                needs_commit = True

        if needs_commit:
            model.repo.commit_and_remove()
            needs_commit = False

        # setup authz for groups just created
        for group_name in new_group_names:
            group = model.Group.by_name(str(group_name))
            cls.group_names.add(group_name)
            needs_commit = True

        if needs_commit:
            model.repo.commit_and_remove()
            needs_commit = False

        if relationships:
            def get_pkg(pkg_name: str):
                pkg = model.Package.by_name(str(pkg_name))
                assert pkg
                return pkg
            for subject_name, relationship, object_name in relationships:
                get_pkg(subject_name).add_relationship(
                    str(relationship), get_pkg(object_name))
                needs_commit = True

            model.repo.commit_and_remove()


    @classmethod
    def create_groups(
            cls, group_dicts: list[dict[str, Any]],
            admin_user_name: Optional[str] = None,
            auth_profile: str = ""):
        '''A more featured interface for creating groups.
        All group fields can be filled, packages added, can have
        an admin user and be a member of other groups.'''
        if admin_user_name:
            admin_users = [model.User.by_name(admin_user_name)]
        else:
            admin_users = []
        assert isinstance(group_dicts, (list, tuple))
        group_attributes = set(('name', 'title', 'description', 'parent_id',
                                'type', 'is_organization'))
        for group_dict in group_dicts:
            if model.Group.by_name(str(group_dict['name'])):
                log.warning('Cannot create group "%s" as it already exists.' %
                            group_dict['name'])
                continue
            pkg_names = group_dict.pop('packages', [])
            group = model.Group(name=str(group_dict['name']))
            group.type = auth_profile or 'group'
            for key in group_dict:
                if key in group_attributes:
                    setattr(group, key, group_dict[key])
                elif key not in ('admins', 'editors', 'parent'):
                    group.extras[key] = group_dict[key]
            assert isinstance(pkg_names, (list, tuple))
            for pkg_name in pkg_names:
                pkg = model.Package.by_name(str(pkg_name))
                assert pkg, pkg_name
                member = model.Member(group=group, table_id=pkg.id,
                                      table_name='package')
                model.Session.add(member)
            model.Session.add(group)
            admins = [model.User.by_name(user_name)
                      for user_name in group_dict.get('admins', [])] + \
                     admin_users
            for admin in admins:
                assert admin
                member = model.Member(group=group, table_id=admin.id,
                                      table_name='user', capacity='admin')
                model.Session.add(member)
            editors = [model.User.by_name(user_name)
                       for user_name in group_dict.get('editors', [])]
            for editor in editors:
                assert editor
                member = model.Member(group=group, table_id=editor.id,
                                      table_name='user', capacity='editor')
                model.Session.add(member)
            # Need to commit the current Group for two reasons:
            # 1. It might have a parent, and the Member will need the Group.id
            #    value allocated on commit.
            # 2. The next Group created may have this Group as a parent so
            #    creation of the Member needs to refer to this one.
            model.Session.commit()
            # add it to a parent's group
            if 'parent' in group_dict:
                parent = model.Group.by_name(str(group_dict['parent']))
                assert parent, group_dict['parent']
                member = model.Member(group=group, table_id=parent.id,
                                      table_name='group', capacity='parent')
                model.Session.add(member)
            cls.group_names.add(group_dict['name'])
        model.repo.commit_and_remove()

    @classmethod
    def create(cls, auth_profile: str = "",
               package_type: Optional[str] = None):
        model.Session.remove()
        cls.pkg_names = [u'annakarenina', u'warandpeace']
        pkg1 = model.Package(name=cls.pkg_names[0], type=package_type)
        model.Session.add(pkg1)
        pkg1.title = u'A Novel By Tolstoy'
        pkg1.version = u'0.7a'
        pkg1.url = u'http://datahub.io'
        # put an & in the url string to test escaping
        if 'alt_url' in model.Resource.get_extra_columns():
            configured_extras = ({'alt_url': u'alt123'},
                                 {'alt_url': u'alt345'})
        else:
            configured_extras = ({}, {})
        pr1 = model.Resource(
            url=u'http://datahub.io/download/x=1&y=2',
            format=u'plain text',
            description=u'Full text. Needs escaping: " Umlaut: \xfc',
            hash=u'abc123',
            extras={'size_extra': u'123'},
            **configured_extras[0]
            )
        pr2 = model.Resource(
            url=u'http://datahub.io/index.json',
            format=u'JSON',
            description=u'Index of the novel',
            hash=u'def456',
            extras={'size_extra': u'345'},
            **configured_extras[1]
            )
        model.Session.add(pr1)
        model.Session.add(pr2)
        pkg1.resources_all.append(pr1)
        pkg1.resources_all.append(pr2)
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
        pkg2 = model.Package(name=cls.pkg_names[1], type=package_type)
        tag1 = model.Tag(name=u'russian')
        tag2 = model.Tag(name=u'tolstoy')

        # Flexible tag, allows spaces, upper-case,
        # and all punctuation except commas
        tag3 = model.Tag(name=u'Flexible \u30a1')

        for obj in [pkg2, tag1, tag2, tag3]:
            model.Session.add(obj)
        pkg1.add_tags([tag1, tag2, tag3])
        pkg2.add_tags([ tag1, tag3 ])
        cls.tag_names = [ t.name for t in (tag1, tag2, tag3) ]
        pkg1.license_id = u'other-open'
        pkg2.license_id = u'cc-nc' # closed license
        pkg2.title = u'A Wonderful Story'
        pkg1.extras = {u'genre':'romantic novel',
                       u'original media':'book'}
        # group
        david = model.Group(name=u'david',
                             title=u'Dave\'s books',
                             description=u'These are books that David likes.',
                             type=auth_profile or 'group')
        roger = model.Group(name=u'roger',
                             title=u'Roger\'s books',
                             description=u'Roger likes these books.',
                             type=auth_profile or 'group')

        for obj in [david, roger]:
            model.Session.add(obj)

        cls.group_names.add(u'david')
        cls.group_names.add(u'roger')

        model.Session.flush()

        model.Session.add(model.Member(table_id=pkg1.id, table_name='package', group=david))
        model.Session.add(model.Member(table_id=pkg2.id, table_name='package', group=david))
        model.Session.add(model.Member(table_id=pkg1.id, table_name='package', group=roger))
        # authz
        sysadmin = model.User(name=u'testsysadmin', password=u'testsysadmin')
        sysadmin.sysadmin = True
        model.Session.add_all([
            model.User(name=u'tester', password=u'tester'),
            model.User(name=u'joeadmin', password=u'joeadmin'),
            model.User(name=u'annafan', about=u'I love reading Annakarenina. My site: http://datahub.io', password=u'annafan'),
            model.User(name=u'russianfan', password=u'russianfan'),
            sysadmin,
            ])
        cls.user_refs.extend([u'tester', u'joeadmin', u'annafan', u'russianfan', u'testsysadmin'])

        # Create activities for packages
        for item in [pkg1, pkg2]:
            from ckanext.activity.model import Activity
            activity = Activity.activity_stream_item(item, 'new', 'not logged in')
            model.Session.add(activity)

        model.repo.commit_and_remove()

    # method used in DGU and all good tests elsewhere
    @classmethod
    def create_users(cls, user_dicts: list[dict[str, Any]]):
        needs_commit = False
        for user_dict in user_dicts:
            user = cls._create_user_without_commit(**user_dict)
            if user:
                needs_commit = True
        if needs_commit:
            model.repo.commit_and_remove()

    @classmethod
    def _create_user_without_commit(cls, name: str = '',
                                    **user_dict: Any):
        if model.User.by_name(name):
            log.warning('Cannot create user "%s" as it already exists.' %
                        name or user_dict['name'])
            return
        # User objects are not revisioned so no need to create a revision
        user_ref = name
        assert user_ref
        for k, v in user_dict.items():
            if v is not None:
                if bool(v):
                    user_dict[k] = v
                else:
                    # avoid unicode warnings
                    user_dict[k] = str(v)
        user = model.User(name=str(name), **user_dict)
        model.Session.add(user)
        cls.user_refs.append(user_ref)
        return user

    @classmethod
    def create_user(cls, name: str = '', **kwargs: Any):
        user = cls._create_user_without_commit(name, **kwargs)
        model.Session.commit()
        return user

    @classmethod
    def flag_for_deletion(
            cls, pkg_names: Union[str, list[str]] = [],
            tag_names: list[str] = [], group_names: list[str] = [],
            user_names: list[str] = []):
        '''If you create a domain object manually in your test then you
        can name it here (flag it up) and it will be deleted when you next
        call CreateTestData.delete().'''
        if isinstance(pkg_names, str):
            pkg_names = [pkg_names]
        cls.pkg_names.extend(pkg_names)
        cls.tag_names.extend(tag_names)
        cls.group_names = cls.group_names.union(set(group_names))
        cls.user_refs.extend(user_names)

    @classmethod
    def delete(cls):
        '''Purges packages etc. that were created by this class.'''
        for pkg_name in cls.pkg_names:
            model.Session().autoflush = False
            pkg = model.Package.by_name(str(pkg_name))
            if pkg:
                pkg.purge()
        for tag_name in cls.tag_names:
            tag = model.Tag.by_name(str(tag_name))
            if tag:
                tag.purge()
        for group_name in cls.group_names:
            group = model.Group.by_name(str(group_name))
            if group:
                model.Session.delete(group)
        for user_name in cls.user_refs:
            user = model.User.get(str(user_name))
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

    @classmethod
    def make_some_vocab_tags(cls):

        # Create a couple of vocabularies.
        genre_vocab = model.Vocabulary(u'genre')
        model.Session.add(genre_vocab)
        composers_vocab = model.Vocabulary(u'composers')
        model.Session.add(composers_vocab)

        # Create some additional free tags for tag search tests.
        tolkien_tag = model.Tag(name="tolkien")
        model.Session.add(tolkien_tag)
        toledo_tag = model.Tag(name="toledo")
        model.Session.add(toledo_tag)
        tolerance_tag = model.Tag(name="tolerance")
        model.Session.add(tolerance_tag)
        tollbooth_tag = model.Tag(name="tollbooth")
        model.Session.add(tollbooth_tag)
        # We have to add free tags to a package or they won't show up in tag results.
        pkg = model.Package.get('warandpeace')
        assert pkg
        pkg.add_tags((tolkien_tag, toledo_tag,
            tolerance_tag, tollbooth_tag))

        # Create some tags that belong to vocabularies.
        sonata_tag = model.Tag(name=u'sonata', vocabulary_id=genre_vocab.id)
        model.Session.add(sonata_tag)

        bach_tag = model.Tag(name=u'Bach', vocabulary_id=composers_vocab.id)
        model.Session.add(bach_tag)

        neoclassical_tag = model.Tag(name='neoclassical',
                vocabulary_id=genre_vocab.id)
        model.Session.add(neoclassical_tag)

        neofolk_tag = model.Tag(name='neofolk', vocabulary_id=genre_vocab.id)
        model.Session.add(neofolk_tag)

        neomedieval_tag = model.Tag(name='neomedieval',
                vocabulary_id=genre_vocab.id)
        model.Session.add(neomedieval_tag)

        neoprog_tag = model.Tag(name='neoprog',
                vocabulary_id=genre_vocab.id)
        model.Session.add(neoprog_tag)

        neopsychedelia_tag = model.Tag(name='neopsychedelia',
                vocabulary_id=genre_vocab.id)
        model.Session.add(neopsychedelia_tag)

        neosoul_tag = model.Tag(name='neosoul', vocabulary_id=genre_vocab.id)
        model.Session.add(neosoul_tag)

        nerdcore_tag = model.Tag(name='nerdcore', vocabulary_id=genre_vocab.id)
        model.Session.add(nerdcore_tag)

        pkg = model.Package.get('warandpeace')
        assert pkg
        pkg.add_tag(bach_tag)
        pkg = model.Package.get('annakarenina')
        assert pkg
        pkg.add_tag(sonata_tag)

        model.Session.commit()



search_items = [{'name':'gils',
              'title':'Government Information Locator Service',
              'url':'',
              'tags':'registry,country-usa,government,federal,gov,workshop-20081101,penguin'.split(','),
              'resources':[{'url':'http://www.dcsf.gov.uk/rsgateway/DB/SFR/s000859/SFR17_2009_tables.xls',
                          'format':'XLS',
                          'last_modified': datetime.datetime(2005, 10, 1),
                          'description':'December 2009 | http://www.statistics.gov.uk/hub/id/119-36345'},
                          {'url':'http://www.dcsf.gov.uk/rsgateway/DB/SFR/s000860/SFR17_2009_key.doc',
                          'format':'DOC',
                          'description':'http://www.statistics.gov.uk/hub/id/119-34565'}],
              'groups':'ukgov test1 test2 penguin',
              'license':'odc-by',
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
     'resources':[{'url':'http://www.decc.gov.uk/assets/decc/statistics/source/prices/qep211.xls', 'format':'XLS', 'description':'Quarterly 23/2/12'}],
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

group_hierarchy_groups = [
    {'name': 'department-of-health',
     'title': 'Department of Health',
     'contact-email': 'contact@doh.gov.uk',
     'type': 'organization',
     'is_organization': True
     },
    {'name': 'food-standards-agency',
     'title': 'Food Standards Agency',
     'contact-email': 'contact@fsa.gov.uk',
     'parent': 'department-of-health',
     'type': 'organization',
     'is_organization': True},
    {'name': 'national-health-service',
     'title': 'National Health Service',
     'contact-email': 'contact@nhs.gov.uk',
     'parent': 'department-of-health',
     'type': 'organization',
     'is_organization': True,
     'editors': ['nhseditor'],
     'admins': ['nhsadmin']},
    {'name': 'nhs-wirral-ccg',
     'title': 'NHS Wirral CCG',
     'contact-email': 'contact@wirral.nhs.gov.uk',
     'parent': 'national-health-service',
     'type': 'organization',
     'is_organization': True,
     'editors': ['wirraleditor'],
     'admins': ['wirraladmin']},
    {'name': 'nhs-southwark-ccg',
     'title': 'NHS Southwark CCG',
     'contact-email': 'contact@southwark.nhs.gov.uk',
     'parent': 'national-health-service',
     'type': 'organization',
     'is_organization': True},
    {'name': 'cabinet-office',
     'title': 'Cabinet Office',
     'contact-email': 'contact@cabinet-office.gov.uk',
     'type': 'organization',
     'is_organization': True},
    ]

group_hierarchy_datasets = [
    {'name': 'doh-spend', 'title': 'Department of Health Spend Data',
     'groups': ['department-of-health']},
    {'name': 'nhs-spend', 'title': 'NHS Spend Data',
     'groups': ['national-health-service']},
    {'name': 'wirral-spend', 'title': 'Wirral Spend Data',
     'groups': ['nhs-wirral-ccg']},
    {'name': 'southwark-spend', 'title': 'Southwark Spend Data',
     'groups': ['nhs-southwark-ccg']},
    ]

group_hierarchy_users = [{'name': 'nhsadmin', 'password': 'pass'},
                         {'name': 'nhseditor', 'password': 'pass'},
                         {'name': 'wirraladmin', 'password': 'pass'},
                         {'name': 'wirraleditor', 'password': 'pass'},
                         ]

# Some test terms and translations.
terms = ('A Novel By Tolstoy',
    'Index of the novel',
    'russian',
    'tolstoy',
    "Dave's books",
    "Roger's books",
    'romantic novel',
    'book',
    '123',
    '456',
    '789',
    'plain text',
    'Roger likes these books.',
)
english_translations = {
    '123': 'jealousy',
    '456': 'realism',
    '789': 'hypocrisy',
}
german_translations = {
    'A Novel By Tolstoy': 'Roman von Tolstoi',
    'Index of the novel': 'Index des Romans',
    'russian': 'Russisch',
    'tolstoy': 'Tolstoi',
    "Dave's books": 'Daves Bucher',
    "Roger's books": 'Rogers Bucher',
    'romantic novel': 'Liebesroman',
    'book': 'Buch',
    '456': 'Realismus',
    '789': 'Heuchelei',
    'plain text': 'Klartext',
    'Roger likes these books.': 'Roger mag diese Bucher.'
}
french_translations = {
    'A Novel By Tolstoy': 'A Novel par Tolstoi',
    'Index of the novel': 'Indice du roman',
    'russian': 'russe',
    'romantic novel': 'roman romantique',
    'book': 'livre',
    '123': 'jalousie',
    '789': 'hypocrisie',
}
