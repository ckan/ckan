import ckan.model as model
from ckan.tests import url_for, CreateTestData, WsgiAppCase

class TestAdminController(WsgiAppCase):
    @classmethod
    def setup_class(cls):
        # setup test data including testsysadmin user
        CreateTestData.create()

    @classmethod
    def teardown_class(self):
        model.repo.rebuild_db()

    #test that only sysadmins can access the /ckan-admin page
    def test_index(self):
        url = url_for('ckanadmin', action='index')
        # redirect as not authorized
        response = self.app.get(url, status=[302])
        # random username
        response = self.app.get(url, status=[401],
                extra_environ={'REMOTE_USER': 'my-random-user-name'})
        # now test real access
        username = u'testsysadmin'.encode('utf8')
        response = self.app.get(url,
                extra_environ={'REMOTE_USER': username})
        assert 'Administration' in response, response

##   This is no longer used
class _TestAdminAuthzController(WsgiAppCase):
    @classmethod
    def setup_class(cls):
        # setup test data including testsysadmin user
        CreateTestData.create()
        model.Session.commit()

    @classmethod
    def teardown_class(self):
        model.repo.rebuild_db()

    def test_role_table(self):

        #logged in as testsysadmin for all actions
        as_testsysadmin = {'REMOTE_USER': 'testsysadmin'}

        def get_system_user_roles():
            sys_query=model.Session.query(model.SystemRole)
            return sorted([(x.user.name,x.role) for x in sys_query.all() if x.user])

        def get_response():
            response = self.app.get(
                    url_for('ckanadmin', action='authz'),
                    extra_environ=as_testsysadmin)
            assert 'Administration - Authorization' in response, response
            return response

        def get_user_form():
           response = get_response()
           return response.forms['theform']


        def check_and_set_checkbox(theform, user, role, should_be, set_to):
           user_role_string = '%s$%s' % (user, role)
           checkboxes = [x for x in theform.fields[user_role_string] \
                                           if x.__class__.__name__ == 'Checkbox']

           assert(len(checkboxes)==1), \
                "there should only be one checkbox for %s/%s" % (user, role)
           checkbox = checkboxes[0]

           #checkbox should be unticked
           assert checkbox.checked==should_be, \
                         "%s/%s checkbox in unexpected state" % (user, role)

           #tick or untick the box and submit the form
           checkbox.checked=set_to
           return theform

        def submit(form):
          return form.submit('save', extra_environ=as_testsysadmin)

        def authz_submit(form):
          return form.submit('authz_save', extra_environ=as_testsysadmin)

        # get and store the starting state of the system roles
        original_user_roles = get_system_user_roles()

        # before we start changing things, check that the roles on the system are as expected
        assert original_user_roles == \
            [(u'logged_in', u'editor'), (u'testsysadmin', u'admin'),  (u'visitor', u'reader')] , \
            "original user roles not as expected " + str(original_user_roles)


        # visitor is not an admin. check that his admin box is unticked, tick it, and submit
        submit(check_and_set_checkbox(get_user_form(), u'visitor', u'admin', False, True))

        # try again, this time we expect the box to be ticked already
        submit(check_and_set_checkbox(get_user_form(), u'visitor', u'admin', True, True))

        # put it back how it was
        submit(check_and_set_checkbox(get_user_form(), u'visitor', u'admin', True, False))

        # should be back to our starting state
        assert original_user_roles == get_system_user_roles()


        # change lots of things
        form = get_user_form()
        check_and_set_checkbox(form, u'visitor', u'editor', False, True)
        check_and_set_checkbox(form, u'visitor', u'reader', True,  False)
        check_and_set_checkbox(form, u'logged_in', u'editor', True, False)
        check_and_set_checkbox(form, u'logged_in', u'reader', False, True)
        submit(form)

        roles=get_system_user_roles()
        # and assert that they've actually changed
        assert (u'visitor', u'editor') in roles and \
               (u'logged_in', u'editor') not in roles and \
               (u'logged_in', u'reader') in roles and \
               (u'visitor', u'reader')  not in roles, \
               "visitor and logged_in roles seem not to have reversed"


        def get_roles_by_name(user=None, group=None):
            if user:
                return [y for (x,y) in get_system_user_roles() if x==user]
            else:
                assert False, 'miscalled'


        # now we test the box for giving roles to an arbitrary user

        # check that tester doesn't have a system role
        assert len(get_roles_by_name(user=u'tester'))==0, \
              "tester should not have roles"

        # get the put tester in the username box
        form = get_response().forms['addform']
        form.fields['new_user_name'][0].value='tester'
        # get the admin checkbox
        checkbox = [x for x in form.fields['admin'] \
                      if x.__class__.__name__ == 'Checkbox'][0]
        # check it's currently unticked
        assert checkbox.checked == False
        # tick it and submit
        checkbox.checked=True
        response = form.submit('add', extra_environ=as_testsysadmin)
        assert "User Added" in response, "don't see flash message"

        assert get_roles_by_name(user=u'tester') == ['admin'], \
            "tester should be an admin now"



