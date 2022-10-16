# encoding: utf-8

from bs4 import BeautifulSoup
from werkzeug.routing import BuildError
import unittest.mock as mock

import ckan.authz as authz
from ckan.lib.helpers import url_for
import pytest
from urllib.parse import urlparse
import ckan.model as model
import ckan.plugins as p
import ckan.logic as logic

import ckan.tests.helpers as helpers
import ckan.tests.factories as factories


@pytest.fixture
def sysadmin():
    user = factories.SysadminWithToken()
    return user


@pytest.fixture
def user():
    user = factories.UserWithToken()
    return user


def _get_location(res):
    location = res.headers['location']
    return urlparse(location)._replace(scheme='', netloc='').geturl()


@pytest.mark.usefixtures("clean_db", "with_request_context")
class TestPackageNew(object):

    @pytest.mark.ckan_config("ckan.plugins", "test_package_controller_plugin")
    @pytest.mark.usefixtures("with_plugins")
    def test_new_plugin_hook(self, app, user):
        plugin = p.get_plugin("test_package_controller_plugin")
        env = {"Authorization": user["token"]}
        app.post(
            url_for("dataset.new"),
            extra_environ=env,
            data={"name": u"plugged", "save": ""},
            follow_redirects=False,
        )
        assert plugin.calls["edit"] == 0, plugin.calls
        assert plugin.calls["create"] == 1, plugin.calls

    @pytest.mark.ckan_config("ckan.plugins", "test_package_controller_plugin")
    @pytest.mark.usefixtures("with_plugins")
    def test_after_create_plugin_hook(self, app, user):
        plugin = p.get_plugin("test_package_controller_plugin")
        env = {"Authorization": user["token"]}
        app.post(
            url_for("dataset.new"),
            extra_environ=env,
            data={"name": u"plugged2", "save": ""},
            follow_redirects=False,
        )
        assert plugin.calls["after_dataset_update"] == 0, plugin.calls
        assert plugin.calls["after_dataset_create"] == 1, plugin.calls

        assert plugin.id_in_dict

    @pytest.mark.usefixtures("clean_index")
    def test_new_indexerror(self, app, user):
        from ckan.lib.search.common import SolrSettings
        bad_solr_url = "http://example.com/badsolrurl"
        solr_url = SolrSettings.get()[0]
        try:
            SolrSettings.init(bad_solr_url)
            new_package_name = u"new-package-missing-solr"
            offset = url_for("dataset.new")
            env = {"Authorization": user["token"]}
            res = app.post(
                offset,
                extra_environ=env,
                data={"save": "", "name": new_package_name},
            )
            assert "Unable to add package to search index" in res, res
        finally:
            SolrSettings.init(solr_url)

    def test_change_locale(self, app, user):
        url = url_for("dataset.new")
        env = {"Authorization": user["token"]}
        res = app.get(url, extra_environ=env)
        res = app.get("/de/dataset/new", extra_environ=env)
        assert helpers.body_contains(res, "Datensatz")

    @pytest.mark.ckan_config("ckan.auth.create_unowned_dataset", "false")
    def test_needs_organization_but_no_organizations_has_button(self, app, sysadmin):
        """ Scenario: The settings say every dataset needs an organization
        but there are no organizations. If the user is allowed to create an
        organization they should be prompted to do so when they try to create
        a new dataset"""
        env = {"Authorization": sysadmin["token"]}
        response = app.get(url=url_for("dataset.new"), extra_environ=env)
        assert url_for("organization.new") in response

    @pytest.mark.ckan_config("ckan.auth.create_unowned_dataset", "false")
    @pytest.mark.ckan_config("ckan.auth.user_create_organizations", "false")
    def test_needs_organization_but_no_organizations_no_button(
        self, monkeypatch, app, user
    ):
        """ Scenario: The settings say every dataset needs an organization
        but there are no organizations. If the user is not allowed to create an
        organization they should be told to ask the admin but no link should be
        presented. Note: This cannot happen with the default ckan and requires
        a plugin to overwrite the package_create behavior"""
        authz._AuthFunctions.get('package_create')
        monkeypatch.setitem(
            authz._AuthFunctions._functions, 'package_create',
            lambda *_: {'success': True})
        env = {"Authorization": user["token"]}
        response = app.get(url=url_for("dataset.new"), extra_environ=env)

        assert url_for("organization.new") not in response
        assert "Ask a system administrator" in response

    def test_name_required(self, app, user):
        env = {"Authorization": user["token"]}
        url = url_for("dataset.new")
        response = app.post(url, extra_environ=env, data={"save": ""})
        assert "Name: Missing value" in response

    def test_first_page_creates_draft_package(self, app, user):
        url = url_for("dataset.new")
        name = factories.Dataset.stub().name
        env = {"Authorization": user["token"]}
        app.post(url, data={
            "name": name,
            "save": "",
            "_ckan_phase": 1
        }, extra_environ=env, follow_redirects=False)
        pkg = model.Package.by_name(name)
        assert pkg.state == "draft"

    def test_resource_required(self, app, user):
        url = url_for("dataset.new")
        name = "one-resource-required"
        env = {"Authorization": user["token"]}
        response = app.post(url, extra_environ=env, data={
            "name": name,
            "save": "",
            "_ckan_phase": 1
        }, follow_redirects=False)
        location = _get_location(response)
        response = app.post(location, extra_environ=env, data={
            "id": "",
            "url": "",
            "save": "go-metadata",
        })
        assert "You must add at least one data resource" in response

    def test_complete_package_with_one_resource(self, app, user):
        url = url_for("dataset.new")
        name = factories.Dataset.stub().name
        env = {"Authorization": user["token"]}
        response = app.post(url, extra_environ=env, data={
            "name": name,
            "save": "",
            "_ckan_phase": 1

        }, follow_redirects=False)
        location = _get_location(response)
        response = app.post(location, extra_environ=env, data={
            "id": "",
            "url": "http://example.com/resource",
            "save": "go-metadata"
        })

        pkg = model.Package.by_name(name)
        assert pkg.resources[0].url == u"http://example.com/resource"
        assert pkg.state == "active"

    def test_complete_package_with_two_resources(self, app):

        user = factories.User()

        url = url_for("dataset.new")
        name = factories.Dataset.stub().name
        response = app.post(
            url,
            data={
                "name": name,
                "save": "",
                "_ckan_phase": 1
            },
            environ_overrides={"REMOTE_USER": user["name"]},
            follow_redirects=False
        )
        location = _get_location(response)
        app.post(location, data={
                "id": "",
                "url": "http://example.com/resource0",
                "save": "again"
            },

            environ_overrides={"REMOTE_USER": user["name"]},
        )
        app.post(location, data={
                "id": "",
                "url": "http://example.com/resource1",
                "save": "go-metadata"
            },
            environ_overrides={"REMOTE_USER": user["name"]},
        )
        pkg = model.Package.by_name(name)
        resources = sorted(pkg.resources, key=lambda r: r.url)
        assert resources[0].url == u"http://example.com/resource0"
        assert resources[1].url == u"http://example.com/resource1"
        assert pkg.state == "active"

    # resource upload is tested in TestExampleIUploaderPlugin

    def test_previous_button_works(self, app, user):
        url = url_for("dataset.new")
        env = {"Authorization": user["token"]}
        response = app.post(url, extra_environ=env, data={
            "name": "previous-button-works",
            "save": "",
            "_ckan_phase": 1
        }, follow_redirects=False)

        location = _get_location(response)
        response = app.post(location, extra_environ=env, data={
            "id": "",
            "save": "go-dataset"
        }, follow_redirects=False)

        assert '/dataset/edit/' in response.headers['location']

    def test_previous_button_populates_form(self, app):

        user = factories.User()

        url = url_for("dataset.new")
        name = factories.Dataset.stub().name
        response = app.post(
            url,
            environ_overrides={"REMOTE_USER": user["name"]},
            data={
                "name": name,
                "save": "",
                "_ckan_phase": 1
            },
            follow_redirects=False
        )

        location = _get_location(response)
        response = app.post(location, data={
            "id": "",
            "save": "go-dataset"
            },
            environ_overrides={"REMOTE_USER": user["name"]},
        )

        assert 'name="title"' in response
        assert f'value="{name}"'

    def test_previous_next_maintains_draft_state(self, app, user):
        url = url_for("dataset.new")
        name = factories.Dataset.stub().name
        env = {"Authorization": user["token"]}
        response = app.post(url, extra_environ=env, data={
            "name": name,
            "save": "",
            "_ckan_phase": 1
        }, follow_redirects=False)

        location = _get_location(response)
        response = app.post(location, extra_environ=env, data={
            "id": "",
            "save": "go-dataset"
        })

        pkg = model.Package.by_name(name)
        assert pkg.state == "draft"

    def test_dataset_edit_org_dropdown_visible_to_normal_user_with_orgs_available(
        self, app, user
    ):
        """
        The 'Organization' dropdown is available on the dataset create/edit
        page to normal (non-sysadmin) users who have organizations available
        to them.
        """
        env = {"Authorization": user["token"]}
        # user is admin of org.
        org = factories.Organization(
            name="my-org", users=[{"name": user["name"], "capacity": "admin"}]
        )

        name = factories.Dataset.stub().name
        url = url_for("dataset.new")
        response = app.post(url, data={
            "name": name,
            "owner_org": org["id"],
            "save": "",
            "_ckan_phase": 1
        }, extra_environ=env, follow_redirects=False)
        location = _get_location(response)
        response = app.post(location, extra_environ=env, data={
            "id": "",
            "url": "http://example.com/resource",
            "save": "go-metadata"
        })

        pkg = model.Package.by_name(name)
        assert pkg.state == "active"

        # edit package page response
        url = url_for("dataset.edit", id=pkg.id)
        pkg_edit_response = app.get(url=url, extra_environ=env)
        # A field with the correct id is in the response

        owner_org_options = [
            option['value'] for option
            in BeautifulSoup(pkg_edit_response.data).body.select(
                "form#dataset-edit"
            )[0].select('[name=owner_org]')[0].select('option')
        ]
        assert org["id"] in owner_org_options

    def test_dataset_edit_org_dropdown_normal_user_can_remove_org(self, app, user):
        """
        A normal user (non-sysadmin) can remove an organization from a dataset
        have permissions on.
        """
        env = {"Authorization": user["token"]}
        # user is admin of org.
        org = factories.Organization(
            name="my-org", users=[{"name": user["name"], "capacity": "admin"}]
        )

        name = factories.Dataset.stub().name
        url = url_for("dataset.new")
        response = app.post(url, data={
            "name": name,
            "owner_org": org["id"],
            "save": "",
            "_ckan_phase": 1
        }, extra_environ=env, follow_redirects=False)
        location = _get_location(response)
        response = app.post(location, extra_environ=env, data={
            "id": "",
            "url": "http://example.com/resource",
            "save": "go-metadata"
        })

        pkg = model.Package.by_name(name)
        assert pkg.state == "active"
        assert pkg.owner_org == org["id"]
        assert pkg.owner_org is not None
        # edit package page response
        url = url_for("dataset.edit", id=pkg.id)
        app.post(url=url, extra_environ=env, data={"owner_org": ""}, follow_redirects=False)

        post_edit_pkg = model.Package.by_name(name)
        assert post_edit_pkg.owner_org is None
        assert post_edit_pkg.owner_org != org["id"]

    def test_dataset_edit_org_dropdown_not_visible_to_normal_user_with_no_orgs_available(
        self, app, user
    ):
        """
        The 'Organization' dropdown is not available on the dataset
        create/edit page to normal (non-sysadmin) users who have no
        organizations available to them.
        """
        # user isn't admin of org.
        org = factories.Organization(name="my-org")
        name = factories.Dataset.stub().name
        url = url_for("dataset.new")
        env = {"Authorization": user["token"]}
        response = app.post(url, data={
            "name": name,
            "save": "",
            "_ckan_phase": 1
        }, extra_environ=env, follow_redirects=False)
        location = _get_location(response)
        response = app.post(location, extra_environ=env, data={
            "id": "",
            "url": "http://example.com/resource",
            "save": "go-metadata"
        })

        pkg = model.Package.by_name(name)
        assert pkg.state == "active"

        # edit package response
        url = url_for(
            "dataset.edit", id=model.Package.by_name(name).id
        )
        pkg_edit_response = app.get(url=url, extra_environ=env)
        # A field with the correct id is in the response
        assert 'value="{0}"'.format(org["id"]) not in pkg_edit_response

    def test_dataset_edit_org_dropdown_visible_to_sysadmin_with_no_orgs_available(
        self, app, sysadmin
    ):
        """
        The 'Organization' dropdown is available to sysadmin users regardless
        of whether they personally have an organization they administrate.
        """
        user = factories.User()
        # user is admin of org.
        org = factories.Organization(
            name="my-org", users=[{"name": user["name"], "capacity": "admin"}]
        )

        url = url_for("dataset.new")
        # user in env is sysadmin
        env = {"Authorization": sysadmin["token"]}
        response = app.get(url=url, extra_environ=env)
        # organization dropdown available in create page.
        assert 'id="field-organizations"' in response
        name = factories.Dataset.stub().name

        response = app.post(url, extra_environ=env, data={
            "name": name,
            "owner_org": org["id"],
            "save": "",
            "_ckan_phase": 1
        }, follow_redirects=False)
        location = _get_location(response)
        response = app.post(location, extra_environ=env, data={
            "id": "",
            "url": "http://example.com/resource",
            "save": "go-metadata"
        })

        pkg = model.Package.by_name(name)
        assert pkg.state == "active"

        # edit package page response
        url = url_for("dataset.edit", id=pkg.id)
        pkg_edit_response = app.get(url=url, extra_environ=env)
        # A field with the correct id is in the response
        assert 'id="field-organizations"' in pkg_edit_response
        # The organization id is in the response in a value attribute
        assert 'value="{0}"'.format(org["id"]) in pkg_edit_response

    def test_unauthed_user_creating_dataset(self, app):

        # provide REMOTE_ADDR to idenfity as remote user, see
        # ckan.views.identify_user() for details
        app.post(
            url=url_for("dataset.new"),
            extra_environ={"REMOTE_ADDR": "127.0.0.1"},
            status=403,
        )

    def test_form_without_initial_data(self, app, user):
        url = url_for("dataset.new")
        env = {"Authorization": user["token"]}
        resp = app.get(url=url, extra_environ=env)
        page = BeautifulSoup(resp.body)
        form = page.select_one('#dataset-edit')
        assert not form.select_one('[name=title]')['value']
        assert not form.select_one('[name=name]')['value']
        assert not form.select_one('[name=notes]').text

    def test_form_with_initial_data(self, app, user):
        url = url_for("dataset.new", name="name",
                      notes="notes", title="title")
        env = {"Authorization": user["token"]}
        resp = app.get(url=url, extra_environ=env)
        page = BeautifulSoup(resp.body)
        form = page.select_one('#dataset-edit')
        assert form.select_one('[name=title]')['value'] == "title"
        assert form.select_one('[name=name]')['value'] == "name"
        assert form.select_one('[name=notes]').text == "notes"


