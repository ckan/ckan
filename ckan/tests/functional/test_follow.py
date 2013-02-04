from pylons.test import pylonsapp
import paste.fixture
import ckan
from routes import url_for
from ckan.tests.html_check import HtmlCheckMethods
import json

class TestFollow(HtmlCheckMethods):

    @classmethod
    def setupClass(cls):
        ckan.tests.CreateTestData.create()
        cls.testsysadmin = ckan.model.User.get('testsysadmin')
        cls.annafan = ckan.model.User.get('annafan')
        cls.russianfan = ckan.model.User.get('russianfan')
        cls.tester = ckan.model.User.get('tester')
        cls.joeadmin = ckan.model.User.get('joeadmin')
        cls.warandpeace = ckan.model.Package.get('warandpeace')
        cls.annakarenina = ckan.model.Package.get('annakarenina')
        cls.app = paste.fixture.TestApp(pylonsapp)

        # Make three users follow annakarenina.
        params = {'id': 'annakarenina'}
        extra_environ = {'Authorization': str(cls.joeadmin.apikey)}
        response = cls.app.post('/api/action/follow_dataset',
            params=json.dumps(params), extra_environ=extra_environ).json
        assert response['success'] is True
        params = {'id': 'annakarenina'}
        extra_environ = {'Authorization': str(cls.annafan.apikey)}
        response = cls.app.post('/api/action/follow_dataset',
            params=json.dumps(params), extra_environ=extra_environ).json
        assert response['success'] is True
        params = {'id': 'annakarenina'}
        extra_environ = {'Authorization': str(cls.russianfan.apikey)}
        response = cls.app.post('/api/action/follow_dataset',
            params=json.dumps(params), extra_environ=extra_environ).json
        assert response['success'] is True

        # Make two users follow annafan.
        params = {'id': 'annafan'}
        extra_environ = {'Authorization': str(cls.russianfan.apikey)}
        response = cls.app.post('/api/action/follow_user',
            params=json.dumps(params), extra_environ=extra_environ).json
        assert response['success'] is True
        params = {'id': 'annafan'}
        extra_environ = {'Authorization': str(cls.tester.apikey)}
        response = cls.app.post('/api/action/follow_user',
            params=json.dumps(params), extra_environ=extra_environ).json
        assert response['success'] is True

    @classmethod
    def teardownClass(cls):
        ckan.model.repo.rebuild_db()

    def test_dataset_read_not_logged_in(self):
        offset = url_for(controller='package', action='read',
                id='warandpeace')
        result = self.app.get(offset)
        assert 'href="/dataset/followers/warandpeace"' in result
        assert 'Followers (0)' in result
        assert 'id="dataset_follow_button"' not in result

        offset = url_for(controller='package', action='read',
                id='annakarenina')
        result = self.app.get(offset)
        assert 'href="/dataset/followers/annakarenina"' in result
        assert 'Followers (3)' in result
        assert 'id="dataset_follow_button"' not in result
    
    def test_dataset_followers_not_logged_in(self): 
        '''Not-logged-in users cannot see /dataset/followers/ pages.'''
        offset = url_for(controller='package', action='followers',
                id='warandpeace')
        result = self.app.get(offset)
        assert result.status == 302
        assert '/user/login' in result.header_dict['location']

    def test_user_read_not_logged_in(self):
        offset = url_for(controller='user', action='read',
                id='joeadmin')
        result = self.app.get(offset)
        assert 'href="/user/followers/joeadmin"' in result
        assert 'Followers (0)' in result
        assert 'id="user_follow_button"' not in result

        offset = url_for(controller='user', action='read',
                id='annafan')
        result = self.app.get(offset)
        assert 'href="/user/followers/annafan"' in result
        assert 'Followers (2)' in result
        assert 'id="user_follow_button"' not in result
    
    def test_user_followers_not_logged_in(self):
        offset = url_for(controller='user', action='followers',
                id='joeadmin')
        result = self.app.get(offset)
        assert result.status == 302
        assert '/user/login' in result.header_dict['location']

    def test_own_user_read_logged_in(self):
        offset = url_for(controller='user', action='read',
                id='joeadmin')
        extra_environ = {'Authorization': str(self.joeadmin.apikey)}
        result = self.app.get(offset, extra_environ=extra_environ)
        assert 'href="/user/followers/joeadmin"' in result
        assert 'My Followers (0)' in result
        assert 'id="user_follow_button"' not in result

        offset = url_for(controller='user', action='read',
                id='annafan')
        extra_environ = {'Authorization': str(self.annafan.apikey)}
        result = self.app.get(offset, extra_environ=extra_environ)
        assert 'href="/user/followers/annafan"' in result
        assert 'My Followers (2)' in result
        assert 'id="user_follow_button"' not in result
    
    def test_own_user_followers_logged_in(self):
        offset = url_for(controller='user', action='followers',
                id='joeadmin')
        extra_environ = {'Authorization': str(self.testsysadmin.apikey)}
        result = self.app.get(offset, extra_environ=extra_environ)
        assert 'href="/user/followers/joeadmin"' in result
        assert 'Followers (0)' in result
        assert 'id="user_follow_button"' in result
        assert '<li class="user">' not in result

    def test_dataset_read_logged_in(self):
        offset = url_for(controller='package', action='read',
                id='warandpeace')
        extra_environ = {'Authorization': str(self.testsysadmin.apikey)}
        result = self.app.get(offset, extra_environ=extra_environ)
        assert 'href="/dataset/followers/warandpeace"' in result
        assert 'Followers (0)' in result
        assert 'id="dataset_follow_button"' in result

        offset = url_for(controller='package', action='read',
                id='annakarenina')
        extra_environ = {'Authorization': str(self.tester.apikey)}
        result = self.app.get(offset, extra_environ=extra_environ)
        assert 'href="/dataset/followers/annakarenina"' in result
        assert 'Followers (3)' in result
        assert 'id="dataset_follow_button"' in result

    def test_dataset_follow_logged_in(self):
        offset = url_for(controller='package', action='followers',
                id='warandpeace')
        extra_environ = {'Authorization': str(self.testsysadmin.apikey)}
        result = self.app.get(offset, extra_environ=extra_environ)
        assert 'id="dataset_follow_button"' in result
        assert 'Followers (0)' in result
        assert 'id="dataset_follow_button"' in result
        assert '<li class="user">' not in result

        offset = url_for(controller='package', action='followers',
                id='annakarenina')
        extra_environ = {'Authorization': str(self.testsysadmin.apikey)}
        result = self.app.get(offset, extra_environ=extra_environ)
        assert 'href="/dataset/followers/annakarenina"' in result
        assert 'Followers (3)' in result
        assert 'id="dataset_follow_button"' in result
        assert str(result).count('<li class="user">') == 3
        assert self.joeadmin.display_name in result
        assert self.annafan.display_name in result
        assert self.russianfan.display_name in result

        # joeadmin is following annakarenina so he should see an Unfollow
        # button.
        offset = url_for(controller='package', action='followers',
                id='annakarenina')
        extra_environ = {'Authorization': str(self.testsysadmin.apikey)}
        result = self.app.get(offset, extra_environ=extra_environ)
        assert 'Unfollow' in result
        
    def test_user_read_logged_in(self):
        offset = url_for(controller='user', action='read',
                id='joeadmin')
        extra_environ = {'Authorization': str(self.tester.apikey)}
        result = self.app.get(offset, extra_environ=extra_environ)
        assert 'href="/user/followers/joeadmin"' in result
        assert 'Followers (0)' in result
        assert 'id="user_follow_button"' in result

        offset = url_for(controller='user', action='read',
                id='annafan')
        extra_environ = {'Authorization': str(self.tester.apikey)}
        result = self.app.get(offset, extra_environ=extra_environ)
        assert 'href="/user/followers/annafan"' in result
        assert 'Followers (2)' in result
        assert 'id="user_follow_button"' in result

    def test_user_follow_logged_in(self):
        offset = url_for(controller='user', action='followers',
                id='joeadmin')
        extra_environ = {'Authorization': str(self.testsysadmin.apikey)}
        result = self.app.get(offset, extra_environ=extra_environ)
        assert 'href="/user/followers/joeadmin"' in result
        assert 'Followers (0)' in result
        assert '<li class="user">' not in result
        assert 'id="user_follow_button"' in result
