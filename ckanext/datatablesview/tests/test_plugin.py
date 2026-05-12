import bs4
import pytest

from ckan.lib.helpers import url_for
from ckan.tests import factories, helpers


@pytest.mark.ckan_config("ckan.plugins", "datastore datatables_view")
@pytest.mark.usefixtures("with_plugins")
def test_ajax_data(app):  # type: ignore
    dataset = factories.Dataset()
    ds = helpers.call_action(
        "datastore_create",
        resource={"package_id": dataset["id"]},
        fields=[{"id": "a", "type": "text"}, {"id": "b", "type": "int"}],
        records=[
            {"a": "one", "b": 1},
            {"a": "two", "b": 2},
        ],
    )
    view = factories.ResourceView(
        view_type="datatables_view", resource_id=ds["resource_id"]
    )
    url = url_for(
        "resource.view",
        id=dataset["id"],
        resource_id=ds["resource_id"],
        view_id=view["id"],
    )

    resp = app.get(url)

    page = bs4.BeautifulSoup(resp.body)

    assert page.body["class"] == ["dt-view"]  # type: ignore