@pytest.mark.usefixtures("non_clean_db", "with_request_context")
class TestPackageEdit(object):
    def test_redirect_after_edit_using_param(self, app, sysadmin):
        return_url = "http://random.site.com/dataset/<NAME>?test=param"
        pkg = factories.Dataset()
        url = url_for("dataset.edit", id=pkg["name"], return_to=return_url)
        env = {"Authorization": sysadmin["token"]}
        resp = app.post(url, extra_environ=env, follow_redirects=False)
        assert resp.headers["location"] == return_url.replace("<NAME>", pkg["name"])

    def test_redirect_after_edit_using_config(self, app, ckan_config, sysadmin):
        expected_redirect = ckan_config["package_edit_return_url"]
        pkg = factories.Dataset()
        url = url_for("dataset.edit", id=pkg["name"])
        env = {"Authorization": sysadmin["token"]}
        resp = app.post(url, extra_environ=env, follow_redirects=False)
        assert resp.headers["location"] == expected_redirect.replace("<NAME>", pkg["name"])

    def test_organization_admin_can_edit(self, app, user):
        env = {"Authorization": user["token"]}
        organization = factories.Organization(
            users=[{"name": user["name"], "capacity": "admin"}]
        )
        dataset = factories.Dataset(owner_org=organization["id"])
        app.post(
            url_for("dataset.edit", id=dataset["name"]),
            extra_environ=env,
            data={
                "notes": u"edited description",
                "save": ""
            }, follow_redirects=False
        )
        result = helpers.call_action("package_show", id=dataset["id"])
        assert u"edited description" == result["notes"]

    def test_organization_editor_can_edit(self, app, user):
        env = {"Authorization": user["token"]}
        organization = factories.Organization(
            users=[{"name": user["name"], "capacity": "editor"}]
        )
        dataset = factories.Dataset(owner_org=organization["id"])
        app.post(
            url_for("dataset.edit", id=dataset["name"]),
            extra_environ=env,
            data={
                "notes": u"edited description",
                "save": ""
            }, follow_redirects=False

        )
        result = helpers.call_action("package_show", id=dataset["id"])
        assert u"edited description" == result["notes"]

    def test_organization_member_cannot_edit(self, app, user):
        env = {"Authorization": user["token"]}
        organization = factories.Organization(
            users=[{"name": user["name"], "capacity": "member"}]
        )
        dataset = factories.Dataset(owner_org=organization["id"])
        app.get(
            url_for("dataset.edit", id=dataset["name"]),
            extra_environ=env,
            status=403)

    def test_user_not_in_organization_cannot_edit(self, app, user):
        organization = factories.Organization()
        dataset = factories.Dataset(owner_org=organization["id"])
        url = url_for("dataset.edit", id=dataset["name"])
        env = {"Authorization": user["token"]}
        app.get(url=url, extra_environ=env, status=403)
        app.post(
            url=url,
            extra_environ=env,
            data={"notes": "edited description"},
            status=403)

    def test_anonymous_user_cannot_edit(self, app):
        organization = factories.Organization()
        dataset = factories.Dataset(owner_org=organization["id"])
        url = url_for("dataset.edit", id=dataset["name"])
        app.get(url=url, status=403)

        app.post(
            url=url,
            data={"notes": "edited description"},
            status=403,
        )

    def test_validation_errors_for_dataset_name_appear(self, app, user):
        """fill out a bad dataset set name and make sure errors appear"""
        env = {"Authorization": user["token"]}
        organization = factories.Organization(
            users=[{"name": user["name"], "capacity": "admin"}]
        )
        dataset = factories.Dataset(owner_org=organization["id"])
        response = app.post(
            url_for("dataset.edit", id=dataset["name"]),
            extra_environ=env,
            data={
                "name": "this is not a valid name",
                "save": ""
            }
        )
        assert "The form contains invalid entries" in response.body

        assert (
            "Name: Must be purely lowercase alphanumeric (ascii) "
            "characters and these symbols: -_" in response.body
        )

    def test_edit_a_dataset_that_does_not_exist_404s(self, app, user):
        env = {"Authorization": user["token"]}
        response = app.get(url_for("dataset.edit", extra_environ=env, id="does-not-exist"))
        assert 404 == response.status_code


