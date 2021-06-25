# -*- coding: utf-8 -*-

from bs4 import BeautifulSoup
import pytest
import ckan.tests.factories as factories
from ckan.lib.helpers import url_for


@pytest.mark.usefixtures("clean_index", "clean_db")
def test_package_search(app):
    group = factories.Group()
    factories.Dataset.create_batch(51, groups=[{"name": group["name"]}])
    resp = app.get(url_for("dataset.search", q=f"groups:{group['name']}"))
    page = BeautifulSoup(resp.data)
    href = page.select_one(".pagination").find("a", text=2)["href"]
    assert f'/dataset/?q=groups%3A{group["name"]}&page=2' == href
    numbers = [
        link["href"].rsplit("_", 1)[-1]
        for link in page.select(".primary .dataset-heading a")
    ]
    assert list(map(str, range(50, 30, -1))) == numbers

    resp = app.get(
        url_for("dataset.search", q=f"groups:{group['name']}", page=2)
    )
    page = BeautifulSoup(resp.data)
    href = page.select_one(".pagination").find("a", text=1)["href"]
    assert f'/dataset/?q=groups%3A{group["name"]}&page=1' == href
    numbers = [
        link["href"].rsplit("_", 1)[-1]
        for link in page.select(".primary .dataset-heading a")
    ]
    assert list(map(str, range(30, 10, -1))) == numbers


@pytest.mark.usefixtures("clean_index", "clean_db")
def test_group_datasets_read(app):
    group = factories.Group()
    factories.Dataset.create_batch(51, groups=[{"name": group["name"]}])
    resp = app.get(
        url_for(controller="group", action="read", id=group["name"])
    )
    page = BeautifulSoup(resp.data)
    href = page.select_one(".pagination").find("a", text=2)["href"]

    assert f'/group/{group["name"]}?page=2' == href
    numbers = [
        link["href"].rsplit("_", 1)[-1]
        for link in page.select(".primary .dataset-heading a")
    ]
    assert list(map(str, range(50, 30, -1))) == numbers

    resp = app.get(
        url_for(controller="group", action="read", id=group["name"], page=2)
    )
    page = BeautifulSoup(resp.data)
    href = page.select_one(".pagination").find("a", text=1)["href"]

    assert f'/group/{group["name"]}?page=1' == href
    numbers = [
        link["href"].rsplit("_", 1)[-1]
        for link in page.select(".primary .dataset-heading a")
    ]
    assert list(map(str, range(30, 10, -1))) == numbers


@pytest.mark.usefixtures("clean_index", "clean_db")
def test_group_index(app):
    factories.Group.create_batch(22)
    resp = app.get(url_for("group.index"))
    page = BeautifulSoup(resp.data)
    href = page.select_one(".pagination").find("a", text=2)["href"]
    assert "/group/?q=&sort=&page=2" == href
    numbers = [
        link["href"].rsplit("_", 1)[-1]
        for link in page.select(".primary .media-view")
    ]

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
    ] == numbers

    resp = app.get(url_for("group.index", page=2))
    page = BeautifulSoup(resp.data)
    href = page.select_one(".pagination").find("a", text=1)["href"]
    assert "/group/?q=&sort=&page=1" == href
    numbers = [
        link["href"].rsplit("_", 1)[-1]
        for link in page.select(".primary .media-view")
    ]
    assert ["20", "21"] == numbers


@pytest.mark.usefixtures("clean_index", "clean_db")
def test_users_index(app):
    factories.User.create_batch(21)
    resp = app.get(url_for("user.index"))
    page = BeautifulSoup(resp.data)
    href = page.select_one(".pagination").find("a", text=2)["href"]
    assert "/user/?q=&order_by=name&page=2" == href
    # this page will list default user, created after db reset,
    # that is skipped by our scraper. So, actually there 20 items,
    # but only 19 of them have been caught by regExp
    numbers = [
        link["href"].rsplit("_", 1)[-1]
        for link in page.select(".primary .user-list a")
    ][1:]

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
    ] == numbers

    resp = app.get(url_for("user.index", page=2))
    page = BeautifulSoup(resp.data)
    href = page.select_one(".pagination").find("a", text=1)["href"]
    assert "/user/?q=&order_by=name&page=1" == href
    numbers = [
        link["href"].rsplit("_", 1)[-1]
        for link in page.select(".primary .user-list a")
    ]

    assert ["19", "20"] == numbers
