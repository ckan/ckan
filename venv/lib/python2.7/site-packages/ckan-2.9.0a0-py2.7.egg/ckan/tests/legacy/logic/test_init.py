# encoding: utf-8

import nose.tools as tools

import ckan.model as model
import ckan.logic as logic

import ckan.lib.create_test_data as create_test_data


class TestMemberLogic(object):
    def test_model_name_to_class(self):
        assert logic.model_name_to_class(model, 'package') == model.Package
        tools.assert_raises(logic.ValidationError,
                            logic.model_name_to_class,
                            model,
                            'inexistent_model_name')


class TestCheckAccess(object):

    @classmethod
    def setup_class(cls):
        model.Session.close_all()
        model.repo.delete_all()

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()

    def setup(self):
        model.repo.rebuild_db()

    def test_check_access_auth_user_obj_is_set(self):

        create_test_data.CreateTestData.create_test_user()

        user_name = 'tester'
        context = {'user': user_name}

        result = logic.check_access('package_create', context)

        assert result
        assert context['__auth_user_obj_checked']
        assert context['auth_user_obj'].name == user_name

    def test_check_access_auth_user_obj_is_not_set_when_ignoring_auth(self):

        create_test_data.CreateTestData.create_test_user()

        user_name = 'tester'
        context = {'user': user_name, 'ignore_auth': True}

        result = logic.check_access('package_create', context)

        assert result
        assert '__auth_user_obj_checked' not in context
        assert context['auth_user_obj'] is None

    def test_check_access_auth_user_obj_is_not_set(self):

        user_names = ('unknown_user', '', None,)
        for user_name in user_names:
            context = {'user': user_name}

            result = logic.check_access('package_search', context)

            assert result
            assert context['__auth_user_obj_checked']
            assert context['auth_user_obj'] is None
