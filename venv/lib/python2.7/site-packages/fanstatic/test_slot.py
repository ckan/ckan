import pytest
from fanstatic import NeededResources, Library, Resource, Slot, SlotError

def test_fill_slot():
    needed = NeededResources()

    lib = Library('lib', '')

    slot = Slot(lib, '.js')
    a = Resource(lib, 'a.js', depends=[slot])

    b = Resource(lib, 'b.js')

    needed.need(a, {slot: b})

    resources = needed.resources()
    assert len(resources) == 2

    # verify filled slot is correctly
    assert resources[0].library is b.library
    assert resources[0].relpath is b.relpath

def test_dont_fill_required_slot():
    needed = NeededResources()

    lib = Library('lib', '')

    slot = Slot(lib, '.js')
    a = Resource(lib, 'a.js', depends=[slot])

    b = Resource(lib, 'b.js')

    needed.need(a)
    
    with pytest.raises(SlotError):
        resources = needed.resources()

def test_no_need_to_fill_in_not_required():
    needed = NeededResources()

    lib = Library('lib', '')

    slot = Slot(lib, '.js', required=False)
    a = Resource(lib, 'a.js', depends=[slot])

    needed.need(a)

    # slot wasn't required and not filled in, so filled slot doesn't show up
    assert needed.resources() == [a]
    
def test_fill_slot_wrong_extension():
    needed = NeededResources()

    lib = Library('lib', '')

    slot = Slot(lib, '.js')
    a = Resource(lib, 'a.js', depends=[slot])

    b = Resource(lib, 'b.css')

    needed.need(a, {slot: b})
    
    with pytest.raises(SlotError):
        resources = needed.resources()

def test_fill_slot_wrong_dependencies():
    needed = NeededResources()
    
    lib = Library('lib', '')

    slot = Slot(lib, '.js')
    a = Resource(lib, 'a.js', depends=[slot])

    c = Resource(lib, 'c.js')
    
    b = Resource(lib, 'b.js', depends=[c])

    needed.need(a, {slot: b})

    with pytest.raises(SlotError):
        resources = needed.resources()

def test_render_filled_slots():
    needed = NeededResources()

    lib = Library('lib', '')

    slot = Slot(lib, '.js')
    a = Resource(lib, 'a.js', depends=[slot])

    b = Resource(lib, 'b.js')

    needed.need(a, {slot: b})

    assert needed.render() == '''\
<script type="text/javascript" src="/fanstatic/lib/b.js"></script>
<script type="text/javascript" src="/fanstatic/lib/a.js"></script>'''

def test_slot_depends():
    
    needed = NeededResources()

    lib = Library('lib', '')

    c = Resource(lib, 'c.js')
    slot = Slot(lib, '.js', depends=[c])
    a = Resource(lib, 'a.js', depends=[slot])
    b = Resource(lib, 'b.js', depends=[c])
    
    needed.need(a, {slot: b})

    assert needed.render() == '''\
<script type="text/javascript" src="/fanstatic/lib/c.js"></script>
<script type="text/javascript" src="/fanstatic/lib/b.js"></script>
<script type="text/javascript" src="/fanstatic/lib/a.js"></script>'''

def test_slot_depends_subset():
    needed = NeededResources()

    lib = Library('lib', '')

    c = Resource(lib, 'c.js')
    slot = Slot(lib, '.js', depends=[c])
    a = Resource(lib, 'a.js', depends=[slot])
    b = Resource(lib, 'b.js', depends=[])
    
    needed.need(a, {slot: b})

    assert needed.render() == '''\
<script type="text/javascript" src="/fanstatic/lib/c.js"></script>
<script type="text/javascript" src="/fanstatic/lib/b.js"></script>
<script type="text/javascript" src="/fanstatic/lib/a.js"></script>'''
    
def test_slot_depends_incorrect():
    needed = NeededResources()

    lib = Library('lib', '')

    c = Resource(lib, 'c.js')
    slot = Slot(lib, '.js', depends=[c])
    a = Resource(lib, 'a.js', depends=[slot])
    d = Resource(lib, 'd.js')
    b = Resource(lib, 'b.js', depends=[d])
    
    needed.need(a, {slot: b})

    with pytest.raises(SlotError):
        needed.render()
  
def test_slot_minified():
    needed = NeededResources(minified=True)

    lib = Library('lib', '')

    slot = Slot(lib, '.js')
    a = Resource(lib, 'a.js', depends=[slot])

    b = Resource(lib, 'b.js', minified='b-min.js')

    needed.need(a, {slot: b})
    assert needed.render() == '''\
<script type="text/javascript" src="/fanstatic/lib/b-min.js"></script>
<script type="text/javascript" src="/fanstatic/lib/a.js"></script>'''
