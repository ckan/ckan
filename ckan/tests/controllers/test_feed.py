# encoding: utf-8

import pytest

import ckan.tests.helpers as helpers
import ckan.tests.factories as factories
import ckan.plugins as plugins


@pytest.mark.usefixtures("clean_db")
class TestFeeds(object):
    @pytest.mark.parametrize("page", [0, -2, "abc"])
    def test_atom_feed_incorrect_page_gives_error(self, page, app):
        group = factories.Group()
        offset = f"/feeds/group/{group['name']}.atom?page={page}"
        res = app.get(offset, status=400)
        assert (
            "&#34;page&#34; parameter must be a positive integer" in res
        ), res

    def test_general_atom_feed_works(self, app):
        dataset = factories.Dataset(notes="Test\x0c Notes")
        offset = "/feeds/dataset.atom"
        res = app.get(offset)
        assert helpers.body_contains(res, u"<title>{0}</title>".format(dataset["title"]))
        assert helpers.body_contains(res, u"<content>Test Notes</content>")

    def test_general_atom_feed_works_with_no_notes(self, app):
        dataset = factories.Dataset(notes=None)
        offset = "/feeds/dataset.atom"
        res = app.get(offset)
        assert helpers.body_contains(res, u"<title>{0}</title>".format(dataset["title"]))
        assert helpers.body_contains(res, u"<content/>")

    def test_group_atom_feed_works(self, app):
        group = factories.Group()
        dataset = factories.Dataset(groups=[{"id": group["id"]}])
        offset = f"/feeds/group/{group['name']}.atom"
        res = app.get(offset)

        assert helpers.body_contains(res, u"<title>{0}</title>".format(dataset["title"]))

    def test_organization_atom_feed_works(self, app):
        org = factories.Organization()
        dataset = factories.Dataset(owner_org=org["id"])
        offset = f"/feeds/organization/{org['name']}.atom"
        res = app.get(offset)

        assert helpers.body_contains(res, u"<title>{0}</title>".format(dataset["title"]))

    def test_custom_atom_feed_works(self, app):
        dataset1 = factories.Dataset(
            title=u"Test weekly",
            extras=[{"key": "frequency", "value": "weekly"}],
        )
        dataset2 = factories.Dataset(
            title=u"Test daily",
            extras=[{"key": "frequency", "value": "daily"}],
        )

        offset = "/feeds/custom.atom"
        params = {"q": "frequency:weekly"}

        res = app.get(offset, query_string=params)

        assert helpers.body_contains(res, u"<title>{0}</title>".format(dataset1["title"]))

        assert not helpers.body_contains(res, u'<title">{0}</title>'.format(dataset2["title"]))


class MockFeedPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IFeed)

    def get_item_additional_fields(self, dataset_dict):
        extras = {e["key"]: e["value"] for e in dataset_dict["extras"]}

        box = tuple(
            float(extras.get(n)) for n in ("ymin", "xmin", "ymax", "xmax")
        )
        return {"geometry": box}
