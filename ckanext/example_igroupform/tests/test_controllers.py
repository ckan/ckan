# encoding: utf-8

import pytest
import six
from ckan.lib.helpers import url_for

import ckan.plugins as plugins
import ckan.tests.helpers as helpers
import ckan.model as model
from ckan.tests import factories

webtest_submit = helpers.webtest_submit
submit_and_follow = helpers.submit_and_follow

custom_group_type = u"grup"
group_type = u"group"


def _get_group_new_page(app, group_type):
    user = factories.User()
    env = {"REMOTE_USER": six.ensure_str(user["name"])}
    response = app.get(url_for("%s.new" % group_type), extra_environ=env,)
    return env, response


@pytest.mark.ckan_config("ckan.plugins", "example_igroupform")
@pytest.mark.usefixtures("clean_db", "with_plugins")
class TestGroupController(object):

    def test_about(self, app):
        user = factories.User()
        group = factories.Group(user=user, type=custom_group_type)
        group_name = group["name"]
        env = {"REMOTE_USER": six.ensure_str(user["name"])}
        url = url_for("%s.about" % custom_group_type, id=group_name)
        response = app.get(url=url, extra_environ=env)
        response.mustcontain(group_name)

    def test_bulk_process(self, app):
        user = factories.User()
        group = factories.Group(user=user, type=custom_group_type)
        group_name = group["name"]
        env = {"REMOTE_USER": six.ensure_str(user["name"])}
        url = url_for("%s.bulk_process" % custom_group_type, id=group_name)
        try:
            response = app.get(url=url, extra_environ=env)
        except Exception as e:
            assert e.args == ("Must be an organization",)
        else:
            raise Exception("Response should have raised an exception")

    def test_delete(self, app):
        user = factories.User()
        group = factories.Group(user=user, type=custom_group_type)
        group_name = group["name"]
        env = {"REMOTE_USER": six.ensure_str(user["name"])}
        url = url_for("%s.delete" % custom_group_type, id=group_name)
        response = app.get(url=url, extra_environ=env)

    def test_custom_group_form_slug(self, app):
        env, response = _get_group_new_page(app, custom_group_type)

        assert (
            '<span class="input-group-addon">/{}/</span>'.format(
                custom_group_type
            )
            in response
        )
        assert 'placeholder="my-{}"'.format(custom_group_type) in response
        assert (
            'data-module-prefix="test.ckan.net/{}/"'.format(custom_group_type)
            in response
        )
        assert (
            'data-module-placeholder="&lt;{}&gt;"'.format(custom_group_type)
            in response
        )


@pytest.mark.ckan_config("ckan.plugins", "example_igroupform_organization")
@pytest.mark.usefixtures("clean_db", "with_plugins")
class TestOrganizationController(object):
    def test_about(self, app):
        user = factories.User()
        group = factories.Organization(user=user, type=custom_group_type)
        group_name = group["name"]
        env = {"REMOTE_USER": six.ensure_str(user["name"])}
        url = url_for("%s.about" % custom_group_type, id=group_name)
        response = app.get(url=url, extra_environ=env)
        response.mustcontain(group_name)

    def test_bulk_process(self, app):
        user = factories.User()
        group = factories.Organization(user=user, type=custom_group_type)
        group_name = group["name"]
        env = {"REMOTE_USER": six.ensure_str(user["name"])}
        url = url_for("%s.bulk_process" % custom_group_type, id=group_name)
        response = app.get(url=url, extra_environ=env)

    def test_delete(self, app):
        user = factories.User()
        group = factories.Organization(user=user, type=custom_group_type)
        group_name = group["name"]
        env = {"REMOTE_USER": six.ensure_str(user["name"])}
        url = url_for("%s.delete" % custom_group_type, id=group_name)
        response = app.get(url=url, extra_environ=env)

    def test_custom_org_form_slug(self, app):
        env, response = _get_group_new_page(app, custom_group_type)

        assert (
            '<span class="input-group-addon">/{}/</span>'.format(
                custom_group_type
            )
            in response
        )
        assert 'placeholder="my-{}"'.format(custom_group_type) in response
        assert (
            'data-module-prefix="test.ckan.net/{}/"'.format(custom_group_type)
            in response
        )
        assert (
            'data-module-placeholder="&lt;{}&gt;"'.format(custom_group_type)
            in response
        )