class TestAdminTrashController(WsgiAppCase):
    def setup(cls):
        CreateTestData.create()

    def teardown(self):
        model.repo.rebuild_db()

    def test_purge_revision(self):
        as_testsysadmin = {'REMOTE_USER': 'testsysadmin'}

        # Put a revision in deleted state
        rev = model.repo.youngest_revision()
        revid = rev.id
        rev.state = model.State.DELETED
        model.Session.commit()

        # check it shows up on trash page and
        url = url_for('ckanadmin', action='trash')
        response = self.app.get(url, extra_environ=as_testsysadmin)
        assert revid in response, response

        # check it can be successfully purged
        form = response.forms['form-purge-revisions']
        res = form.submit('purge-revisions', status=[302], extra_environ=as_testsysadmin)
        res = res.follow(extra_environ=as_testsysadmin)
        assert not revid in res, res
        rev = model.Session.query(model.Revision).filter_by(id=revid).first()
        assert rev is None, rev

    def test_purge_package(self):
        as_testsysadmin = {'REMOTE_USER': 'testsysadmin'}

        # Put packages in deleted state
        rev = model.repo.new_revision()
        pkg = model.Package.by_name(u'warandpeace')
        pkg.state = model.State.DELETED
        model.repo.commit_and_remove()

        # Check shows up on trash page
        url = url_for('ckanadmin', action='trash')
        response = self.app.get(url, extra_environ=as_testsysadmin)
        assert 'dataset/warandpeace' in response, response

        # Check we get correct error message on attempted purge
        form = response.forms['form-purge-packages']
        response = form.submit('purge-packages', status=[302],
                extra_environ=as_testsysadmin)
        response = response.follow(extra_environ=as_testsysadmin)
        assert 'Cannot purge package' in response, response
        assert 'dataset/warandpeace' in response

        # now check we really can purge when things are ok
        model.repo.new_revision()
        pkg = model.Package.by_name(u'annakarenina')
        pkg.state = model.State.DELETED
        model.repo.commit_and_remove()

        response = self.app.get(url, extra_environ=as_testsysadmin)
        assert 'dataset/warandpeace' in response, response
        assert 'dataset/annakarenina' in response, response

        form = response.forms['form-purge-packages']
        res = form.submit('purge-packages', status=[302], extra_environ=as_testsysadmin)
        res = res.follow(extra_environ=as_testsysadmin)

        pkgs = model.Session.query(model.Package).all()
        assert len(pkgs) == 0

    def test_purge_youngest_revision(self):
        as_testsysadmin = {'REMOTE_USER': 'testsysadmin'}

        id = u'warandpeace'
        log_message = 'test_1234'
        edit_url = url_for(controller='package', action='edit', id=id)

        # Manually create a revision
        res = self.app.get(edit_url, extra_environ=as_testsysadmin)
        fv = res.forms['dataset-edit']
        fv['title'] = 'RevisedTitle'
        fv['log_message'] = log_message
        res = fv.submit('save', extra_environ=as_testsysadmin)

        # Delete that revision
        rev = model.repo.youngest_revision()
        assert rev.message == log_message
        rev.state = model.State.DELETED
        model.Session.commit()

        # Run a purge
        url = url_for('ckanadmin', action='trash')
        res = self.app.get(url, extra_environ=as_testsysadmin)
        form = res.forms['form-purge-revisions']
        res = form.submit('purge-revisions', status=[302], extra_environ=as_testsysadmin)
        res = res.follow(extra_environ=as_testsysadmin)

        # Verify the edit page can be loaded (ie. does not 404)
        res = self.app.get(edit_url, extra_environ=as_testsysadmin)

    def test_undelete(self):
        as_testsysadmin = {'REMOTE_USER': 'testsysadmin'}

        rev = model.repo.youngest_revision()
        rev_id = rev.id
        rev.state = model.State.DELETED
        model.Session.commit()

        # Click undelete
        url = url_for('ckanadmin', action='trash')
        res = self.app.get(url, extra_environ=as_testsysadmin)
        form = res.forms['undelete-'+rev.id]
        res = form.submit('action', status=[302], extra_environ=as_testsysadmin)
        res = res.follow(extra_environ=as_testsysadmin)

        assert 'Revision updated' in res
        assert not 'DELETED' in res

        rev = model.repo.youngest_revision()
        assert rev.id == rev_id
        assert rev.state == model.State.ACTIVE
