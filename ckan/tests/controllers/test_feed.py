# encoding: utf-8

import pytest
import six

from ckan.lib.helpers import url_for

import ckan.tests.helpers as helpers
import ckan.tests.factories as factories
import ckan.plugins as plugins
if six.PY2:
    from webhelpers.feedgenerator import GeoAtom1Feed


@pytest.mark.usefixtures("clean_db", "with_request_context")
class TestFeeds(object):
    @pytest.mark.parametrize("page", [0, -2, "abc"])
    def test_atom_feed_incorrect_page_gives_error(self, page, app):
        group = factories.Group()
        offset = url_for(
            u"feeds.group", id=group["name"]
        ) + u"?page={}".format(page)
        res = app.get(offset, status=400)
        assert (
            "&#34;page&#34; parameter must be a positive integer" in res
        ), res

    def test_general_atom_feed_works(self, app):
        dataset = factories.Dataset()
        offset = url_for(u"feeds.general")
        res = app.get(offset)

        assert helpers.body_contains(res, u"<title>{0}</title>".format(dataset["title"]))

    def test_group_atom_feed_works(self, app):
        group = factories.Group()
        dataset = factories.Dataset(groups=[{"id": group["id"]}])
        offset = url_for(u"feeds.group", id=group["name"])
        res = app.get(offset)

        assert helpers.body_contains(res, u"<title>{0}</title>".format(dataset["title"]))

    def test_organization_atom_feed_works(self, app):
        group = factories.Organization()
        dataset = factories.Dataset(owner_org=group["id"])
        offset = url_for(u"feeds.organization", id=group["name"])
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

        offset = url_for(u"feeds.custom")
        params = {"q": "frequency:weekly"}

        res = app.get(offset, query_string=params)

        assert helpers.body_contains(res, u"<title>{0}</title>".format(dataset1["title"]))

        assert not helpers.body_contains(res, u'<title">{0}</title>'.format(dataset2["title"]))


@pytest.mark.skipif(six.PY3, reason="Relies on webhelpers")
@pytest.mark.ckan_config("ckan.plugins", "test_feed_plugin")
@pytest.mark.usefixtures("clean_db", "clean_index", "with_plugins", "with_request_context")
class TestCustomFeedPlugin:
    def test_custom_class_used(self, app):
        offset = url_for(u"feeds.general")
        res = app.get(offset)

        assert helpers.body_contains(
            res,
            'xmlns:georss="http://www.georss.org/georss"'
        )

    def test_additional_fields_added(self, app):
        metadata = {
            "ymin": "-2373790",
            "xmin": "2937940",
            "ymax": "-1681290",
            "xmax": "3567770",
        }

        extras = [{"key": k, "value": v} for (k, v) in metadata.items()]

        factories.Dataset(extras=extras)
        offset = url_for(u"feeds.general")
        res = app.get(offset)

        assert helpers.body_contains(
            res,
            "<georss:box>-2373790.000000 2937940.000000 -1681290.000000 3567770.000000</georss:box>"
        )


class MockFeedPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IFeed)

    def get_feed_class(self):
        return GeoAtom1Feed

    def get_item_additional_fields(self, dataset_dict):
        extras = {e["key"]: e["value"] for e in dataset_dict["extras"]}

        box = tuple(
            float(extras.get(n)) for n in ("ymin", "xmin", "ymax", "xmax")
        )
        return {"geometry": box}
