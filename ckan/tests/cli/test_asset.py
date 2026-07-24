import pytest
from ckan import types
from ckan.cli.cli import ckan
from click.testing import CliRunner
from typing import Any


@pytest.mark.usefixtures("with_extended_cli")
def test_build_and_clean(
    cli: CliRunner,
    ckan_config: types.FixtureCkanConfig,
    tmpdir: Any,
    monkeypatch: pytest.MonkeyPatch,
):
    """After build, there are some folders with assets inside webassets
    path. And after cleaning they must be empty.
    """
    monkeypatch.setitem(ckan_config, "ckan.webassets.path", tmpdir)
    cli.invoke(ckan, ["asset", "build"])

    for folder in tmpdir.listdir():
        if not folder.isdir():
            continue
        assert folder.listdir()

    cli.invoke(ckan, ["asset", "clean"])
    for folder in tmpdir.listdir():
        if not folder.isdir():
            continue
        assert not folder.listdir()
