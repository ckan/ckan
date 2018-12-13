import webob

from datetime import datetime, timedelta

from fanstatic import LibraryRegistry, Library, Publisher, Delegator, Resource
from fanstatic.publisher import FOREVER


def test_resource(tmpdir):
    foo_library_dir = tmpdir.mkdir('foo')
    resource = tmpdir.join('foo').join('test.js')
    resource.write('/* a test */')

    libraries = LibraryRegistry(
        [Library('foo', foo_library_dir.strpath)])

    app = Publisher(libraries)

    request = webob.Request.blank('/foo/test.js')
    response = request.get_response(app)
    assert response.body == '/* a test */'


def test_just_publisher():
    app = Publisher({})
    request = webob.Request.blank('')
    response = request.get_response(app)
    assert response.status == '404 Not Found'

    request = webob.Request.blank('/')
    response = request.get_response(app)
    assert response.status == '404 Not Found'


def test_just_library(tmpdir):
    foo_library_dir = tmpdir.mkdir('foo')
    resource = tmpdir.join('foo').join('test.js')
    resource.write('/* a test */')

    libraries = LibraryRegistry([Library('foo', foo_library_dir.strpath)])

    app = Publisher(libraries)

    request = webob.Request.blank('/foo')
    response = request.get_response(app)
    assert response.status == '404 Not Found'


def test_unknown_library(tmpdir):
    foo_library_dir = tmpdir.mkdir('foo')
    resource = tmpdir.join('foo').join('test.js')
    resource.write('/* a test */')

    libraries = LibraryRegistry(
        [Library('foo', foo_library_dir.strpath)])

    app = Publisher(libraries)

    request = webob.Request.blank('/bar/')
    response = request.get_response(app)
    assert response.status == '404 Not Found'



def test_resource_version_skipped(tmpdir):
    foo_library_dir = tmpdir.mkdir('foo')
    resource = tmpdir.join('foo').join('test.js')
    resource.write('/* a test */')

    libraries = LibraryRegistry(
        [Library('foo', foo_library_dir.strpath)])

    app = Publisher(libraries)

    request = webob.Request.blank('/foo/:version:something/test.js')
    response = request.get_response(app)
    assert response.body == '/* a test */'


def test_resource_no_version_no_cache(tmpdir):
    foo_library_dir = tmpdir.mkdir('foo')
    resource = tmpdir.join('foo').join('test.js')
    resource.write('/* a test */')

    libraries = LibraryRegistry(
        [Library('foo', foo_library_dir.strpath)])

    app = Publisher(libraries)

    request = webob.Request.blank('/foo/test.js')
    response = request.get_response(app)
    assert response.body == '/* a test */'
    assert response.cache_control.max_age is None
    assert response.expires is None


def test_resource_hash_cache(tmpdir):
    foo_library_dir = tmpdir.mkdir('foo')
    resource = tmpdir.join('foo').join('test.js')
    resource.write('/* a test */')

    libraries = LibraryRegistry(
        [Library('foo', foo_library_dir.strpath)])

    app = Publisher(libraries)

    request = webob.Request.blank('/foo/:version:something/test.js')
    response = request.get_response(app)
    assert response.body == '/* a test */'
    assert response.cache_control.max_age == FOREVER
    # the test has just run and will take less than a full day to
    # run. we therefore expect the expires to be greater than
    # one_day_ago + FOREVER
    utc = response.expires.tzinfo  # get UTC as a hack
    one_day_ago = datetime.now(utc) - timedelta(days=1)
    future = one_day_ago + timedelta(seconds=FOREVER)
    assert response.expires > future


def test_resource_cache_only_for_success(tmpdir):
    foo_library_dir = tmpdir.mkdir('foo')

    libraries = LibraryRegistry(
        [Library('foo', foo_library_dir.strpath)])

    app = Publisher(libraries)

    request = webob.Request.blank('/foo/:version:something/nonexistent.js')
    response = request.get_response(app)
    assert response.status == '404 Not Found'
    assert response.cache_control.max_age is None
    assert response.expires is None


def test_delegator(tmpdir):
    foo_library_dir = tmpdir.mkdir('foo')
    resource = tmpdir.join('foo').join('test.js')
    resource.write('/* a test */')

    libraries = LibraryRegistry(
        [Library('foo', foo_library_dir.strpath)])

    publisher = Publisher(libraries)

    def real_app(environ, start_response):
        start_response('200 OK', [])
        return ['Hello world!']

    delegator = Delegator(real_app, publisher)

    request = webob.Request.blank('/fanstatic/foo/test.js')
    response = request.get_response(delegator)
    assert response.body == '/* a test */'

    # A deeper fanstatic.
    request = webob.Request.blank('/foo/bar/fanstatic/foo/test.js')
    response = request.get_response(delegator)
    assert response.body == '/* a test */'

    request = webob.Request.blank('/somethingelse')
    response = request.get_response(delegator)
    assert response.body == 'Hello world!'


