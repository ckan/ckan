from ckan.tests import *
import ckan.model as model
import ckan.authz as authz
import simplejson
import webhelpers

ACCESS_DENIED = [401,403]
def get_license_name(id):
    return model.Session.get(model.License, id).name


class TestRestController(TestController):

    @classmethod
    def setup_class(self):
        try:
            CreateTestData.delete()
        except:
            pass
        model.Session.remove()
        CreateTestData.create()
        model.Package(name=u'--')
        rev = model.repo.new_revision()
        model.repo.commit_and_remove()


    @classmethod
    def teardown_class(self):
        model.Session.remove()
        model.repo.rebuild_db()
        model.Session.remove()

    def setup(self):
        self.testpackagevalues = {
            'name' : u'testpkg',
            'title': u'Some Title',
            'url': u'http://blahblahblah.mydomain',
            'resources': [{u'url':u'http://blah.com/file.xml',
                           u'format':u'xml',
                           u'description':u'Main file'},
                          {u'url':u'http://blah.com/file2.xml',
                           u'format':u'xml',
                           u'description':u'Second file'},],
            'tags': [u'russion', u'novel'],
            'license_id': u'4',
            'extras': {'genre' : u'horror',
                       'media' : u'dvd',
                       }
            }
        self.testgroupvalues = {
            'name' : u'testgroup',
            'title' : u'Some Group Title',
            'description' : 'Great group!',
            'packages' : [u'annakarenina', 'warandpeace'],
            }
        self.random_name = u'http://myrandom.openidservice.org/'
        self.user = model.User(name=self.random_name)
        model.Session.commit()
        self.extra_environ={ 'Authorization' : str(self.user.apikey) }
        model.Session.remove()


    def teardown(self):
        model.Session.remove()
        user = model.User.by_name(self.random_name)
        if user:
            user.purge()
        pkg = model.Package.by_name(self.testpackagevalues['name'])
        if pkg:
            pkg.purge()
        model.Session.commit()
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
        offset = '/api/rest/package/annakarenina'
        res = self.app.get(offset, status=[200])
        assert 'annakarenina' in res, res
        assert '"license_id": 9' in res, res
        expected_license = '"license": "%s"' % get_license_name(9)
        assert expected_license in res, repr(res) + repr(expected_license)
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
        # Test Package Entity Get 404.
        offset = '/api/rest/group/22222'
        res = self.app.get(offset, status=404)
        model.Session.remove()

    def test_06_create_pkg(self):
        # Test Packages Register Post 200.
        offset = '/api/rest/package'
        postparams = '%s=1' % simplejson.dumps(self.testpackagevalues)
        res = self.app.post(offset, params=postparams, status=[200],
                extra_environ=self.extra_environ)
        model.Session.remove()
        pkg = model.Package.by_name(self.testpackagevalues['name'])
        assert pkg
        assert pkg.title == self.testpackagevalues['title'], pkg
        assert pkg.url == self.testpackagevalues['url'], pkg
        assert pkg.license_id == int(self.testpackagevalues['license_id']), pkg
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
        assert '"license_id": %s' % self.testpackagevalues['license_id'] in res, res
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
            'name':'testpkg06',
            'download_url':'testurl',
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

    def _test_09_entity_put_404(self):
        # TODO: get this working again. At present returns 400
        # Test Package Entity Put 404.
        offset = '/api/rest/package/22222'
        postparams = '%s=1' % simplejson.dumps(self.testpackagevalues)
        # res = self.app.post(offset, params=postparams, status=[404],
        #        extra_environ=self.extra_environ)
        model.Session.remove()

    def test_10_edit_pkg(self):
        # Test Packages Entity Put 200.

        # create a package with testpackagevalues
        tag_names = [u'tag1', u'tag2', u'tag3']
        if not model.Package.by_name(self.testpackagevalues['name']):
            rev = model.repo.new_revision()
            pkg = model.Package()
            pkg.name = self.testpackagevalues['name']
            pkg.url = self.testpackagevalues['url']
            tags = [model.Tag(name=tag_name) for tag_name in tag_names]
            pkg.tags = tags
            pkg.extras = {u'key1':u'val1', u'key2':u'val2'}
            model.Session.commit()

            pkg = model.Package.by_name(self.testpackagevalues['name'])
            model.setup_default_user_roles(pkg, [self.user])
            rev = model.repo.new_revision()
            model.repo.commit_and_remove()
        assert model.Package.by_name(self.testpackagevalues['name'])

        # edit it
        pkg_vals = {'name':u'somethingnew',
                    'title':u'newtesttitle',
                    'extras':{u'key3':u'val3', u'key2':None},
                    'tags':[u'tag1', u'tag2', u'tag4', u'tag5']
                    }
        offset = '/api/rest/package/%s' % self.testpackagevalues['name']
        postparams = '%s=1' % simplejson.dumps(pkg_vals)
        res = self.app.post(offset, params=postparams, status=[200],
                            extra_environ=self.extra_environ)
        model.Session.remove()
        pkg = model.Package.query.filter_by(name=pkg_vals['name']).one()
        assert pkg.title == pkg_vals['title']
        pkg_tagnames = [tag.name for tag in pkg.tags]
        for tagname in pkg_vals['tags']:
            assert tagname in pkg_tagnames, 'tag %r not in %r' % (tagname, pkg_tagnames)
        # check that unsubmitted fields are unchanged
        assert pkg.url == self.testpackagevalues['url'], pkg.url
        
        assert len(pkg.extras) == 2, pkg.extras
        for key, value in {u'key1':u'val1', u'key3':u'val3'}.items():
            assert pkg.extras[key] == value, pkg.extras

    def test_10_edit_pkg_with_download_url(self):
        # 2/12/09 download_url is deprecated - remove in future
        test_params = {
            'name':'testpkg10',
            'download_url':'testurl',
            }
        rev = model.repo.new_revision()
        pkg = model.Package()
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
        pkg = model.Package.query.filter_by(name=test_params['name']).one()
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
            rev = model.repo.new_revision()
            model.repo.commit_and_remove()
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
        group = model.Group.query.filter_by(name=group_vals['name']).one()
        assert group.name == group_vals['name']
        assert group.title == group_vals['title']
        assert len(group.packages) == 1, group.packages
        assert group.packages[0].name == group_vals['packages'][0]


    def test_10_edit_pkg_name_duplicate(self):
        # create a package with testpackagevalues
        if not model.Package.by_name(self.testpackagevalues['name']):
            pkg = model.Package()
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
        rev = model.repo.new_revision()
        res = self.app.delete(offset, status=[200],
                extra_environ=self.extra_environ)
        pkg = model.Package.by_name(self.testpackagevalues['name'])
        assert pkg.state.name == 'deleted'
        model.Session.remove()

    def test_11_delete_group(self):
        # Test Groups Entity Delete 200.

        # create a group with testpackagevalues
        group = model.Group.by_name(self.testgroupvalues['name'])
        if not group:
            group = model.Group()
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
        rev = model.repo.new_revision()
        res = self.app.delete(offset, status=[200],
                extra_environ=self.extra_environ)
        assert not model.Group.by_name(self.testgroupvalues['name'])
        model.Session.remove()

    def test_12_get_pkg_404(self):
        # Test Package Entity Get 404.
        assert not model.Package.query.filter_by(name=self.testpackagevalues['name']).count()
        offset = '/api/rest/package/%s' % self.testpackagevalues['name']
        res = self.app.get(offset, status=404)
        model.Session.remove()

    def test_12_get_group_404(self):
        # Test Package Entity Get 404.
        assert not model.Group.query.filter_by(name=self.testgroupvalues['name']).count()
        offset = '/api/rest/group/%s' % self.testgroupvalues['name']
        res = self.app.get(offset, status=404)
        model.Session.remove()

    def test_13_delete_pkg_404(self):
        # Test Packages Entity Delete 404.
        assert not model.Package.query.filter_by(name=self.testpackagevalues['name']).count()
        offset = '/api/rest/package/%s' % self.testpackagevalues['name']
        res = self.app.delete(offset, status=[404],
                              extra_environ=self.extra_environ)

    def test_13_delete_group_404(self):
        # Test Packages Entity Delete 404.
        assert not model.Group.query.filter_by(name=self.testgroupvalues['name']).count()
        offset = '/api/rest/group/%s' % self.testgroupvalues['name']
        res = self.app.delete(offset, status=[404],
                              extra_environ=self.extra_environ)

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
        CreateTestData.delete()

    def setup(self):
        self.testpackagevalues = {
            'name' : u'testpkg',
            'title': 'Some Title',
            'url': u'http://blahblahblah.mydomain',
            'resources': [{u'url':u'http://blahblahblah.mydomain'}],
            'tags': ['russion', 'novel'],
            'license_id': '4',
        }

        self.pkg = model.Package()
        self.pkg.name = self.testpackagevalues['name']
        self.pkg.add_resource(self.testpackagevalues['resources'][0]['url'])
        rev = model.repo.new_revision()

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

    def test_08_all_fields(self):
        model.Rating(user_ip_address=u'123.1.2.3',
                     package=model.Package.by_name(u'annakarenina'),
                     rating=3.0)
        model.repo.commit_and_remove()
        
        query = {'q': 'russian', 'all_fields':1}
        json_query = simplejson.dumps(query)
        offset = self.base_url + '?qjson=%s' % json_query
        res = self.app.get(offset, status=200)
        res_dict = simplejson.loads(res.body)
        assert res_dict['count'] == 2, res_dict
        print res_dict['results']
        anna_rec = res_dict['results'][0]
        assert anna_rec['name'] == 'annakarenina', res_dict['results']
        assert anna_rec['title'] == 'A Novel By Tolstoy', res_dict['results']
        assert anna_rec['license'] == 'OKD Compliant::Other', anna_rec['license']
        assert anna_rec['tags'] == ['russian', 'tolstoy'], anna_rec['tags']
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
        offset = self.base_url + '?all_fields=1&tags=russian&limit=1'
        res = self.app.get(offset, status=200)
        res_dict = simplejson.loads(res.body)
        assert res_dict['count'] == 2, res_dict
        assert len(res_dict['results']) == 1, res_dict
        assert res_dict['results'][0]['name'] == 'annakarenina', res_dict['results'][0]['name']

    def test_11_pagination_offset_limit(self):
        offset = self.base_url + '?all_fields=1&tags=russian&offset=1&limit=1'
        res = self.app.get(offset, status=200)
        res_dict = simplejson.loads(res.body)
        assert res_dict['count'] == 2, res_dict
        assert len(res_dict['results']) == 1, res_dict
        assert res_dict['results'][0]['name'] == 'warandpeace', res_dict['results'][0]['name']

