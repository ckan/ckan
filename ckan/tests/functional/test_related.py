import json

from nose.tools import assert_equal, assert_raises

import ckan.tests as tests
import ckan.model as model
import ckan.logic as logic
import ckan.lib.helpers as h
import ckan.tests.functional.base as base
import ckan.tests.functional.api.base as apibase


class TestRelatedUI(base.FunctionalTestCase):
    @classmethod
    def setup_class(self):
        model.Session.remove()
        tests.CreateTestData.create()

    @classmethod
    def teardown_class(self):
        model.repo.rebuild_db()

    def test_related_new(self):
        offset = h.url_for(controller='related',
                           action='new', id='warandpeace')
        res = self.app.get(offset, status=200,
                           extra_environ={"REMOTE_USER": "testsysadmin"})
        assert 'URL' in res, "URL missing in response text"
        assert 'Title' in res, "Title missing in response text"

        data = {
            "title": "testing_create",
            "url": u"http://ckan.org/feed/",
        }
        res = self.app.post(offset, params=data,
                            status=[200,302],
                            extra_environ={"REMOTE_USER": "testsysadmin"})

    def test_related_new_missing(self):
        offset = h.url_for(controller='related',
                           action='new', id='non-existent dataset')
        res = self.app.get(offset, status=404,
                           extra_environ={"REMOTE_USER": "testsysadmin"})

    def test_related_new_fail(self):
        offset = h.url_for(controller='related',
                           action='new', id='warandpeace')
        print '@@@@', offset
        res = self.app.get(offset, status=200,
                           extra_environ={"REMOTE_USER": "testsysadmin"})
        assert 'URL' in res, "URL missing in response text"
        assert 'Title' in res, "Title missing in response text"

        data = {
            "title": "testing_create",
        }
        res = self.app.post(offset, params=data,
                            status=[200,302],
                            extra_environ={"REMOTE_USER": "testsysadmin"})
        assert 'error' in res, res



