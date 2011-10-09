from ckan.misc import MarkdownFormat

class TestFormatText:

    def test_markdown(self):
        instr = '''# Hello World

**Some bolded text.**

*Some italicized text.*
'''
        exp = '''<h1>Hello World</h1>
<p><strong>Some bolded text.</strong>
</p>
<p><em>Some italicized text.</em>
</p>'''
        format = MarkdownFormat()
        out = format.to_html(instr)
        assert out == exp

    def test_markdown_blank(self):
        instr = None
        format = MarkdownFormat()
        out = format.to_html(instr)
        assert out == ''

    def test_evil_markdown(self):
        instr = 'Evil <script src="http://evilserver.net/evil.js";>'
        exp = '''<p>Evil [HTML_REMOVED]
</p>'''
        format = MarkdownFormat()
        out = format.to_html(instr)
        assert out == exp, out
        
    def test_internal_link(self):
        instr = 'package:test-_pkg'
        exp = '<a href="/package/test-_pkg">package:test-_pkg</a>'
        format = MarkdownFormat()
        out = format.to_html(instr)
        assert exp in out, '\nGot: %s\nWanted: %s' % (out, exp)

    def test_normal_link(self):
        instr = '<http://somelink/>'
        exp = '<a href="http://somelink/" target="_blank" rel="nofollow">http://somelink/</a>'
        format = MarkdownFormat()
        out = format.to_html(instr)
        assert exp in out, '\nGot: %s\nWanted: %s' % (out, exp)

    def test_auto_link(self):
        instr = 'http://somelink.com'
        exp = '<a href="http://somelink.com" target="_blank" rel="nofollow">http://somelink.com</a>'
        format = MarkdownFormat()
        out = format.to_html(instr)
        assert exp in out, '\nGot: %s\nWanted: %s' % (out, exp)

    def test_auto_link_after_whitespace(self):
        instr = 'go to http://somelink.com'
        exp = 'go to <a href="http://somelink.com" target="_blank" rel="nofollow">http://somelink.com</a>'
        format = MarkdownFormat()
        out = format.to_html(instr)
        assert exp in out, '\nGot: %s\nWanted: %s' % (out, exp)

    def test_malformed_link_1(self):
        instr = u'<a href=\u201dsomelink\u201d>somelink</a>'
        exp = '<a href="TAG MALFORMED" target="_blank" rel="nofollow">somelink</a>'
        format = MarkdownFormat()
        out = format.to_html(instr)
        assert exp in out, '\nGot: %s\nWanted: %s' % (out, exp)

    def test_malformed_link_2(self):
        instr = u'<a href="http://url.com> url >'
        exp = '<a href="TAG MALFORMED" target="_blank" rel="nofollow"> url &gt;'
        format = MarkdownFormat()
        out = format.to_html(instr)
        assert exp in out, '\nGot: %s\nWanted: %s' % (out, exp)

    def test_malformed_link_3(self):
        instr = u'<a href="http://url.com"> url'
        exp = '<a href="http://url.com" target="_blank" rel="nofollow"> url'
        # NB when this is put into Genshi, it will close the tag for you.
        format = MarkdownFormat()
        out = format.to_html(instr)
        assert exp in out, '\nGot: %s\nWanted: %s' % (out, exp)

