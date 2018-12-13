import time
import shutil
import os
from pkg_resources import resource_filename

from fanstatic.checksum import list_directory, md5, mtime
from fanstatic.checksum import VCS_NAMES, IGNORED_EXTENSIONS


def _copy_testdata(tmpdir):
    src = resource_filename('fanstatic', 'testdata/MyPackage')
    dst = tmpdir / 'MyPackage'
    shutil.copytree(src, str(dst))
    return dst


def test_list_directory(tmpdir):
    testdata_path = str(_copy_testdata(tmpdir))
    expected = [
        tmpdir.join('MyPackage/setup.py').strpath,
        tmpdir.join('MyPackage/MANIFEST.in').strpath,
        tmpdir.join('MyPackage/src/mypackage/__init__.py').strpath,
        tmpdir.join('MyPackage/src/mypackage/resources/style.css').strpath,
        ]
    found = list(list_directory(testdata_path, include_directories=False))
    assert sorted(found) == sorted(expected)

    expected.extend([
        tmpdir.join('MyPackage').strpath,
        tmpdir.join('MyPackage/src').strpath,
        tmpdir.join('MyPackage/src/mypackage').strpath,
        tmpdir.join('MyPackage/src/mypackage/resources').strpath,
    ])
    found = list(list_directory(testdata_path))
    assert sorted(found) == sorted(expected)


def test_list_directory_no_vcs_name(tmpdir):
    testdata_path = str(_copy_testdata(tmpdir))
    tmpdir.join('/MyPackage/.novcs').ensure(dir=True)
    tmpdir.join('/MyPackage/.novcs/foo').write('Contents of foo')
    expected = [
        tmpdir.join('MyPackage').strpath,
        tmpdir.join('MyPackage/.novcs').strpath,
        tmpdir.join('MyPackage/.novcs/foo').strpath,
        tmpdir.join('MyPackage/setup.py').strpath,
        tmpdir.join('MyPackage/MANIFEST.in').strpath,
        tmpdir.join('MyPackage/src').strpath,
        tmpdir.join('MyPackage/src/mypackage').strpath,
        tmpdir.join('MyPackage/src/mypackage/__init__.py').strpath,
        tmpdir.join('MyPackage/src/mypackage/resources').strpath,
        tmpdir.join('MyPackage/src/mypackage/resources/style.css').strpath,
        ]
    found = list(list_directory(testdata_path))
    assert sorted(found) == sorted(expected)


def test_list_directory_vcs_name(tmpdir):
    testdata_path = str(_copy_testdata(tmpdir))
    for name in VCS_NAMES:
        tmpdir.join('/MyPackage/%s' % name).ensure(dir=True)
        tmpdir.join('/MyPackage/%s/foo' % name).write('Contents of foo')
        expected = [
            tmpdir.join('MyPackage').strpath,
            tmpdir.join('MyPackage/setup.py').strpath,
            tmpdir.join('MyPackage/MANIFEST.in').strpath,
            tmpdir.join('MyPackage/src').strpath,
            tmpdir.join('MyPackage/src/mypackage').strpath,
            tmpdir.join('MyPackage/src/mypackage/__init__.py').strpath,
            tmpdir.join('MyPackage/src/mypackage/resources').strpath,
            tmpdir.join('MyPackage/src/mypackage/resources/style.css').strpath,
            ]
        found = list(list_directory(testdata_path))
        assert sorted(found) == sorted(expected)
        tmpdir.join('/MyPackage/%s' % name).remove(rec=True)


def test_list_directory_dot_file(tmpdir):
    testdata_path = str(_copy_testdata(tmpdir))
    tmpdir.join('/MyPackage/.woekie').ensure()
    expected = [
        tmpdir.join('MyPackage').strpath,
        tmpdir.join('MyPackage/.woekie').strpath,
        tmpdir.join('MyPackage/setup.py').strpath,
        tmpdir.join('MyPackage/MANIFEST.in').strpath,
        tmpdir.join('MyPackage/src').strpath,
        tmpdir.join('MyPackage/src/mypackage').strpath,
        tmpdir.join('MyPackage/src/mypackage/__init__.py').strpath,
        tmpdir.join('MyPackage/src/mypackage/resources').strpath,
        tmpdir.join('MyPackage/src/mypackage/resources/style.css').strpath,
        ]
    found = list(list_directory(testdata_path))
    assert sorted(found) == sorted(expected)


