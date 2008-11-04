import inspect
from ckan.modes import PresentationRequest
from ckan.modes import RegisterPost
import ckan.model
import ckan.model as model

class TestPresentationRequest(object):

    path = '/myregister'
    body = None
    user = 'unittester'

    def test(self):
        request = PresentationRequest(
            path=self.path,
            body=self.body,
            user=self.user
        )
        assert request.path == self.path
        assert request.body == self.body
        assert request.user == self.user


class BaseTestPresentationMode(object):

    mode_class = None
    request_path = None
    request_body = None
    request_user = 'unittester'

    def test_execute(self):
        self.create_mode()
        self.execute_mode()
        self.check_mode()
        self.check_model()

    def create_mode(self):
        request = self.create_request()
        self.mode = self.mode_class(request=request)

    def create_request(self):
        return PresentationRequest(
            path=self.request_path,
            body=self.request_body,
            user=self.request_user,
        )

    def execute_mode(self):
        self.mode.execute()

    def check_mode(self):
        assert self.mode.response_code == self.response_code
 
    def check_model(self):
        pass 


class BaseTestPackagePresentation(BaseTestPresentationMode):
    
    @classmethod
    def setup_class(self):
        try:
            self.purge_package()
        except:
            model.Session.remove()

    @classmethod
    def teardown_class(self):
        try:
            self.purge_package()
        except:
            model.Session.remove()

    @classmethod
    def purge_package(self):
        name = self.request_body['name']
        pkg = model.Package.by_name(name)
        if pkg:
            pkg.purge()
            model.Session.commit()
        
    @classmethod
    def purge_tag(self):
        name = 'notatag'
        tag = model.Tag.by_name(name)
        if tag:
            tag.purge()
            model.Session.commit()
        
    @classmethod
    def create_package(self):
        ckan.model.repo.begin_transaction()
        try:
            p = model.Package(name=self.request_body['name'])
        except:
            raise
        else:
            ckan.model.repo.commit()

    @classmethod
    def get_package(self, pkg_name):
        return model.Package.by_name(pkg_name)

    @classmethod
    def get_tag(self, tag_name):
        return model.Tag.by_name(tag_name)


class TestPostPackage200(BaseTestPackagePresentation):

    mode_class = RegisterPost
    request_path = '/package'
    request_body = {'name': 'registerposttest'}
    response_code = 200


class TestPostPackageWithTags200(BaseTestPackagePresentation):

    mode_class = RegisterPost
    request_path = '/package'
    request_body = {
        'name': 'registerposttest',
        'url': 'http://registerposttest.non/',
        'download_url': 'http://registerposttest.non/',
        'notes': 'Item 1: Blah\nItem 2: Blah',
        'tags': ['a', 'b', 'c', 'notatag']
    }
    response_code = 200

    def check_model(self):
        p = self.get_package(self.request_body['name'])
        assert p.name == self.request_body['name']
        assert p.url == self.request_body['url'], p.url
        assert p.download_url == self.request_body['download_url']
        assert p.notes == self.request_body['notes']

        tag_names = [t.name for t in p.tags]
        assert 'a' in tag_names, tag_names
        assert 'b' in tag_names, tag_names
        assert 'c' in tag_names, tag_names
        assert 'notatag' in tag_names, tag_names

class TestPostPackage409(BaseTestPackagePresentation):

    mode_class = RegisterPost
    request_path = '/package'
    request_body = {'name': 'registerposttest'}
    response_code = 409

    @classmethod
    def setup_class(self):
        self.purge_package()
        self.create_package()

        


