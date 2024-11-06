# encoding: utf-8

import datetime
import pytest
try:
    from unittest import mock
except ImportError:
    import mock
from six import text_type as str

from ckan.tests import helpers, factories
from ckan.logic import _actions
from ckanext.xloader.plugin import _should_remove_unsupported_resource_from_datastore


@pytest.mark.usefixtures("clean_db", "with_plugins")
@pytest.mark.ckan_config("ckan.plugins", "datastore xloader")
class TestNotify(object):
    def test_submit_on_resource_create(self, monkeypatch):
        func = mock.Mock()
        monkeypatch.setitem(_actions, "xloader_submit", func)

        dataset = factories.Dataset()

        assert not func.called

        helpers.call_action(
            "resource_create",
            {},
            package_id=dataset["id"],
            url="http://example.com/file.csv",
            format="CSV",
        )

        assert func.called

    def test_submit_when_url_changes(self, monkeypatch):
        func = mock.Mock()
        monkeypatch.setitem(_actions, "xloader_submit", func)

        dataset = factories.Dataset()

        resource = helpers.call_action(
            "resource_create",
            {},
            package_id=dataset["id"],
            url="http://example.com/file.pdf",
        )

        assert not func.called  # because of the format being PDF

        helpers.call_action(
            "resource_update",
            {},
            id=resource["id"],
            package_id=dataset["id"],
            url="http://example.com/file.csv",
            format="CSV",
        )

        assert func.called

    @pytest.mark.parametrize("toolkit_config_value, mock_xloader_formats, url_type, datastore_active, expected_result", [
        # Test1: Should pass as it is an upload with an active datastore entry but an unsupported format
        (True, False, 'upload', True, True),
        # Test2: Should fail as it is a supported XLoader format.
        (True, True, 'upload', True, False),
        # Test3: Should fail as the config option is turned off.
        (False, False, 'upload', True, False),
        # Test4: Should fail as the url_type is not supported.
        (True, False, 'custom_type', True, False),
        # Test5: Should fail as datastore is inactive.
        (True, False, 'upload', False, False),
        # Test6: Should pass as it is a recognised resource type with an active datastore entry but an unsupported format
        (True, False, '', True, True),
        # Test7: Should pass as it is a recognised resource type with an active datastore entry but an unsupported format
        (True, False, None, True, True),
    ])
    def test_should_remove_unsupported_resource_from_datastore(
            self, toolkit_config_value, mock_xloader_formats, url_type, datastore_active, expected_result):

        # Setup mock data
        res_dict = {
            'format': 'some_format',
            'url_type': url_type,
            'datastore_active': datastore_active,
            'extras': {'datastore_active': datastore_active}
        }

        # Assert the result based on the logic paths covered
        with helpers.changed_config('ckanext.xloader.clean_datastore_tables', toolkit_config_value):
            with mock.patch('ckanext.xloader.utils.XLoaderFormats.is_it_an_xloader_format') as mock_is_xloader_format:
                mock_is_xloader_format.return_value = mock_xloader_formats
                assert _should_remove_unsupported_resource_from_datastore(res_dict) == expected_result

    def _pending_task(self, resource_id):
        return {
            "entity_id": resource_id,
            "entity_type": "resource",
            "task_type": "xloader",
            "last_updated": str(datetime.datetime.utcnow()),
            "state": "pending",
            "key": "xloader",
            "value": "{}",
            "error": "{}",
        }
