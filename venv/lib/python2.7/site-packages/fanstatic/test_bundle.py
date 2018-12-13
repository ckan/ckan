from fanstatic import Library, Resource, NeededResources

from fanstatic.core import bundle_resources, Bundle

def test_bundle_resources():
    foo = Library('foo', '')
    x1 = Resource(foo, 'a.css')
    x2 = Resource(foo, 'b.css')

    bundle = bundle_resources([x1, x2])
    assert len(bundle) == 1
    assert isinstance(bundle[0], Bundle)

    x3 = Resource(foo, 'c.css', dont_bundle=True)
    # x3 is not bundle safe.
    bundle = bundle_resources([x1, x3])
    assert len(bundle) == 2
    # We don't create bundles of one element.
    assert bundle[0] == x1
    assert bundle[1] == x3

    # x2 and x1 are not bundled because x3 is in the way.
    # (sort_resources in NeededResources fixes the sorting)
    bundle = bundle_resources([x1, x3, x2])
    assert bundle == [x1, x3, x2]

    # XXX sort_resources does not take care of this for us:
    needed = NeededResources(bundle=True)
    needed.need(x1)
    needed.need(x3)
    needed.need(x2)
    # The resources are sorted by renderer order, library dependencies
    # and resource dependencies.
    bundle = bundle_resources(needed.resources())
    assert len(bundle) == 2
    assert isinstance(bundle[0], Bundle)
    assert bundle[1] == x3

    bar = Library('bar', '')
    y1 = Resource(bar, 'y1.css')
    y2 = Resource(bar, 'y2.css')

    bundle = bundle_resources([x1, x2, y1, y2])
    assert len(bundle) == 2

    y3 = Resource(bar, 'subdir/y3.css')
    y4 = Resource(bar, 'subdir/y4.css')
    bundle = bundle_resources([y1, y2, y3, y4])
    assert len(bundle) == 2


def test_render_bundle():
    foo = Library('foo', '')
    x1 = Resource(foo, 'a.css')
    x2 = Resource(foo, 'b.css')
    x3 = Resource(foo, 'c.css', dont_bundle=True)
    needed = NeededResources(resources=[x1, x2, x3])
    assert needed.render() == '''<link rel="stylesheet" type="text/css" href="/fanstatic/foo/a.css" />
<link rel="stylesheet" type="text/css" href="/fanstatic/foo/b.css" />
<link rel="stylesheet" type="text/css" href="/fanstatic/foo/c.css" />'''

    needed = NeededResources(resources=[x1, x2, x3], bundle=True)
    assert needed.render() == '''<link rel="stylesheet" type="text/css" href="/fanstatic/foo/:bundle:a.css;b.css" />
<link rel="stylesheet" type="text/css" href="/fanstatic/foo/c.css" />'''

    x4 = Resource(foo, 'subdir/subdir/x4.css')
    x5 = Resource(foo, 'subdir/subdir/x5.css')
    needed = NeededResources(resources=[x1, x2, x4, x5], bundle=True)
    assert needed.render() == '''<link rel="stylesheet" type="text/css" href="/fanstatic/foo/:bundle:a.css;b.css" />
<link rel="stylesheet" type="text/css" href="/fanstatic/foo/subdir/subdir/:bundle:x4.css;x5.css" />'''

