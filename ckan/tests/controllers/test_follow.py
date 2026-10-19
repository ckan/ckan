"""Follow controls support both native form submissions and HTMX updates."""

from bs4 import BeautifulSoup
import pytest

from ckan.common import config
from ckan.lib.helpers import url_for
import ckan.logic as logic
from ckan.tests import factories


@pytest.mark.usefixtures("clean_db")
@pytest.mark.ckan_config("WTF_CSRF_ENABLED", True)
@pytest.mark.parametrize("entity_type,factory,action_type,sidebar", [
    ("dataset", factories.Dataset, "dataset", "package-info"),
    ("group", factories.Group, "group", "group-info"),
    ("organization", factories.Organization, "group", "organization-info"),
    ("user", factories.User, "user", "user-info"),
])
@pytest.mark.parametrize("htmx", [False, True])
def test_follow_controls(app, entity_type, factory, action_type, sidebar, htmx):
    follower = factories.UserWithToken()
    entity = factory()
    app.set_session_user(follower["id"])
    headers = {}
    if htmx:
        headers["HX-Request"] = "true"
    read_url = url_for(entity_type + ".read", id=entity["id"])
    response = app.get(read_url)
    csrf_field = config["WTF_CSRF_FIELD_NAME"]

    for action, following in [("follow", True), ("unfollow", False)]:
        action_url = url_for(entity_type + "." + action, id=entity["id"])
        form = BeautifulSoup(response.body, "html.parser").find(
            "form", action=action_url
        )
        token = form.find("input", {"name": csrf_field})["value"]
        app.post(action_url, headers=headers, status=400)
        response = app.post(
            action_url, data={csrf_field: token}, headers=headers,
            follow_redirects=False
        )
        if htmx:
            assert response.status_code == 200
            assert "<html" not in response
        else:
            assert response.status_code == 302
            assert response.headers["Location"].endswith(read_url)
            response = app.get(read_url, headers=headers)
            assert "<html" in response

        assert logic.get_action("am_following_" + action_type)(
            {"user": follower["name"]}, {"id": entity["id"]}
        ) == following
        soup = BeautifulSoup(response.body, "html.parser")
        next_action = "unfollow" if following else "follow"
        next_url = url_for(entity_type + "." + next_action, id=entity["id"])
        form = soup.find("form", action=next_url)
        assert form is not None
        assert form["method"] == "post"
        assert form["hx-post"] == next_url
        assert form["hx-target"] == "#" + sidebar
        assert form["hx-swap"] == "outerHTML"
        assert form.find("input", {"name": csrf_field}) is not None
        button = form.find("button", {"type": "submit"})
        assert button is not None
        assert button.get_text(strip=True) == next_action.capitalize()
        assert button.find("i")["aria-hidden"] == "true"


@pytest.mark.usefixtures("clean_db")
def test_native_follow_validation_error_is_flashed(app):
    follower = factories.UserWithToken()
    headers = {"Authorization": follower["token"]}
    url = url_for("user.follow", id=follower["id"])

    response = app.post(url, headers=headers)

    assert "You cannot follow yourself" in response
