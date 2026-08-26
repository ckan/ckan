import pytest
from bs4 import BeautifulSoup

from ckan.lib.helpers import url_for


@pytest.mark.usefixtures("clean_db")
def test_login_checkbox_input_is_sibling_of_label(app):
    response = app.get(url_for("user.login"), status=200)
    html = BeautifulSoup(response.data, "html.parser")

    checkbox = html.select_one("#field-remember")
    label = html.select_one('label[for="field-remember"]')

    assert checkbox is not None
    assert label is not None
    assert checkbox.find_parent("label") is None
    assert checkbox.parent is label.parent
    assert label.get("for") == checkbox.get("id")
