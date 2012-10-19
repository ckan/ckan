import re
import sgmllib

import paste.fixture


class HtmlCheckMethods(object):
    '''A collection of methods to check properties of a html page, usually
    in the form returned by paster.'''
    
    def named_div(self, div_name, html):
        'strips html to just the <div id="DIV_NAME"> section'
        the_html = self._get_html_from_res(html)
        start_div = the_html.find(u'<div id="%s"' % div_name)
        end_div = the_html.find(u'<!-- #%s -->' % div_name)
        if end_div == -1:
            end_div = the_html.find(u'<!-- /%s -->' % div_name)
        div_html = the_html[start_div:end_div]
        assert div_html
        return div_html

    def main_div(self, html):
        'strips html to just the <div id="main"> section'
        return self.named_div('main', html)

    def sidebar(self, html):
        'strips html to just the <div id="primary"> section'
        return self.named_div('primary', html)

    def strip_tags(self, res):
        '''Call strip_tags on a TestResponse object to strip any and all HTML and normalise whitespace.'''
        if not isinstance(res, basestring):
            res = res.body.decode('utf-8')
        return Stripper().strip(res)    

    def check_named_element(self, html, tag_name, *html_to_find):
        '''Searches in the html and returns True if it can find a particular
        tag and all its subtags & data which contains all the of the
        html_to_find'''
        named_element_re = re.compile('(<(%(tag)s\w*).*?(>.*?</%(tag)s)?>)' % {'tag':tag_name}) 
        html_str = self._get_html_from_res(html)
        self._check_html(named_element_re, html_str.replace('\n', ''), html_to_find)

    def check_tag_and_data(self, html, *html_to_find):
        '''Searches in the html and returns True if it can find a tag and its
        PC Data immediately following it which contains all the of the
        html_to_find'''
        if not hasattr(self, 'tag_and_data_re'):
            self.tag_and_data_re = re.compile('(<(?P<tagname>\w*)[^>]*>[^<]*?</(?P=tagname)>)')
            # matches "<tag stuff> stuff </tag>"
        self._check_html(self.tag_and_data_re, html, html_to_find)

    def check_tag(self, html, *html_to_find):
        '''Searches in the html and returns True if it can find a tag which
        contains all the of the html_to_find'''
        if not hasattr(self, 'tag_re'):
            self.tag_re = re.compile('(<[^>]*>)')
        self._check_html(self.tag_re, html, html_to_find)

    def _get_html_from_res(self, html):
        if isinstance(html, paste.fixture.TestResponse):
            html_str = html.body.decode('utf8')
        elif isinstance(html, unicode):
            html_str = html
        elif isinstance(html, str):
            html_str = html.decode('utf8')
        else:
            raise TypeError
        return html_str # always unicode

    def _check_html(self, regex_compiled, html, html_to_find):
        html_to_find = [unicode(html_bit) for html_bit in html_to_find]
        partly_matching_tags = []
        html_str = self._get_html_from_res(html)
        for tag in regex_compiled.finditer(html_str):
            found_all=True
            for i, html_bit_to_find in enumerate(html_to_find):
                assert isinstance(html_bit_to_find, (str, unicode)), html_bit_to_find
                html_bit_to_find = unicode(html_bit_to_find)
                find_inverse = html_bit_to_find.startswith('!')
                if (find_inverse and html_bit_to_find[1:] in tag.group()) or \
                   (not find_inverse and html_bit_to_find not in tag.group()):
                    found_all = False
                    if i>0:
                        partly_matching_tags.append(tag.group())
                    break
            if found_all:
                return # found it
        # didn't find it
        if partly_matching_tags:
            assert 0, "Couldn't find %s in html. Closest matches were:\n%s" % (', '.join(["'%s'" % html.encode('utf8') for html in html_to_find]), '\n'.join([tag.encode('utf8') for tag in partly_matching_tags]))
        else:
            assert 0, "Couldn't find %s in html. Tags matched were:\n%s" % (', '.join(["'%s'" % html.encode('utf8') for html in html_to_find]), '\n'.join([tag.group() for tag in regex_compiled.finditer(html_str)]))



class Stripper(sgmllib.SGMLParser):
    '''A simple helper class to cleanly strip HTML from a response.'''
    def __init__(self):
        sgmllib.SGMLParser.__init__(self)

    def strip(self, html):
        self.str = u""
        self.feed(html)
        self.close()
        return u' '.join(self.str.split())

    def handle_data(self, data):
        self.str += data