class TestRelated:

    @classmethod
    def setup_class(self):
        model.Session.remove()
        tests.CreateTestData.create()

    @classmethod
    def teardown_class(self):
        model.repo.rebuild_db()

    def test_create(self):
        p = model.Package.get('warandpeace')
        r = model.Related()
        p.related.append(r)

        assert len(p.related) == 1, p.related
        assert len(r.datasets) == 1, r.datasets

        model.Session.add(p)
        model.Session.add(r)
        model.Session.commit()

        # To get the RelatedDataset objects (for state change)
        assert p.related_count == 1, p.related_count
        assert len(model.Related.get_for_dataset(p)) == 1
        assert len(model.Related.get_for_dataset(p,status='inactive')) == 0
        p.related.remove(r)
        model.Session.delete(r)
        model.Session.commit()

        assert len(p.related) == 0
        assert p.related_count == 0, p.related_count


    def test_inactive_related(self):
        p = model.Package.get('warandpeace')
        r = model.Related()
        p.related.append(r)
        assert len(p.related) == 1, p.related
        model.Session.add(r)
        model.Session.commit()

        # To get the RelatedDataset objects (for state change)
        assert p.related_count == 1, p.related_count
        assert len(model.Related.get_for_dataset(p,status='active')) == 1
        assert len(model.Related.get_for_dataset(p,status='inactive')) == 0
        r.deactivate( p )
        r.deactivate( p ) # Does nothing.
        model.Session.refresh(p)
        assert p.related_count == 0, p.related_count
        assert len(model.Related.get_for_dataset(p,status='active')) == 0
        assert len(model.Related.get_for_dataset(p,status='inactive')) == 1

        model.Session.refresh(p) # Would like to get rid of the need for this
        assert len(p.related) == 0, p.related # not sure inactive item ...
        model.Session.delete(r)


    def _related_create(self, title, description, type, url, image_url):
        usr = logic.get_action('get_site_user')({'model':model,'ignore_auth': True},{})

        context = dict(model=model, user=usr['name'], session=model.Session)
        data_dict = dict(title=title,description=description,
                         url=url,image_url=image_url,type=type)
        return logic.get_action("related_create")( context, data_dict )

    def test_related_create(self):
        rel = self._related_create("Title", "Description",
                        "visualization",
                        "http://ckan.org",
                        "http://ckan.org/files/2012/03/ckanlogored.png")
        assert rel['title'] == "Title", rel
        assert rel['description'] == "Description", rel
        assert rel['type'] == "visualization", rel
        assert rel['url'] == "http://ckan.org", rel
        assert rel['image_url'] == "http://ckan.org/files/2012/03/ckanlogored.png", rel

    def test_related_create_fail(self):
        try:
            rel = self._related_create("Title", "Description",
                        None,
                        "http://ckan.org",
                        "http://ckan.org/files/2012/03/ckanlogored.png")
            assert False, "Create succeeded with missing field"
        except logic.ValidationError, e:
            assert 'type' in e.error_dict and e.error_dict['type'] == [u'Missing value']

    def test_related_create_featured_as_sysadmin(self):
        '''Sysadmin can create featured related items'''
        usr = logic.get_action('get_site_user')({'model':model,'ignore_auth': True},{})

        context = {
            'model': model,
            'user': usr['name'],
            'session': model.Session
        }

        data_dict = {
            'title': 'Title',
            'description': 'Description',
            'type': 'visualization',
            'url': 'http://ckan.org',
            'image_url': 'http://ckan.org/files/2012/03/ckanlogored.png',
            'featured': 1,
        }

        result = logic.get_action("related_create")(context, data_dict)

        assert_equal(result['featured'], 1)

    def test_related_create_featured_as_non_sysadmin_fails(self):
        '''Non-sysadmin users should not be able to create featured relateds'''

        context = {
            'model': model,
            'user': 'annafan',
            'session': model.Session
        }

        data_dict = {
            'title': 'Title',
            'description': 'Description',
            'type': 'visualization',
            'url': 'http://ckan.org',
            'image_url': 'http://ckan.org/files/2012/03/ckanlogored.png',
            'featured': 1,
        }

        assert_raises(
            logic.NotAuthorized,
            logic.get_action('related_create'),
            context,
            data_dict)

    def test_related_create_not_featured_as_non_sysadmin_succeeds(self):
        '''Non-sysadmins can set featured to false'''

        context = {
            'model': model,
            'user': 'annafan',
            'session': model.Session
        }

        data_dict = {
            'title': 'Title',
            'description': 'Description',
            'type': 'visualization',
            'url': 'http://ckan.org',
            'image_url': 'http://ckan.org/files/2012/03/ckanlogored.png',
            'featured': 0,
        }

        result = logic.get_action("related_create")(context, data_dict)

        assert_equal(result['featured'], 0)

    def test_related_create_featured_empty_as_non_sysadmin_succeeds(self):
        '''Non-sysadmins can leave featured empty.'''

        context = {
            'model': model,
            'user': 'annafan',
            'session': model.Session
        }

        data_dict = {
            'title': 'Title',
            'description': 'Description',
            'type': 'visualization',
            'url': 'http://ckan.org',
            'image_url': 'http://ckan.org/files/2012/03/ckanlogored.png',
        }

        result = logic.get_action("related_create")(context, data_dict)

        assert_equal(result['featured'], 0)

    def test_related_delete(self):
        rel = self._related_create("Title", "Description",
                        "visualization",
                        "http://ckan.org",
                        "http://ckan.org/files/2012/03/ckanlogored.png")
        usr = logic.get_action('get_site_user')({'model':model,'ignore_auth': True},{})
        context = dict(model=model, user=usr['name'], session=model.Session)
        data_dict = dict(id=rel['id'])
        logic.get_action('related_delete')(context, data_dict)

        r = model.Related.get(rel['id'])
        assert r is None, r # Ensure it doesn't exist

    def test_related_update(self):
        rel = self._related_create("Title", "Description",
                        "visualization",
                        "http://ckan.org",
                        "http://ckan.org/files/2012/03/ckanlogored.png")

        usr = logic.get_action('get_site_user')({'model':model,'ignore_auth': True},{})
        context = dict(model=model, user=usr['name'], session=model.Session)
        data_dict = rel
        data_dict['title'] = "New Title"
        result = logic.get_action('related_update')(context,data_dict)
        assert result['title'] == 'New Title'

    def test_sysadmin_changes_related_items_featured_field(self):
        '''Sysadmins can change featured field'''
        rel = self._related_create(
            "Title",
            "Description",
            "visualization",
            "http://ckan.org",
            "http://ckan.org/files/2012/03/ckanlogored.png")

        usr = logic.get_action('get_site_user')({'model':model,'ignore_auth': True},{})
        context = {
            'model': model,
            'user': usr['name'],
            'session': model.Session
        }

        data_dict = rel
        data_dict['title'] = "New Title"
        data_dict['featured'] = 1
        result = logic.get_action('related_update')(context,data_dict)
        assert_equal(result['title'], 'New Title')
        assert_equal(result['featured'], 1)

    def test_non_sysadmin_changes_related_items_featured_field_fails(self):
        '''Non-sysadmins cannot change featured field'''

        context = {
            'model': model,
            'user': 'annafan',
            'session': model.Session
        }

        data_dict = {
            'title': 'Title',
            'description': 'Description',
            'type': 'visualization',
            'url': 'http://ckan.org',
            'image_url': 'http://ckan.org/files/2012/03/ckanlogored.png',
        }

        # Create the related item as annafan
        result = logic.get_action('related_create')(context, data_dict)

        # Try to change it to a featured item
        result['featured'] = 1

        try:
            logic.get_action('related_update')(context, result)
        except logic.NotAuthorized, e:
            # Check it's the correct authorization error
            assert 'featured' in str(e)

    def test_non_sysadmin_can_update_related_item(self):
        '''Non-sysadmins can change related item.

        If they don't change the featured field.
        '''

        context = {
            'model': model,
            'user': 'annafan',
            'session': model.Session
        }

        data_dict = {
            'title': 'Title',
            'description': 'Description',
            'type': 'visualization',
            'url': 'http://ckan.org',
            'image_url': 'http://ckan.org/files/2012/03/ckanlogored.png',
        }

        # Create the related item as annafan
        result = logic.get_action('related_create')(context, data_dict)

        # Try to change it to a featured item
        result['title'] = 'New Title'

        result = logic.get_action('related_update')(context, result)
        assert_equal(result['title'], 'New Title')

    def test_related_show(self):
        rel = self._related_create("Title", "Description",
                        "visualization",
                        "http://ckan.org",
                        "http://ckan.org/files/2012/03/ckanlogored.png")

        usr = logic.get_action('get_site_user')({'model':model,'ignore_auth': True},{})
        context = dict(model=model, user=usr['name'], session=model.Session)
        data_dict = {'id': rel['id']}

        result = logic.get_action('related_show')(context,data_dict)
        assert rel['id'] == result['id'], result
        assert rel['title'] == result['title'], result
        assert rel['description'] == result['description'], result
        assert rel['description'] == result['description'], result

    def test_related_list_missing_id_and_name(self):
        p = model.Package.get('warandpeace')
        usr = logic.get_action('get_site_user')({'model':model,'ignore_auth': True},{})
        context = dict(model=model, user=usr['name'], session=model.Session)
        data_dict = {}
        related_list = logic.get_action('related_list')(context, data_dict)
        assert len(related_list) == 8
        related_keys = set(['view_count', 'description', 'title', 'url',
            'created', 'featured', 'image_url', 'type', 'id', 'owner_id'])
        for related in related_list:
            assert set(related.keys()) == related_keys


    def test_related_list(self):
        p = model.Package.get('warandpeace')
        r = model.Related(title="Title", type="idea")
        p.related.append(r)
        r = model.Related(title="Title 2", type="idea")
        p.related.append(r)
        model.Session.add(r)
        model.Session.commit()

        assert len(p.related) == 2
        assert p.related_count == 2, p.related_count

        usr = logic.get_action('get_site_user')({'model':model,'ignore_auth': True},{})
        context = dict(model=model, user=usr['name'], session=model.Session)
        data_dict = {'id': p.id}

        result = logic.get_action('related_list')(context,data_dict)
        assert len(result) == len(p.related)