@pytest.mark.usefixtures("non_clean_db", "with_request_context")
class TestPackageOwnerOrgList(object):

    owner_org_select = '<select id="field-organizations" name="owner_org"'

    def test_org_list_shown_if_new_dataset_and_user_is_admin_or_editor_in_an_org(self, app, user):
        env = {"Authorization": user["token"]}
        factories.Organization(
            users=[{"name": user["name"], "capacity": "admin"}]
        )
        response = app.get(url_for("dataset.new"), extra_environ=env)
        assert self.owner_org_select in response.body

    def test_org_list_shown_if_admin_or_editor_of_the_dataset_org(self, app, user):
        env = {"Authorization": user["token"]}
        organization = factories.Organization(
            users=[{"name": user["name"], "capacity": "admin"}]
        )
        dataset = factories.Dataset(owner_org=organization["id"])
        response = app.get(url_for("dataset.edit", id=dataset["name"]), extra_environ=env)
        assert self.owner_org_select in response.body

    @pytest.mark.ckan_config('ckan.auth.allow_dataset_collaborators', True)
    def test_org_list_not_shown_if_user_is_a_collaborator_with_default_config(self, app, user):
        env = {"Authorization": user["token"]}
        organization1 = factories.Organization()
        dataset = factories.Dataset(owner_org=organization1["id"])

        factories.Organization(
            users=[{"name": user["name"], "capacity": "admin"}]
        )
        helpers.call_action(
            'package_collaborator_create',
            id=dataset['id'], user_id=user["name"], capacity='editor')

        response = app.get(url_for("dataset.edit", id=dataset["name"]), extra_environ=env)
        assert self.owner_org_select not in response.body

        response = app.post(
            url_for("dataset.edit", id=dataset["name"]),
            extra_environ=env,
            data={
                "notes": "changed",
                "save": ""
            },
            follow_redirects=False
        )
        updated_dataset = helpers.call_action("package_show", id=dataset["id"])
        assert updated_dataset['owner_org'] == organization1['id']

    @pytest.mark.ckan_config('ckan.auth.allow_dataset_collaborators', True)
    @pytest.mark.ckan_config('ckan.auth.allow_collaborators_to_change_owner_org', True)
    def test_org_list_shown_if_user_is_a_collaborator_with_config_enabled(self, app, user):
        env = {"Authorization": user["token"]}
        organization1 = factories.Organization()
        dataset = factories.Dataset(owner_org=organization1["id"])

        organization2 = factories.Organization(
            users=[{"name": user["name"], "capacity": "admin"}]
        )
        helpers.call_action(
            'package_collaborator_create',
            id=dataset['id'], user_id=user["name"], capacity='editor')

        response = app.get(url_for("dataset.edit", id=dataset["name"]), extra_environ=env)
        assert self.owner_org_select in response.body

        response = app.post(
            url_for("dataset.edit", id=dataset["name"]),
            extra_environ=env,
            data={
                "notes": "changed",
                "owner_org": organization2['id'],
                "save": ""
            },
            follow_redirects=False
        )
        updated_dataset = helpers.call_action("package_show", id=dataset["id"])
        assert updated_dataset['owner_org'] == organization2['id']


@pytest.mark.usefixtures("non_clean_db", "with_request_context")
class TestPackageRead(object):
    def test_read(self, app):
        dataset = factories.Dataset()
        response = app.get(url_for("dataset.read", id=dataset["name"]))
        assert helpers.body_contains(response, dataset["title"])
        assert helpers.body_contains(response, dataset["notes"][:60].split("\n")[0])

    def test_organization_members_can_read_private_datasets(self, app):
        members = {
            "member": factories.UserWithToken(),
            "editor": factories.UserWithToken(),
            "admin": factories.UserWithToken(),
            "sysadmin": factories.SysadminWithToken(),
        }
        organization = factories.Organization(
            users=[
                {"name": members["member"]["id"], "capacity": "member"},
                {"name": members["editor"]["id"], "capacity": "editor"},
                {"name": members["admin"]["id"], "capacity": "admin"},
            ]
        )
        dataset = factories.Dataset(owner_org=organization["id"], private=True)
        for _, user_dict in members.items():
            env = {"Authorization": user_dict["token"]}
            response = app.get(url_for("dataset.read", id=dataset["name"]), extra_environ=env)
            assert dataset["title"] in response.body
            assert dataset["notes"] in response.body

    def test_anonymous_users_cannot_see_private_datasets(self, app):
        organization = factories.Organization()
        dataset = factories.Dataset(owner_org=organization["id"], private=True)
        response = app.get(
            url_for("dataset.read", id=dataset["name"]), status=404
        )
        assert 404 == response.status_code

    def test_user_not_in_organization_cannot_see_private_datasets(self, app, user):
        organization = factories.Organization()
        dataset = factories.Dataset(owner_org=organization["id"], private=True)
        env = {"Authorization": user["token"]}
        response = app.get(
            url_for("dataset.read", id=dataset["name"]), extra_environ=env, status=404)
        assert 404 == response.status_code

    def test_read_rdf(self, app):
        """ The RDF outputs now live in ckanext-dcat"""
        dataset1 = factories.Dataset()

        offset = url_for("dataset.read", id=dataset1["name"]) + ".rdf"
        app.get(offset, status=404)

    def test_read_n3(self, app):
        """ The RDF outputs now live in ckanext-dcat"""
        dataset1 = factories.Dataset()

        offset = url_for("dataset.read", id=dataset1["name"]) + ".n3"
        app.get(offset, status=404)

    # Test the 'reveal_private_datasets' flag

    @pytest.mark.ckan_config("ckan.auth.reveal_private_datasets", "True")
    def test_anonymous_users_cannot_read_private_datasets(self, app):
        organization = factories.Organization()
        dataset = factories.Dataset(owner_org=organization["id"], private=True)
        response = app.get(
            url_for("dataset.read", id=dataset["name"]),
            follow_redirects=False
        )
        assert 302 == response.status_code
        assert '/login' in response.headers[u"Location"]

    @pytest.mark.ckan_config("ckan.auth.reveal_private_datasets", "True")
    def test_user_not_in_organization_cannot_read_private_datasets(self, app, user):
        organization = factories.Organization()
        dataset = factories.Dataset(owner_org=organization["id"], private=True)
        env = {"Authorization": user["token"]}
        response = app.get(
            url_for("dataset.read", id=dataset["name"]), extra_environ=env, status=403)
        assert 403 == response.status_code


