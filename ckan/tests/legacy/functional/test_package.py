# encoding: utf-8


import pytest
from six import string_types
from ckan.common import config
from difflib import unified_diff

from ckan.tests.legacy import url_for
import ckan.tests.legacy as tests
from ckan.tests.legacy.html_check import HtmlCheckMethods
import ckan.model as model
from ckan.lib.create_test_data import CreateTestData
from ckan.logic.action import get, update
from ckan import plugins
from ckan.lib.search.common import SolrSettings
from ckan.tests.helpers import body_contains

existing_extra_html = (
    '<label class="field_opt" for="Package-%(package_id)s-extras-%(key)s">%(capitalized_key)s</label>',
    '<input id="Package-%(package_id)s-extras-%(key)s" name="Package-%(package_id)s-extras-%(key)s" size="20" type="text" value="%(value)s">',
)


class TestPackageBase(object):
    key1 = u"key1 Less-than: < Umlaut: \xfc"
    value1 = u"value1 Less-than: < Umlaut: \xfc"

    # Note: Can't put a quotation mark in key1 or value1 because
    # paste.fixture doesn't unescape the value in an input field
    # on form submission. (But it works in real life.)

    def _assert_form_errors(self, res):
        self.check_tag(res, "<form", "has-errors")
        assert "field_error" in res, res

    def diff_responses(self, res1, res2):
        return self.diff_html(res1.body, res2.body)

    def diff_html(self, html1, html2):
        return "\n".join(unified_diff(html1.split("\n"), html2.split("\n")))