class TestRelatedActionAPI(apibase.BaseModelApiTestCase):

    @classmethod
    def setup_class(cls):
        model.Session.remove()
        tests.CreateTestData.create()
        cls.user_name = u'russianfan' # created in CreateTestData
        cls.init_extra_environ(cls.user_name)

    @classmethod
    def teardown_class(self):
        model.repo.rebuild_db()

    def test_api_create_invalid(self):
        res = self.app.post("/api/3/action/related_create", params="{}=1",
                            status=self.STATUS_409_CONFLICT,
                            extra_environ=self.extra_environ)
        r = json.loads(res.body)
        assert r['success'] == False, r


    def _create(self, rtype="visualization", title="Test related item"):
        r = {
            "type": rtype,
            "title": title
        }
        postparams = '%s=1' % json.dumps(r)
        res = self.app.post("/api/3/action/related_create", params=postparams,
                            status=self.STATUS_200_OK,
                            extra_environ=self.extra_environ)
        r = json.loads(res.body)
        return r

    def test_api_create_valid(self):
        r = self._create()
        assert r['success'] == True, r
        assert r['result']['type'] == "visualization"
        assert r['result']['title'] == "Test related item"

    def test_api_show(self):
        existing = self._create()

        r = {
            "id": existing["result"]["id"]
        }
        postparams = '%s=1' % json.dumps(r)
        res = self.app.post("/api/3/action/related_show", params=postparams,
                            status=self.STATUS_200_OK,
                            extra_environ=self.extra_environ)
        r = json.loads(res.body)
        assert r['success'] == True, r
        assert r['result']['type'] == "visualization"
        assert r['result']['title'] == "Test related item"


    def test_api_list(self):
        p = model.Package.get('warandpeace')
        one = model.Related(type="idea", title="one")
        two = model.Related(type="idea", title="two")
        p.related.append(one)
        p.related.append(two)
        model.Session.commit()

        r = {
            "id": p.id
        }
        postparams = '%s=1' % json.dumps(r)
        res = self.app.post("/api/3/action/related_list", params=postparams,
                            status=self.STATUS_200_OK,
                            extra_environ=self.extra_environ)
        r = json.loads(res.body)
        assert r['success'] == True, r
        assert r['result'][0]['type'] == "idea"
        assert r['result'][0]['title'] == "two", r

        p.related.remove(one)
        p.related.remove(two)
        model.Session.delete(one)
        model.Session.delete(two)

    def test_api_delete(self):
        existing = self._create()

        r = {
            "id": existing["result"]["id"]
        }
        postparams = '%s=1' % json.dumps(r)
        res = self.app.post("/api/3/action/related_delete", params=postparams,
                            status=self.STATUS_200_OK,
                            extra_environ=self.extra_environ)
        r = json.loads(res.body)
        assert r['success'] == True, r
        assert r['result'] is None, r

    def test_api_delete_fail(self):
        existing = self._create()
        r = {
            "id": existing["result"]["id"]
        }

        usr = model.User.by_name("annafan")
        extra={'Authorization' : str(usr.apikey)}

        postparams = '%s=1' % json.dumps(r)
        res = self.app.post("/api/3/action/related_delete", params=postparams,
                            status=self.STATUS_403_ACCESS_DENIED,
                            extra_environ=extra)
        r = json.loads(res.body)
        assert r['success'] == False, r
        assert r[u'error'][u'__type'] == "Authorization Error", r