@pytest.mark.usefixtures("non_clean_db", "with_request_context")
class TestPackageDelete(object):
    def test_owner_delete(self, app, user):
        env = {"Authorization": user["token"]}
        owner_org = factories.Organization(
            users=[{"name": user["name"], "capacity": "admin"}]
        )
        dataset = factories.Dataset(owner_org=owner_org["id"])

        response = app.post(
            url_for("dataset.delete", id=dataset["name"]),
            extra_environ=env
            )
        assert 200 == response.status_code

        deleted = helpers.call_action("package_show", id=dataset["id"])
        assert "deleted" == deleted["state"]

    def test_delete_on_non_existing_dataset(self, app):
        response = app.post(
            url_for("dataset.delete", id="schrodingersdatset"),

        )
        assert 404 == response.status_code

    def test_sysadmin_can_delete_any_dataset(self, app, sysadmin):
        owner_org = factories.Organization()
        dataset = factories.Dataset(owner_org=owner_org["id"])
        env = {"Authorization": sysadmin["token"]}
        response = app.post(
            url_for("dataset.delete", id=dataset["name"]),
            extra_environ=env
            )
        assert 200 == response.status_code

        deleted = helpers.call_action("package_show", id=dataset["id"])
        assert "deleted" == deleted["state"]

    def test_anon_user_cannot_delete_owned_dataset(self, app, user):
        owner_org = factories.Organization(
            users=[{"name": user["name"], "capacity": "admin"}]
        )
        dataset = factories.Dataset(owner_org=owner_org["id"])

        response = app.post(
            url_for("dataset.delete", id=dataset["name"]), status=403
        )
        assert helpers.body_contains(response, "Unauthorized to delete package")

        deleted = helpers.call_action("package_show", id=dataset["id"])
        assert "active" == deleted["state"]

    def test_logged_in_user_cannot_delete_owned_dataset(self, app, user):
        env = {"Authorization": user["token"]}
        owner = factories.User()
        owner_org = factories.Organization(
            users=[{"name": owner["id"], "capacity": "admin"}]
        )
        dataset = factories.Dataset(owner_org=owner_org["id"])

        response = app.post(
            url_for("dataset.delete", id=dataset["name"]),
            extra_environ=env
            )
        assert 403 == response.status_code
        assert helpers.body_contains(response, "Unauthorized to delete package")

    def test_confirm_cancel_delete(self, app):
        """Test confirmation of deleting datasets

        When package_delete is made as a get request, it should return a
        'do you want to delete this dataset? confirmation page"""
        user = factories.User()
        owner_org = factories.Organization(
            users=[{"name": user["name"], "capacity": "admin"}]
        )
        dataset = factories.Dataset(owner_org=owner_org["id"])
        response = app.get(
            url_for("dataset.delete", id=dataset["name"]),
            environ_overrides={"REMOTE_USER": user["name"]},
        )
        assert 200 == response.status_code
        message = "Are you sure you want to delete dataset - {name}?"
        assert helpers.body_contains(response, message.format(name=dataset["title"]))

        response = app.post(
            url_for("dataset.delete", id=dataset["name"]),
            environ_overrides={"REMOTE_USER": user["name"]},
            data={"cancel": ""}
            )
        assert 200 == response.status_code

    @pytest.mark.ckan_config("ckan.plugins", "test_package_controller_plugin")
    @pytest.mark.usefixtures("with_plugins")
    def test_delete(self, app, user, sysadmin):
        dataset = factories.Dataset()
        plugin = p.get_plugin("test_package_controller_plugin")
        plugin.calls.clear()
        url = url_for("dataset.delete", id=dataset["name"])
        user_env = {"Authorization": user["token"]}
        app.post(url, extra_environ=user_env)
        sysadmin_env = {"Authorization": sysadmin["token"]}
        app.post(url, extra_environ=sysadmin_env)

        assert model.Package.get(dataset["name"]).state == u"deleted"

        assert plugin.calls["delete"] == 2
        assert plugin.calls["after_dataset_delete"] == 2


@pytest.mark.usefixtures("non_clean_db", "with_request_context")
class TestResourceNew(object):
    def test_manage_dataset_resource_listing_page(self, app, user):
        env = {"Authorization": user["token"]}
        organization = factories.Organization(user=user)
        dataset = factories.Dataset(owner_org=organization["id"])
        resource = factories.Resource(package_id=dataset["id"])
        response = app.get(
            url_for("dataset.resources", id=dataset["name"]),
            extra_environ=env
            )
        assert resource["name"] in response
        assert resource["description"][:60].split("\n")[0] in response
        assert resource["format"] in response

    def test_unauth_user_cannot_view_manage_dataset_resource_listing_page(
        self, app, user
    ):
        env = {"Authorization": user["token"]}
        organization = factories.Organization(user=user)
        dataset = factories.Dataset(owner_org=organization["id"])
        resource = factories.Resource(package_id=dataset["id"])
        response = app.get(
            url_for("dataset.resources", id=dataset["name"]),
            extra_environ=env
            )
        assert resource["name"] in response
        assert resource["description"][:60].split("\n")[0] in response
        assert resource["format"] in response

    def test_404_on_manage_dataset_resource_listing_page_that_does_not_exist(
        self, app, user
    ):
        env = {"Authorization": user["token"]}
        response = app.get(
            url_for("dataset.resources", id="does-not-exist"),
            extra_environ=env
            )
        assert 404 == response.status_code

    def test_add_new_resource_with_link_and_download(self, app, user):
        dataset = factories.Dataset()
        env = {"Authorization": user["token"]}
        response = app.post(
            url_for(
                "{}_resource.new".format(dataset["type"]), id=dataset["id"]
            ),
            extra_environ=env,
            data={
                "id": "",
                "url": "http://test.com/",
                "save": "go-dataset-complete"
            }
        )
        result = helpers.call_action("package_show", id=dataset["id"])
        response = app.get(
            url_for(
                "{}_resource.download".format(dataset["type"]),
                id=dataset["id"],
                resource_id=result["resources"][0]["id"],
            ),
            extra_environ=env,
            follow_redirects=False
        )
        assert 302 == response.status_code

    def test_editor_can_add_new_resource(self, app, user):
        env = {"Authorization": user["token"]}
        organization = factories.Organization(
            users=[{"name": user["name"], "capacity": "editor"}]
        )
        dataset = factories.Dataset(owner_org=organization["id"])

        app.post(
            url_for(
                "{}_resource.new".format(dataset["type"]), id=dataset["id"]
            ),
            extra_environ=env,
            data={
                "id": "",
                "name": "test resource",
                "url": "http://test.com/",
                "save": "go-dataset-complete"
            }
        )
        result = helpers.call_action("package_show", id=dataset["id"])
        assert 1 == len(result["resources"])
        assert u"test resource" == result["resources"][0]["name"]

    def test_admin_can_add_new_resource(self, app, user):
        env = {"Authorization": user["token"]}
        organization = factories.Organization(
            users=[{"name": user["name"], "capacity": "admin"}]
        )
        dataset = factories.Dataset(owner_org=organization["id"])

        app.post(
            url_for(
                "{}_resource.new".format(dataset["type"]), id=dataset["id"]
            ),
            extra_environ=env,
            data={
                "id": "",
                "name": "test resource",
                "url": "http://test.com/",
                "save": "go-dataset-complete"
            }
        )
        result = helpers.call_action("package_show", id=dataset["id"])
        assert 1 == len(result["resources"])
        assert u"test resource" == result["resources"][0]["name"]

    def test_member_cannot_add_new_resource(self, app, user):
        env = {"Authorization": user["token"]}
        organization = factories.Organization(
            users=[{"name": user["name"], "capacity": "member"}]
        )
        dataset = factories.Dataset(owner_org=organization["id"])

        app.get(
            url_for(
                "{}_resource.new".format(dataset["type"]), id=dataset["id"]
            ),
            extra_environ=env,
            status=403,
        )

        app.post(
            url_for(
                "{}_resource.new".format(dataset["type"]), id=dataset["id"]
            ),
            extra_environ=env,
            data={"name": "test", "url": "test", "save": "save", "id": ""},
            status=403,
        )

    def test_non_organization_users_cannot_add_new_resource(self, app, user):
        """on an owned dataset"""
        organization = factories.Organization()
        dataset = factories.Dataset(owner_org=organization["id"])
        env = {"Authorization": user["token"]}
        app.get(
            url_for(
                "{}_resource.new".format(dataset["type"]), id=dataset["id"]
            ),
            extra_environ=env,
            status=403,
        )

        app.post(
            url_for(
                "{}_resource.new".format(dataset["type"]), id=dataset["id"]
            ),
            extra_environ=env,
            data={"name": "test", "url": "test", "save": "save", "id": ""},
            status=403,
        )

    def test_anonymous_users_cannot_add_new_resource(self, app):
        organization = factories.Organization()
        dataset = factories.Dataset(owner_org=organization["id"])

        app.get(
            url_for(
                "{}_resource.new".format(dataset["type"]), id=dataset["id"]
            ), status=403
        )

        app.post(
            url_for(
                "{}_resource.new".format(dataset["type"]), id=dataset["id"]
            ),
            data={"name": "test", "url": "test", "save": "save", "id": ""},
            status=403
        )

    def test_anonymous_users_cannot_edit_resource(self, app):
        organization = factories.Organization()
        dataset = factories.Dataset(owner_org=organization["id"])
        resource = factories.Resource(package_id=dataset["id"])

        with app.flask_app.test_request_context():
            app.get(
                url_for(
                    "{}_resource.edit".format(dataset["type"]),
                    id=dataset["id"],
                    resource_id=resource["id"],
                ),
                status=403,
            )

            app.post(
                url_for(
                    "{}_resource.edit".format(dataset["type"]),
                    id=dataset["id"],
                    resource_id=resource["id"],
                ),
                data={"name": "test", "url": "test", "save": "save", "id": ""},
                status=403,
            )


