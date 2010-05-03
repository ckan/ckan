from pylons import config

from ckan.tests import *
import ckan.model as model
import ckan.authz as authz
import simplejson
import webhelpers
from ckan.lib.create_test_data import CreateTestData

ACCESS_DENIED = [401,403]

class TestRest(TestController):

    @classmethod
    def setup_class(self):
        try:
            CreateTestData.delete()
        except:
            pass
        model.Session.remove()
        CreateTestData.create()
        model.Session.add(model.Package(name=u'--'))
        rev = model.repo.new_revision()
        model.repo.commit_and_remove()
        from ckan.model.changeset import ChangesetRegister
        changesets = ChangesetRegister()
        changesets.construct_from_revision(rev)

        self.testpackage_license_id = u'gpl-3.0'
        self.testpackagevalues = {
            'name' : u'testpkg',
            'title': u'Some Title',
            'url': u'http://blahblahblah.mydomain',
            'resources': [{
                u'url':u'http://blah.com/file.xml',
                u'format':u'xml',
                u'description':u'Main file',
                u'hash':u'abc123',
            }, {
                u'url':u'http://blah.com/file2.xml',
                u'format':u'xml',
                u'description':u'Second file',
                u'hash':u'def123',
            }],
            'tags': [u'russion', u'novel'],
            'license_id': self.testpackage_license_id,
            'extras': {
                'genre' : u'horror',
                'media' : u'dvd',
            },
        }
        self.testgroupvalues = {
            'name' : u'testgroup',
            'title' : u'Some Group Title',
            'description' : u'Great group!',
            'packages' : [u'annakarenina', 'warandpeace'],
        }
        self.random_name = u'http://myrandom.openidservice.org/'
        self.user = model.User(name=self.random_name)
        model.Session.add(self.user)
        model.Session.commit()
        model.Session.remove()
        self.extra_environ={'Authorization' : str(self.user.apikey)}

    @classmethod
    def teardown_class(self):
        model.Session.remove()
        model.repo.rebuild_db()
        model.Session.remove()

    def test_01_register_post_noauth(self):
        # Test Packages Register Post 401.
        offset = '/api/rest/package'
        postparams = '%s=1' % simplejson.dumps(self.testpackagevalues)
        res = self.app.post(offset, params=postparams, status=ACCESS_DENIED)

    def test_01_entity_put_noauth(self):
        # Test Packages Entity Put 401.
        offset = '/api/rest/package/%s' % u'--'
        postparams = '%s=1' % simplejson.dumps(self.testpackagevalues)
        res = self.app.post(offset, params=postparams, status=ACCESS_DENIED)

    def test_01_entity_delete_noauth(self):
        # Test Packages Entity Delete 401.
        offset = '/api/rest/package/%s' % u'annakarenina'
        res = self.app.delete(offset, status=ACCESS_DENIED)

    def test_02_list_package(self):
        # Test Packages Register Get 200.
        offset = '/api/rest/package'
        res = self.app.get(offset, status=[200])
        assert 'annakarenina' in res, res
        assert 'warandpeace' in res, res

    def test_02_list_tags(self):
        # Test Packages Register Get 200.
        offset = '/api/rest/tag'
        res = self.app.get(offset, status=[200])
        assert 'russian' in res, res
        assert 'tolstoy' in res, res

    def test_02_list_groups(self):
        offset = '/api/rest/group'
        res = self.app.get(offset, status=[200])
        assert 'david' in res, res
        assert 'roger' in res, res

    def test_04_get_package(self):
        # Test Packages Register Get 200.
        #   ..or is that "entity get"? "register get" == "list" --jb
        offset = '/api/rest/package/annakarenina'
        res = self.app.get(offset, status=[200])
        anna = model.Package.by_name(u'annakarenina')
        assert 'annakarenina' in res, res
        assert '"license_id": "other-open"' in res, str(res)
        assert 'russian' in res, res
        assert 'tolstoy' in res, res
        assert '"extras": {' in res, res
        assert '"genre": "romantic novel"' in res, res
        assert '"original media": "book"' in res, res
        assert 'annakarenina.com/download' in res, res
        assert '"plain text"' in res, res
        assert '"Index of the novel"' in res, res
        # 2/12/09 download_url is now deprecated - to be removed in the future
        assert '"download_url": "http://www.annakarenina.com/download/x=1&y=2"' in res, res
        assert '"id": "%s"' % anna.id in res, res


    def _test_04_ckan_url(self):
        # NB This only works if run on its own
        config['ckan_host'] = 'test.ckan.net'
        offset = '/api/rest/package/annakarenina'
        res = self.app.get(offset, status=[200])
        assert 'ckan_url' in res
        assert '"ckan_url": "http://test.ckan.net/package/annakarenina"' in res, res

    def test_04_get_tag(self):
        offset = '/api/rest/tag/tolstoy'
        res = self.app.get(offset, status=[200])
        assert 'annakarenina' in res, res
        assert not 'warandpeace' in res, res

    def test_04_get_group(self):
        offset = '/api/rest/group/roger'
        res = self.app.get(offset, status=[200])
        assert 'annakarenina' in res, res
        assert not 'warandpeace' in res, res

    def test_05_get_404_package(self):
        # Test Package Entity Get 404.
        offset = '/api/rest/package/22222'
        res = self.app.get(offset, status=404)
        model.Session.remove()

    def test_05_get_404_group(self):
        # Test Group Entity Get 404.
        offset = '/api/rest/group/22222'
        res = self.app.get(offset, status=404)
        model.Session.remove()

    def test_05_get_404_tag(self):
        # Test Tag Entity Get 404.
        offset = '/api/rest/tag/doesntexist'
        res = self.app.get(offset, status=404)
        model.Session.remove()

    def test_06_create_pkg(self):
        # Test Packages Register Post 200.
        assert not model.Package.by_name(self.testpackagevalues['name'])
        offset = '/api/rest/package'
        postparams = '%s=1' % simplejson.dumps(self.testpackagevalues)
        res = self.app.post(offset, params=postparams, status=[200],
                extra_environ=self.extra_environ)
        model.Session.remove()
        pkg = model.Package.by_name(self.testpackagevalues['name'])
        assert pkg
        assert pkg.title == self.testpackagevalues['title'], pkg
        assert pkg.url == self.testpackagevalues['url'], pkg
        assert pkg.license_id == self.testpackage_license_id, pkg
        assert len(pkg.tags) == 2
        assert len(pkg.extras) == 2, len(pkg.extras)
        for key, value in self.testpackagevalues['extras'].items():
            assert pkg.extras[key] == value, pkg.extras
        assert len(pkg.resources) == len(self.testpackagevalues['resources']), pkg.resources
        for res_index, resource in enumerate(self.testpackagevalues['resources']):
            comp_resource = pkg.resources[res_index]
            for key in resource.keys():
                comp_value = getattr(comp_resource, key)
                assert comp_value == resource[key], '%s != %s' % (comp_value, resource[key])

        # Test Package Entity Get 200.
        offset = '/api/rest/package/%s' % self.testpackagevalues['name']
        res = self.app.get(offset, status=[200])
        assert self.testpackagevalues['name'] in res, res
        assert '"license_id": "%s"' % self.testpackagevalues['license_id'] in res, res
        assert self.testpackagevalues['tags'][0] in res, res
        assert self.testpackagevalues['tags'][1] in res, res
        assert '"extras": {' in res, res
        for key, value in self.testpackagevalues['extras'].items():
            assert '"%s": "%s"' % (key, value) in res, res
        
        model.Session.remove()
        
        # Test Packages Register Post 409 (conflict - create duplicate package).
        offset = '/api/rest/package'
        postparams = '%s=1' % simplejson.dumps(self.testpackagevalues)
        res = self.app.post(offset, params=postparams, status=[409],
                extra_environ=self.extra_environ)
        model.Session.remove()

    def test_06_create_pkg_using_download_url(self):
        # 2/12/09 download_url is deprecated - remove in future
        test_params = {
            'name':u'testpkg06',
            'download_url':u'testurl',
            }
        offset = '/api/rest/package'
        postparams = '%s=1' % simplejson.dumps(test_params)
        res = self.app.post(offset, params=postparams, status=[200],
                extra_environ=self.extra_environ)
        model.Session.remove()
        pkg = model.Package.by_name(test_params['name'])
        assert pkg
        assert pkg.name == test_params['name'], pkg
        assert len(pkg.resources) == 1, pkg.resources
        assert pkg.resources[0].url == test_params['download_url'], pkg.resources[0]

    def test_06_create_group(self):
        offset = '/api/rest/group'
        postparams = '%s=1' % simplejson.dumps(self.testgroupvalues)
        res = self.app.post(offset, params=postparams, status=200,
                extra_environ=self.extra_environ)
        model.Session.remove()
        group = model.Group.by_name(self.testgroupvalues['name'])
        assert group
        model.setup_default_user_roles(group, [self.user])
        rev = model.repo.new_revision()
        model.repo.commit_and_remove()
        group = model.Group.by_name(self.testgroupvalues['name'])
        assert group
        assert group.title == self.testgroupvalues['title'], group
        assert group.description == self.testgroupvalues['description'], group
        assert len(group.packages) == 2, len(group.packages)
        anna = model.Package.by_name(u'annakarenina')
        warandpeace = model.Package.by_name(u'warandpeace')
        assert anna in group.packages
        assert warandpeace in group.packages

        # Test Package Entity Get 200.
        offset = '/api/rest/group/%s' % self.testgroupvalues['name']
        res = self.app.get(offset, status=[200])
        assert self.testgroupvalues['name'] in res, res
        assert self.testgroupvalues['packages'][0] in res, res
        assert self.testgroupvalues['packages'][1] in res, res
        
        model.Session.remove()
        
        # Test Packages Register Post 409 (conflict - create duplicate package).
        offset = '/api/rest/group'
        postparams = '%s=1' % simplejson.dumps(self.testgroupvalues)
        res = self.app.post(offset, params=postparams, status=[409],
                extra_environ=self.extra_environ)
        model.Session.remove()

    def test_06_rate_package(self):
        # Test Rating Register Post 200.
        self.clear_all_tst_ratings()
        offset = '/api/rest/rating'
        rating_opts = {'package':u'warandpeace',
                       'rating':5}
        postparams = '%s=1' % simplejson.dumps(rating_opts)
        res = self.app.post(offset, params=postparams, status=[200],
                extra_environ=self.extra_environ)
        model.Session.remove()
        pkg = model.Package.by_name(rating_opts['package'])
        assert pkg
        assert len(pkg.ratings) == 1
        assert pkg.ratings[0].rating == rating_opts['rating'], pkg.ratings

        # Get package to see rating
        offset = '/api/rest/package/%s' % rating_opts['package']
        res = self.app.get(offset, status=[200])
        assert rating_opts['package'] in res, res
        assert '"ratings_average": %s.0' % rating_opts['rating'] in res, res
        assert '"ratings_count": 1' in res, res
        
        model.Session.remove()
        
        # Rerate package
        offset = '/api/rest/rating'
        postparams = '%s=1' % simplejson.dumps(rating_opts)
        res = self.app.post(offset, params=postparams, status=[200],
                extra_environ=self.extra_environ)
        model.Session.remove()
        pkg = model.Package.by_name(rating_opts['package'])
        assert pkg
        assert len(pkg.ratings) == 1
        assert pkg.ratings[0].rating == rating_opts['rating'], pkg.ratings

    def test_06_rate_package_out_of_range(self):
        self.clear_all_tst_ratings()
        offset = '/api/rest/rating'
        rating_opts = {'package':u'warandpeace',
                       'rating':0}
        postparams = '%s=1' % simplejson.dumps(rating_opts)
        res = self.app.post(offset, params=postparams, status=[400],
                extra_environ=self.extra_environ)
        model.Session.remove()
        pkg = model.Package.by_name(rating_opts['package'])
        assert pkg
        assert len(pkg.ratings) == 0

    def _test_09_entity_put_404(self):
        # TODO: get this working again. At present returns 400
        # Test Package Entity Put 404.
        offset = '/api/rest/package/22222'
        postparams = '%s=1' % simplejson.dumps(self.testpackagevalues)
        # res = self.app.post(offset, params=postparams, status=[404],
        #        extra_environ=self.extra_environ)
        model.Session.remove()

    def test_10_edit_pkg_values(self):
        # Test Packages Entity Put 200.

        # create a package with testpackagevalues
        tag_names = [u'tag1', u'tag2', u'tag3']
        pkg = model.Package.by_name(self.testpackagevalues['name'])
        if not pkg:
            pkg = model.Package()
            model.Session.add(pkg)
        rev = model.repo.new_revision()
        pkg.name = self.testpackagevalues['name']
        pkg.url = self.testpackagevalues['url']
        tags = [model.Tag(name=tag_name) for tag_name in tag_names]
        for tag in tags:
            model.Session.add(tag)
        pkg.tags = tags
        pkg.extras = {u'key1':u'val1', u'key2':u'val2'}
        model.Session.commit()

        pkg = model.Package.by_name(self.testpackagevalues['name'])
        model.setup_default_user_roles(pkg, [self.user])
        rev = model.repo.new_revision()
        model.repo.commit_and_remove()

        # edit it
        pkg_vals = {
            'name':u'somethingnew',
            'title':u'newtesttitle',
            'resources': [
                {
                    u'url':u'http://blah.com/file2.xml',
                    u'format':u'xml',
                    u'description':u'Appendix 1',
                    u'hash':u'def123',
                },
                {
                    u'url':u'http://blah.com/file3.xml',
                    u'format':u'xml',
                    u'description':u'Appenddic 2',
                    u'hash':u'ghi123',
                },
            ],
            'extras':{u'key3':u'val3', u'key2':None},
            'tags':[u'tag1', u'tag2', u'tag4', u'tag5'],
        }
        offset = '/api/rest/package/%s' % self.testpackagevalues['name']
        postparams = '%s=1' % simplejson.dumps(pkg_vals)
        res = self.app.post(offset, params=postparams, status=[200],
                            extra_environ=self.extra_environ)

        # Check submitted field have changed.
        model.Session.remove()
        pkg = model.Session.query(model.Package).filter_by(name=pkg_vals['name']).one()
        # - title
        assert pkg.title == pkg_vals['title']
        # - tags
        pkg_tagnames = [tag.name for tag in pkg.tags]
        for tagname in pkg_vals['tags']:
            assert tagname in pkg_tagnames, 'tag %r not in %r' % (tagname, pkg_tagnames)
        # - resources
        assert len(pkg.resources), "Package has no resources: %s" % pkg
        assert len(pkg.resources) == 2, len(pkg.resources)
        resource = pkg.resources[0]
        assert resource.url == u'http://blah.com/file2.xml', resource.url
        assert resource.format == u'xml', resource.format
        assert resource.description == u'Appendix 1', resource.description
        assert resource.hash == u'def123', resource.hash
        resource = pkg.resources[1]
        assert resource.url == 'http://blah.com/file3.xml', resource.url
        assert resource.format == u'xml', resource.format
        assert resource.description == u'Appenddic 2', resource.description
        assert resource.hash == u'ghi123', resource.hash

        # Check unsubmitted fields have not changed.
        # - url
        assert pkg.url == self.testpackagevalues['url'], pkg.url
        # - extras
        assert len(pkg.extras) == 2, pkg.extras
        for key, value in {u'key1':u'val1', u'key3':u'val3'}.items():
            assert pkg.extras[key] == value, pkg.extras

    def test_10_edit_pkg_with_download_url(self):
        # 2/12/09 download_url is deprecated - remove in future
        test_params = {
            'name':u'testpkg10',
            'download_url':u'testurl',
            }
        rev = model.repo.new_revision()
        pkg = model.Package()
        model.Session.add(pkg)
        pkg.name = test_params['name']
        pkg.download_url = test_params['download_url']
        model.Session.commit()

        pkg = model.Package.by_name(test_params['name'])
        model.setup_default_user_roles(pkg, [self.user])
        rev = model.repo.new_revision()
        model.repo.commit_and_remove()
        assert model.Package.by_name(test_params['name'])

        # edit it
        pkg_vals = {'download_url':u'newurl'}
        offset = '/api/rest/package/%s' % test_params['name']
        postparams = '%s=1' % simplejson.dumps(pkg_vals)
        res = self.app.post(offset, params=postparams, status=[200],
                            extra_environ=self.extra_environ)
        model.Session.remove()
        pkg = model.Session.query(model.Package).filter_by(name=test_params['name']).one()
        assert len(pkg.resources) == 1, pkg.resources
        assert pkg.resources[0].url == pkg_vals['download_url']

    def test_10_edit_group(self):
        # create a group with testgroupvalues
        group = model.Group.by_name(self.testgroupvalues['name'])
        if not group:
            offset = '/api/rest/group'
            postparams = '%s=1' % simplejson.dumps(self.testgroupvalues)
            res = self.app.post(offset, params=postparams, status=[200],
                    extra_environ=self.extra_environ)
            model.Session.remove()
            group = model.Group.by_name(self.testgroupvalues['name'])
        assert group
        assert len(group.packages) == 2, group.packages
        user = model.User.by_name(self.random_name)
        model.setup_default_user_roles(group, [user])

        # edit it
        group_vals = {'name':u'somethingnew', 'title':u'newtesttitle',
                      'packages':[u'annakarenina']}
        offset = '/api/rest/group/%s' % self.testgroupvalues['name']
        postparams = '%s=1' % simplejson.dumps(group_vals)
        res = self.app.post(offset, params=postparams, status=[200],
                            extra_environ=self.extra_environ)
        model.Session.remove()
        group = model.Session.query(model.Group).filter_by(name=group_vals['name']).one()
        assert group.name == group_vals['name']
        assert group.title == group_vals['title']
        assert len(group.packages) == 1, group.packages
        assert group.packages[0].name == group_vals['packages'][0]


    def test_10_edit_pkg_name_duplicate(self):
        # create a package with testpackagevalues
        if not model.Package.by_name(self.testpackagevalues['name']):
            pkg = model.Package()
            model.Session.add(pkg)
            pkg.name = self.testpackagevalues['name']
            rev = model.repo.new_revision()
            model.Session.commit()

            pkg = model.Package.by_name(self.testpackagevalues['name'])
            model.setup_default_user_roles(pkg, [self.user])
            rev = model.repo.new_revision()
            model.repo.commit_and_remove()
        assert model.Package.by_name(self.testpackagevalues['name'])
        
        # create a package with name 'dupname'
        dupname = u'dupname'
        if not model.Package.by_name(dupname):
            pkg = model.Package()
            model.Session.add(pkg)
            pkg.name = dupname
            rev = model.repo.new_revision()
            model.Session.commit()
        assert model.Package.by_name(dupname)

        # edit first package to have dupname
        pkg_vals = {'name':dupname}
        offset = '/api/rest/package/%s' % self.testpackagevalues['name']
        postparams = '%s=1' % simplejson.dumps(pkg_vals)
        res = self.app.post(offset, params=postparams, status=[409],
                            extra_environ=self.extra_environ)
        model.Session.remove()

    def test_10_edit_group_name_duplicate(self):
        # create a group with testgroupvalues
        if not model.Group.by_name(self.testgroupvalues['name']):
            group = model.Group()
            model.Session.add(group)
            group.name = self.testgroupvalues['name']
            rev = model.repo.new_revision()
            model.Session.commit()

            group = model.Group.by_name(self.testgroupvalues['name'])
            model.setup_default_user_roles(group, [self.user])
            rev = model.repo.new_revision()
            model.repo.commit_and_remove()
        assert model.Group.by_name(self.testgroupvalues['name'])
        
        # create a group with name 'dupname'
        dupname = u'dupname'
        if not model.Group.by_name(dupname):
            group = model.Group()
            model.Session.add(group)
            group.name = dupname
            rev = model.repo.new_revision()
            model.Session.commit()
        assert model.Group.by_name(dupname)

        # edit first group to have dupname
        group_vals = {'name':dupname}
        offset = '/api/rest/group/%s' % self.testgroupvalues['name']
        postparams = '%s=1' % simplejson.dumps(group_vals)
        res = self.app.post(offset, params=postparams, status=[409],
                            extra_environ=self.extra_environ)
        model.Session.remove()
        
    def test_11_delete_pkg(self):
        # Test Packages Entity Delete 200.

        # create a package with testpackagevalues
        if not model.Package.by_name(self.testpackagevalues['name']):
            pkg = model.Package()
            model.Session.add(pkg)
            pkg.name = self.testpackagevalues['name']
            rev = model.repo.new_revision()
            model.repo.commit_and_remove()

            pkg = model.Package.by_name(self.testpackagevalues['name'])
            model.setup_default_user_roles(pkg, [self.user])
            rev = model.repo.new_revision()
            model.repo.commit_and_remove()
        assert model.Package.by_name(self.testpackagevalues['name'])

        # delete it
        offset = '/api/rest/package/%s' % self.testpackagevalues['name']
        res = self.app.delete(offset, status=[200],
                extra_environ=self.extra_environ)
        pkg = model.Package.by_name(self.testpackagevalues['name'])
        assert pkg.state == 'deleted'
        model.Session.remove()

    def test_11_delete_group(self):
        # Test Groups Entity Delete 200.

        # create a group with testpackagevalues
        group = model.Group.by_name(self.testgroupvalues['name'])
        if not group:
            group = model.Group()
            model.Session.add(group)
            group.name = self.testgroupvalues['name']
            rev = model.repo.new_revision()
            model.repo.commit_and_remove()

            group = model.Group.by_name(self.testgroupvalues['name'])
            model.setup_default_user_roles(group, [self.user])
            rev = model.repo.new_revision()
            model.repo.commit_and_remove()
        assert group
        user = model.User.by_name(self.random_name)
        model.setup_default_user_roles(group, [user])

        # delete it
        offset = '/api/rest/group/%s' % self.testgroupvalues['name']
        res = self.app.delete(offset, status=[200],
                extra_environ=self.extra_environ)
        assert not model.Group.by_name(self.testgroupvalues['name'])
        model.Session.remove()

    def test_12_get_pkg_404(self):
        # Test Package Entity Get 404.
        pkg_name = u'random_one'
        assert not model.Session.query(model.Package).filter_by(name=pkg_name).count()
        offset = '/api/rest/package/%s' % pkg_name
        res = self.app.get(offset, status=404)
        model.Session.remove()

    def test_12_get_group_404(self):
        # Test Package Entity Get 404.
        assert not model.Session.query(model.Group).filter_by(name=self.testgroupvalues['name']).count()
        offset = '/api/rest/group/%s' % self.testgroupvalues['name']
        res = self.app.get(offset, status=404)
        model.Session.remove()

    def test_13_delete_pkg_404(self):
        # Test Packages Entity Delete 404.
        pkg_name = u'random_one'
        assert not model.Session.query(model.Package).filter_by(name=pkg_name).count()
        offset = '/api/rest/package/%s' % pkg_name
        res = self.app.delete(offset, status=[404],
                              extra_environ=self.extra_environ)

    def test_13_delete_group_404(self):
        # Test Packages Entity Delete 404.
        assert not model.Session.query(model.Group).filter_by(name=self.testgroupvalues['name']).count()
        offset = '/api/rest/group/%s' % self.testgroupvalues['name']
        res = self.app.delete(offset, status=[404],
                              extra_environ=self.extra_environ)

    def test_14_get_revision(self):
        rev = model.Revision.youngest(model.Session)
        offset = '/api/rest/revision/%s' % rev.id
        res = self.app.get(offset, status=[200])
        res_dict = simplejson.loads(res.body)
        assert rev.id == res_dict['id']
        assert rev.timestamp.isoformat() == res_dict['timestamp'], (rev.timestamp.isoformat(), res_dict['timestamp'])
        assert 'packages' in res_dict
        assert isinstance(res_dict['packages'], list)
        assert len(res_dict['packages']) != 0, "List of package names is empty: %s" % res_dict['packages']

    def test_14_get_revision_404(self):
        revision_id = "xxxxxxxxxxxxxxxxxxxxxxxxxx"
        offset = '/api/rest/revision/%s' % revision_id
        res = self.app.get(offset, status=404)
        model.Session.remove()

    def test_15_list_changesets(self):
        offset = '/api/rest/changeset'
        res = self.app.get(offset, status=[200])
        from ckan.model.changeset import ChangesetRegister
        changesets = ChangesetRegister()
        assert len(changesets), "No changesets found in model."
        for id in changesets:
            assert id in res, "Didn't find changeset id '%s' in: %s" % (id, res)

    def test_15_get_changeset(self):
        from ckan.model.changeset import ChangesetRegister
        changesets = ChangesetRegister()
        assert len(changesets), "No changesets found in model."
        for id in changesets:
            offset = '/api/rest/changeset/%s' % id
            res = self.app.get(offset, status=[200])
            changeset_data = simplejson.loads(res.body)
            assert 'id' in changeset_data, "No 'id' in changeset data: %s" % changeset_data
            assert 'meta' in changeset_data, "No 'meta' in changeset data: %s" % changeset_data
            assert 'changes' in changeset_data, "No 'changes' in changeset data: %s" % changeset_data

    def test_15_get_changeset_404(self):
        changeset_id = "xxxxxxxxxxxxxxxxxxxxxxxxxx"
        offset = '/api/rest/changeset/%s' % changeset_id
        res = self.app.get(offset, status=404)
        model.Session.remove()

    def test_16_list_licenses(self):
        from ckan.model.license import LicenseRegister
        register = LicenseRegister()
        assert len(register), "No changesets found in model."
        offset = '/api/rest/licenses'
        res = self.app.get(offset, status=[200])
        licenses_data = simplejson.loads(res.body)
        assert len(licenses_data) == len(register), (len(licenses_data), len(register))
        for license_data in licenses_data:
            id = license_data['id']
            license = register[id]
            assert license['title'] == license.title
            assert license['url'] == license.url
            
