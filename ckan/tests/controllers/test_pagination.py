# -*- coding: utf-8 -*-

from bs4 import BeautifulSoup
import pytest
import ckan.tests.factories as factories
from ckan.tests.helpers import call_action
from ckan.lib.helpers import url_for
from ckan.lib.pagination import Page


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


@pytest.mark.usefixtures("clean_db", "clean_index")
@pytest.mark.ckan_config("ckan.datasets_per_page", 1)
class TestPaginationSettings:
    @pytest.mark.ckan_config("ckan.pagination.css_class.widget", "custom-pagination")
    def test_widget_class(self, app, package_factory):
        package_factory.create_batch(3)

        resp = app.get(url_for("dataset.search"))
        page = BeautifulSoup(resp.body)
        assert page.select_one(".pagination-wrapper .custom-pagination")

    @pytest.mark.ckan_config("ckan.pagination.css_class.item", "custom-item")
    def test_item_class(self, app, package_factory):
        package_factory.create_batch(3)

        resp = app.get(url_for("dataset.search"))
        page = BeautifulSoup(resp.body)
        items = page.select(".pagination-wrapper .pagination .custom-item")
        # 3 datasets + link to the last page
        assert len(items) == 4

    @pytest.mark.ckan_config("ckan.pagination.css_class.link", "custom-link")
    def test_link_class(self, app, package_factory):
        package_factory.create_batch(3)

        resp = app.get(url_for("dataset.search"))
        page = BeautifulSoup(resp.body)
        items = page.select(".pagination-wrapper .pagination .page-item .custom-link")
        # 3 datasets + link to the last page
        assert len(items) == 4

    @pytest.mark.ckan_config("ckan.pagination.template", "$page of $page_count")
    def test_custom_template(self, app, package_factory):
        package_factory.create_batch(3)

        resp = app.get(url_for("dataset.search", page=2))
        page = BeautifulSoup(resp.body)
        widget = page.select_one(".pagination-wrapper .pagination")
        assert widget.text == "2 of 3"

    @pytest.mark.ckan_config("ckan.pagination.factory", "ckan.tests.controllers.test_pagination:CustomPage")
    def test_custom_factory(self, app, package_factory):
        package_factory.create_batch(3)
        resp = app.get(url_for("dataset.search", page=2))
        page = BeautifulSoup(resp.body)
        items = page.select(".pagination-wrapper .page-item .page-link")
        assert items[-1].text == "NEXT"

    @pytest.mark.ckan_config("ckan.pagination.factory", "ckan.tests.controllers.test_pagination:WrongCustomPage")
    def test_wrong_custom_factory(self, app, package_factory):
        package_factory.create_batch(3)
        resp = app.get(url_for("dataset.search", page=2))
        page = BeautifulSoup(resp.body)
        items = page.select(".pagination-wrapper .page-item .page-link")
        assert items[-1].text == "»"

    @pytest.mark.ckan_config("ckan.pagination.factory", "ckan.tests.controllers.test_pagination:NonExistingCustomPage")
    def test_non_existing_custom_factory(self, app, package_factory):
        package_factory.create_batch(3)
        resp = app.get(url_for("dataset.search", page=2))
        page = BeautifulSoup(resp.body)
        items = page.select(".pagination-wrapper .page-item .page-link")
        assert items[-1].text == "»"


class CustomPage(Page):
    def pager(self, *args, **kwargs):
        kwargs["symbol_next"] = "NEXT"
        return super().pager(*args, **kwargs)


class WrongCustomPage:
    def pager(self, *args, **kwargs):
        kwargs["symbol_next"] = "NEXT"
        return super().pager(*args, **kwargs)