@pytest.mark.usefixtures("non_clean_db", "with_plugins", "with_request_context")
class TestResourceDownload(object):

    def test_resource_download_content_type(self, create_with_upload, app):

        dataset = factories.Dataset()
        resource = create_with_upload(
            u"hello,world", u"file.csv",
            package_id=dataset[u"id"]
        )

        assert resource[u"mimetype"] == u"text/csv"
        url = url_for(
            u"{}_resource.download".format(dataset[u"type"]),
            id=dataset[u"id"],
            resource_id=resource[u"id"],
        )

        response = app.get(url)

        assert response.headers[u"Content-Type"] == u"text/csv"


@pytest.mark.ckan_config("ckan.plugins", "image_view")
@pytest.mark.usefixtures("non_clean_db", "with_plugins", "with_request_context")
class TestResourceView(object):
    def test_resource_view_create(self, app):
        user = factories.User()
        owner_org = factories.Organization(
            users=[{"name": user["name"], "capacity": "admin"}]
        )
        dataset = factories.Dataset(owner_org=owner_org["id"])
        resource = factories.Resource(package_id=dataset["id"])

        url = url_for(
            "resource.edit_view",
            id=resource["package_id"],
            resource_id=resource["id"],
            view_type="image_view",
        )

        response = app.post(
            url,
            environ_overrides={"REMOTE_USER": user["name"]},
            data={"title": "Test Image View"}
        )
        assert helpers.body_contains(response, "Test Image View")

    def test_resource_view_edit(self, app):
        user = factories.User()
        owner_org = factories.Organization(
            users=[{"name": user["name"], "capacity": "admin"}]
        )
        dataset = factories.Dataset(owner_org=owner_org["id"])
        resource = factories.Resource(package_id=dataset["id"])

        resource_view = factories.ResourceView(resource_id=resource["id"])
        url = url_for(
            "resource.edit_view",
            id=resource_view["package_id"],
            resource_id=resource_view["resource_id"],
            view_id=resource_view["id"],
        )

        response = app.post(
            url,
            environ_overrides={"REMOTE_USER": user["name"]},
            data={"title": "Updated RV Title"}
        )
        assert helpers.body_contains(response, "Updated RV Title")

    @pytest.mark.ckan_config("ckan.views.default_views", "")
    def test_resource_view_delete(self, app):
        user = factories.User()
        owner_org = factories.Organization(
            users=[{"name": user["name"], "capacity": "admin"}]
        )
        dataset = factories.Dataset(owner_org=owner_org["id"])
        resource = factories.Resource(package_id=dataset["id"])

        resource_view = factories.ResourceView(resource_id=resource["id"])
        url = url_for(
            "resource.edit_view",
            id=resource_view["package_id"],
            resource_id=resource_view["resource_id"],
            view_id=resource_view["id"],
        )

        response = app.post(
            url,
            environ_overrides={"REMOTE_USER": user["name"]},
            data={"delete": "Delete"}
        )
        assert helpers.body_contains(response, "This resource has no views")

    def test_existent_resource_view_page_returns_ok_code(self, app):
        resource_view = factories.ResourceView()

        url = url_for(
            "resource.read",
            id=resource_view["package_id"],
            resource_id=resource_view["resource_id"],
            view_id=resource_view["id"],
        )

        app.get(url, status=200)

    def test_inexistent_resource_view_page_returns_not_found_code(self, app):
        resource_view = factories.ResourceView()

        url = url_for(
            "resource.read",
            id=resource_view["package_id"],
            resource_id=resource_view["resource_id"],
            view_id="inexistent-view-id",
        )

        app.get(url, status=404)

    def test_resource_view_description_is_rendered_as_markdown(self, app):
        resource_view = factories.ResourceView(description="Some **Markdown**")
        url = url_for(
            "resource.read",
            id=resource_view["package_id"],
            resource_id=resource_view["resource_id"],
            view_id=resource_view["id"],
        )
        response = app.get(url)
        assert helpers.body_contains(response, "Some <strong>Markdown</strong>")


@pytest.mark.usefixtures("non_clean_db", "with_request_context")
class TestResourceRead(object):
    def test_existing_resource_with_not_associated_dataset(self, app):

        dataset = factories.Dataset()
        resource = factories.Resource()

        url = url_for(
            "{}_resource.read".format(dataset["type"]),
            id=dataset["id"], resource_id=resource["id"]
        )

        app.get(url, status=404)

    def test_resource_read_logged_in_user(self, app, user):
        """
        A logged-in user can view resource page.
        """
        dataset = factories.Dataset()
        resource = factories.Resource(package_id=dataset["id"])

        url = url_for(
            "{}_resource.read".format(dataset["type"]),
            id=dataset["id"], resource_id=resource["id"]
        )
        env = {"Authorization": user["token"]}
        app.get(url, extra_environ=env, status=200)

    def test_resource_read_anon_user(self, app):
        """
        An anon user can view resource page.
        """
        dataset = factories.Dataset()
        resource = factories.Resource(package_id=dataset["id"])

        url = url_for(
            "{}_resource.read".format(dataset["type"]),
            id=dataset["id"], resource_id=resource["id"]
        )

        app.get(url, status=200)

    def test_resource_read_sysadmin(self, app, sysadmin):
        """
        A sysadmin can view resource page.
        """
        dataset = factories.Dataset()
        resource = factories.Resource(package_id=dataset["id"])

        url = url_for(
            "{}_resource.read".format(dataset["type"]),
            id=dataset["id"], resource_id=resource["id"]
        )
        env = {"Authorization": sysadmin["token"]}
        app.get(url, extra_environ=env, status=200)

    def test_user_not_in_organization_cannot_see_private_dataset(self, app, user):
        organization = factories.Organization()
        dataset = factories.Dataset(owner_org=organization["id"], private=True)
        resource = factories.Resource(package_id=dataset["id"])

        url = url_for(
            "{}_resource.read".format(dataset["type"]),
            id=dataset["id"], resource_id=resource["id"]
        )
        env = {"Authorization": user["token"]}
        app.get(url, extra_environ=env, status=404)

    def test_organization_members_can_read_resources_in_private_datasets(
        self, app
    ):
        members = {
            "member": factories.User(password="correct123"),
            "editor": factories.User(password="correct123"),
            "admin": factories.User(password="correct123"),
            "sysadmin": factories.Sysadmin(password="correct123"),
        }
        organization = factories.Organization(
            users=[
                {"name": members["member"]["id"], "capacity": "member"},
                {"name": members["editor"]["id"], "capacity": "editor"},
                {"name": members["admin"]["id"], "capacity": "admin"},
            ]
        )
        dataset = factories.Dataset(owner_org=organization["id"], private=True)
        resource = factories.Resource(package_id=dataset["id"])

        for _, user_dict in members.items():
            user_token = factories.APIToken(user=user_dict["name"])
            env = {"Authorization": user_token["token"]}
            response = app.get(
                url_for(
                    "{}_resource.read".format(dataset["type"]),
                    id=dataset["name"],
                    resource_id=resource["id"],
                ),
                extra_environ=env
            )
            assert resource["description"][:60].split("\n")[0] in response.body

    def test_anonymous_users_cannot_see_resources_in_private_datasets(self, app):
        organization = factories.Organization()
        dataset = factories.Dataset(owner_org=organization["id"], private=True)
        resource = factories.Resource(package_id=dataset["id"])
        response = app.get(
            url_for("{}_resource.read".format(dataset["type"]),
                    id=dataset["id"], resource_id=resource['id']),
            status=404
        )
        assert 404 == response.status_code

    # Test the 'reveal_private_datasets' flag

    @pytest.mark.ckan_config("ckan.auth.reveal_private_datasets", "True")
    def test_user_not_in_organization_cannot_read_resources_in_private_dataset(self, app, user):
        organization = factories.Organization()
        dataset = factories.Dataset(owner_org=organization["id"], private=True)
        resource = factories.Resource(package_id=dataset["id"])

        url = url_for(
            "{}_resource.read".format(dataset["type"]),
            id=dataset["id"], resource_id=resource["id"]
        )
        env = {"Authorization": user["token"]}
        app.get(url, extra_environ=env, status=403)

    @pytest.mark.ckan_config("ckan.auth.reveal_private_datasets", "True")
    def test_anonymous_users_cannot_read_resources_in_private_dataset(self, app):
        organization = factories.Organization()
        dataset = factories.Dataset(owner_org=organization["id"], private=True)
        resource = factories.Resource(package_id=dataset["id"])
        response = app.get(
            url_for("{}_resource.read".format(dataset["type"]),
                    id=dataset["id"], resource_id=resource['id']),
            follow_redirects=False
        )
        assert 302 == response.status_code
        assert '/login' in response.headers[u"Location"]


