import pytest
import ckan.tests.factories as factories

@pytest.fixture()
def with_datapusher_token(non_clean_db, ckan_config, monkeypatch):
    """Set mandatory datapusher option.

    It must be applied before `datapusher` plugin is loaded via `with_plugins`,
    but after DB initialization via `non_clean_db`.

    """
    token = factories.SysadminWithToken()["token"]
    monkeypatch.setitem(
        ckan_config,
        "ckan.datapusher.api_token",
        token,
    )

