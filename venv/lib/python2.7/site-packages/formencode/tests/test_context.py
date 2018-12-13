from nose.tools import assert_raises

from formencode.context import Context, ContextRestoreError

c1 = Context(default=None)
c2 = Context()


def test_one():
    state = c1.set(foo=1)
    assert_is(c1, 'foo', 1)
    state.restore()
    assert_is(c1, 'foo', None)
    state = c1.set(foo=2)
    state2 = c2.set(foo='test')
    assert_is(c1, 'foo', 2)
    assert_is(c2, 'foo', 'test')
    change_state(c1, assert_is, c1, 'foo', 3, foo=3)
    assert_is(c1, 'foo', 2)
    state.restore()
    state2.restore()


def change_state(context, func, *args, **change):
    state = context.set(**change)
    try:
        return func(*args)
    finally:
        state.restore()


def test_fail():
    c3 = Context()
    res1 = c3.set(a=1)
    res2 = c3.set(b=2)
    assert_raises(ContextRestoreError, res1.restore)
    assert c3.b == 2
    assert c3.a == 1
    res2.restore()
    res1.restore()


def assert_is(ob, attr, value):
    assert getattr(ob, attr) == value


def test_default():
    con = Context()
    res = con.set(a=2)
    con.set_default(a=4, b=1)
    assert con.b == 1
    assert con.a == 2
    res.restore()
    assert con.a == 4