@pytest.mark.usefixtures("non_clean_db", "with_request_context")
class TestResourceDelete(object):
    def test_dataset_owners_can_delete_resources(self, app, user):
        env = {"Authorization": user["token"]}
        owner_org = factories.Organization(
            users=[{"name": user["name"], "capacity": "admin"}]
        )
        dataset = factories.Dataset(owner_org=owner_org["id"])
        resource = factories.Resource(package_id=dataset["id"])
        response = app.post(
            url_for(
                "{}_resource.delete".format(dataset["type"]),
                id=dataset["name"],
                resource_id=resource["id"],
            ),
            extra_environ=env
        )
        assert 200 == response.status_code
        assert helpers.body_contains(response, "This dataset has no data")

        with pytest.raises(logic.NotFound):
            helpers.call_action("resource_show", id=resource["id"])

    def test_deleting_non_existing_resource_404s(self, app, user):
        env = {"Authorization": user["token"]}
        owner_org = factories.Organization(
            users=[{"name": user["name"], "capacity": "admin"}]
        )
        dataset = factories.Dataset(owner_org=owner_org["id"])
        response = app.post(
            url_for(
                "{}_resource.delete".format(dataset["type"]),
                id=dataset["name"],
                resource_id="doesnotexist",
            ),
            extra_environ=env
        )
        assert 404 == response.status_code

    def test_anon_users_cannot_delete_owned_resources(self, app):
        user = factories.User()
        owner_org = factories.Organization(
            users=[{"name": user["id"], "capacity": "admin"}]
        )
        dataset = factories.Dataset(owner_org=owner_org["id"])
        resource = factories.Resource(package_id=dataset["id"])

        app.post(
            url_for(
                "{}_resource.delete".format(dataset["type"]),
                id=dataset["name"],
                resource_id=resource["id"],
            ),
            status=403,
        )

    def test_logged_in_users_cannot_delete_resources_they_do_not_own(
        self, app, user
    ):
        # setup our dataset
        owner = factories.User()
        owner_org = factories.Organization(
            users=[{"name": owner["id"], "capacity": "admin"}]
        )
        dataset = factories.Dataset(owner_org=owner_org["id"])
        resource = factories.Resource(package_id=dataset["id"])

        # access as another user
        env = {"Authorization": user["token"]}
        response = app.post(
            url_for(
                "{}_resource.delete".format(dataset["type"]),
                id=dataset["name"],
                resource_id=resource["id"],
            ),
            extra_environ=env
        )
        assert 403 == response.status_code
        assert helpers.body_contains(response, "Unauthorized to delete package")

    def test_sysadmins_can_delete_any_resource(self, app, sysadmin):
        owner_org = factories.Organization()
        dataset = factories.Dataset(owner_org=owner_org["id"])
        resource = factories.Resource(package_id=dataset["id"])
        env = {"Authorization": sysadmin["token"]}
        response = app.post(
            url_for(
                "{}_resource.delete".format(dataset["type"]),
                id=dataset["name"],
                resource_id=resource["id"],
            ),
            extra_environ=env
        )
        assert 200 == response.status_code
        assert helpers.body_contains(response, "This dataset has no data")

        with pytest.raises(logic.NotFound):
            helpers.call_action("resource_show", id=resource["id"])

    def test_confirm_and_cancel_deleting_a_resource(self, app):
        """Test confirmation of deleting resources

        When resource_delete is made as a get request, it should return a
        'do you want to delete this reource? confirmation page"""
        user = factories.User()
        owner_org = factories.Organization(
            users=[{"name": user["name"], "capacity": "admin"}]
        )
        dataset = factories.Dataset(owner_org=owner_org["id"])
        resource = factories.Resource(package_id=dataset["id"])
        response = app.get(
            url_for(
                "{}_resource.delete".format(dataset["type"]),
                id=dataset["name"],
                resource_id=resource["id"],
            ),
            environ_overrides={"REMOTE_USER": user["name"]},
        )
        assert 200 == response.status_code
        message = "Are you sure you want to delete resource - {name}?"
        assert helpers.body_contains(response, message.format(name=resource["name"]))

        response = app.post(
            url_for(
                "{}_resource.delete".format(dataset["type"]),
                id=dataset["name"],
                resource_id=resource["id"],
            ),
            environ_overrides={"REMOTE_USER": user["name"]},
            data={"cancel": ""},
        )
        assert 200 == response.status_code


