
import doctest

from formencode.htmlgen import html

# A test value that can't be encoded as ascii:
uni_value = u'\xff'
str_value = uni_value if str is unicode else uni_value.encode('utf-8')


def test_basic():
    output = '<a href="test">hey there</a>'
    assert str(html.a(href='test')('hey there')) == output
    assert str(html.a('hey there')(href='test')) == output
    assert str(html.a(href='test', c='hey there')) == output
    assert str(html.a('hey there', href='test')) == output
    assert str(html.a(href='test')('hey ', 'there')) == output
    assert str(html.a(href='test')(['hey ', 'there'])) == output


def test_compound():
    output = '<b>Hey <i>you</i>!</b>'
    assert str(html.b('Hey ', html.i('you'), '!')) == output
    assert str(html.b()('Hey ')(html.i()('you'))('!')) == output
    inner = html('Hey ', html.i('you'), '!')
    assert html.str(inner) == 'Hey <i>you</i>!'
    assert str(inner) == 'Hey <i>you</i>!'
    assert str(html.b(inner)) == output


def test_unicode():
    try:
        uni_value.encode('ascii')
    except ValueError:
        pass
    else:
        assert False, (
            "We need something that can't be ASCII-encoded: %r (%r)"
            % (uni_value, uni_value.encode('ascii')))
    assert unicode(html.b(uni_value)) == u'<b>%s</b>' % uni_value


def test_quote():
    assert html.quote('<hey>!') == '&lt;hey&gt;!'
    assert html.quote(uni_value) == str_value
    assert html.quote(None) == ''
    assert html.str(None) == ''
    assert str(html.b('<hey>')) == '<b>&lt;hey&gt;</b>'


def test_comment():

    def strip(s):
        """ElementTree in Py < 2.7 adds whitespace, strip this."""
        s = str(s).strip()
        if s.startswith('<!--') and s.endswith('-->'):
            s = '<!--%s-->' % s[4:-3].strip()
        return s

    assert strip(html.comment('test')) == '<!--test-->'
    assert strip(html.comment(uni_value)) == '<!--%s-->' % str_value
    assert strip(html.comment('test')('this')) == '<!--testthis-->'


def test_none():
    assert html.str(None) == ''
    assert str(html.b(class_=None)('hey')) == '<b>hey</b>'
    assert str(html.b(class_=' ')(None)) == '<b class=" " />'


def test_namespace():
    output = '<b tal:content="options/whatever" />'
    assert str(html.b(**{'tal:content': 'options/whatever'})) == output
    assert str(html.b(tal__content='options/whatever')) == output


if __name__ == '__main__':
    # It's like a super-mini py.test...
    for name, value in globals().iteritems():
        if name.startswith('test'):
            print name
            value()
    from formencode import htmlgen
    doctest.testmod(htmlgen)
    print 'doctest'
