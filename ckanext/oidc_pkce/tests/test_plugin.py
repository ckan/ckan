import pytest

import ckan.plugins as p


@pytest.mark.ckan_config("ckan.plugins", "oidc_pkce")
@pytest.mark.usefixtures("with_plugins")
def test_plugin():
    assert p.plugin_loaded("oidc_pkce")