@pytest.mark.usefixtures("clean_db", "clean_index", "with_request_context")
class TestSearch(object):
    def test_search_basic(self, app):
        dataset1 = factories.Dataset()

        offset = url_for("dataset.search")
        page = app.get(offset)

        assert helpers.body_contains(page, dataset1["name"])

    def test_search_language_toggle(self, app):
        dataset1 = factories.Dataset()

        with app.flask_app.test_request_context():
            offset = url_for("dataset.search", q=dataset1["name"])
        page = app.get(offset)

        assert helpers.body_contains(page, dataset1["name"])
        assert helpers.body_contains(page, "q=" + dataset1["name"])

    def test_search_sort_by_blank(self, app):
        factories.Dataset()

        # ?sort has caused an exception in the past
        offset = url_for("dataset.search") + "?sort"
        app.get(offset)

    def test_search_sort_by_bad(self, app):
        factories.Dataset()

        # bad spiders try all sorts of invalid values for sort. They should get
        # a 400 error with specific error message. No need to alert the
        # administrator.
        offset = url_for("dataset.search") + "?sort=gvgyr_fgevat+nfp"
        response = app.get(offset)
        if response.status == 200:
            import sys

            sys.stdout.write(response.body)
            raise Exception(
                "Solr returned an unknown error message. "
                "Please check the error handling "
                "in ckan/lib/search/query.py:run"
            )

    def test_search_solr_syntax_error(self, app):
        factories.Dataset()

        # SOLR raises SyntaxError when it can't parse q (or other fields?).
        # Whilst this could be due to a bad user input, it could also be
        # because CKAN mangled things somehow and therefore we flag it up to
        # the administrator and give a meaningless error, just in case
        offset = url_for("dataset.search") + "?q=--included"
        search_response = app.get(offset)

        search_response_html = BeautifulSoup(search_response.data)
        err_msg = search_response_html.select("#search-error")
        err_msg = "".join([n.text for n in err_msg])
        assert "error while searching" in err_msg

    def test_search_plugin_hooks(self, app):
        with p.use_plugin("test_package_controller_plugin") as plugin:

            offset = url_for("dataset.search")
            app.get(offset)

            # get redirected ...
            assert plugin.calls["before_dataset_search"] == 1, plugin.calls
            assert plugin.calls["after_dataset_search"] == 1, plugin.calls

    def test_search_page_request(self, app):
        """Requesting package search page returns list of datasets."""

        factories.Dataset(name="dataset-one", title="Dataset One")
        factories.Dataset(name="dataset-two", title="Dataset Two")
        factories.Dataset(name="dataset-three", title="Dataset Three")

        search_url = url_for("dataset.search")
        search_response = app.get(search_url)

        assert "3 datasets found" in search_response

        search_response_html = BeautifulSoup(search_response.data)
        ds_titles = search_response_html.select(
            ".dataset-list " ".dataset-item " ".dataset-heading a"
        )
        ds_titles = [n.string.strip() for n in ds_titles]

        assert len(ds_titles) == 3
        assert "Dataset One" in ds_titles
        assert "Dataset Two" in ds_titles
        assert "Dataset Three" in ds_titles

    def test_search_page_results(self, app):
        """Searching for datasets returns expected results."""

        factories.Dataset(name="dataset-one", title="Dataset One")
        factories.Dataset(name="dataset-two", title="Dataset Two")
        factories.Dataset(name="dataset-three", title="Dataset Three")

        search_url = url_for("dataset.search")
        search_results = app.get(search_url, query_string={'q': 'One'})

        assert "1 dataset found" in search_results

        search_response_html = BeautifulSoup(search_results.data)
        ds_titles = search_response_html.select(
            ".dataset-list " ".dataset-item " ".dataset-heading a"
        )
        ds_titles = [n.string.strip() for n in ds_titles]

        assert len(ds_titles) == 1
        assert "Dataset One" in ds_titles

    @pytest.mark.ckan_config('ckan.datasets_per_page', 1)
    def test_repeatable_params(self, app):
        """Searching for datasets returns expected results."""

        factories.Dataset(name="dataset-one", title="Test Dataset One")
        factories.Dataset(name="dataset-two", title="Test Dataset Two")

        search_url = url_for("dataset.search", title=['Test', 'Dataset'])
        search_results = app.get(search_url)
        html = BeautifulSoup(search_results.data)
        links = html.select('.pagination a')
        # first, second and "Next" pages
        assert len(links) == 3

        params = [set(urlparse(a['href']).query.split('&')) for a in links]
        for group in params:
            assert 'title=Test' in group
            assert 'title=Dataset' in group

    def test_search_page_no_results(self, app):
        """Search with non-returning phrase returns no results."""

        factories.Dataset(name="dataset-one", title="Dataset One")
        factories.Dataset(name="dataset-two", title="Dataset Two")
        factories.Dataset(name="dataset-three", title="Dataset Three")

        search_url = url_for("dataset.search")
        search_results = app.get(search_url, query_string={'q': 'Nout'})

        assert 'No datasets found for "Nout"' in search_results

        search_response_html = BeautifulSoup(search_results.data)
        ds_titles = search_response_html.select(
            ".dataset-list " ".dataset-item " ".dataset-heading a"
        )
        ds_titles = [n.string for n in ds_titles]

        assert len(ds_titles) == 0

    def test_search_page_results_tag(self, app):
        """Searching with a tag returns expected results."""

        factories.Dataset(
            name="dataset-one", title="Dataset One", tags=[{"name": "my-tag"}]
        )
        factories.Dataset(name="dataset-two", title="Dataset Two")
        factories.Dataset(name="dataset-three", title="Dataset Three")

        search_url = url_for("dataset.search")
        search_response = app.get(search_url)
        assert "/dataset/?tags=my-tag" in search_response

        tag_search_response = app.get("/dataset?tags=my-tag")

        assert "1 dataset found" in tag_search_response

        search_response_html = BeautifulSoup(tag_search_response.data)
        ds_titles = search_response_html.select(
            ".dataset-list " ".dataset-item " ".dataset-heading a"
        )
        ds_titles = [n.string.strip() for n in ds_titles]

        assert len(ds_titles) == 1
        assert "Dataset One" in ds_titles

    def test_search_page_results_tags(self, app):
        """Searching with a tag returns expected results with multiple tags"""

        factories.Dataset(
            name="dataset-one",
            title="Dataset One",
            tags=[
                {"name": "my-tag-1"},
                {"name": "my-tag-2"},
                {"name": "my-tag-3"},
            ],
        )
        factories.Dataset(name="dataset-two", title="Dataset Two")
        factories.Dataset(name="dataset-three", title="Dataset Three")

        params = "/dataset/?tags=my-tag-1&tags=my-tag-2&tags=my-tag-3"
        tag_search_response = app.get(params)

        assert "1 dataset found" in tag_search_response

        search_response_html = BeautifulSoup(tag_search_response.data)
        ds_titles = search_response_html.select(".filtered")
        assert len(ds_titles) == 3

    def test_search_page_results_private(self, app):
        """Private datasets don't show up in dataset search results."""
        org = factories.Organization()

        factories.Dataset(
            name="dataset-one",
            title="Dataset One",
            owner_org=org["id"],
            private=True,
        )
        factories.Dataset(name="dataset-two", title="Dataset Two")
        factories.Dataset(name="dataset-three", title="Dataset Three")

        search_url = url_for("dataset.search")
        search_response = app.get(search_url)

        search_response_html = BeautifulSoup(search_response.data)
        ds_titles = search_response_html.select(
            ".dataset-list " ".dataset-item " ".dataset-heading a"
        )
        ds_titles = [n.string.strip() for n in ds_titles]

        assert len(ds_titles) == 2
        assert "Dataset One" not in ds_titles
        assert "Dataset Two" in ds_titles
        assert "Dataset Three" in ds_titles

    def test_user_not_in_organization_cannot_search_private_datasets(
        self, app, user
    ):

        organization = factories.Organization()
        factories.Dataset(owner_org=organization["id"], private=True)
        search_url = url_for("dataset.search")
        env = {"Authorization": user["token"]}
        search_response = app.get(search_url, extra_environ=env)

        search_response_html = BeautifulSoup(search_response.data)
        ds_titles = search_response_html.select(
            ".dataset-list " ".dataset-item " ".dataset-heading a"
        )
        assert [n.string for n in ds_titles] == []

    def test_user_in_organization_can_search_private_datasets(self, app, user):
        env = {"Authorization": user["token"]}
        organization = factories.Organization(
            users=[{"name": user["name"], "capacity": "member"}]
        )
        factories.Dataset(
            title="A private dataset",
            owner_org=organization["id"],
            private=True,
        )
        search_url = url_for("dataset.search")
        search_response = app.get(search_url, extra_environ=env)

        search_response_html = BeautifulSoup(search_response.data)
        ds_titles = search_response_html.select(
            ".dataset-list " ".dataset-item " ".dataset-heading a"
        )
        assert [n.string.strip() for n in ds_titles] == ["A private dataset"]

    def test_user_in_different_organization_cannot_search_private_datasets(
        self, app, user
    ):
        env = {"Authorization": user["token"]}
        factories.Organization(
            users=[{"name": user["name"], "capacity": "member"}]
        )
        org2 = factories.Organization()
        factories.Dataset(
            title="A private dataset", owner_org=org2["id"], private=True
        )
        search_url = url_for("dataset.search")
        search_response = app.get(search_url, extra_environ=env)

        search_response_html = BeautifulSoup(search_response.data)
        ds_titles = search_response_html.select(
            ".dataset-list " ".dataset-item " ".dataset-heading a"
        )
        assert [n.string for n in ds_titles] == []

    @pytest.mark.ckan_config("ckan.search.default_include_private", "false")
    def test_search_default_include_private_false(self, app, user):
        env = {"Authorization": user["token"]}
        organization = factories.Organization(
            users=[{"name": user["name"], "capacity": "member"}]
        )
        factories.Dataset(owner_org=organization["id"], private=True)
        search_url = url_for("dataset.search")
        search_response = app.get(search_url, extra_environ=env)

        search_response_html = BeautifulSoup(search_response.data)
        ds_titles = search_response_html.select(
            ".dataset-list " ".dataset-item " ".dataset-heading a"
        )
        assert [n.string for n in ds_titles] == []

    def test_sysadmin_can_search_private_datasets(self, app, sysadmin):
        organization = factories.Organization()
        factories.Dataset(
            title="A private dataset",
            owner_org=organization["id"],
            private=True,
        )
        search_url = url_for("dataset.search")
        env = {"Authorization": sysadmin["token"]}
        search_response = app.get(search_url, extra_environ=env)

        search_response_html = BeautifulSoup(search_response.data)
        ds_titles = search_response_html.select(
            ".dataset-list " ".dataset-item " ".dataset-heading a"
        )
        assert [n.string.strip() for n in ds_titles] == ["A private dataset"]

    def test_search_with_extra_params(self, app):
        url = url_for('dataset.search')
        url += '?ext_a=1&ext_a=2&ext_b=3'
        search_result = {
            'count': 0,
            'sort': "score desc, metadata_modified desc",
            'facets': {},
            'search_facets': {},
            'results': []
        }
        search = mock.Mock(return_value=search_result)
        logic._actions['package_search'] = search
        app.get(url)
        search.assert_called()
        extras = search.call_args[0][1]['extras']
        assert extras == {'ext_a': ['1', '2'], 'ext_b': '3'}