class TestRelationships(TestController):
    @classmethod
    def setup_class(self):
        CreateTestData.create()
        username = u'barry'
        self.user = model.User(name=username)
        model.Session.add(self.user)
        model.Session.commit()
        model.Session.remove()
        self.extra_environ={ 'Authorization' : str(self.user.apikey) }
        self.comment = u'Comment umlaut: \xfc.'


    @classmethod
    def teardown_class(self):
        model.Session.remove()
        model.repo.rebuild_db()
        model.Session.remove()

    def _get_relationships(self, package1_name='annakarenina', type='relationships', package2_name=None):
        if not package2_name:
            offset = '/api/rest/package/%s/%s' % (str(package1_name), type)
        else:
            offset = '/api/rest/package/%s/%s/%s/' % (
                str(package1_name), type, str(package2_name))
        allowable_statuses = [200]
        if type:
            allowable_statuses.append(404)
        res = self.app.get(offset, status=allowable_statuses)
        if res.status == 200:
            res_dict = simplejson.loads(res.body) if res.body else []
            return res_dict
        else:
            return 404

    def _get_relationships_via_package(self, package1_name):
        offset = '/api/rest/package/%s' % (str(package1_name))
        res = self.app.get(offset, status=200)
        res_dict = simplejson.loads(res.body) if res.body else []
        return res_dict['relationships']

    @property
    def war(self):
        return model.Package.by_name(u'warandpeace')
    @property
    def anna(self):
        return model.Package.by_name(u'annakarenina')
    @property
    def anna_offset(self):
        return '/api/rest/package/annakarenina'

    def _check_relationships_rest(self, pkg1_name, pkg2_name=None,
                                 expected_relationships=[]):
        rels = self._get_relationships(package1_name=pkg1_name,
                                      package2_name=pkg2_name)
        assert len(rels) == len(expected_relationships), \
               'Found %i relationships, but expected %i.\nFound: %r' % \
               (len(rels), len(expected_relationships),
                ['%s %s %s' % (rel['subject'], rel['type'], rel['object']) \
                 for rel in rels])
        for rel in rels:
            the_expected_rel = None
            for expected_rel in expected_relationships:
                if expected_rel['type'] == rel['type'] and \
                   (pkg2_name or expected_rel['object'] == pkg2_name):
                    the_expected_rel = expected_rel
                    break
            if not the_expected_rel:
                raise Exception('Unexpected relationship: %s %s %s' %
                                (rel['subject'], rel['type'], rel['object']))
            for field in ('subject', 'object', 'type', 'comment'):
                if the_expected_rel.has_key(field):
                    assert rel[field] == the_expected_rel[field], rel

    def _check_relationship_dict(self, rel_dict, subject, type, object, comment):
        assert rel_dict['subject'] == subject, rel_dict
        assert rel_dict['object'] == object, rel_dict
        assert rel_dict['type'] == type, rel_dict
        assert rel_dict['comment'] == comment, rel_dict


    def test_01_add_relationship(self):
        # check anna has no existing relationships
        assert not self.anna.get_relationships()
        assert self._get_relationships(package1_name='annakarenina') == []
        assert self._get_relationships(package1_name='annakarenina',
                                       package2_name='warandpeace') == []
        assert self._get_relationships(package1_name='annakarenina',
                                       type='child_of',
                                       package2_name='warandpeace') == 404
        assert self._get_relationships_via_package('annakarenina') == []

        # make annakarenina parent of warandpeace
        offset='/api/rest/package/annakarenina/parent_of/warandpeace'
        postparams = '%s=1' % simplejson.dumps({'comment':self.comment})
        res = self.app.post(offset, params=postparams, status=[200],
                            extra_environ=self.extra_environ)

    def test_02_read_relationship(self):
        'check relationship is made (in test 01)'

        # check model is right
        rels = self.anna.get_relationships()
        assert len(rels) == 1, rels
        assert rels[0].type == 'child_of'
        assert rels[0].subject.name == 'warandpeace'
        assert rels[0].object.name == 'annakarenina'

        # check '/api/rest/package/annakarenina/relationships'
        rels = self._get_relationships(package1_name='annakarenina')
        assert len(rels) == 1
        self._check_relationship_dict(rels[0],
               'annakarenina', 'parent_of', 'warandpeace', self.comment)

        # check '/api/rest/package/annakarenina/relationships/warandpeace'
        rels = self._get_relationships(package1_name='annakarenina',
                                      package2_name='warandpeace')
        assert len(rels) == 1
        self._check_relationship_dict(rels[0],
               'annakarenina', 'parent_of', 'warandpeace', self.comment)

        # check '/api/rest/package/annakarenina/parent_of/warandpeace'
        rels = self._get_relationships(package1_name='annakarenina',
                                       type='parent_of',
                                      package2_name='warandpeace')
        assert len(rels) == 1
        self._check_relationship_dict(rels[0],
               'annakarenina', 'parent_of', 'warandpeace', self.comment)

        # same checks in reverse direction
        rels = self._get_relationships(package1_name='warandpeace')
        assert len(rels) == 1
        self._check_relationship_dict(rels[0],
               'warandpeace', 'child_of', 'annakarenina', self.comment)

        rels = self._get_relationships(package1_name='warandpeace',
                                      package2_name='annakarenina')
        assert len(rels) == 1
        self._check_relationship_dict(rels[0],
               'warandpeace', 'child_of', 'annakarenina', self.comment)

        rels = self._get_relationships(package1_name='warandpeace',
                                       type='child_of',
                                      package2_name='annakarenina')
        assert len(rels) == 1
        self._check_relationship_dict(rels[0],
               'warandpeace', 'child_of', 'annakarenina', self.comment)

        # check '/api/rest/package/annakarenina'
        rels = self._get_relationships_via_package('annakarenina')
        assert len(rels) == 1
        self._check_relationship_dict(rels[0],
               'annakarenina', 'parent_of', 'warandpeace', self.comment)
        

    def test_03_update_relationship(self):
        self._check_relationships_rest('warandpeace', 'annakarenina',
                                      [{'type': 'child_of',
                                        'comment': self.comment}])

        offset='/api/rest/package/annakarenina/parent_of/warandpeace'
        comment = u'New comment.'
        postparams = '%s=1' % simplejson.dumps({'comment':comment})
        res = self.app.post(offset, params=postparams, status=[200],
                            extra_environ=self.extra_environ)

        self._check_relationships_rest('warandpeace', 'annakarenina',
                                      [{'type': 'child_of',
                                        'comment': u'New comment.'}])

    def test_04_update_relationship_no_change(self):
        offset='/api/rest/package/annakarenina/parent_of/warandpeace'

        comment = u'New comment.' # same as previous test
        postparams = '%s=1' % simplejson.dumps({'comment':comment})
        res = self.app.post(offset, params=postparams, status=[200],
                            extra_environ=self.extra_environ)

        self._check_relationships_rest('warandpeace', 'annakarenina',
                                      [{'type': 'child_of',
                                        'comment': u'New comment.'}])

        
    def test_05_delete_relationship(self):
        self._check_relationships_rest('warandpeace', 'annakarenina',
                                      [{'type': 'child_of',
                                        'comment': u'New comment.'}])

        offset='/api/rest/package/annakarenina/parent_of/warandpeace'
        res = self.app.delete(offset, status=[200],
                              extra_environ=self.extra_environ)

        self._check_relationships_rest('warandpeace', 'annakarenina',
                                      [])


