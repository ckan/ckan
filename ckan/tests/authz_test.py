import ckan.authz

class TestAuthorizer:

    controller = ckan.authz.Authorizer()

    def test_1(self):
        action = ckan.authz.actions['revision-purge']
        username = 'testadmin'
        assert self.controller.is_authorized(username=username, action=action)
        assert not self.controller.is_authorized(username='blah', action=action)