@pytest.mark.usefixtures("non_clean_db", "with_request_context")
class TestPackageFollow(object):
    def test_package_follow(self, app, user):

        package = factories.Dataset()

        follow_url = url_for("dataset.follow", id=package["id"])
        env = {"Authorization": user["token"]}
        response = app.post(follow_url, extra_environ=env)
        assert "You are now following {0}".format(package["title"]) in response

    def test_package_follow_not_exist(self, app, user):
        """Pass an id for a package that doesn't exist"""
        env = {"Authorization": user["token"]}
        follow_url = url_for("dataset.follow", id="not-here")
        response = app.post(follow_url, extra_environ=env)

        assert "Dataset not found" in response

    def test_package_unfollow(self, app, user):

        package = factories.Dataset()
        env = {"Authorization": user["token"]}
        follow_url = url_for("dataset.follow", id=package["id"])
        app.post(follow_url, extra_environ=env)

        unfollow_url = url_for("dataset.unfollow", id=package["id"])
        unfollow_response = app.post(unfollow_url, extra_environ=env)

        assert (
            "You are no longer following {0}".format(package["title"])
            in unfollow_response
        )

    def test_package_unfollow_not_following(self, app, user):
        """Unfollow a package not currently following"""

        package = factories.Dataset()
        env = {"Authorization": user["token"]}
        unfollow_url = url_for("dataset.unfollow", id=package["id"])
        unfollow_response = app.post(unfollow_url, extra_environ=env)

        assert (
            "You are not following {0}".format(package["id"])
            in unfollow_response
        )

    def test_package_unfollow_not_exist(self, app, user):
        """Unfollow a package that doesn't exist."""
        env = {"Authorization": user["token"]}
        unfollow_url = url_for("dataset.unfollow", id="not-here")
        unfollow_response = app.post(unfollow_url, extra_environ=env)
        assert "Dataset not found" in unfollow_response

    def test_package_follower_list(self, app, sysadmin):
        """Following users appear on followers list page."""
        env = {"Authorization": sysadmin["token"]}
        package = factories.Dataset()

        follow_url = url_for("dataset.follow", id=package["id"])
        app.post(follow_url, extra_environ=env)

        followers_url = url_for("dataset.followers", id=package["id"])

        # Only sysadmins can view the followers list pages
        followers_response = app.get(followers_url, extra_environ=env, status=200)
        assert sysadmin["display_name"] in followers_response


@pytest.mark.usefixtures("non_clean_db", "with_request_context")
class TestDatasetRead(object):
    def test_dataset_read(self, app):

        dataset = factories.Dataset()

        url = url_for("dataset.read", id=dataset["name"])
        response = app.get(url)
        assert dataset["title"] in response

    def test_redirect_when_given_id(self, app):
        dataset = factories.Dataset()
        response = app.get(
            url_for("dataset.read", id=dataset["id"]),
            follow_redirects=False
        )
        # redirect replaces the ID with the name in the URL
        expected_url = url_for("dataset.read", id=dataset["name"], _external=True)
        assert response.headers['location'] == expected_url

    def test_no_redirect_loop_when_name_is_the_same_as_the_id(self, app):
        dataset = factories.Dataset(id="abc", name="abc")
        app.get(
            url_for("dataset.read", id=dataset["id"]), status=200
        )  # ie no redirect


@pytest.mark.usefixtures('non_clean_db', 'with_request_context')
class TestCollaborators(object):

    def test_collaborators_tab_not_shown(self, app, sysadmin):
        dataset = factories.Dataset()
        env = {"Authorization": sysadmin["token"]}
        response = app.get(
            url_for('dataset.edit', id=dataset['name']),
            extra_environ=env
            )
        assert 'Collaborators' not in response

        # Route not registered
        with pytest.raises(BuildError):
            url_for('dataset.collaborators_read', id=dataset['name'])
        app.get(
            '/dataset/collaborators/{}'.format(dataset['name']), status=404)

    @pytest.mark.ckan_config('ckan.auth.allow_dataset_collaborators', 'true')
    def test_collaborators_tab_shown(self, app, sysadmin):
        dataset = factories.Dataset()
        env = {"Authorization": sysadmin["token"]}
        response = app.get(
            url_for('dataset.edit', id=dataset['name']),
            extra_environ=env
            )
        assert 'Collaborators' in response

        # Route registered
        url = url_for('dataset.collaborators_read', id=dataset['name'])
        app.get(url,  extra_environ=env)

    @pytest.mark.ckan_config('ckan.auth.allow_dataset_collaborators', 'true')
    def test_collaborators_no_admins_by_default(self, app, sysadmin):
        dataset = factories.Dataset()
        env = {"Authorization": sysadmin["token"]}
        url = url_for('dataset.new_collaborator', id=dataset['name'])
        response = app.get(url, extra_environ=env)

        assert '<option value="admin">' not in response

    @pytest.mark.ckan_config('ckan.auth.allow_dataset_collaborators', 'true')
    @pytest.mark.ckan_config('ckan.auth.allow_admin_collaborators', 'true')
    def test_collaborators_admins_enabled(self, app, sysadmin):
        dataset = factories.Dataset()
        env = {"Authorization": sysadmin["token"]}
        url = url_for('dataset.new_collaborator', id=dataset['name'])
        response = app.get(url, extra_environ=env)

        assert '<option value="admin">' in response


@pytest.mark.usefixtures('clean_db', 'with_request_context')
class TestResourceListing(object):
    def test_resource_listing_premissions_sysadmin(self, app, sysadmin):
        org = factories.Organization()
        pkg = factories.Dataset(owner_org=org["id"])
        env = {"Authorization": sysadmin["token"]}
        app.get(
            url_for("dataset.resources", id=pkg["name"]),
            extra_environ=env,
            status=200)

    def test_resource_listing_premissions_auth_user(self, app, user):
        env = {"Authorization": user["token"]}
        org = factories.Organization(user=user)
        pkg = factories.Dataset(owner_org=org["id"])

        app.get(
            url_for("dataset.resources", id=pkg["name"]),
            extra_environ=env,
            status=200)

    def test_resource_listing_premissions_non_auth_user(self, app, user):
        org = factories.Organization()
        pkg = factories.Dataset(owner_org=org["id"])
        env = {"Authorization": user["token"]}
        app.get(
            url_for("dataset.resources", id=pkg["name"]),
            extra_environ=env,
            status=403)

    def test_resource_listing_premissions_not_logged_in(self, app):
        pkg = factories.Dataset()
        url = url_for("dataset.resources", id=pkg["name"])
        app.get(url, status=403)


@pytest.mark.usefixtures('clean_db', 'with_request_context')
class TestNonActivePackages:
    def test_read(self, app):
        pkg = factories.Dataset(state="deleted")
        url = url_for("dataset.read", id=pkg["name"])
        app.get(url, status=404)

    def test_read_as_admin(self, app, sysadmin):
        pkg = factories.Dataset(state="deleted")
        url = url_for("dataset.read", id=pkg["name"])
        env = {"Authorization": sysadmin["token"]}
        app.get(url, extra_environ=env, status=200)


@pytest.mark.usefixtures("clean_db", "clean_index")
class TestReadOnly(object):
    def test_read_nonexistentpackage(self, app):
        name = "anonexistentpackage"
        url = url_for("dataset.read", id=name)
        app.get(url, status=404)

    def test_read_internal_links(self, app):
        pkg = factories.Dataset(
            notes="Decoy link here: decoy:decoy, real links here: dataset:pkg-1, "
            "tag:tag_1 group:test-group-1 and a multi-word tag: tag:\"multi word with punctuation.\"",)
        res = app.get(url_for("dataset.read", id=pkg["name"]))
        page = BeautifulSoup(res.data)
        link = page.body.find("a", text="dataset:pkg-1")
        assert link
        assert link["href"] == "/dataset/pkg-1"

        link = page.body.find("a", text="group:test-group-1")
        assert link
        assert link["href"] == "/group/test-group-1"
        assert "decoy</a>" not in res, res
        assert 'decoy"' not in res, res

    @pytest.mark.ckan_config("ckan.plugins", "test_package_controller_plugin")
    @pytest.mark.usefixtures("with_plugins")
    def test_read_plugin_hook(self, app):
        pkg = factories.Dataset()
        plugin = p.get_plugin("test_package_controller_plugin")
        plugin.calls.clear()
        app.get(url_for("dataset.read", id=pkg["name"]))
        assert plugin.calls["read"] == 1
        assert plugin.calls["after_dataset_show"] == 1
