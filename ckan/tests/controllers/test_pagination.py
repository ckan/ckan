# -*- coding: utf-8 -*-

from bs4 import BeautifulSoup
import pytest
import ckan.tests.factories as factories
from ckan.tests.helpers import call_action
from ckan.lib.helpers import url_for


@pytest.mark.usefixtures("clean_db", "clean_index")
def test_package_search(app):
    group = factories.Group()
    all_names = [
        dataset["name"]
        for dataset in factories.Dataset.create_batch(51, groups=[{"name": group["name"]}])
    ]
    resp = app.get(url_for("dataset.search", q=f"groups:{group['name']}"))
    page = BeautifulSoup(resp.data)
    href = page.select_one(".pagination").find("a", text=2)["href"]
    assert f'/dataset/?q=groups%3A{group["name"]}&page=2' == href
    names = [
        link["href"].rsplit("/", 1)[-1]
        for link in page.select(".primary .dataset-heading a")
    ]
    assert all_names[:-21:-1] == names

    resp = app.get(
        url_for("dataset.search", q=f"groups:{group['name']}", page=2)
    )
    page = BeautifulSoup(resp.data)
    href = page.select_one(".pagination").find("a", text=1)["href"]
    assert f'/dataset/?q=groups%3A{group["name"]}&page=1' == href
    names = [
        link["href"].rsplit("/", 1)[-1]
        for link in page.select(".primary .dataset-heading a")
    ]
    assert all_names[-21:-41:-1] == names


@pytest.mark.usefixtures("clean_db", "clean_index")
def test_group_datasets_read(app):
    group = factories.Group()
    all_names = [
        dataset["name"]
        for dataset in factories.Dataset.create_batch(51, groups=[{"name": group["name"]}])
    ]
    resp = app.get(
        url_for(controller="group", action="read", id=group["name"])
    )
    page = BeautifulSoup(resp.data)
    href = page.select_one(".pagination").find("a", text=2)["href"]

    assert f'/group/{group["name"]}?page=2' == href
    names = [
        link["href"].rsplit("/", 1)[-1]
        for link in page.select(".primary .dataset-heading a")
    ]
    assert all_names[:-21:-1] == names

    resp = app.get(
        url_for(controller="group", action="read", id=group["name"], page=2)
    )
    page = BeautifulSoup(resp.data)
    href = page.select_one(".pagination").find("a", text=1)["href"]

    assert f'/group/{group["name"]}?page=1' == href
    names = [
        link["href"].rsplit("/", 1)[-1]
        for link in page.select(".primary .dataset-heading a")
    ]
    assert all_names[-21:-41:-1] == names


@pytest.mark.usefixtures("clean_db", "clean_index")
def test_group_index(app):
    all_names = [
        group["name"]
        for group in sorted(factories.Group.create_batch(22), key=lambda g: g["name"])
    ]

    resp = app.get(url_for("group.index", sort="name"))
    page = BeautifulSoup(resp.data)
    href = page.select_one(".pagination").find("a", text=2)["href"]
    assert "/group/?q=&sort=name&page=2" == href
    names = [
        link["href"].rsplit("/", 1)[-1]
        for link in page.select(".primary .media-view")
    ]

    assert all_names[:20] == names

    resp = app.get(url_for("group.index", sort="name", page=2))
    page = BeautifulSoup(resp.data)
    href = page.select_one(".pagination").find("a", text=1)["href"]
    assert "/group/?q=&sort=name&page=1" == href
    names = [
        link["href"].rsplit("/", 1)[-1]
        for link in page.select(".primary .media-view")
    ]
    assert all_names[20:] == names


@pytest.mark.usefixtures("clean_db", "clean_index")
def test_users_index(app):
    factories.User.create_batch(21)
    all_names = [
        user.name if factories.User._meta.model.VALID_NAME.match(user.name) else user[0].id
        for user in
        call_action("user_list", {"return_query": True}, order_by="name")
    ]
    resp = app.get(url_for("user.index"))
    page = BeautifulSoup(resp.data)
    href = page.select_one(".pagination").find("a", text=2)["href"]
    assert "/user/?q=&order_by=name&page=2" == href

    names = [
        link["href"].rsplit("/", 1)[-1]
        for link in page.select(".primary .user-list a")
    ]

    assert all_names[:20] == names

    resp = app.get(url_for("user.index", page=2))
    page = BeautifulSoup(resp.data)
    href = page.select_one(".pagination").find("a", text=1)["href"]
    assert "/user/?q=&order_by=name&page=1" == href
    names = [
        link["href"].rsplit("/", 1)[-1]
        for link in page.select(".primary .user-list a")
    ]

    assert all_names[20:] == names
