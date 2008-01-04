import ckan.authz

class TestBlacklister:

    def test_1(self):
        blacklister = ckan.authz.Blacklister()
        bad_username = '83.222.23.234'
        good_username = '124.168.141.31'
        good_username2 = 'testadmin'
        assert blacklister.is_blacklisted(bad_username)
        assert not blacklister.is_blacklisted(good_username)
        assert not blacklister.is_blacklisted(good_username2)


class TestAuthorizer:

    controller = ckan.authz.Authorizer()

    def test_admins_ok(self):
        action = ckan.authz.actions['revision-purge']
        username = 'testadmin'
        assert self.controller.is_authorized(username=username, action=action)
        assert not self.controller.is_authorized(username='blah', action=action)

    def test_blacklist_edit(self):
        action = ckan.authz.actions['package-update']
        username = 'testadmin'
        bad_username = '83.222.23.234'
        assert self.controller.is_authorized(username=username, action=action)
        assert not self.controller.is_authorized(username=bad_username, action=action)



