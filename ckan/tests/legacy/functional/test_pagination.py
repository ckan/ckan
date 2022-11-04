# encoding: utf-8

import re

import pytest

from ckan.lib.create_test_data import CreateTestData
from ckan.tests.legacy import url_for


def scrape_search_results(response, object_type):
    assert object_type in ("dataset", "group_dataset", "group", "user")
    if object_type != "group_dataset":
        exp = 'a href="/%s/%s_(\d\d)' % (object_type, object_type)
        results = re.findall(exp, str(response))
    else:
        object_type = "dataset"
        exp = 'href="/%s/%s_(\d\d)' % (object_type, object_type)
        results = re.findall(exp, str(response))
    return results


def test_scrape_user():
    html = """
          <li class="username">
          <img src="//gravatar.com/avatar/d41d8cd98f00b204e9800998ecf8427e?s=16&amp;d=http://test.ckan.net/images/icons/user.png" /> <a href="/user/user_00">user_00</a>
          </li>
          ...
          <li class="username">
          <img src="//gravatar.com/avatar/d41d8cd98f00b204e9800998ecf8427e?s=16&amp;d=http://test.ckan.net/images/icons/user.png" /> <a href="/user/user_01">user_01</a>
          </li>

      """
    res = scrape_search_results(html, "user")
    assert res == ["00", "01"]


@pytest.fixture
def fake_groups():
    # no. entities per page is hardcoded into the controllers, so
    # create enough of each here so that we can test pagination
    num_groups = 22

    # CS: nasty_string ignore
    groups = [u"group_%s" % str(i).zfill(2) for i in range(0, num_groups)]

    CreateTestData.create_arbitrary([], extra_group_names=groups)


@pytest.fixture
def fake_users():
    # no. entities per page is hardcoded into the controllers, so
    # create enough of each here so that we can test pagination
    num_users = 21

    # CS: nasty_string ignore
    users = [u"user_%s" % str(i).zfill(2) for i in range(num_users)]

    CreateTestData.create_arbitrary([], extra_user_names=users)


@pytest.fixture
def fake_packages():
    # no. entities per page is hardcoded into the controllers, so
    # create enough of each here so that we can test pagination
    num_packages_in_large_group = 51

    packages = []
    for i in range(num_packages_in_large_group):
        packages.append(
            {
                # CS: nasty_string ignore
                "name": u"dataset_%s" % str(i).zfill(2),
                "groups": u"group_00",
            }
        )

    CreateTestData.create_arbitrary(packages)


@pytest.mark.usefixtures("clean_index", "clean_db", "fake_packages")
def test_package_search_p1(app):
    res = app.get(url_for("dataset.search", q="groups:group_00"))
    assert 'href="/dataset/?q=groups%3Agroup_00&amp;page=2"' in res
    pkg_numbers = scrape_search_results(res.data, "dataset")

    assert [
        "50",
        "49",
        "48",
        "47",
        "46",
        "45",
        "44",
        "43",
        "42",
        "41",
        "40",
        "39",
        "38",
        "37",
        "36",
        "35",
        "34",
        "33",
        "32",
        "31",
    ] == pkg_numbers

    res = app.get(url_for("dataset.search", q="groups:group_00", page=2))
    assert 'href="/dataset/?q=groups%3Agroup_00&amp;page=1"' in res
    pkg_numbers = scrape_search_results(res.data, "dataset")
    assert [
        "30",
        "29",
        "28",
        "27",
        "26",
        "25",
        "24",
        "23",
        "22",
        "21",
        "20",
        "19",
        "18",
        "17",
        "16",
        "15",
        "14",
        "13",
        "12",
        "11",
    ] == pkg_numbers


@pytest.mark.usefixtures("clean_index", "clean_db", "fake_packages")
def test_group_datasets_read_p1(app):
    res = app.get(url_for(controller="group", action="read", id="group_00"))
    assert 'href="/group/group_00?page=2' in res, res
    pkg_numbers = scrape_search_results(res.data, "group_dataset")
    assert [
        "50",
        "49",
        "48",
        "47",
        "46",
        "45",
        "44",
        "43",
        "42",
        "41",
        "40",
        "39",
        "38",
        "37",
        "36",
        "35",
        "34",
        "33",
        "32",
        "31",
    ] == pkg_numbers

    res = app.get(
        url_for(controller="group", action="read", id="group_00", page=2)
    )
    assert 'href="/group/group_00?page=1' in res, res
    pkg_numbers = scrape_search_results(res.data, "group_dataset")
    assert [
        "30",
        "29",
        "28",
        "27",
        "26",
        "25",
        "24",
        "23",
        "22",
        "21",
        "20",
        "19",
        "18",
        "17",
        "16",
        "15",
        "14",
        "13",
        "12",
        "11",
    ] == pkg_numbers


@pytest.mark.usefixtures("clean_index", "clean_db", "fake_groups")
def test_group_index(app):
    res = app.get(url_for("group.index"))
    assert 'href="/group/?q=&amp;sort=&amp;page=2"' in res, res
    grp_numbers = scrape_search_results(res.data, "group")
    assert [
        "00",
        "01",
        "02",
        "03",
        "04",
        "05",
        "06",
        "07",
        "08",
        "09",
        "10",
        "11",
        "12",
        "13",
        "14",
        "15",
        "16",
        "17",
        "18",
        "19",
    ] == grp_numbers

    res = app.get(url_for("group.index", page=2))
    assert 'href="/group/?q=&amp;sort=&amp;page=1"' in res
    grp_numbers = scrape_search_results(res.data, "group")
    assert ["20", "21"] == grp_numbers


@pytest.mark.usefixtures("clean_index", "clean_db", "fake_users")
def test_users_index(app):
    res = app.get(url_for("user.index"))
    assert 'href="/user/?q=&amp;order_by=name&amp;page=2"' in res
    user_numbers = scrape_search_results(res.data, "user")

    assert [
        "00",
        "01",
        "02",
        "03",
        "04",
        "05",
        "06",
        "07",
        "08",
        "09",
        "10",
        "11",
        "12",
        "13",
        "14",
        "15",
        "16",
        "17",
        "18",
        "19",
    ] == user_numbers

    res = app.get(url_for("user.index", page=2))
    assert 'href="/user/?q=&amp;order_by=name&amp;page=1"' in res
    user_numbers = scrape_search_results(res.data, "user")
    assert ["20"] == user_numbers
