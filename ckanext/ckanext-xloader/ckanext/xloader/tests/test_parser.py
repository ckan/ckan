# -*- coding: utf-8 -*-
import os
import pytest

from decimal import Decimal
from datetime import datetime

from tabulator import Stream
from ckanext.xloader.parser import TypeConverter

csv_filepath = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "samples", "date_formats.csv")
)


class TestParser(object):
    def test_simple(self):
        with Stream(csv_filepath, format='csv',
                    post_parse=[TypeConverter().convert_types]) as stream:
            assert stream.sample == [
                [
                    'date',
                    'temperature',
                    'place'
                ],
                [
                    datetime(2011, 1, 2, 0, 0),
                    Decimal('-1'),
                    'Galway'
                ],
                [
                    datetime(2011, 1, 3, 0, 0),
                    Decimal('0.5'),
                    'Galway'
                ],
                [
                    datetime(2011, 1, 2, 0, 0),
                    Decimal('5'),
                    'Berkeley'
                ],
                [
                    datetime(2003, 11, 1, 0, 0),
                    Decimal('6'),
                    'Berkeley'
                ],
            ]

    @pytest.mark.ckan_config("ckanext.xloader.parse_dates_dayfirst", True)
    def test_dayfirst(self):
        print('test_dayfirst')
        with Stream(csv_filepath, format='csv',
                    post_parse=[TypeConverter().convert_types]) as stream:
            assert stream.sample == [
                [
                    'date',
                    'temperature',
                    'place'
                ],
                [
                    datetime(2011, 1, 2, 0, 0),
                    Decimal('-1'),
                    'Galway'
                ],
                [
                    datetime(2011, 3, 1, 0, 0),
                    Decimal('0.5'),
                    'Galway'
                ],
                [
                    datetime(2011, 2, 1, 0, 0),
                    Decimal('5'),
                    'Berkeley'
                ],
                [
                    datetime(2003, 1, 11, 0, 0),
                    Decimal('6'),
                    'Berkeley'
                ],
            ]

    @pytest.mark.ckan_config("ckanext.xloader.parse_dates_yearfirst", True)
    def test_yearfirst(self):
        print('test_yearfirst')
        with Stream(csv_filepath, format='csv',
                    post_parse=[TypeConverter().convert_types]) as stream:
            assert stream.sample == [
                [
                    'date',
                    'temperature',
                    'place'
                ],
                [
                    datetime(2011, 1, 2, 0, 0),
                    Decimal('-1'),
                    'Galway'
                ],
                [
                    datetime(2011, 1, 3, 0, 0),
                    Decimal('0.5'),
                    'Galway'
                ],
                [
                    datetime(2011, 1, 2, 0, 0),
                    Decimal('5'),
                    'Berkeley'
                ],
                [
                    datetime(2011, 1, 3, 0, 0),
                    Decimal('6'),
                    'Berkeley'
                ],
            ]

    @pytest.mark.ckan_config("ckanext.xloader.parse_dates_dayfirst", True)
    @pytest.mark.ckan_config("ckanext.xloader.parse_dates_yearfirst", True)
    def test_yearfirst_dayfirst(self):
        with Stream(csv_filepath, format='csv',
                    post_parse=[TypeConverter().convert_types]) as stream:
            assert stream.sample == [
                [
                    'date',
                    'temperature',
                    'place'
                ],
                [
                    datetime(2011, 1, 2, 0, 0),
                    Decimal('-1'),
                    'Galway'
                ],
                [
                    datetime(2011, 3, 1, 0, 0),
                    Decimal('0.5'),
                    'Galway'
                ],
                [
                    datetime(2011, 2, 1, 0, 0),
                    Decimal('5'),
                    'Berkeley'
                ],
                [
                    datetime(2011, 3, 1, 0, 0),
                    Decimal('6'),
                    'Berkeley'
                ],
            ]
