# encoding: utf-8

import os

import pytest

import ckan.model as model
from ckan.common import config
from ckan.model.license import LicenseRegister
from ckan.tests import factories

this_dir = os.path.dirname(os.path.realpath(__file__))


@pytest.fixture
def reset():
    yield
    if hasattr(model.Package, "_license_register"):
        del model.Package._license_register


@pytest.mark.usefixtures("non_clean_db", "reset")
def test_default_register_has_basic_properties_of_a_license():
    config["licenses_group_url"] = None
    reg = LicenseRegister()

    license = reg["cc-by"]
    assert license.url == "http://www.opendefinition.org/licenses/cc-by"
    assert license.isopen()
    assert license.title == "Creative Commons Attribution"


@pytest.mark.usefixtures("non_clean_db", "reset")
@pytest.mark.ckan_config(
    "licenses_group_url", "file:///%s/licenses.v1" % this_dir
)
def test_import_v1_style_register():
    reg = LicenseRegister()

    license = reg["cc-by"]
    assert license.url == "http://www.opendefinition.org/licenses/cc-by"
    assert license.isopen()
    assert license.title == "Creative Commons Attribution"


# v2 is used by http://licenses.opendefinition.org in recent times
@pytest.mark.usefixtures("non_clean_db", "reset")
@pytest.mark.ckan_config(
    "licenses_group_url", "file:///%s/licenses.v2" % this_dir
)
def test_import_v2_style_register():
    reg = LicenseRegister()
    license = reg["CC-BY-4.0"]
    assert license.url == "https://creativecommons.org/licenses/by/4.0/"
    assert license.isopen()
    assert license.title == "Creative Commons Attribution 4.0"


@pytest.mark.usefixtures("reset")
@pytest.mark.ckan_config(
    "licenses_group_url", "file:///%s/licenses.v1" % this_dir
)
@pytest.mark.ckan_config("ckan.locale_default", "ca")
def test_import_v1_style_register_i18n(app):
    sysadmin = factories.Sysadmin(password="correct123")
    sysadmin_token = factories.APIToken(user=sysadmin["name"])
    env = {"Authorization": sysadmin_token["token"]}
    resp = app.get("/dataset/new", environ_overrides=env)
    assert "Altres (Oberta)" in resp.body


@pytest.mark.usefixtures("reset")
@pytest.mark.ckan_config(
    "licenses_group_url", "file:///%s/licenses.v2" % this_dir
)
@pytest.mark.ckan_config("ckan.locale_default", "ca")
def test_import_v2_style_register_i18n(app):
    sysadmin = factories.Sysadmin(password="correct123")
    sysadmin_token = factories.APIToken(user=sysadmin["name"])
    env = {"Authorization": sysadmin_token["token"]}
    resp = app.get("/dataset/new", environ_overrides=env)
    assert "Altres (Oberta)" in resp.body


def test_access_via_attribute():
    license = LicenseRegister()["cc-by"]
    assert license.od_conformance == "approved"


def test_access_via_attribute_2():
    license = LicenseRegister()["cc-by"]
    assert license.od_conformance
    assert license.osd_conformance == "not reviewed"
