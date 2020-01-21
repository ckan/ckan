# -*- coding: utf-8 -*-


from ckan.cli.cli import ckan


def test_build_and_clean(cli, ckan_config, tmpdir, monkeypatch):
    """After build, there are some folders with assets inside
    `%(ckan.storage_path)/webassets`. And after cleaning they must
    be empty.

    """
    monkeypatch.setitem(ckan_config, u'ckan.storage_path', str(tmpdir))
    cli.invoke(ckan, [u'asset', u'build'])
    assert len(tmpdir.listdir()) == 1
    webassets_folder = tmpdir.listdir()[0]
    assert webassets_folder.basename == u'webassets'
    for folder in webassets_folder.listdir():
        if not folder.isdir():
            continue
        assert folder.listdir()

    cli.invoke(ckan, [u'asset', u'clean'])
    for folder in webassets_folder.listdir():
        if not folder.isdir():
            continue
        assert not folder.listdir()