class TestPackageForm(TestPackageBase):
    """Inherit this in tests for these form testing methods"""

    def _check_package_read(self, res, **params):
        assert not "Error" in res, res
        assert u"%s - Datasets" % params["title"] in res, res
        main_res = self.main_div(res)
        main_div = main_res
        main_div_str = main_div.encode("utf8")
        assert params["name"] in main_div, main_div_str
        assert params["title"] in main_div, main_div_str
        assert params["version"] in main_div, main_div_str
        self.check_named_element(main_div, "a", 'href="%s"' % params["url"])
        prefix = "Dataset-%s-" % params.get("id", "")
        for res_index, values in self._get_resource_values(
            params["resources"], by_resource=True
        ):
            self.check_named_element(main_div, "tr", *values)
        assert params["notes"] in main_div, main_div_str
        license = model.Package.get_license_register()[params["license_id"]]
        assert license.title in main_div, (license.title, main_div_str)
        tag_names = list(params["tags"])
        self.check_named_element(main_div, "ul", *tag_names)
        if "state" in params:
            assert "State: %s" % params["state"] in main_div.replace(
                "</strong>", ""
            ), main_div_str
        if isinstance(params["extras"], dict):
            extras = []
            for key, value in params["extras"].items():
                extras.append((key, value, False))
        elif isinstance(params["extras"], (list, tuple)):
            extras = params["extras"]
        else:
            raise NotImplementedError
        for key, value, deleted in extras:
            if not deleted:
                key_in_html_body = self.escape_for_html_body(key)
                value_in_html_body = self.escape_for_html_body(value)
                self.check_named_element(
                    main_div, "tr", key_in_html_body, value_in_html_body
                )
            else:
                self.check_named_element(main_div, "tr", "!" + key)
                self.check_named_element(main_div, "tr", "!" + value)

    def _get_resource_values(self, resources, by_resource=False):
        assert isinstance(resources, (list, tuple))
        for res_index, resource in enumerate(resources):
            if by_resource:
                values = []
            for i, res_field in enumerate(
                model.Resource.get_columns(extra_columns=False)
            ):
                if isinstance(resource, string_types):
                    expected_value = resource if res_field == "url" else ""
                elif hasattr(resource, res_field):
                    expected_value = getattr(resource, res_field)
                elif isinstance(resource, (list, tuple)):
                    expected_value = resource[i]
                elif isinstance(resource, dict):
                    expected_value = resource.get(res_field, u"")
                else:
                    raise NotImplemented
                if not by_resource:
                    yield (res_index, res_field, expected_value)
                else:
                    values.append(expected_value)
            if by_resource:
                yield (res_index, values)

    def escape_for_html_body(self, unescaped_str):
        # just deal with chars in tests
        return unescaped_str.replace("<", "&lt;")

    def check_form_filled_correctly(self, res, **params):
        if "pkg" in params:
            for key, value in params["pkg"].as_dict().items():
                if key == "license":
                    key = "license_id"
                params[key] = value
        prefix = ""
        main_res = self.main_div(res)
        self.check_tag(main_res, prefix + "name", params["name"])
        self.check_tag(main_res, prefix + "title", params["title"])
        self.check_tag(main_res, prefix + "version", params["version"])
        self.check_tag(main_res, prefix + "url", params["url"])
        # for res_index, res_field, expected_value in self._get_resource_values(params['resources']):
        #    ## only check fields that are on the form
        #    if res_field not in ['url', 'id', 'description', 'hash']:
        #        continue
        #    self.check_tag(main_res, '%sresources__%i__%s' % (prefix, res_index, res_field), expected_value)
        self.check_tag_and_data(main_res, prefix + "notes", params["notes"])
        self.check_tag_and_data(main_res, "selected", params["license_id"])
        if isinstance(params["tags"], string_types):
            tags = list(map(lambda s: s.strip(), params["tags"].split(",")))
        else:
            tags = params["tags"]
        for tag in tags:
            self.check_tag(main_res, prefix + "tag_string", tag)
        if "state" in params:
            self.check_tag_and_data(main_res, "selected", str(params["state"]))
        if isinstance(params["extras"], dict):
            extras = []
            for key, value in params["extras"].items():
                extras.append((key, value, False))
        else:
            extras = params["extras"]
        for num, (key, value, deleted) in enumerate(sorted(extras)):
            key_in_html_body = self.escape_for_html_body(key)
            value_in_html_body = self.escape_for_html_body(value)
            key_escaped = key
            value_escaped = value
            self.check_tag(main_res, "extras__%s__key" % num, key_in_html_body)
            self.check_tag(main_res, "extras__%s__value" % num, value_escaped)
            if deleted:
                self.check_tag(
                    main_res, "extras__%s__deleted" % num, "checked"
                )

        assert params["log_message"] in main_res, main_res

    def _check_redirect(
        self,
        app,
        return_url_param,
        expected_redirect,
        pkg_name_to_edit="",
        extra_environ=None,
    ):
        """
        @param return_url_param - encoded url to be given as param - if None
                       then assume redirect is specified in pylons config
        @param expected_redirect - url we expect to redirect to (but <NAME>
                       not yet substituted)
        @param pkg_name_to_edit - '' means create a new dataset
        """
        try:
            new_name = u"new-name"
            offset_params = {}
            if pkg_name_to_edit:
                pkg_name = pkg_name_to_edit
                pkg = model.Package.by_name(pkg_name)
                assert pkg
                pkg_id = pkg.id
                named_route = "dataset.edit"
                offset_params["id"] = pkg_name_to_edit
            else:
                named_route = "dataset.new"
                pkg_id = ""
            if return_url_param:
                offset_params["return_to"] = return_url_param
            offset = url_for(named_route, **offset_params)
            res = app.post(offset, extra_environ=extra_environ, data={
                "name": new_name,
                "save": ""
            }, follow_redirects=False)

            assert not "Error" in res, res
            redirected_to = res.headers['location']

            expected_redirect_url = expected_redirect.replace(
                "<NAME>", new_name
            )
            assert redirected_to == expected_redirect_url, (
                "Redirected to %s but should have been %s"
                % (redirected_to, expected_redirect_url)
            )
        finally:
            # revert name change or pkg creation
            pkg = model.Package.by_name(new_name)
            if pkg:
                if pkg_name_to_edit:
                    pkg.name = pkg_name_to_edit
                else:
                    pkg.purge()
                model.repo.commit_and_remove()


