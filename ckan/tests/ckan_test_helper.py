from webtest import TestApp
from pylons import config

import ckan.logic as logic
import ckan.model as model
import ckan.lib.helpers as h
import ckan.config.middleware as middleware


class CkanTestHelper(object):

    ''' This object is designed to aid writing ckan tests.

    The aim is to:

        * Make the tests easier to write.

        * Increase the separation of the tests from the ckan codebase.

        * Make the tests simpler and clearer to read.

        * Reduce the amount of test boiler plate.

    It is likely that some extra create functions will be needed, tags etc
    and some extra helper functions may also be required.
    '''

    ################################################################
    #                                                              #
    #                       Base functionality                     #
    #                                                              #
    ################################################################

    def config_update(self, data):
        ''' Update the app config and restart the app using that config.

        example::

            config_update({'ckan.legacy_templates': 'no'})
        '''
        self._config.update(data)
        # reset the app
        self._app = None

    def config_reset(self):
        ''' Reset the config to the original one supplied '''
        self._config = self._original_config.copy()
        # reset the app
        self._app = None

    def reset_db(self):
        ''' Clear the test data. '''
        model.repo.rebuild_db()
        self._reset_data()

    def api_action(self, action, data=None, user=None, status=None):
        ''' Call the action api and return the result dict if we have a http
        status of 200.  For any other statuses the full data is returned.

        example::

            ds = t.api_action('package_show',
                              {'id': 'my_dataset'},
                              user='test_user')
        '''
        if not data:
            data = {}
        url = '/api/action/%s' % action
        extra_environ = None
        if user:
            apikey = self._user_attr(user, 'apikey')
            extra_environ = {'Authorization': str(apikey)}

        resp = self._get_app().post_json(
            url, data, status=status, extra_environ=extra_environ)
        if resp.status_int == 200:
            return resp.json['result']
        return resp.json

    def logic_action(self, action, data=None, user=None, context=None):
        ''' Call the logic action function.

        example::

            ds = t.logic_action('package_show',
                                {'id': 'my_dataset'},
                                user='test_user')
        '''
        if not data:
            data = {}
        if not context:
            context = {}
        if user:
            user_name = self._user_attr(user, 'name')
            context['user'] = user_name
        return logic.get_action(action)(context, data)

    def list_dict_reduce(self, list_, field):
        ''' Take a list of dicts and return a list of values being the field
        for each dict.

        example::

            my_list = [{'id': 1, 'value': 'one'},
                       {'id': 2, 'value': 'two'},
                       {'id': 3, 'value': 'three'}]

            list_dict_reduce(my_list, 'id') => [1, 2, 3]
            list_dict_reduce(my_list, 'value') => ['one', 'two', 'three']
        '''
        output = []
        for row in list_:
            output.append(row.get(field))
        return output

    ################################################################
    #                                                              #
    #                  Front-end functionality                     #
    #                                                              #
    ################################################################

    def get_url(self, *args, **kw):
        ''' Request the page via a GET call
        a status can be supplied as a named parameter.

        examples::

            get_url('/some_url')
            get_url('named_route', status=200)
            get_url('named_route', param=something)
            get_url(controller='home', action='index')

        returns a webtest response.
        '''
        status = kw.pop('status', None)
        url = h.url_for(*args, **kw)
        extra_environ = {}
        return self._get_app().get(url,
                                   status=status,
                                   extra_environ=extra_environ)

    def assert_location(self, response, controller=None, action=None):
        ''' Asserts that the response is from the controller and or action

        example::
            r = get_url('/user/login')
            assert_location(r, action='login', controller='user')
        '''

        c = response.c
        if action:
            assert c.action == action, \
                'Expected action `%s` got `%s`' % (action, c.action)
        if controller:
            assert c.controller == controller, \
                'Expected controller `%s` got `%s`' \
                % (controller, c.controller)

    def auto_follow(self, response):
        ''' Follow any redirects. '''
        while response.status_int == 302:
            response = response.follow()
        return response

    def login(self, user):
        ''' Login to the front end as the provided user.

        user specifies the user and can be one of
        a) user model
        b) user dictionary
        c) name of a user that has been created via create_user()
        d) 'test_sysadmin' a sysadmin, created if needed

        NOTE: The user will remain logged in until they explicitly
        logout or the application is reset. '''
        r = self.get_url(controller='user', action='login')

        user_name = self._user_attr(user, 'name')
        f = r.forms[1]
        f['login'] = user_name
        f['password'] = self._user_attr(user, 'password')
        r = f.submit()

        r = self.auto_follow(r)
        self.assert_location(r, controller='user', action='dashboard')
        assert r.pyquery('span.username').text() == user_name

    def logout(self):
        ''' Log out of the front end. '''
        r = self.get_url(controller='user', action='logout')
        self.auto_follow(r)

    ################################################################
    #                                                              #
    #                  Test data creation functions                #
    #                                                              #
    #  create_xxx() functions are used to create test data.        #
    #  the created data is returned.                               #
    #  They can be called as follows                               #
    #                                                              #
    #  passing data as a dict                                      #
    #  create_xxx({'key1': value, 'key2': value})                  #
    #  create_xxx({'key1': value, 'key2': value}, user=user)       #
    #                                                              #
    #  passing data as keywords                                    #
    #  create_xxx(key1=value, key2=value)                          #
    #  create_xxx(key1=value, key2=value, user=user)               #
    #                                                              #
    #  You can only pass the data either as a dict or as keywords  #
    #                                                              #
    #  user specifies the user and can be one of                   #
    #  a) user model                                               #
    #  b) user dictionary                                          #
    #  c) name of a user that has been created via create_user()   #
    #  d) 'test_sysadmin' a sysadmin, created if needed            #
    #                                                              #
    #  When data is created via the create_xxx() methods the dict  #
    #  of the creation is stored and can be retrieved by the       #
    #  coresponding xxx(name) method. generally the name of the    #
    #  object is given but related uses the title.                 #
    #                                                              #
    #  organization/group membership                               #
    #                                                              #
    #  add_group_role() and add_org_role() are used to add users   #
    #  as members of a group or organization.                      #
    #                                                              #
    #  eg add_org_role(org, user, role)                            #
    #  org and user can be a model, dict or name of created data.  #
    #  role is the name of the role.                               #
    #  The role is added by test_sysadmin user.                    #
    #                                                              #
    ################################################################

    def create_user(self, *args, **kw):
        ''' Create user test data.  A quick way of setting up users for
        testing. '''
        user, data = self._create_params(args, kw)
        name = data['name']
        if 'password' not in data:
            data['password'] = '%s password' % name
        if 'email' not in data:
            data['email'] = '%s@example.com' % name
        result = self._action('user_create', data, user=user)
        # we store the password as it is helpful to have for logging in etc.
        result['password'] = data['password']
        self._users[name] = result
        return result

    def user(self, name):
        ''' Get the user dict of a user created via create_user(). '''
        # if test_sysadmin is requested check they have been created
        if name == 'test_sysadmin' and not self._sys_admin:
            self._get_sysadmin()
        return self._users[name]

    def create_org(self, *args, **kw):
        ''' Create organizations test data.  A quick way of setting up
        organizations for testing. '''
        user, data = self._create_params(args, kw)
        name = data['name']
        result = self._action('organization_create', data, user=user)
        self._orgs[name] = result
        return result

    def org(self, name):
        ''' Get the organization dict of an organization created via
        create_org(). '''
        return self._orgs[name]

    def create_group(self, *args, **kw):
        ''' Create groups test data.  A quick way of setting up groups for
        testing. '''
        user, data = self._create_params(args, kw)
        name = data['name']
        result = self._action('group_create', data, user=user)
        self._groups[name] = result
        return result

    def group(self, name):
        ''' Get the group dict of a group created via create_group(). '''
        return self._groups[name]

    def create_dataset(self, *args, **kw):
        ''' Create datasets test data.  A quick way of setting up datasets
        for testing. '''
        user, data = self._create_params(args, kw)
        name = data['name']
        result = self._action('package_create', data, user=user)
        self._datasets[name] = result
        return result

    def dataset(self, name):
        ''' Get the dataset dict of a dataset created via create_dataset(). '''
        return self._datasets[name]

    def create_related(self, *args, **kw):
        ''' Create related items test data.  A quick way of setting up
        related items for testing. '''
        user, data = self._create_params(args, kw)
        name = data['title']
        if 'type' not in data:
            data['type'] = 'Application'
        result = self._action('related_create', data, user=user)
        self._related_items[name] = result
        return result

    def related(self, name):
        ''' Get the related dict of a related item created via
        create_related(). '''
        return self._related_items[name]

    def add_org_role(self, org, user, role):
        ''' Add a user to a organization with a role. '''
        org_id = self._org_attr(org, 'id')
        return self._member_create('organization_member_create',
                                   org_id, user, role)

    def add_group_role(self, group, user, role):
        ''' Add a user to a group with a role. '''
        group_id = self._group_attr(group, 'id')
        return self._member_create('group_member_create',
                                   group_id, user, role)

    ################################################################
    #                                                              #
    #                        Internal Logic                        #
    #                                                              #
    ################################################################

    def __init__(self):
        self._app = None
        self._original_config = config.copy()
        self._config = config.copy()
        self._reset_data()

    # The function used to create test data
    # `logic_action` or `api_action`
    # This is mainly to check that these routes are identical.
    _action = logic_action

    def _create_params(self, args, kw):
        # process params for the data creation functions we return a user if
        # one is supplied and a data dict the data dict can be supplied as a
        # dict as the first param or as keywords.
        user = kw.pop('user', None)
        if args:
            assert len(args) == 1 and isinstance(args[0], dict), \
                'only one positional parameter allowed and it must be a dict'
            data = args[0]
            assert not kw, \
                'named parameters cannot be used if a data dict is supplied'
        else:
            data = kw
        return user, data

    def _reset_data(self):
        # We cache some data.  If the database is reset then we need to
        # clear these caches.
        self._sys_admin = None
        self._users = {}
        self._orgs = {}
        self._groups = {}
        self._datasets = {}
        self._related_items = {}

    def _user_attr(self, user, attr):
        ''' Return the attribute attr for the user.  The user can be a User
        model, a user dict or the name of a user created via create_user().
        '''
        return self._obj_attr(user, attr, self.user)

    def _group_attr(self, group, attr):
        ''' Return the attribute attr for the group.  The group can be a Group
        model, a group dict or the name of a group created via create_group().
        '''
        return self._obj_attr(group, attr, self.group)

    def _org_attr(self, org, attr):
        ''' Return the attribute attr for the org.  The org can be a Group
        model, a org dict or the name of a org created via create_group().
        '''
        return self._obj_attr(org, attr, self.org)

    def _obj_attr(self, obj, attr, store):
        ''' Get the attr of an obj. '''
        if isinstance(obj, basestring):
            return store(obj)[attr]
        elif isinstance(obj, dict):
            return obj[attr]
        elif isinstance(obj, model.DomainObject):
            return getattr(obj, attr)

    def _member_create(self, fn, id_, user, role):
        ''' Create a membership. '''
        username = self._user_attr(user, 'name')
        self._action(fn,
                     {'id': id_, 'username': username, 'role': role},
                     user='test_sysadmin')

    def _get_app(self):
        ''' Return the app creating it if it is not initialized already. '''
        if not self._app:
            wsgiapp = middleware.make_app(
                self._config['global_conf'], **self._config)
            self._app = TestApp(wsgiapp)
        return self._app

    def _get_sysadmin(self):
        ''' Find the sys admin and create if does not exist. '''
        if not self._sys_admin:
            sys_admin = model.User.get('test_sysadmin')
            if not sys_admin:
                sys_admin = model.User(name='test_sysadmin', sysadmin=True)
                model.Session.add(sys_admin)
                model.Session.commit()
                model.Session.remove()
            self._sys_admin = sys_admin
            self._users['test_sysadmin'] = self._action(
                'user_show', {'id': 'test_sysadmin'}, user=sys_admin)
        return self._sys_admin