def test_publisher_ignores(tmpdir):
    foo_library_dir = tmpdir.mkdir('foo')
    tmpdir.join('foo').mkdir('.svn').join('entries').write('secret')
    foo_library = Library('foo', foo_library_dir.strpath)

    publisher = Publisher(LibraryRegistry([foo_library]))
    request = webob.Request.blank('/foo/.svn/entries')
    response = request.get_response(publisher)
    assert response.body == 'secret'

    foo_library = Library('foo', foo_library_dir.strpath, ignores=['.svn'])
    publisher = Publisher(LibraryRegistry([foo_library]))
    request = webob.Request.blank('/foo/.svn/entries')
    response = request.get_response(publisher)
    assert response.status_int == 404

    foo_library.ignores.extend(['*.psd', '*.ttf'])
    tmpdir.join('foo').join('font.ttf').write('I am a font.')
    request = webob.Request.blank('/foo/font.ttf')
    response = request.get_response(publisher)
    assert response.status_int == 404

    tmpdir.join('foo').join('logo.psd').write('I am a logo.')
    request = webob.Request.blank('/foo/logo.psd')
    response = request.get_response(publisher)
    assert response.status_int == 404

    request = webob.Request.blank('/foo/:bundle:logo.psd')
    response = request.get_response(publisher)
    assert response.status_int == 404

def test_bundle_resources(tmpdir):
    foo_library_dir = tmpdir.mkdir('foo')
    foo = Library('foo', foo_library_dir.strpath)

    test1 = Resource(foo, 'test1.js')
    tmpdir.join('foo').join('test1.js').write('/* a test 1 */')
    test2 = Resource(foo, 'test2.js')
    tmpdir.join('foo').join('test2.js').write('/* a test 2 */')

    libraries = LibraryRegistry([foo])

    app = Publisher(libraries)

    request = webob.Request.blank('/')
    response = request.get_response(app)
    assert response.status_int == 404

    request = webob.Request.blank('/foo/:bundle:test1.js;test2.js')
    response = request.get_response(app)
    assert response.body == '''/* a test 1 */
/* a test 2 */'''
    assert response.cache_control.max_age is None

    request = webob.Request.blank('/foo/:version:123/:bundle:test1.js;test2.js')
    response = request.get_response(app)
    assert response
    assert response.cache_control.max_age is not None

    # Dirty bundles yield a 404:
    request = webob.Request.blank('/foo/:bundle:test1.js;test2.js;test1.js')
    response = request.get_response(app)
    assert response.status_int == 404

    request = webob.Request.blank('/foo/:bundle:XXX.js')
    response = request.get_response(app)
    assert response.status_int == 404

    request = webob.Request.blank('/foo/:bundle:/etc/passwd;/etc/shadow.js')
    response = request.get_response(app)
    assert response.status_int == 404

    request = webob.Request.blank('/foo/../:bundle:hacxor')
    response = request.get_response(app)
    assert response.status_int == 403

    subdir = tmpdir.join('foo').mkdir('sub').mkdir('sub')
    r1 = Resource(foo, 'sub/sub/r1.css')
    subdir.join('r1.css').write('r1')
    r2 = Resource(foo, 'sub/sub/r2.css')
    subdir.join('r2.css').write('r2')

    request = webob.Request.blank('/foo/sub/sub/:bundle:r1.css;r2.css')
    response = request.get_response(app)
    assert response.body == '''r1
r2'''

    r3 = Resource(foo, 'r3.css')
    # r3 does not exist, trigger bundleapp error.
    request = webob.Request.blank('/foo/:bundle:r3.css')
    response = request.get_response(app)
    assert response.status_int == 404

    r4 = Resource(foo, 'sub/sub/r4.css', depends=[r1, r2])
    subdir.join('r4.css').write('r4')
    request = webob.Request.blank('/foo/sub/sub/:bundle:r1.css;r2.css;r4.css')
    response = request.get_response(app)
    assert response.body == '''r1
r2
r4'''

    # An incorrect bundle, as the order of the paths does not correspond to
    # the dependency order of the Resources.
    request = webob.Request.blank('/foo/sub/sub/:bundle:r1.css;r4.css;r2.css')
    response = request.get_response(app)
    assert response.status_int == 404
