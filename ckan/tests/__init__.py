"""Pylons application test package

When the test runner finds and executes tests within this directory,
this file will be loaded to setup the test environment.

It registers the root directory of the project in sys.path and
pkg_resources, in case the project hasn't been installed with
setuptools. It also initializes the application via websetup (paster
setup-app) with the project's test.ini configuration file.
"""
import os
import sys
import re
from unittest import TestCase

import sgmllib
import pkg_resources
import paste.fixture
import paste.script.appinstall
from paste.deploy import loadapp
from routes import url_for

from ckan.lib.create_test_data import CreateTestData

__all__ = ['url_for',
        'TestController',
        'CreateTestData',
        ]

here_dir = os.path.dirname(os.path.abspath(__file__))
conf_dir = os.path.dirname(os.path.dirname(here_dir))

sys.path.insert(0, conf_dir)
pkg_resources.working_set.add_entry(conf_dir)
pkg_resources.require('Paste')
pkg_resources.require('PasteScript')

test_file = os.path.join(conf_dir, 'test.ini')

cmd = paste.script.appinstall.SetupCommand('setup-app')
cmd.run([test_file])

import ckan.model as model
model.repo.rebuild_db()

# A simple helper class to cleanly strip HTML from a response.
class Stripper(sgmllib.SGMLParser):
    def __init__(self):
        sgmllib.SGMLParser.__init__(self)

    def strip(self, html):
        self.str = ""
        self.feed(html)
        self.close()
        return ' '.join(self.str.split())

    def handle_data(self, data):
        self.str += data

class TestController(object):

    def __init__(self, *args, **kwargs):
        wsgiapp = loadapp('config:test.ini', relative_to=conf_dir)
        self.app = paste.fixture.TestApp(wsgiapp)

    def create_100_packages(self):
        rev = model.repo.new_revision()
        for i in range(0,100):
            name = u"testpackage%s" % i
            model.Session.add(model.Package(name=name))
        model.Session.commit()
        model.Session.remove()

    def purge_100_packages(self):
        listRegister = self.get_model().packages
        for i in range(0,100):
            name = u"testpackage%s" % i
            pkg = model.Package.by_name(name)
            pkg.purge(name)
        model.Session.commit()
        model.Session.remove()

    def create_200_tags(self):
        for i in range(0,200):
            name = u"testtag%s" % i
            model.Session.add(model.Tag(name=name))
            print "Created tag: %s" % name
        model.Session.commit()
        model.Session.remove()

    def purge_200_tags(self):
        for i in range(0,200):
            name = u"testtag%s" % i
            tag = model.Tag.by_name(name)
            tag.purge()
        model.Session.commit()
        model.Session.remove()

    @classmethod
    def clear_all_tst_ratings(self):
        ratings = model.Session.query(model.Rating).filter_by(package=model.Package.by_name(u'annakarenina')).all()
        ratings += model.Session.query(model.Rating).filter_by(package=model.Package.by_name(u'warandpeace')).all()
        for rating in ratings[:]:
            model.Session.delete(rating)
        model.repo.commit_and_remove()

    def main_div(self, html):
        'strips html to just the <div id="main"> section'
        the_html = html.body.decode('utf8')
        return the_html[the_html.find(u'<div id="main">'):the_html.find(u'<!-- /main -->')]

    def preview_div(self, html):
        'strips html to just the <div id="preview"> section'
        the_html = html.body.decode('utf8')
        preview_html = the_html[the_html.find(u'<div id="preview"'):the_html.find(u'<!-- /preview -->')]
        assert preview_html, the_html
        return preview_html

    def sidebar(self, html):
        'strips html to just the <div id="primary"> section'
        the_html = str(html)
        return the_html[the_html.find('<div id="primary"'):the_html.find('<div id="main">')]

    def strip_tags(self, res):
        '''Call strip_tags on a TestResponse object to strip any and all HTML and normalise whitespace.'''
        return Stripper().strip(str(res))

    def check_named_element(self, html, tag_name, *html_to_find):
        '''Searches in the html and returns True if it can find a particular
        tag and all its subtags & data which contains all the of the
        html_to_find'''
        named_element_re = re.compile('(<(%(tag)s\w*).*?>.*?</%(tag)s>)' % {'tag':tag_name}) 
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
        assert 0, "Couldn't find %s in html. Closest matches were:\n%s" % (', '.join(["'%s'" % html.encode('utf8') for html in html_to_find]), '\n'.join([tag.encode('utf8') for tag in partly_matching_tags]))
