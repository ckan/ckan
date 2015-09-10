import ckan.lib.helpers as h

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
        out = h.render_markdown(instr)
        assert out == exp

    def test_markdown_blank(self):
        instr = None
        out = h.render_markdown(instr)
        assert out == ''

    def test_evil_markdown(self):
        instr = 'Evil <script src="http://evilserver.net/evil.js";>'
        exp = '''<p>Evil \n</p>'''
        out = h.render_markdown(instr)
        assert out == exp, out

    def test_internal_link(self):
        instr = 'dataset:test-_pkg'
        exp = '<p><a href="/dataset/test-_pkg">dataset:test-_pkg</a>\n</p>'
        out = h.render_markdown(instr)
        assert exp in out, '\nGot: %s\nWanted: %s' % (out, exp)

    def test_internal_tag_link(self):
        """Asserts links like 'tag:test-tag' work"""
        instr = 'tag:test-tag foobar'
        exp = '<a href="/tag/test-tag">tag:test-tag</a> foobar'
        out = h.render_markdown(instr)
        assert exp in out, '\nGot: %s\nWanted: %s' % (out, exp)

    def test_internal_tag_linked_with_quotes(self):
        """Asserts links like 'tag:"test-tag"' work"""
        instr = 'tag:"test-tag" foobar'
        exp = '<p><a href="/tag/test-tag">tag:&#34;test-tag&#34;</a> foobar\n</p>'
        out = h.render_markdown(instr)
        assert exp in out, '\nGot: %s\nWanted: %s' % (out, exp)

    def test_internal_tag_linked_with_quotes_and_space(self):
        """Asserts links like 'tag:"test tag"' work"""
        instr = 'tag:"test tag" foobar'
        exp = '<p><a href="/tag/test%20tag">tag:&#34;test tag&#34;</a> foobar\n</p>'
        out = h.render_markdown(instr)
        assert exp in out, '\nGot: %s\nWanted: %s' % (out, exp)

    def test_internal_tag_with_no_opening_quote_only_matches_single_word(self):
        """Asserts that without an opening quote only one word is matched"""
        instr = 'tag:test tag" foobar'  # should match 'tag:test'
        exp = '<a href="/tag/test">tag:test</a> tag" foobar'
        out = h.render_markdown(instr)
        assert exp in out, '\nGot: %s\nWanted: %s' % (out, exp)

    def test_internal_tag_with_no_opening_quote_wont_match_the_closing_quote(self):
        """Asserts that 'tag:test" tag' is matched, but to 'tag:test'"""
        instr = 'tag:test" foobar'  # should match 'tag:test'
        exp = '<a href="/tag/test">tag:test</a>" foobar'
        out = h.render_markdown(instr)
        assert exp in out, '\nGot: %s\nWanted: %s' % (out, exp)

    def test_internal_tag_with_no_closing_quote_does_not_match(self):
        """Asserts that without an opening quote only one word is matched"""
        instr = 'tag:"test tag foobar'
        out = h.render_markdown(instr)
        assert "<a href" not in out

    def test_tag_names_match_simple_punctuation(self):
        """Asserts punctuation and capital letters are matched in the tag name"""
        instr = 'tag:"Test- _." foobar'
        exp = '<p><a href="/tag/Test-%20_.">tag:&#34;Test- _.&#34;</a> foobar\n</p>'
        out = h.render_markdown(instr)
        assert exp in out, '\nGot: %s\nWanted: %s' % (out, exp)

    def test_tag_names_do_not_match_commas(self):
        """Asserts commas don't get matched as part of a tag name"""
        instr = 'tag:Test,tag foobar'
        exp = '<a href="/tag/Test">tag:Test</a>,tag foobar'
        out = h.render_markdown(instr)
        assert exp in out, '\nGot: %s\nWanted: %s' % (out, exp)

    def test_tag_names_dont_match_non_space_whitespace(self):
        """Asserts that the only piece of whitespace matched in a tagname is a space"""
        whitespace_characters = '\t\n\r\f\v'
        for ch in whitespace_characters:
            instr = 'tag:Bad' + ch + 'space'
            exp = '<a href="/tag/Bad">tag:Bad</a>'
            out = h.render_markdown(instr)
            assert exp in out, '\nGot: %s\nWanted: %s' % (out, exp)

    def test_tag_names_with_unicode_alphanumeric(self):
        """Asserts that unicode alphanumeric characters are captured"""
        instr = u'tag:"Japanese katakana \u30a1" blah'
        exp = u'<p><a href="/tag/Japanese%20katakana%20%E3%82%A1">tag:&#34;Japanese katakana \u30a1&#34;</a> blah\n</p>'
        out = h.render_markdown(instr)
        assert exp in out, u'\nGot: %s\nWanted: %s' % (out, exp)

    def test_normal_link(self):
        instr = 'http://somelink/'
        exp = '<a href="http://somelink/" target="_blank" rel="nofollow">http://somelink/</a>'
        out = h.render_markdown(instr)
        assert exp in out, '\nGot: %s\nWanted: %s' % (out, exp)

        instr = 'http://somelink.com/#anchor'
        exp = '<a href="http://somelink.com/#anchor" target="_blank" rel="nofollow">http://somelink.com/#anchor</a>'
        out = h.render_markdown(instr)
        assert exp in out, '\nGot: %s\nWanted: %s' % (out, exp)

        instr = 'http://www.somelink.com/#anchor'
        exp = '<a href="http://www.somelink.com/#anchor" target="_blank" rel="nofollow">http://www.somelink.com/#anchor</a>'
        out = h.render_markdown(instr)
        assert exp in out, '\nGot: %s\nWanted: %s' % (out, exp)

    def test_auto_link(self):
        instr = 'http://somelink.com'
        exp = '<a href="http://somelink.com" target="_blank" rel="nofollow">http://somelink.com</a>'
        out = h.render_markdown(instr)
        assert exp in out, '\nGot: %s\nWanted: %s' % (out, exp)

    def test_auto_link_after_whitespace(self):
        instr = 'go to http://somelink.com'
        exp = 'go to <a href="http://somelink.com" target="_blank" rel="nofollow">http://somelink.com</a>'
        out = h.render_markdown(instr)
        assert exp in out, '\nGot: %s\nWanted: %s' % (out, exp)

    def test_malformed_link_1(self):
        instr = u'<a href=\u201dsomelink\u201d>somelink</a>'
        exp = '<p>somelink\n</p>'
        out = h.render_markdown(instr)
        assert exp in out, '\nGot: %s\nWanted: %s' % (out, exp)

    def test_multiline_links(self):
        instr = u'''I get 10 times more traffic from [Google][] than from
[Yahoo][] or [MSN][].

  [google]: http://google.com/        "Google"
  [yahoo]:  http://search.yahoo.com/  "Yahoo Search"
  [msn]:    http://search.msn.com/    "MSN Search"'''
        exp = '''<p>I get 10 times more traffic from <a href="http://google.com/" title="Google">Google</a> than from
   <a href="http://search.yahoo.com/" title="Yahoo Search">Yahoo</a> or <a href="http://search.msn.com/" title="MSN Search">MSN</a>.
</p>'''
        # NB when this is put into Genshi, it will close the tag for you.
        out = h.render_markdown(instr)
        assert exp in out, '\nGot: %s\nWanted: %s' % (out, exp)
