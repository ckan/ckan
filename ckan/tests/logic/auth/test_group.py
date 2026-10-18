"""Tests for authorization in ckan/logic/auth/group.py."""

import pytest

from ckan import model
from ckan.tests import factories, helpers

logic = helpers.logic


@pytest.mark.usefixtures("non_clean_db")
def test_group_show__deleted_group_is_hidden_to_public():
    group = factories.Group(state="deleted")
    context = {"model": model}
    context["user"] = ""

    with pytest.raises(logic.NotAuthorized):
        helpers.call_auth("group_show", context=context, id=group["name"])


@pytest.mark.usefixtures("non_clean_db")
def test_group_show__deleted_group_is_visible_to_its_member():

    fred = factories.User()
    fred["capacity"] = "editor"
    org = factories.Group(users=[fred], state="deleted")
    context = {"model": model}
    context["user"] = fred["name"]

    ret = helpers.call_auth("group_show", context=context, id=org["name"])
    assert ret


@pytest.mark.usefixtures("non_clean_db")
def test_group_show__deleted_org_is_visible_to_its_member():

    fred = factories.User()
    fred["capacity"] = "editor"
    org = factories.Organization(users=[fred], state="deleted")
    context = {"model": model}
    context["user"] = fred["name"]

    ret = helpers.call_auth("group_show", context=context, id=org["name"])
    assert ret


@pytest.mark.usefixtures("non_clean_db")
@pytest.mark.ckan_config("ckan.auth.public_user_details", False)
def test_group_show__user_is_hidden_to_public():
    group = factories.Group()
    context = {"model": model}
    context["user"] = ""

    with pytest.raises(logic.NotAuthorized):
        helpers.call_auth(
            "group_show",
            context=context,
            id=group["name"],
            include_users=True,
        )


@pytest.mark.usefixtures("non_clean_db")
def test_group_show__user_is_avail_to_public():
    group = factories.Group()
    context = {"model": model}
    context["user"] = ""

    assert helpers.call_auth("group_show", context=context, id=group["name"])


@pytest.mark.parametrize("func", ["group_package_show", "member_list"])
def test_anonymous_can_call_get_method(func):
    user = factories.User()
    context = {"user": "", "model": model}
    assert helpers.call_auth(func, context, id=user["id"])
