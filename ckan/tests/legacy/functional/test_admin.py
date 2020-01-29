# encoding: utf-8

import pytest
import ckan.model as model
from ckan.tests.legacy import url_for, CreateTestData


@pytest.mark.usefixtures("clean_db")
def test_index(app):
    CreateTestData.create()
    url = url_for("admin.index")
    response = app.get(url, status=403)
    # random username
    response = app.get(
        url, status=403, extra_environ={"REMOTE_USER": "my-random-user-name"}
    )
    # now test real access
    username = u"testsysadmin".encode("utf8")
    response = app.get(url, extra_environ={"REMOTE_USER": username})
    assert "Administration" in response, response
