from nose.tools import assert_equal

import ckan.lib.accept as accept

class TestAccept:
    def test_accept_invalid(self):
        ct, markup, ext = accept.parse_header(None)
        assert_equal( ct, "text/html; charset=utf-8")
        assert_equal( markup, True)
        assert_equal( ext, "html")

    def test_accept_invalid2(self):
        ct, markup, ext = accept.parse_header("")
        assert_equal( ct, "text/html; charset=utf-8")
        assert_equal( markup, True)
        assert_equal( ext, "html")

    def test_accept_invalid3(self):
        ct, markup, ext = accept.parse_header("wombles")
        assert_equal( ct, "text/html; charset=utf-8")
        assert_equal( markup, True)
        assert_equal( ext, "html")


    def test_accept_valid(self):
        a = "text/turtle,application/turtle,application/rdf+xml,text/plain;q=0.8,*/*;q=.5"
        ct, markup, ext = accept.parse_header(a)
        assert_equal( ct, "application/rdf+xml; charset=utf-8")
        assert_equal( markup, True)
        assert_equal( ext, "rdf")

    def test_accept_valid2(self):
        a = "text/turtle,application/turtle,application/rdf+xml;q=0.9,text/plain;q=0.8,*/*;q=.5"
        ct, markup, ext = accept.parse_header(a)
        assert_equal( ct, "application/rdf+xml; charset=utf-8")
        assert_equal( markup, True)
        assert_equal( ext, "rdf")

    def test_accept_valid4(self):
        a = "application/xml,application/xhtml+xml,text/html;q=0.9,text/plain;q=0.8,image/png,*/*;q=0.5"
        ct, markup, ext = accept.parse_header(a)
        assert_equal( ct, "text/html; charset=utf-8")
        assert_equal( markup, True)
        assert_equal( ext, "html")

    def test_accept_valid5(self):
        a = "application/rdf+xml;q=0.5,application/xhtml+xml,text/html;q=0.9"
        ct, markup, ext = accept.parse_header(a)
        assert_equal( ct, "text/html; charset=utf-8")
        assert_equal( markup, True)
        assert_equal( ext, "html")

    def test_accept_valid6(self):
        a = "application/rdf+xml;q=0.9,application/xhtml+xml,text/html;q=0.5"
        ct, markup, ext = accept.parse_header(a)
        assert_equal( ct, "application/rdf+xml; charset=utf-8")
        assert_equal( markup, True)
        assert_equal( ext, "rdf")
