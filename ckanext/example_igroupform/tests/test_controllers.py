# encoding: utf-8

import pytest
import six
import bs4
from ckan.lib.helpers import url_for

import ckan.tests.helpers as helpers
import ckan.model as model
from ckan.tests import factories

custom_group_type = u"grup"
group_type = u"group"


def _get_group_new_page(app, group_type):
    user = factories.User()
    env = {"REMOTE_USER": six.ensure_str(user["name"])}
    response = app.get(url_for("%s.new" % group_type), extra_environ=env,)
    return env, response


@pytest.mark.ckan_config("ckan.plugins", "example_igroupform")
@pytest.mark.usefixtures("clean_db", "with_plugins", "with_request_context")
class TestGroupController(object):
    def test_about(self, app):
        user = factories.User()
        group = factories.Group(user=user, type=custom_group_type)
        group_name = group["name"]
        env = {"REMOTE_USER": six.ensure_str(user["name"])}
        url = url_for("%s.about" % custom_group_type, id=group_name)
        response = app.get(url=url, extra_environ=env)
        assert helpers.body_contains(response, group_name)

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

        assert helpers.body_contains(
            response,
            '<span class="input-group-addon">/{}/</span>'.format(
                custom_group_type
            ),
        )
        assert helpers.body_contains(
            response, 'placeholder="my-{}"'.format(custom_group_type)
        )
        assert helpers.body_contains(
            response,
            'data-module-prefix="test.ckan.net/{}/"'.format(custom_group_type),
        )
        assert helpers.body_contains(
            response,
            'data-module-placeholder="&lt;{}&gt;"'.format(custom_group_type),
        )


@pytest.mark.ckan_config("ckan.plugins", "example_igroupform_organization")
@pytest.mark.usefixtures("clean_db", "with_plugins", "with_request_context")
class TestOrganizationController(object):
    def test_about(self, app):
        user = factories.User()
        group = factories.Organization(user=user, type=custom_group_type)
        group_name = group["name"]
        env = {"REMOTE_USER": six.ensure_str(user["name"])}
        url = url_for("%s.about" % custom_group_type, id=group_name)
        response = app.get(url=url, extra_environ=env)
        assert helpers.body_contains(response, group_name)

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

        assert helpers.body_contains(
            response,
            '<span class="input-group-addon">/{}/</span>'.format(
                custom_group_type
            ),
        )
        assert helpers.body_contains(
            response, 'placeholder="my-{}"'.format(custom_group_type)
        )
        assert helpers.body_contains(
            response,
            'data-module-prefix="test.ckan.net/{}/"'.format(custom_group_type),
        )
        assert helpers.body_contains(
            response,
            'data-module-placeholder="&lt;{}&gt;"'.format(custom_group_type),
        )


@pytest.mark.ckan_config("ckan.plugins", "example_igroupform")
@pytest.mark.usefixtures("clean_db", "with_plugins", "with_request_context")
class TestGroupControllerNew(object):
    def test_save(self, app):
        url = url_for("%s.new" % custom_group_type)
        user = factories.User()
        env = {"REMOTE_USER": six.ensure_str(user["name"])}
        app.post(
            url, data={"name": "saved", "title": ""}, environ_overrides=env
        )

        # check saved ok
        group = model.Group.by_name(u"saved")
        assert group.title == u""
        assert group.type == custom_group_type
        assert group.state == "active"

    def test_custom_group_form(self, app):
        """Our custom group form is being used for new groups."""
        env, response = _get_group_new_page(app, custom_group_type)

        assert helpers.body_contains(response, "My Custom Group Form!")


@pytest.mark.ckan_config(
    "ckan.plugins", "example_igroupform_default_group_type"
)
@pytest.mark.usefixtures("clean_db", "with_plugins", "with_request_context")
class TestGroupControllerNew_DefaultGroupType(object):
    def test_save(self, app):
        url = url_for("%s.new" % group_type)
        user = factories.User()
        env = {"REMOTE_USER": six.ensure_str(user["name"])}
        app.post(
            url, data={"name": "saved", "title": ""}, environ_overrides=env
        )

        # check saved ok
        group = model.Group.by_name(u"saved")
        assert group.title == u""
        assert group.type == group_type
        assert group.state == "active"

    def test_custom_group_form(self, app):
        """Our custom group form is being used for new groups."""
        env, response = _get_group_new_page(app, group_type)

        assert helpers.body_contains(response, "My Custom Group Form!")


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
@pytest.mark.usefixtures("clean_db", "with_plugins", "with_request_context")
class TestGroupControllerEdit(object):
    def test_group_doesnt_exist(self, app):
        user = factories.User()
        env = {"REMOTE_USER": six.ensure_str(user["name"])}
        url = url_for("%s.edit" % custom_group_type, id="doesnt_exist")
        app.get(url=url, extra_environ=env, status=404)

    def test_custom_group_form(self, app):
        """Our custom group form is being used to edit groups."""
        env, response, group_name = _get_group_edit_page(
            app, custom_group_type
        )

        assert helpers.body_contains(response, "My Custom Group Form!")


@pytest.mark.ckan_config(
    "ckan.plugins", "example_igroupform_default_group_type"
)
@pytest.mark.usefixtures("clean_db", "with_plugins", "with_request_context")
class TestGroupControllerEdit_DefaultGroupType(object):
    def test_group_doesnt_exist(self, app):
        user = factories.User()
        env = {"REMOTE_USER": six.ensure_str(user["name"])}
        url = url_for("%s.edit" % group_type, id="doesnt_exist")
        res = app.get(url=url, extra_environ=env)
        assert res.status_code == 404

    def test_custom_group_form(self, app):
        """Our custom group form is being used to edit groups."""
        env, response, group_name = _get_group_edit_page(app, group_type)

        assert helpers.body_contains(response, "My Custom Group Form!")


@pytest.mark.ckan_config("ckan.plugins", u"example_igroupform_v2")
@pytest.mark.usefixtures(
    "with_plugins", "with_request_context"
)
class TestGroupBlueprintPreparations(object):
    def test_additional_routes_are_registered(self, app):
        resp = app.get("/fancy_type/fancy-route", status=200)
        assert resp.body == u'Hello, fancy_type'

    def test_existing_routes_are_replaced(self, app):
        resp = app.get("/fancy_type/new", status=200)
        assert resp.body == u'Hello, new fancy_type'

    @pytest.mark.usefixtures(u'clean_db', u'clean_index')
    def test_existing_routes_are_untouched(self, app):
        resp = app.get("/fancy_type", status=200)
        page = bs4.BeautifulSoup(resp.body)
        links = [
            a['href'] for a in page.select(".breadcrumb a")
        ]
        assert links == ['/', '/fancy_type/']
