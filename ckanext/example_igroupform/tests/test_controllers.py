# encoding: utf-8

import pytest
import bs4
from ckan.lib.helpers import url_for

import ckan.tests.helpers as helpers
import ckan.model as model
from ckan.tests import factories

custom_group_type = u"grup"
group_type = u"group"


@pytest.fixture
def user():
    user = factories.UserWithToken()
    return user


def _get_group_new_page(app, env, group_type):
    response = app.get(url_for("%s.new" % group_type), extra_environ=env)
    return response


@pytest.mark.ckan_config("ckan.plugins", "example_igroupform")
@pytest.mark.usefixtures("non_clean_db", "with_plugins", "with_request_context")
class TestGroupController(object):
    def test_about(self, app, user):
        env = {"Authorization": user["token"]}
        group = factories.Group(user=user, type=custom_group_type)
        group_name = group["name"]
        url = url_for("%s.about" % custom_group_type, id=group_name)
        response = app.get(url=url, extra_environ=env)
        assert helpers.body_contains(response, group_name)

    def test_bulk_process(self, app, user):
        env = {"Authorization": user["token"]}
        group = factories.Group(user=user, type=custom_group_type)
        group_name = group["name"]
        url = url_for("%s.bulk_process" % custom_group_type, id=group_name)
        try:
            app.get(url=url, extra_environ=env)
        except Exception as e:
            assert e.args == ("Must be an organization",)
        else:
            raise Exception("Response should have raised an exception")

    def test_delete(self, app, user):
        env = {"Authorization": user["token"]}
        group = factories.Group(user=user, type=custom_group_type)
        group_name = group["name"]
        url = url_for("%s.delete" % custom_group_type, id=group_name)
        app.get(url=url, extra_environ=env)

    def test_custom_group_form_slug(self, app, user):
        env = {"Authorization": user["token"]}
        response = _get_group_new_page(app, env, custom_group_type)

        assert helpers.body_contains(
            response,
            '<label class="input-group-text">/{}/</label>'.format(
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
@pytest.mark.usefixtures("clean_db", "clean_index", "with_plugins", "with_request_context")
class TestOrganizationController(object):
    def test_about(self, app, user):
        env = {"Authorization": user["token"]}
        group = factories.Organization(user=user, type=custom_group_type)
        group_name = group["name"]
        url = url_for("%s.about" % custom_group_type, id=group_name)
        response = app.get(url=url, extra_environ=env)
        assert helpers.body_contains(response, group_name)

    def test_bulk_process(self, app, user):
        env = {"Authorization": user["token"]}
        group = factories.Organization(user=user, type=custom_group_type)
        group_name = group["name"]
        url = url_for("%s.bulk_process" % custom_group_type, id=group_name)
        app.get(url=url, extra_environ=env)

    def test_delete(self, app, user):
        env = {"Authorization": user["token"]}
        group = factories.Organization(user=user, type=custom_group_type)
        group_name = group["name"]
        url = url_for("%s.delete" % custom_group_type, id=group_name)
        app.get(url=url, extra_environ=env)

    def test_custom_org_form_slug(self, app, user):
        env = {"Authorization": user["token"]}
        response = _get_group_new_page(app, env, custom_group_type)

        assert helpers.body_contains(
            response,
            '<label class="input-group-text">/{}/</label>'.format(
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

    def test_pagination(self, app, user):
        env = {"Authorization": user["token"]}
        group = factories.Organization(user=user, type=custom_group_type)
        group_name = group["name"]
        for _ in range(0, 21):
            factories.Dataset(owner_org=group['id'], user=user)
        url = url_for("%s.read" % custom_group_type, id=group_name)
        response = app.get(url=url, extra_environ=env)
        assert helpers.body_contains(
            response,
            '/grup/{}?page=2'.format(group_name)
        )
        assert not helpers.body_contains(
            response,
            '/organization/{}?page=2'.format(group_name)
        )


@pytest.mark.ckan_config("ckan.plugins", "example_igroupform")
@pytest.mark.usefixtures("clean_db", "with_plugins", "with_request_context")
class TestGroupControllerNew(object):
    def test_save(self, app, user):
        url = url_for("%s.new" % custom_group_type)
        env = {"Authorization": user["token"]}
        app.post(url, extra_environ=env, data={"name": "saved", "title": ""})

        # check saved ok
        group = model.Group.by_name(u"saved")
        assert group.title == u""
        assert group.type == custom_group_type
        assert group.state == "active"

    def test_custom_group_form(self, app, user):
        """Our custom group form is being used for new groups."""
        env = {"Authorization": user["token"]}
        response = _get_group_new_page(app, env, custom_group_type)

        assert helpers.body_contains(response, "My Custom Group Form!")


@pytest.mark.ckan_config(
    "ckan.plugins", "example_igroupform_default_group_type"
)
@pytest.mark.usefixtures("clean_db", "with_plugins", "with_request_context")
class TestGroupControllerNewDefaultGroupType(object):
    def test_save(self, app, user):
        url = url_for("%s.new" % group_type)
        env = {"Authorization": user["token"]}
        app.post(url, extra_environ=env, data={"name": "saved", "title": ""})

        # check saved ok
        group = model.Group.by_name(u"saved")
        assert group.title == u""
        assert group.type == group_type
        assert group.state == "active"

    def test_custom_group_form(self, app, user):
        """Our custom group form is being used for new groups."""
        env = {"Authorization": user["token"]}
        response = _get_group_new_page(app, env, group_type)

        assert helpers.body_contains(response, "My Custom Group Form!")


def _get_group_edit_page(app, user, group_type, group_name=None):
    env = {"Authorization": user["token"]}
    if group_name is None:
        group = factories.Group(user=user, type=group_type)
        group_name = group["name"]
    url = url_for("%s.edit" % group_type, id=group_name)
    response = app.get(url=url, extra_environ=env)
    return response, group_name


@pytest.mark.ckan_config("ckan.plugins", "example_igroupform")
@pytest.mark.usefixtures("clean_db", "with_plugins", "with_request_context")
class TestGroupControllerEdit(object):
    def test_group_doesnt_exist(self, app, user):
        env = {"Authorization": user["token"]}
        url = url_for("%s.edit" % custom_group_type, id="doesnt_exist")
        app.get(url=url, extra_environ=env, status=404)

    def test_custom_group_form(self, app, user):
        """Our custom group form is being used to edit groups."""
        response, _ = _get_group_edit_page(
            app, user, custom_group_type
        )

        assert helpers.body_contains(response, "My Custom Group Form!")


@pytest.mark.ckan_config(
    "ckan.plugins", "example_igroupform_default_group_type"
)
@pytest.mark.usefixtures("clean_db", "with_plugins", "with_request_context")
class TestGroupControllerEditDefaultGroupType(object):
    def test_group_doesnt_exist(self, app, user):
        env = {"Authorization": user["token"]}
        url = url_for("%s.edit" % group_type, id="doesnt_exist")
        res = app.get(url=url, extra_environ=env)
        assert res.status_code == 404

    def test_custom_group_form(self, app, user):
        """Our custom group form is being used to edit groups."""
        response, _ = _get_group_edit_page(app, user, group_type)

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


@pytest.mark.ckan_config("ckan.plugins", u"example_igroupform")
@pytest.mark.usefixtures(
    "with_plugins", "with_request_context", "clean_db"
)
class TestCustomGroupBlueprint(object):
    def test_group_listing_labels(self, app):
        resp = app.get("/grup", status=200)
        page = bs4.BeautifulSoup(resp.body)
        links = page.select(".breadcrumb a")
        assert [a["href"] for a in links] == ["/", "/grup/"]
        assert links[-1].text == "Grups"
        assert page.head.title.text.startswith("Grups")

    def test_group_creation_labels(self, app, user):
        env = {"Authorization": user["token"]}
        resp = app.get("/grup", extra_environ=env, status=200)
        page = bs4.BeautifulSoup(resp.body)
        btn = page.select_one('.page_primary_action .btn')
        assert btn.text.strip() == 'Add Grup'

        resp = app.get("/grup/new", extra_environ=env, status=200)
        page = bs4.BeautifulSoup(resp.body)
        assert page.select_one('.page-heading').text.strip() == 'Create Grup'
        assert page.select_one(
            '.form-actions .btn').text.strip() == 'Create Grup'

    @pytest.mark.ckan_config('ckan.default.group_type', 'grup')
    def test_default_group_type(self, app):
        resp = app.get("/", status=200)
        page = bs4.BeautifulSoup(resp.body)
        link = page.select_one('.masthead .navbar-nav a[href="/grup/"]')
        assert link
        assert link.text == 'Grups'
