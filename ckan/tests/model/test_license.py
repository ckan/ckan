# encoding: utf-8

import os

import pytest

import ckan.model as model
from ckan.common import config
from ckan.model.license import LicenseRegister
from ckan.tests import factories

this_dir = os.path.dirname(os.path.realpath(__file__))


@pytest.fixture
def reset(clean_db):
    yield
    if hasattr(model.Package, "_license_register"):
        del model.Package._license_register


@pytest.mark.usefixtures("reset")
def test_default_register_has_basic_properties_of_a_license():
    config["licenses_group_url"] = None
    reg = LicenseRegister()

    license = reg["cc-by"]
    assert license.url == "http://www.opendefinition.org/licenses/cc-by"
    assert license.isopen()
    assert license.title == "Creative Commons Attribution"


@pytest.mark.usefixtures("reset")
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
@pytest.mark.usefixtures("reset")
@pytest.mark.ckan_config(
    "licenses_group_url", "file:///%s/licenses.v2" % this_dir
)
def test_import_v2_style_register():
    reg = LicenseRegister()
    license = reg["CC-BY-4.0"]
    assert license.url == "https://creativecommons.org/licenses/by/4.0/"
    assert license.isopen()
    assert license.title == "Creative Commons Attribution 4.0"


@pytest.mark.usefixtures("reset", "with_request_context")
@pytest.mark.ckan_config(
    "licenses_group_url", "file:///%s/licenses.v1" % this_dir
)
@pytest.mark.ckan_config("ckan.locale_default", "ca")
def test_import_v1_style_register_i18n(app):
    sysadmin = factories.Sysadmin()
    resp = app.get(
        "/dataset/new", extra_environ={"REMOTE_USER": str(sysadmin["name"])}
    )
    assert "Altres (Oberta)" in resp.body


@pytest.mark.usefixtures("reset", "with_request_context")
@pytest.mark.ckan_config(
    "licenses_group_url", "file:///%s/licenses.v2" % this_dir
)
@pytest.mark.ckan_config("ckan.locale_default", "ca")
def test_import_v2_style_register_i18n(app):
    sysadmin = factories.Sysadmin()
    resp = app.get(
        "/dataset/new", extra_environ={"REMOTE_USER": str(sysadmin["name"])}
    )
    assert "Altres (Oberta)" in resp.body


def test_access_via_attribute():
    license = LicenseRegister()["cc-by"]
    assert license.od_conformance == "approved"


def test_access_via_key():
    license = LicenseRegister()["cc-by"]
    assert license["od_conformance"] == "approved"


def test_access_via_dict():
    license = LicenseRegister()["cc-by"]
    license_dict = license.as_dict()
    assert license_dict["od_conformance"] == "approved"
    assert license_dict["osd_conformance"] == "not reviewed"


def test_access_via_attribute():
    license = LicenseRegister()["cc-by"]
    assert license.is_okd_compliant
    assert not license.is_osi_compliant


def test_access_via_key():
    license = LicenseRegister()["cc-by"]
    assert license["is_okd_compliant"]
    assert not license["is_osi_compliant"]


def test_access_via_dict():
    license = LicenseRegister()["cc-by"]
    license_dict = license.as_dict()
    assert license_dict["is_okd_compliant"]
    assert not license_dict["is_osi_compliant"]