class TestSearch(TestController):
    @classmethod
    def setup_class(self):
        try:
            CreateTestData.delete()
        except:
            pass
        model.Session.remove()
        CreateTestData.create()
        self.base_url = '/api/search/package'

    @classmethod
    def teardown_class(self):
        model.Session.remove()
        model.repo.rebuild_db()
        model.Session.remove()

    def setup(self):
        self.testpackagevalues = {
            'name' : u'testpkg',
            'title': 'Some Title',
            'url': u'http://blahblahblah.mydomain',
            'resources': [{u'url':u'http://blahblahblah.mydomain',
                           u'format':u'', u'description':''}],
            'tags': ['russion', 'novel'],
            'license_id': u'gpl-3.0',
            'extras': {'national_statistic':'yes',
                       'geographic_coverage':'England, Wales'},
        }

        CreateTestData.create_arbitrary(self.testpackagevalues)

        model.Session.commit()
        model.Session.remove()


    def teardown(self):
        model.Session.remove()
        pkg = model.Package.by_name(self.testpackagevalues['name'])
        if pkg:
            pkg.purge()
        model.Session.commit()
        model.Session.remove()

    def test_01_uri_q(self):
        offset = self.base_url + '?q=%s' % self.testpackagevalues['name']
        res = self.app.get(offset, status=200)
        res_dict = simplejson.loads(res.body)
        assert u'testpkg' in res_dict['results'], res_dict['results']
        assert res_dict['count'] == 1, res_dict['count']

    def test_02_post_q(self):
        offset = self.base_url
        query = {'q':'testpkg'}
        res = self.app.post(offset, params=query, status=200)
        res_dict = simplejson.loads(res.body)
        assert u'testpkg' in res_dict['results'], res_dict['results']
        assert res_dict['count'] == 1, res_dict['count']

    def test_03_uri_qjson(self):
        query = {'q': self.testpackagevalues['name']}
        json_query = simplejson.dumps(query)
        offset = self.base_url + '?qjson=%s' % json_query
        res = self.app.get(offset, status=200)
        res_dict = simplejson.loads(res.body)
        assert u'testpkg' in res_dict['results'], res_dict['results']
        assert res_dict['count'] == 1, res_dict['count']

    def test_04_post_qjson(self):
        query = {'q': self.testpackagevalues['name']}
        json_query = simplejson.dumps(query)
        offset = self.base_url
        res = self.app.post(offset, params=json_query, status=200)
        res_dict = simplejson.loads(res.body)
        assert u'testpkg' in res_dict['results'], res_dict['results']
        assert res_dict['count'] == 1, res_dict['count']

    def test_05_uri_qjson_tags(self):
        query = {'q': 'annakarenina tags:russian tags:tolstoy'}
        json_query = simplejson.dumps(query)
        offset = self.base_url + '?qjson=%s' % json_query
        res = self.app.get(offset, status=200)
        res_dict = simplejson.loads(res.body)
        assert u'annakarenina' in res_dict['results'], res_dict['results']
        assert res_dict['count'] == 1, res_dict
        
    def test_05_uri_qjson_tags_multiple(self):
        query = {'q': 'tags:russian tags:tolstoy'}
        json_query = simplejson.dumps(query)
        offset = self.base_url + '?qjson=%s' % json_query
        res = self.app.get(offset, status=200)
        res_dict = simplejson.loads(res.body)
        assert u'annakarenina' in res_dict['results'], res_dict['results']
        assert res_dict['count'] == 1, res_dict

    def test_06_uri_q_tags(self):
        query = webhelpers.util.html_escape('annakarenina tags:russian tags:tolstoy')
        offset = self.base_url + '?q=%s' % query
        res = self.app.get(offset, status=200)
        res_dict = simplejson.loads(res.body)
        assert u'annakarenina' in res_dict['results'], res_dict['results']
        assert res_dict['count'] == 1, res_dict['count']

    def test_07_uri_qjson_tags(self):
        query = {'q': '', 'tags':['tolstoy']}
        json_query = simplejson.dumps(query)
        offset = self.base_url + '?qjson=%s' % json_query
        res = self.app.get(offset, status=200)
        res_dict = simplejson.loads(res.body)
        assert u'annakarenina' in res_dict['results'], res_dict['results']
        assert res_dict['count'] == 1, res_dict

    def test_07_uri_qjson_tags_multiple(self):
        query = {'q': '', 'tags':['tolstoy', 'russian']}
        json_query = simplejson.dumps(query)
        offset = self.base_url + '?qjson=%s' % json_query
        res = self.app.get(offset, status=200)
        res_dict = simplejson.loads(res.body)
        assert u'annakarenina' in res_dict['results'], res_dict['results']
        assert res_dict['count'] == 1, res_dict

    def test_07_uri_qjson_tags_reverse(self):
        query = {'q': '', 'tags':['russian']}
        json_query = simplejson.dumps(query)
        offset = self.base_url + '?qjson=%s' % json_query
        res = self.app.get(offset, status=200)
        res_dict = simplejson.loads(res.body)
        assert u'annakarenina' in res_dict['results'], res_dict['results']
        assert res_dict['count'] == 2, res_dict

    def test_07_uri_qjson_extras(self):
        query = {"geographic_coverage":"England"}
        json_query = simplejson.dumps(query)
        offset = self.base_url + '?qjson=%s' % json_query
        res = self.app.get(offset, status=200)
        res_dict = simplejson.loads(res.body)
        assert res_dict['count'] == 1, res_dict

    def test_07_uri_qjson_extras_2(self):
        query = {"national_statistic":"yes"}
        json_query = simplejson.dumps(query)
        offset = self.base_url + '?qjson=%s' % json_query
        res = self.app.get(offset, status=200)
        res_dict = simplejson.loads(res.body)
        assert res_dict['count'] == 1, res_dict
        
        
    def test_08_all_fields(self):
        rating = model.Rating(user_ip_address=u'123.1.2.3',
                              package=model.Package.by_name(u'annakarenina'),
                              rating=3.0)
        model.Session.add(rating)
        model.repo.commit_and_remove()
        
        query = {'q': 'russian', 'all_fields':1}
        json_query = simplejson.dumps(query)
        offset = self.base_url + '?qjson=%s' % json_query
        res = self.app.get(offset, status=200)
        res_dict = simplejson.loads(res.body)
        assert res_dict['count'] == 2, res_dict
        print res_dict['results']
        for rec in res_dict['results']:
            if rec['name'] == 'annakarenina':
                anna_rec = rec
                break
        assert anna_rec['name'] == 'annakarenina', res_dict['results']
        assert anna_rec['title'] == 'A Novel By Tolstoy', anna_rec['title']
        assert anna_rec['license_id'] == u'other-open', anna_rec['license_id']
        assert len(anna_rec['tags']) == 2, anna_rec['tags']
        for expected_tag in ['russian', 'tolstoy']:
            assert expected_tag in anna_rec['tags']
        assert anna_rec['ratings_average'] == 3.0, anna_rec['ratings_average']
        assert anna_rec['ratings_count'] == 1, anna_rec['ratings_count']

    def test_09_just_tags(self):
        offset = self.base_url + '?tags=russian&all_fields=1'
        res = self.app.get(offset, status=200)
        res_dict = simplejson.loads(res.body)
        assert res_dict['count'] == 2, res_dict

    def test_10_multiple_tags_with_plus(self):
        offset = self.base_url + '?tags=tolstoy+russian&all_fields=1'
        res = self.app.get(offset, status=200)
        res_dict = simplejson.loads(res.body)
        assert res_dict['count'] == 1, res_dict

    def test_10_multiple_tags_with_ampersand(self):
        offset = self.base_url + '?tags=tolstoy&tags=russian&all_fields=1'
        res = self.app.get(offset, status=200)
        res_dict = simplejson.loads(res.body)
        assert res_dict['count'] == 1, res_dict

    def test_10_many_tags_with_ampersand(self):
        offset = self.base_url + '?tags=tolstoy&tags=russian&tags=tolstoy'
        res = self.app.get(offset, status=200)
        res_dict = simplejson.loads(res.body)
        assert res_dict['count'] == 1, res_dict

    def test_11_pagination_limit(self):
        offset = self.base_url + '?all_fields=1&tags=russian&limit=1&order_by=name'
        res = self.app.get(offset, status=200)
        res_dict = simplejson.loads(res.body)
        assert res_dict['count'] == 2, res_dict
        assert len(res_dict['results']) == 1, res_dict
        assert res_dict['results'][0]['name'] == 'annakarenina', res_dict['results'][0]['name']

    def test_11_pagination_offset_limit(self):
        offset = self.base_url + '?all_fields=1&tags=russian&offset=1&limit=1&order_by=name'
        res = self.app.get(offset, status=200)
        res_dict = simplejson.loads(res.body)
        assert res_dict['count'] == 2, res_dict
        assert len(res_dict['results']) == 1, res_dict
        assert res_dict['results'][0]['name'] == 'warandpeace', res_dict['results'][0]['name']

    def test_12_search_revision(self):
        offset = '/api/search/revision'
        res = self.app.get(offset, status=200)
        revs = model.Session.query(model.Revision).all()
        res_dict = simplejson.loads(res.body)
        for rev in revs:
            print rev
            assert rev.id in res_dict, (rev.id, res_dict)

    def test_12_search_revision_since_rev(self):
        offset = '/api/search/revision'
        revs = model.Session.query(model.Revision).all()
        rev_first = revs[-1]
        params = "?since_rev=%s" % str(rev_first.id)
        res = self.app.get(offset+params, status=200)
        res_list = simplejson.loads(res.body)
        assert rev_first.id not in res_list
        for rev in revs[:-1]:
            assert rev.id in res_list, (rev.id, res_list)

    def test_12_search_revision_since_time(self):
        offset = '/api/search/revision'
        revs = model.Session.query(model.Revision).all()
        rev_first = revs[-1]
        params = "?since_time=%s" % model.strftimestamp(rev_first.timestamp)
        res = self.app.get(offset+params, status=200)
        res_list = simplejson.loads(res.body)
        assert rev_first.id not in res_list
        for rev in revs[:-1]:
            assert rev.id in res_list, (rev.id, res_list)

    def test_strftimestamp(self):
        import datetime
        t = datetime.datetime(2012, 3, 4, 5, 6, 7, 890123)
        s = model.strftimestamp(t)
        assert s == "2012-03-04T05:06:07.890123", s

    def test_strptimestamp(self):
        import datetime
        s = "2012-03-04T05:06:07.890123"
        t = model.strptimestamp(s)
        assert t == datetime.datetime(2012, 3, 4, 5, 6, 7, 890123), t


class TestApiMisc(TestController):
    @classmethod
    def setup_class(self):
        try:
            CreateTestData.delete()
        except:
            pass
        model.Session.remove()
        CreateTestData.create()
        self.base_url = '/api'

    @classmethod
    def teardown_class(self):
        model.Session.remove()
        CreateTestData.delete()

    def test_0_tag_counts(self):
        offset = self.base_url + '/tag_counts'
        res = self.app.get(offset, status=200)
        assert '["russian", 2]' in res, res
        assert '["tolstoy", 1]' in res, res
        
