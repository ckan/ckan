# encoding: utf-8

import datetime
import pytest
import six
import hashlib

from ckan.common import config

import ckan.lib.helpers as h


WITH_HTML = u"""Data exposed: &mdash;
Size of dump and data set: size?
Notes: this is the classic RDF source but historically has had some problems with RDF correctness.
"""

WITH_UNICODE = u"""[From the project website] This project collects information on China’s foreign aid from the China Commerce Yearbook (中国商务年鉴) and the Almanac of China’s Foreign Economic Relations & Trade (中国对外经济贸易年间), published annually by China’s Ministry of Commerce (MOFCOM). Data is reported for each year between 1990 and 2005, with the exception of 2002, in which year China’s Ministry of Commerce published no project-level data on its foreign aid giving."""


class TestHelpers(object):
    def test_extract_markdown(self):
        assert "Data exposed" in h.markdown_extract(WITH_HTML)
        assert "collects information" in h.markdown_extract(WITH_UNICODE)

    def test_datetime_to_date_str(self):
        res = datetime.datetime(2008, 4, 13, 20, 40, 20, 123456).isoformat()
        assert res == "2008-04-13T20:40:20.123456"

    def test_date_str_to_datetime_date_only(self):
        res = h.date_str_to_datetime("2008-04-13")
        assert res == datetime.datetime(2008, 4, 13)

    def test_date_str_to_datetime(self):
        res = h.date_str_to_datetime("2008-04-13T20:40:20.123456")
        assert res == datetime.datetime(2008, 4, 13, 20, 40, 20, 123456)

    def test_date_str_to_datetime_without_microseconds(self):
        # This occurs in ckan.net timestamps - not sure how they appeared
        res = h.date_str_to_datetime("2008-04-13T20:40:20")
        assert res == datetime.datetime(2008, 4, 13, 20, 40, 20)

    def test_date_str_to_datetime_with_timezone(self):
        with pytest.raises(ValueError):
            h.date_str_to_datetime("2008-04-13T20:40:20-01:30")

    def test_date_str_to_datetime_with_timezone_without_colon(self):
        with pytest.raises(ValueError):
            h.date_str_to_datetime("2008-04-13T20:40:20-0130")

    def test_date_str_to_datetime_with_garbage_on_end(self):
        with pytest.raises(ValueError):
            h.date_str_to_datetime("2008-04-13T20:40:20foobar")

    def test_date_str_to_datetime_with_ambiguous_microseconds(self):
        res = h.date_str_to_datetime("2008-04-13T20:40:20.1234")
        assert res == datetime.datetime(2008, 4, 13, 20, 40, 20, 123400)

    def test_gravatar(self):
        email = "zephod@gmail.com"
        expected = '<img src="//gravatar.com/avatar/7856421db6a63efa5b248909c472fbd2?s=200&amp;d=mm"'

        email_hash = hashlib.md5(six.ensure_binary(email)).hexdigest()
        res = h.gravatar(email_hash, 200, default="mm")
        assert expected in res

    def test_gravatar_config_set_default(self):
        """Test when default gravatar is None, it is pulled from the config file"""
        email = "zephod@gmail.com"
        default = config.get("ckan.gravatar_default", "identicon")
        expected = '<img src="//gravatar.com/avatar/7856421db6a63efa5b248909c472fbd2?s=200&amp;d=%s"' % default
        email_hash = hashlib.md5(six.ensure_binary(email)).hexdigest()
        res = h.gravatar(email_hash, 200)
        assert expected in res

    def test_gravatar_encodes_url_correctly(self):
        """Test when the default gravatar is a url, it gets urlencoded"""
        email = "zephod@gmail.com"
        default = "http://example.com/images/avatar.jpg"
        expected = '<img src="//gravatar.com/avatar/7856421db6a63efa5b248909c472fbd2?s=200&amp;d=http%3A%2F%2Fexample.com%2Fimages%2Favatar.jpg"'

        email_hash = hashlib.md5(six.ensure_binary(email)).hexdigest()
        res = h.gravatar(email_hash, 200, default=default)
        assert expected in res

    def test_parse_rfc_2822_no_timezone_specified(self):
        """
        Parse "Tue, 15 Nov 1994 12:45:26" successfully.

        Assuming it's UTC.
        """
        dt = h.parse_rfc_2822_date("Tue, 15 Nov 1994 12:45:26")
        assert dt.isoformat() == "1994-11-15T12:45:26+00:00"

    @pytest.mark.skipif(six.PY3, reason="`email.utils` always assumes UTC")
    def test_parse_rfc_2822_no_timezone_specified_assuming_local(self):
        """
        Parse "Tue, 15 Nov 1994 12:45:26" successfully.

        Assuming it's local.
        """
        dt = h.parse_rfc_2822_date(
            "Tue, 15 Nov 1994 12:45:26", assume_utc=False
        )
        assert dt.isoformat() == "1994-11-15T12:45:26"
        assert dt.tzinfo is None

    def test_parse_rfc_2822_gmt_case(self):
        """
        Parse "Tue, 15 Nov 1994 12:45:26 GMT" successfully.

        GMT obs-zone specified
        """
        dt = h.parse_rfc_2822_date("Tue, 15 Nov 1994 12:45:26 GMT")
        assert dt.isoformat() == "1994-11-15T12:45:26+00:00"

    def test_parse_rfc_2822_with_offset(self):
        """
        Parse "Tue, 15 Nov 1994 12:45:26 +0700" successfully.
        """
        dt = h.parse_rfc_2822_date("Tue, 15 Nov 1994 12:45:26 +0700")
        assert dt.isoformat() == "1994-11-15T12:45:26+07:00"

    def test_escape_js(self):

        input_str = '{"type":"point", "desc":"Bla bla O\'hara.\\nNew line."}'

        expected_str = '{\\"type\\":\\"point\\", \\"desc\\":\\"Bla bla O\\\'hara.\\\\nNew line.\\"}'

        output_str = h.escape_js(input_str)

        assert output_str == expected_str

    @pytest.mark.usefixtures("clean_db", "with_request_context")
    def test_get_pkg_dict_extra(self):

        from ckan.lib.create_test_data import CreateTestData
        from ckan import model
        from ckan.logic import get_action

        CreateTestData.create()

        pkg_dict = get_action("package_show")(
            {"model": model, "user": u"tester"}, {"id": "annakarenina"}
        )

        assert h.get_pkg_dict_extra(pkg_dict, "genre") == "romantic novel"

        assert h.get_pkg_dict_extra(pkg_dict, "extra_not_found") is None

        assert (
            h.get_pkg_dict_extra(pkg_dict, "extra_not_found", "default_value")
            == "default_value"
        )

        model.repo.rebuild_db()