class TestReadOnly(TestPackageForm, HtmlCheckMethods):
    @pytest.fixture(autouse=True)
    def initial_data(self, clean_db, clean_index):
        CreateTestData.create()

    def test_read_nonexistentpackage(self, app):
        name = "anonexistentpackage"
        offset = url_for("dataset.read", id=name)
        res = app.get(offset, status=404)

    def test_read_internal_links(self, app):
        pkg_name = (u"link-test",)
        CreateTestData.create_arbitrary(
            [
                {
                    "name": pkg_name,
                    "notes": "Decoy link here: decoy:decoy, real links here: dataset:pkg-1, "
                    'tag:tag_1 group:test-group-1 and a multi-word tag: tag:"multi word with punctuation."',
                }
            ]
        )
        offset = url_for("dataset.read", id=pkg_name)
        res = app.get(offset)

        def check_link(res, controller, id):
            id_in_uri = id.strip('"').replace(
                " ", "+"
            )  # remove quotes and percent-encode spaces
            self.check_tag_and_data(
                res,
                "a ",
                "%s/%s" % (controller, id_in_uri),
                "%s:%s" % (controller, id.replace('"', "&#34;")),
            )

        check_link(res.body, "dataset", "pkg-1")
        check_link(res.body, "group", "test-group-1")
        assert "decoy</a>" not in res, res
        assert 'decoy"' not in res, res

    @pytest.mark.ckan_config("ckan.plugins", "test_package_controller_plugin")
    @pytest.mark.usefixtures("with_plugins")
    def test_read_plugin_hook(self, app):
        plugin = plugins.get_plugin("test_package_controller_plugin")
        name = u"annakarenina"
        offset = url_for("dataset.read", id=name)
        res = app.get(offset)

        assert plugin.calls["read"] == 1, plugin.calls
        assert plugin.calls["after_show"] == 1, plugin.calls

    @pytest.mark.usefixtures("with_request_context")
    def test_resource_list(self, app):
        # TODO restore this test. It doesn't make much sense with the
        # present resource list design.
        name = "annakarenina"
        cache_url = "http://thedatahub.org/test_cache_url.csv"
        # add a cache_url to the first resource in the package
        context = {
            "model": model,
            "session": model.Session,
            "user": "testsysadmin",
        }
        data = {"id": "annakarenina"}
        pkg = get.package_show(context, data)
        pkg["resources"][0]["cache_url"] = cache_url
        # FIXME need to pretend to be called by the api
        context["api_version"] = 3
        update.package_update(context, pkg)
        # check that the cache url is included on the dataset view page
        offset = url_for("dataset.read", id=name)
        res = app.get(offset)
        # assert '[cached]'in res
        # assert cache_url in res