@pytest.mark.ckan_config("ckan.plugins", "example_igroupform")
@pytest.mark.usefixtures("clean_db", "with_plugins")
class TestGroupControllerNew(object):

    def test_save(self, app):
        env, response = _get_group_new_page(app, custom_group_type)
        form = response.forms["group-edit"]
        form["name"] = u"saved"

        response = submit_and_follow(app, form, env, "save")
        # check correct redirect
        assert (
            response.request.url
            == "http://test.ckan.net/%s/saved" % custom_group_type
        )
        # check saved ok
        group = model.Group.by_name(u"saved")
        assert group.title == u""
        assert group.type == custom_group_type
        assert group.state == "active"

    def test_custom_group_form(self, app):
        """Our custom group form is being used for new groups."""
        env, response = _get_group_new_page(app, custom_group_type)

        assert "My Custom Group Form!" in response


@pytest.mark.ckan_config("ckan.plugins", "example_igroupform_default_group_type")
@pytest.mark.usefixtures("clean_db", "with_plugins")
class TestGroupControllerNew_DefaultGroupType(object):
    def test_save(self, app):
        env, response = _get_group_new_page(app, group_type)
        form = response.forms["group-edit"]
        form["name"] = u"saved"

        response = submit_and_follow(app, form, env, "save")
        # check correct redirect
        assert (
            response.request.url
            == "http://test.ckan.net/%s/saved" % group_type
        )
        # check saved ok
        group = model.Group.by_name(u"saved")
        assert group.title == u""
        assert group.type == group_type
        assert group.state == "active"

    def test_custom_group_form(self, app):
        """Our custom group form is being used for new groups."""
        env, response = _get_group_new_page(app, group_type)

        assert "My Custom Group Form!" in response


def _get_group_edit_page(app, group_type, group_name=None):
    user = factories.User()
    if group_name is None:
        group = factories.Group(user=user, type=group_type)
        group_name = group["name"]
    env = {"REMOTE_USER": six.ensure_str(user["name"])}
    url = url_for("%s.edit" % group_type, id=group_name)
    response = app.get(url=url, extra_environ=env)
    return env, response, group_name


@pytest.mark.ckan_config("ckan.plugins", "example_igroupform")
@pytest.mark.usefixtures("clean_db", "with_plugins")
class TestGroupControllerEdit(object):
    def test_group_doesnt_exist(self, app):
        user = factories.User()
        env = {"REMOTE_USER": six.ensure_str(user["name"])}
        url = url_for("%s.edit" % custom_group_type, id="doesnt_exist")
        app.get(url=url, extra_environ=env, status=404)

    def test_save(self, app):
        env, response, group_name = _get_group_edit_page(
            app, custom_group_type
        )
        form = response.forms["group-edit"]

        response = submit_and_follow(app, form, env, "save")
        group = model.Group.by_name(group_name)
        assert group.state == "active"
        assert group.type == custom_group_type

    def test_custom_group_form(self, app):
        """Our custom group form is being used to edit groups."""
        env, response, group_name = _get_group_edit_page(
            app, custom_group_type
        )

        assert "My Custom Group Form!" in response


@pytest.mark.ckan_config("ckan.plugins", "example_igroupform_default_group_type")
@pytest.mark.usefixtures("clean_db", "with_plugins")
class TestGroupControllerEdit_DefaultGroupType(object):
    def test_group_doesnt_exist(self, app):
        user = factories.User()
        env = {"REMOTE_USER": six.ensure_str(user["name"])}
        url = url_for("%s.edit" % group_type, id="doesnt_exist")
        app.get(url=url, extra_environ=env, status=404)

    def test_save(self, app):
        env, response, group_name = _get_group_edit_page(app, group_type)
        form = response.forms["group-edit"]

        response = submit_and_follow(app, form, env, "save")
        group = model.Group.by_name(group_name)
        assert group.state == "active"
        assert group.type == group_type

    def test_custom_group_form(self, app):
        """Our custom group form is being used to edit groups."""
        env, response, group_name = _get_group_edit_page(app, group_type)

        assert "My Custom Group Form!" in response
