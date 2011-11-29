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

    def test_internal_tag_link(self):
        """Asserts links like 'tag:test-tag' work"""
        instr = 'tag:test-tag foobar'
        exp = '<a href="/tag/test-tag">tag:test-tag</a> foobar'
        format = MarkdownFormat()
        out = format.to_html(instr)
        assert exp in out, '\nGot: %s\nWanted: %s' % (out, exp)

    def test_internal_tag_linked_with_quotes(self):
        """Asserts links like 'tag:"test-tag"' work"""
        instr = 'tag:"test-tag" foobar'
        exp = '<a href="/tag/test-tag">tag:"test-tag"</a> foobar'
        format = MarkdownFormat()
        out = format.to_html(instr)
        assert exp in out, '\nGot: %s\nWanted: %s' % (out, exp)

    def test_internal_tag_linked_with_quotes_and_space(self):
        """Asserts links like 'tag:"test tag"' work"""
        instr = 'tag:"test tag" foobar'
        exp = '<a href="/tag/test%20tag">tag:"test tag"</a> foobar'
        format = MarkdownFormat()
        out = format.to_html(instr)
        assert exp in out, '\nGot: %s\nWanted: %s' % (out, exp)

    def test_internal_tag_with_no_opening_quote_only_matches_single_word(self):
        """Asserts that without an opening quote only one word is matched"""
        instr = 'tag:test tag" foobar' # should match 'tag:test'
        exp = '<a href="/tag/test">tag:test</a> tag" foobar'
        format = MarkdownFormat()
        out = format.to_html(instr)
        assert exp in out, '\nGot: %s\nWanted: %s' % (out, exp)

    def test_internal_tag_with_no_opening_quote_wont_match_the_closing_quote(self):
        """Asserts that 'tag:test" tag' is matched, but to 'tag:test'"""
        instr = 'tag:test" foobar' # should match 'tag:test'
        exp = '<a href="/tag/test">tag:test</a>" foobar'
        format = MarkdownFormat()
        out = format.to_html(instr)
        assert exp in out, '\nGot: %s\nWanted: %s' % (out, exp)

    def test_internal_tag_with_no_closing_quote_does_not_match(self):
        """Asserts that without an opening quote only one word is matched"""
        instr = 'tag:"test tag foobar'
        format = MarkdownFormat()
        out = format.to_html(instr)
        assert "<a href" not in out

    def test_tag_names_match_simple_punctuation(self):
        """Asserts punctuation and capital letters are matched in the tag name"""
        instr = 'tag:"Test- _." foobar'
        exp = '<a href="/tag/Test-%20_.">tag:"Test- _."</a> foobar'
        format = MarkdownFormat()
        out = format.to_html(instr)
        assert exp in out, '\nGot: %s\nWanted: %s' % (out, exp)

    def test_tag_names_do_not_match_commas(self):
        """Asserts commas don't get matched as part of a tag name"""
        instr = 'tag:Test,tag foobar'
        exp = '<a href="/tag/Test">tag:Test</a>,tag foobar'
        format = MarkdownFormat()
        out = format.to_html(instr)
        assert exp in out, '\nGot: %s\nWanted: %s' % (out, exp)

    def test_tag_names_dont_match_non_space_whitespace(self):
        """Asserts that the only piece of whitespace matched in a tagname is a space"""
        whitespace_characters = '\t\n\r\f\v'
        for ch in whitespace_characters:
            instr = 'tag:Bad' + ch + 'space'
            exp = '<a href="/tag/Bad">tag:Bad</a>'
            format = MarkdownFormat()
            out = format.to_html(instr)
            assert exp in out, '\nGot: %s\nWanted: %s' % (out, exp)
    
    def test_tag_names_with_unicode_alphanumeric(self):
        """Asserts that unicode alphanumeric characters are captured"""
        instr = u'tag:"Japanese katakana \u30a1" blah'
        exp = u'<a href="/tag/Japanese%20katakana%20%E3%82%A1">tag:"Japanese katakana \u30a1"</a>'
        format = MarkdownFormat()
        out = format.to_html(instr)
        assert exp in out, u'\nGot: %s\nWanted: %s' % (out, exp)

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

    def test_multiline_links(self):
        instr = u'''I get 10 times more traffic from [Google][] than from
[Yahoo][] or [MSN][].

  [google]: http://google.com/        "Google"
  [yahoo]:  http://search.yahoo.com/  "Yahoo Search"
  [msn]:    http://search.msn.com/    "MSN Search"'''
        exp = '''I get 10 times more traffic from <a href="http://google.com/" title="Google">Google</a> than from
   <a href="http://search.yahoo.com/" title="Yahoo Search">Yahoo</a> or <a href="http://search.msn.com/" title="MSN Search">MSN</a>.'''
        # NB when this is put into Genshi, it will close the tag for you.
        format = MarkdownFormat()
        out = format.to_html(instr)
        assert exp in out, '\nGot: %s\nWanted: %s' % (out, exp)