class TestEdit(TestPackageForm):
    editpkg_name = u"editpkgtest"

    @pytest.fixture(autouse=True)
    def initial_data(self, clean_db):
        CreateTestData.create()
        CreateTestData.create_arbitrary(
            {
                "name": self.editpkg_name,
                "url": u"editpkgurl.com",
                "tags": [u"mytesttag"],
                "resources": [
                    {
                        "url": u'url escape: & umlaut: \xfc quote: "',
                        "description": u'description escape: & umlaut: \xfc quote "',
                    }
                ],
            }
        )

        self.editpkg = model.Package.by_name(self.editpkg_name)
        self.pkgid = self.editpkg.id
        self.offset = url_for("dataset.edit", id=self.editpkg_name)

        self.editpkg = model.Package.by_name(self.editpkg_name)
        self.admin = model.User.by_name(u"testsysadmin")

        self.extra_environ_admin = {
            "REMOTE_USER": self.admin.name.encode("utf8")
        }
        self.extra_environ_russianfan = {"REMOTE_USER": "russianfan"}

    def test_redirect_after_edit_using_param(self, app):
        return_url = "http://random.site.com/dataset/<NAME>?test=param"
        # It's useful to know that this url encodes to:
        # 'http%3A%2F%2Frandom.site.com%2Fdataset%2F%3CNAME%3E%3Ftest%3Dparam'
        expected_redirect = return_url
        self._check_redirect(
            app,
            return_url,
            expected_redirect,
            pkg_name_to_edit=self.editpkg_name,
            extra_environ=self.extra_environ_admin,
        )

    def test_redirect_after_edit_using_config(self, app):
        return_url = ""  # redirect comes from test.ini setting
        expected_redirect = config["package_edit_return_url"]
        self._check_redirect(
            app,
            return_url,
            expected_redirect,
            pkg_name_to_edit=self.editpkg_name,
            extra_environ=self.extra_environ_admin,
        )

    def test_edit_404(self, app):
        self.offset = url_for("dataset.edit", id="random_name")
        app.get(self.offset, status=404)

    def test_edit_pkg_with_relationships(self, app):

        # add a relationship to a package
        pkg = model.Package.by_name(self.editpkg_name)
        anna = model.Package.by_name(u"annakarenina")
        pkg.add_relationship(u"depends_on", anna)
        model.repo.commit_and_remove()

        # check relationship before the test
        rels = model.Package.by_name(self.editpkg_name).get_relationships()
        assert (
            str(rels)
            == "[<*PackageRelationship editpkgtest depends_on annakarenina>]"
        )

        # edit the package
        self.offset = url_for("dataset.edit", id=self.editpkg_name)
        res = app.post(self.offset, extra_environ=self.extra_environ_admin, data={
            "save": "",
            "title": "New Title"
        }, follow_redirects=False)

        # check relationship still exists
        rels = model.Package.by_name(self.editpkg_name).get_relationships()
        assert (
            str(rels)
            == "[<*PackageRelationship editpkgtest depends_on annakarenina>]"
        )


class TestDelete(object):
    @pytest.fixture
    def initial_data(self, clean_db):
        CreateTestData.create()
        CreateTestData.create_test_user()

    @pytest.fixture
    def users(self, initial_data):
        admin = model.User.by_name(u"testsysadmin")
        return {
            "admin": {"REMOTE_USER": admin.name.encode("utf8")},
            "tester": {"REMOTE_USER": "tester"},
        }

    @pytest.mark.ckan_config("ckan.plugins", "test_package_controller_plugin")
    @pytest.mark.usefixtures("with_plugins")
    def test_delete(self, app, users):
        plugin = plugins.get_plugin("test_package_controller_plugin")

        offset = url_for("dataset.delete", id="warandpeace")
        # Since organizations, any owned dataset can be edited/deleted by any
        # user
        app.post(offset, extra_environ=users["tester"])

        app.post(offset, extra_environ=users["admin"])

        assert model.Package.get("warandpeace").state == u"deleted"

        assert plugin.calls["delete"] == 2
        assert plugin.calls["after_delete"] == 2