def test_list_directory_ignored_extensions(tmpdir):
    testdata_path = str(_copy_testdata(tmpdir))
    for ext in IGNORED_EXTENSIONS:
        tmpdir.join('/MyPackage/bar%s' % ext).ensure()
        expected = [
            tmpdir.join('MyPackage').strpath,
            tmpdir.join('MyPackage/setup.py').strpath,
            tmpdir.join('MyPackage/MANIFEST.in').strpath,
            tmpdir.join('MyPackage/src').strpath,
            tmpdir.join('MyPackage/src/mypackage').strpath,
            tmpdir.join('MyPackage/src/mypackage/__init__.py').strpath,
            tmpdir.join('MyPackage/src/mypackage/resources').strpath,
            tmpdir.join('MyPackage/src/mypackage/resources/style.css').strpath,
            ]
        found = list(list_directory(testdata_path))
        assert sorted(found) == sorted(expected)


def test_mtime(tmpdir):
    testdata_path = str(_copy_testdata(tmpdir))
    sleep = 0.02
    # Sleep extra long on filesystems that report in seconds
    # instead of milliseconds.
    if os.path.getmtime(os.curdir).is_integer():
        sleep += 1

    # Compute a first mtime for the test package:
    mtime_start = mtime(testdata_path)
    # Add a file (+ contents!) and see the mtime changed:
    tmpdir.join('/MyPackage/A').write('Contents for A')
    mtime_after_add = mtime(testdata_path)
    assert mtime_after_add != mtime_start

    # Remove the file again, the mtime changed:
    time.sleep(sleep) 
    tmpdir.join('/MyPackage/A').remove()
    mtime_after_remove = mtime(testdata_path)
    assert mtime_after_remove != mtime_after_add
    assert mtime_after_remove != mtime_start

    # Obviously, changing the contents will change the mtime too:
    tmpdir.join('/MyPackage/B').write('Contents for B')
    mtime_start = mtime(testdata_path)
    # Wait a split second in order to let the disk catch up.
    time.sleep(sleep)
    tmpdir.join('/MyPackage/B').write('Contents for B have changed')
    assert mtime(testdata_path) != mtime_start
    tmpdir.join('/MyPackage/B').remove()

    # Moving, or renaming a file should change the mtime:
    mtime_start = mtime(testdata_path)
    time.sleep(sleep)
    tmpdir.join('/MyPackage/setup.py').rename(
        tmpdir.join('/MyPackage/setup.py.renamed'))
    expected = [
        tmpdir.join('MyPackage').strpath,
        tmpdir.join('MyPackage/MANIFEST.in').strpath,
        tmpdir.join('MyPackage/setup.py.renamed').strpath,
        tmpdir.join('MyPackage/src').strpath,
        tmpdir.join('MyPackage/src/mypackage').strpath,
        tmpdir.join('MyPackage/src/mypackage/__init__.py').strpath,
        tmpdir.join('MyPackage/src/mypackage/resources').strpath,
        tmpdir.join('MyPackage/src/mypackage/resources/style.css').strpath,
        ]
    found = list(list_directory(testdata_path))
    assert sorted(found) == sorted(expected)
    assert mtime(testdata_path) != mtime_start


def test_md5(tmpdir):
    testdata_path = str(_copy_testdata(tmpdir))

    # Compute a first md5 for the test package:
    md5_start = md5(testdata_path)
    # Add a file (+ contents!) and see the md5 changed:
    tmpdir.join('/MyPackage/A').write('Contents for A')
    md5_after_add = md5(testdata_path)
    assert md5_after_add != md5_start

    # Remove the file again, the md5 is back to the previous one:
    # This is a difference from the mtime approach!
    tmpdir.join('/MyPackage/A').remove()
    md5_after_remove = md5(testdata_path)
    assert md5_after_remove != md5_after_add
    assert md5_after_remove == md5_start

    # Obviously, changing the contents will change the md5 too:
    tmpdir.join('/MyPackage/B').write('Contents for B')
    md5_start = md5(testdata_path)
    # Wait a split second in order to let the disk catch up.
    tmpdir.join('/MyPackage/B').write('Contents for B have changed')
    assert md5(testdata_path) != md5_start
    tmpdir.join('/MyPackage/B').remove()

    # Moving, or renaming a file should change the md5:
    md5_start = md5(testdata_path)
    tmpdir.join('/MyPackage/setup.py').rename(
        tmpdir.join('/MyPackage/setup.py.renamed'))
    expected = [
        tmpdir.join('MyPackage').strpath,
        tmpdir.join('MyPackage/MANIFEST.in').strpath,
        tmpdir.join('MyPackage/setup.py.renamed').strpath,
        tmpdir.join('MyPackage/src').strpath,
        tmpdir.join('MyPackage/src/mypackage').strpath,
        tmpdir.join('MyPackage/src/mypackage/__init__.py').strpath,
        tmpdir.join('MyPackage/src/mypackage/resources').strpath,
        tmpdir.join('MyPackage/src/mypackage/resources/style.css').strpath,
        ]
    found = list(list_directory(testdata_path))
    assert sorted(found) == sorted(expected)
    assert md5(testdata_path) != md5_start

