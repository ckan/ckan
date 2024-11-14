import pytest
import io

from datetime import datetime

from requests import Response

from ckan.cli.cli import ckan
from ckan.plugins import toolkit
from ckan.tests import helpers, factories

from unittest import mock

from ckanext.xloader import jobs
from ckanext.xloader.utils import get_xloader_user_apitoken


_TEST_FILE_CONTENT = "x, y\n1,2\n2,4\n3,6\n4,8\n5,10"


def get_response(download_url, headers):
    """Mock jobs.get_response() method."""
    resp = Response()
    resp.raw = io.BytesIO(_TEST_FILE_CONTENT.encode())
    resp.headers = headers
    return resp


def get_large_response(download_url, headers):
    """Mock jobs.get_response() method to fake a large file."""
    resp = Response()
    resp.raw = io.BytesIO(_TEST_FILE_CONTENT.encode())
    resp.headers = {'content-length': 2000000000}
    return resp


@pytest.fixture
def apikey():
    if toolkit.check_ckan_version(min_version="2.10"):
        sysadmin = factories.SysadminWithToken()
    else:
        # To provide support with CKAN 2.9
        sysadmin = factories.Sysadmin()
        sysadmin["token"] = get_xloader_user_apitoken()

    return sysadmin["token"]


@pytest.fixture
def data(create_with_upload, apikey):
    dataset = factories.Dataset()
    resource = create_with_upload(
        _TEST_FILE_CONTENT,
        "multiplication_2.csv",
        url="http://data",
        package_id=dataset["id"]
    )
    callback_url = toolkit.url_for(
        "api.action", ver=3, logic_function="xloader_hook", qualified=True
    )
    return {
        'api_key': apikey,
        'job_type': 'xloader_to_datastore',
        'result_url': callback_url,
        'metadata': {
            'ignore_hash': True,
            'ckan_url': toolkit.config.get('ckan.site_url'),
            'resource_id': resource["id"],
            'set_url_type': False,
            'task_created': datetime.utcnow().isoformat(),
            'original_url': resource["url"],
        }
    }


@pytest.mark.usefixtures("clean_db", "with_plugins")
class TestXLoaderJobs(helpers.FunctionalRQTestBase):

    def test_xloader_data_into_datastore(self, cli, data):
        self.enqueue(jobs.xloader_data_into_datastore, [data])
        with mock.patch("ckanext.xloader.jobs.get_response", get_response):
            stdout = cli.invoke(ckan, ["jobs", "worker", "--burst"]).output
            assert "File hash: d44fa65eda3675e11710682fdb5f1648" in stdout
            assert "Fields: [{'id': 'x', 'type': 'text'}, {'id': 'y', 'type': 'text'}]" in stdout
            assert "Copying to database..." in stdout
            assert "Creating search index..." in stdout
            assert "Express Load completed" in stdout

        resource = helpers.call_action("resource_show", id=data["metadata"]["resource_id"])
        assert resource["datastore_contains_all_records_of_source_file"]

    def test_xloader_ignore_hash(self, cli, data):
        self.enqueue(jobs.xloader_data_into_datastore, [data])
        with mock.patch("ckanext.xloader.jobs.get_response", get_response):
            stdout = cli.invoke(ckan, ["jobs", "worker", "--burst"]).output
            assert "Express Load completed" in stdout

        self.enqueue(jobs.xloader_data_into_datastore, [data])
        with mock.patch("ckanext.xloader.jobs.get_response", get_response):
            stdout = cli.invoke(ckan, ["jobs", "worker", "--burst"]).output
            assert "Copying to database..." in stdout
            assert "Express Load completed" in stdout

        data["metadata"]["ignore_hash"] = False
        self.enqueue(jobs.xloader_data_into_datastore, [data])
        with mock.patch("ckanext.xloader.jobs.get_response", get_response):
            stdout = cli.invoke(ckan, ["jobs", "worker", "--burst"]).output
            assert "Ignoring resource - the file hash hasn't changed" in stdout

    def test_data_too_big_error_if_content_length_bigger_than_config(self, cli, data):
        self.enqueue(jobs.xloader_data_into_datastore, [data])
        with mock.patch("ckanext.xloader.jobs.get_response", get_large_response):
            stdout = cli.invoke(ckan, ["jobs", "worker", "--burst"]).output
            assert "Data too large to load into Datastore:" in stdout

    def test_data_max_excerpt_lines_config(self, cli, data):
        self.enqueue(jobs.xloader_data_into_datastore, [data])
        with mock.patch("ckanext.xloader.jobs.get_response", get_large_response):
            with mock.patch("ckanext.xloader.jobs.MAX_EXCERPT_LINES", 1):
                stdout = cli.invoke(ckan, ["jobs", "worker", "--burst"]).output
                assert "Loading excerpt of ~1 lines to DataStore." in stdout

        resource = helpers.call_action("resource_show", id=data["metadata"]["resource_id"])
        assert resource["datastore_contains_all_records_of_source_file"] is False


@pytest.mark.usefixtures("clean_db")
class TestSetResourceMetadata(object):
    def test_simple(self):
        resource = factories.Resource()

        jobs.set_resource_metadata(
            {
                "datastore_contains_all_records_of_source_file": True,
                "datastore_active": True,
                "ckan_url": "http://www.ckan.org/",
                "resource_id": resource["id"],
            }
        )

        resource = helpers.call_action("resource_show", id=resource["id"])
        assert resource["datastore_contains_all_records_of_source_file"]
        assert resource["datastore_active"]
        assert resource["ckan_url"] == "http://www.ckan.org/"