class TestNew:
    @pytest.fixture
    def env_user(self, clean_db):
        CreateTestData.create_test_user()

        return {"REMOTE_USER": "tester"}

    @pytest.mark.ckan_config("ckan.plugins", "test_package_controller_plugin")
    @pytest.mark.usefixtures("with_plugins")
    def test_new_plugin_hook(self, env_user, app):
        plugin = plugins.get_plugin("test_package_controller_plugin")
        offset = url_for("dataset.new")
        new_name = u"plugged"
        res = app.post(offset, extra_environ=env_user, data={
            "name": new_name,
            "save": ""
        }, follow_redirects=False)
        assert plugin.calls["edit"] == 0, plugin.calls
        assert plugin.calls["create"] == 1, plugin.calls

    @pytest.mark.ckan_config("ckan.plugins", "test_package_controller_plugin")
    @pytest.mark.usefixtures("with_plugins")
    def test_after_create_plugin_hook(self, env_user, app):
        plugin = plugins.get_plugin("test_package_controller_plugin")
        offset = url_for("dataset.new")
        new_name = u"plugged2"
        res = app.post(offset, extra_environ=env_user, data={
            "name": new_name,
            "save": ""
        }, follow_redirects=False)
        assert plugin.calls["after_update"] == 0, plugin.calls
        assert plugin.calls["after_create"] == 1, plugin.calls

        assert plugin.id_in_dict

    @pytest.mark.usefixtures("clean_db", "clean_index")
    @pytest.mark.xfail(reason="DetachedInstance error.")
    def test_new_indexerror(self, env_user, app):
        bad_solr_url = "http://example.com/badsolrurl"
        solr_url = SolrSettings.get()[0]
        try:
            SolrSettings.init(bad_solr_url)
            new_package_name = u"new-package-missing-solr"

            offset = url_for("dataset.new")
            res = app.post(offset, extra_environ=env_user,  data={
                "save": "",
                "name": new_package_name,
            })
            assert "Unable to add package to search index" in res, res
        finally:
            SolrSettings.init(solr_url)

    def test_change_locale(self, env_user, app):
        offset = url_for("dataset.new")
        res = app.get(offset, extra_environ=env_user)

        res = app.get("/de/dataset/new", extra_environ=env_user)
        assert body_contains(res, "Datensatz")


class TestNonActivePackages:
    non_active_name = u"test_nonactive"

    @pytest.fixture(autouse=True)
    def initial_data(self, clean_db):
        CreateTestData.create()
        pkg = model.Package(name=self.non_active_name)
        model.Session.add(pkg)
        model.repo.commit_and_remove()

        pkg = (
            model.Session.query(model.Package)
            .filter_by(name=self.non_active_name)
            .one()
        )
        admin = model.User.by_name(u"joeadmin")
        model.repo.commit_and_remove()

        pkg = (
            model.Session.query(model.Package)
            .filter_by(name=self.non_active_name)
            .one()
        )
        pkg.delete()  # becomes non active
        model.repo.commit_and_remove()

    def test_read(self, app):
        offset = url_for("dataset.read", id=self.non_active_name)
        res = app.get(offset, status=404)

    def test_read_as_admin(self, app):
        offset = url_for("dataset.read", id=self.non_active_name)
        res = app.get(
            offset, status=200, extra_environ={"REMOTE_USER": "testsysadmin"}
        )


class TestResourceListing:
    @pytest.fixture(autouse=True)
    def initial_data(self, clean_db, app):
        CreateTestData.create()
        users = {}
        tester = model.User.by_name(u"tester")
        tests.call_action_api(
            app, "organization_create", name="test_org_2", apikey=tester.apikey
        )

        tests.call_action_api(
            app,
            "package_create",
            name="crimeandpunishment",
            owner_org="test_org_2",
            apikey=tester.apikey,
        )

    @pytest.fixture
    def users(self):
        return {
            "admin": {"REMOTE_USER": "testsysadmin"},
            "tester": {"REMOTE_USER": "tester"},
            "someone_else": {"REMOTE_USER": "someone_else"},
        }

    def test_resource_listing_premissions_sysadmin(self, app, users):
        # sysadmin 200
        app.get(
            "/dataset/resources/crimeandpunishment",
            extra_environ=users["admin"],
            status=200,
        )

    def test_resource_listing_premissions_auth_user(self, app, users):
        # auth user 200
        app.get(
            "/dataset/resources/crimeandpunishment",
            extra_environ=users["tester"],
            status=200,
        )

    def test_resource_listing_premissions_non_auth_user(self, app, users):
        # non auth user 403
        app.get(
            "/dataset/resources/crimeandpunishment",
            extra_environ=users["someone_else"],
            status=403,
        )

    def test_resource_listing_premissions_not_logged_in(self, app):
        # not logged in 403
        app.get("/dataset/resources/crimeandpunishment", status=403)
