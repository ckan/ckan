# -*- coding: utf-8 -*-
from __future__ import print_function
from __future__ import absolute_import
import os
import pytest
import six
import sqlalchemy.orm as orm
import datetime
import logging
from six import text_type as str

from decimal import Decimal

from ckan.tests import factories
from ckanext.xloader import loader
from ckanext.xloader.loader import get_write_engine
from ckanext.xloader.job_exceptions import LoaderError

import ckan.plugins as p

logger = logging.getLogger(__name__)


def get_sample_filepath(filename):
    return os.path.abspath(
        os.path.join(os.path.dirname(__file__), "samples", filename)
    )


@pytest.fixture()
def Session():
    engine = get_write_engine()
    Session = orm.scoped_session(orm.sessionmaker(bind=engine))
    yield Session
    Session.close()


@pytest.mark.skipif(
    p.toolkit.check_ckan_version(max_version='2.7.99'),
    reason="fixtures do not have permission populate full_text_trigger")
@pytest.mark.usefixtures("full_reset", "with_plugins")
@pytest.mark.ckan_config("ckan.plugins", "datastore xloader")
class TestLoadBase(object):
    def _get_records(
        self, Session, table_name, limit=None, exclude_full_text_column=True
    ):
        c = Session.connection()
        if exclude_full_text_column:
            cols = self._get_column_names(Session, table_name)
            cols = ", ".join(
                loader.identifier(col) for col in cols if col != "_full_text"
            )
        else:
            cols = "*"
        sql = 'SELECT {cols} FROM "{table_name}"'.format(
            cols=cols, table_name=table_name
        )
        if limit is not None:
            sql += " LIMIT {}".format(limit)
        results = c.execute(sql)
        return results.fetchall()

    def _get_column_names(self, Session, table_name):
        # SELECT column_name FROM information_schema.columns WHERE table_name='test1';
        c = Session.connection()
        sql = (
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name='{}'
            ORDER BY ordinal_position;
            """.format(table_name)
        )
        results = c.execute(sql)
        records = results.fetchall()
        return [r[0] for r in records]

    def _get_column_types(self, Session, table_name):
        c = Session.connection()
        sql = (
            """
            SELECT udt_name
            FROM information_schema.columns
            WHERE table_name='{}'
            ORDER BY ordinal_position;
            """.format(table_name)
        )
        results = c.execute(sql)
        records = results.fetchall()
        return [r[0] for r in records]


class TestLoadCsv(TestLoadBase):
    def test_simple(self, Session):
        csv_filepath = get_sample_filepath("simple.csv")
        resource = factories.Resource()
        resource_id = resource['id']
        loader.load_csv(
            csv_filepath,
            resource_id=resource_id,
            mimetype="text/csv",
            logger=logger,
        )

        assert self._get_records(
            Session, resource_id, limit=1, exclude_full_text_column=False
        ) == [
            (
                1,
                "'-01':2,3 '1':4 '2011':1 'galway':5",
                u"2011-01-01",
                u"1",
                u"Galway",
            )
        ]
        assert self._get_records(Session, resource_id) == [
            (1, u"2011-01-01", u"1", u"Galway"),
            (2, u"2011-01-02", u"-1", u"Galway"),
            (3, u"2011-01-03", u"0", u"Galway"),
            (4, u"2011-01-01", u"6", u"Berkeley"),
            (5, None, None, u"Berkeley"),
            (6, u"2011-01-03", u"5", None),
        ]
        assert self._get_column_names(Session, resource_id) == [
            u"_id",
            u"_full_text",
            u"date",
            u"temperature",
            u"place",
        ]
        assert self._get_column_types(Session, resource_id) == [
            u"int4",
            u"tsvector",
            u"text",
            u"text",
            u"text",
        ]

    def test_simple_with_indexing(self, Session):
        csv_filepath = get_sample_filepath("simple.csv")
        resource = factories.Resource()
        resource_id = resource['id']
        fields = loader.load_csv(
            csv_filepath,
            resource_id=resource_id,
            mimetype="text/csv",
            logger=logger,
        )
        loader.create_column_indexes(
            fields=fields, resource_id=resource_id, logger=logger
        )

        assert (
            self._get_records(
                Session, resource_id, limit=1, exclude_full_text_column=False
            )[0][1]
            == "'-01':2,3 '1':4 '2011':1 'galway':5"
        )

    # test disabled by default to avoid adding large file to repo and slow test
    @pytest.mark.skip
    def test_boston_311_complete(self):
        # to get the test file:
        # curl -o ckanext/xloader/tests/samples/boston_311.csv https://data.boston.gov/dataset/8048697b-ad64-4bfc-b090-ee00169f2323/resource/2968e2c0-d479-49ba-a884-4ef523ada3c0/download/311.csv  # noqa
        csv_filepath = get_sample_filepath("boston_311.csv")
        resource = factories.Resource()
        resource_id = resource['id']
        import time

        t0 = time.time()
        print(
            "{} Start load".format(
                time.strftime("%H:%M:%S", time.localtime(t0))
            )
        )
        loader.load_csv(
            csv_filepath,
            resource_id=resource_id,
            mimetype="text/csv",
            logger=logger,
        )
        print("Load: {}s".format(time.time() - t0))

    # test disabled by default to avoid adding large file to repo and slow test
    @pytest.mark.skip
    def test_boston_311_sample5(self):
        # to create the test file:
        # head -n 100001 ckanext/xloader/tests/samples/boston_311.csv > ckanext/xloader/tests/samples/boston_311_sample5.csv
        csv_filepath = get_sample_filepath("boston_311_sample5.csv")
        resource = factories.Resource()
        resource_id = resource['id']
        import time

        t0 = time.time()
        print(
            "{} Start load".format(
                time.strftime("%H:%M:%S", time.localtime(t0))
            )
        )
        loader.load_csv(
            csv_filepath,
            resource_id=resource_id,
            mimetype="text/csv",
            logger=logger,
        )
        print("Load: {}s".format(time.time() - t0))

    def test_boston_311(self, Session):
        csv_filepath = get_sample_filepath("boston_311_sample.csv")
        resource = factories.Resource()
        resource_id = resource['id']
        loader.load_csv(
            csv_filepath,
            resource_id=resource_id,
            mimetype="text/csv",
            logger=logger,
        )

        records = self._get_records(Session, resource_id)
        print(records)
        assert records == [
            (
                1,
                u"101002153891",
                u"2017-07-06 23:38:43",
                u"2017-07-21 08:30:00",
                None,
                u"ONTIME",
                u"Open",
                u" ",
                u"Street Light Outages",
                u"Public Works Department",
                u"Street Lights",
                u"Street Light Outages",
                u"PWDx_Street Light Outages",
                u"PWDx",
                None,
                None,
                u"480 Harvard St  Dorchester  MA  02124",
                u"8",
                u"07",
                u"4",
                u"B3",
                u"Greater Mattapan",
                u"9",
                u"Ward 14",
                u"1411",
                u"480 Harvard St",
                u"02124",
                u"42.288",
                u"-71.0927",
                u"Citizens Connect App",
            ),  # noqa
            (
                2,
                u"101002153890",
                u"2017-07-06 23:29:13",
                u"2017-09-11 08:30:00",
                None,
                u"ONTIME",
                u"Open",
                u" ",
                u"Graffiti Removal",
                u"Property Management",
                u"Graffiti",
                u"Graffiti Removal",
                u"PROP_GRAF_GraffitiRemoval",
                u"PROP",
                u" https://mayors24.cityofboston.gov/media/boston/report/photos/595f0000048560f46d94b9fa/report.jpg",
                None,
                u"522 Saratoga St  East Boston  MA  02128",
                u"1",
                u"09",
                u"1",
                u"A7",
                u"East Boston",
                u"1",
                u"Ward 1",
                u"0110",
                u"522 Saratoga St",
                u"02128",
                u"42.3807",
                u"-71.0259",
                u"Citizens Connect App",
            ),  # noqa
            (
                3,
                u"101002153889",
                u"2017-07-06 23:24:20",
                u"2017-09-11 08:30:00",
                None,
                u"ONTIME",
                u"Open",
                u" ",
                u"Graffiti Removal",
                u"Property Management",
                u"Graffiti",
                u"Graffiti Removal",
                u"PROP_GRAF_GraffitiRemoval",
                u"PROP",
                u" https://mayors24.cityofboston.gov/media/boston/report/photos/595efedb048560f46d94b9ef/report.jpg",
                None,
                u"965 Bennington St  East Boston  MA  02128",
                u"1",
                u"09",
                u"1",
                u"A7",
                u"East Boston",
                u"1",
                u"Ward 1",
                u"0112",
                u"965 Bennington St",
                u"02128",
                u"42.386",
                u"-71.008",
                u"Citizens Connect App",
            ),
        ]  # noqa
        print(self._get_column_names(Session, resource_id))
        assert self._get_column_names(Session, resource_id) == [
            u"_id",
            u"_full_text",
            u"CASE_ENQUIRY_ID",
            u"open_dt",
            u"target_dt",
            u"closed_dt",
            u"OnTime_Status",
            u"CASE_STATUS",
            u"CLOSURE_REASON",
            u"CASE_TITLE",
            u"SUBJECT",
            u"REASON",
            u"TYPE",
            u"QUEUE",
            u"Department",
            u"SubmittedPhoto",
            u"ClosedPhoto",
            u"Location",
            u"Fire_district",
            u"pwd_district",
            u"city_council_district",
            u"police_district",
            u"neighborhood",
            u"neighborhood_services_district",
            u"ward",
            u"precinct",
            u"LOCATION_STREET_NAME",
            u"LOCATION_ZIPCODE",
            u"Latitude",
            u"Longitude",
            u"Source",
        ]  # noqa
        print(self._get_column_types(Session, resource_id))
        assert self._get_column_types(Session, resource_id) == [
            u"int4",
            u"tsvector",
        ] + [u"text"] * (len(records[0]) - 1)

    def test_brazilian(self, Session):
        csv_filepath = get_sample_filepath("brazilian_sample.csv")
        resource = factories.Resource()
        resource_id = resource['id']
        loader.load_csv(
            csv_filepath,
            resource_id=resource_id,
            mimetype="text/csv",
            logger=logger,
        )

        records = self._get_records(Session, resource_id)
        print(records)
        assert records[0] == (
            1,
            u"01/01/1996 12:00:00 AM",
            u"1100015",
            u"ALTA FLORESTA D'OESTE",
            u"RO",
            None,
            u"128",
            u"0",
            u"8",
            u"119",
            u"1",
            u"0",
            u"3613",
            u"3051",
            u"130",
            u"7",
            u"121",
            u"3716",
            u"3078",
            u"127",
            u"7",
            None,
            None,
            None,
            None,
            u"6794",
            u"5036",
            u"1758",
            None,
            None,
            None,
            None,
            None,
            None,
            u"337",
            u"0.26112759",
            u"0.17210683",
            u"0.43323442",
            u"0.13353115",
            u"24.833692447908199",
            None,
            None,
            u"22.704964",
            u"67.080006197818605",
            u"65.144188573097907",
            u"74.672390253375497",
            u"16.7913561569619",
            u"19.4894563570641",
            u"8.649237411458509",
            u"7.60165422117368",
            u"11.1540090366186",
            u"17.263407056738099",
            u"8.5269823",
            u"9.2213373",
            u"5.3085136",
            u"52.472769803217503",
            None,
            None,
            None,
            None,
            None,
            None,
            u"25.0011414302354",
            u"22.830887000000001",
            u"66.8150490097632",
            u"64.893674212235595",
            u"74.288246611754104",
            u"17.0725384713319",
            u"19.8404105332814",
            u"8.856561911292371",
            u"7.74275834336647",
            u"11.357671741889",
            u"17.9410577459881",
            u"8.3696527",
            u"8.9979973",
            u"5.0570836",
            u"53.286314230720798",
            None,
            None,
            None,
            None,
            None,
            u"122988",
            None,
            u"10.155015000000001",
            u"14.826086999999999",
            u"11.671533",
            u"9.072917",
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
        )  # noqa
        print(self._get_column_names(Session, resource_id))
        assert self._get_column_names(Session, resource_id) == [
            u"_id",
            u"_full_text",
            u"NU_ANO_CENSO",
            u"CO_MUNICIPIO",
            u"MUNIC",
            u"SIGLA",
            u"CO_UF",
            u"SCHOOLS_NU",
            u"SCHOOLS_FED_NU",
            u"SCHOOLS_ESTADUAL_NU",
            u"SCHOOLS_MUN_NU",
            u"SCHOOLS_PRIV_NU",
            u"SCHOOLS_FED_STUD",
            u"SCHOOLS_ESTADUAL_STUD",
            u"SCHOOLS_MUN_STUD",
            u"SCHOOLS_PRIV_STUD",
            u"SCHOOLS_URBAN_NU",
            u"SCHOOLS_RURAL_NU",
            u"SCHOOLS_URBAN_STUD",
            u"SCHOOLS_RURAL_STUD",
            u"SCHOOLS_NIVFUND_1_NU",
            u"SCHOOLS_NIVFUND_2_NU",
            u"SCHOOLS_EIGHTYEARS_NU",
            u"SCHOOLS_NINEYEARS_NU",
            u"SCHOOLS_EIGHTYEARS_STUD",
            u"SCHOOLS_NINEYEARS_STUD",
            u"MATFUND_NU",
            u"MATFUND_I_NU",
            u"MATFUND_T_NU",
            u"SCHOOLS_INTERNET_AVG",
            u"SCHOOLS_WATER_PUBLIC_AVG",
            u"SCHOOLS_WATER_AVG",
            u"SCHOOLS_ELECTR_PUB_AVG",
            u"SCHOOLS_SEWAGE_PUB_AVG",
            u"SCHOOLS_SEWAGE_AVG",
            u"PROFFUNDTOT_NU",
            u"PROFFUNDINC_PC",
            u"PROFFUNDCOMP_PC",
            u"PROFMED_PC",
            u"PROFSUP_PC",
            u"CLASSSIZE",
            u"CLASSSIZE_I",
            u"CLASSSIZE_T",
            u"STUDTEACH",
            u"RATE_APROV",
            u"RATE_APROV_I",
            u"RATE_APROV_T",
            u"RATE_FAILURE",
            u"RATE_FAILURE_I",
            u"RATE_FAILURE_T",
            u"RATE_ABANDON",
            u"RATE_ABANDON_I",
            u"RATE_ABANDON_T",
            u"RATE_TRANSFER",
            u"RATE_TRANSFER_I",
            u"RATE_TRANSFER_T",
            u"RATE_OVERAGE",
            u"RATE_OVERAGE_I",
            u"RATE_OVERAGE_T",
            u"PROVA_MEAN_PORT_I",
            u"PROVA_MEAN_PORT_T",
            u"PROVA_MEAN_MAT_I",
            u"PROVA_MEAN_MAT_T",
            u"CLASSSIZE_PUB",
            u"STUDTEACH_PUB",
            u"RATE_APROV_PUB",
            u"RATE_APROV_I_PUB",
            u"RATE_APROV_T_PUB",
            u"RATE_FAILURE_PUB",
            u"RATE_FAILURE_I_PUB",
            u"RATE_FAILURE_T_PUB",
            u"RATE_ABANDON_PUB",
            u"RATE_ABANDON_I_PUB",
            u"RATE_ABANDON_T_PUB",
            u"RATE_TRANSFER_PUB",
            u"RATE_TRANSFER_I_PUB",
            u"RATE_TRANSFER_T_PUB",
            u"RATE_OVERAGE_PUB",
            u"RATE_OVERAGE_I_PUB",
            u"RATE_OVERAGE_T_PUB",
            u"PROVA_MEAN_PORT_I_PUB",
            u"PROVA_MEAN_PORT_T_PUB",
            u"PROVA_MEAN_MAT_I_PUB",
            u"PROFFUNDTOT_NU_PUB",
            u"PROVA_MEAN_MAT_T_PUB",
            u"EDUCTEACH_PUB",
            u"EDUCTEACH_FEDERAL",
            u"EDUCTEACH_STATE",
            u"EDUCTEACH_MUN",
            u"PROVA_MEAN_PORT_I_STATE",
            u"PROVA_MEAN_PORT_T_STATE",
            u"PROVA_MEAN_MAT_I_STATE",
            u"PROVA_MEAN_MAT_T_STATE",
            u"PROVA_MEAN_PORT_I_MUN",
            u"PROVA_MEAN_PORT_T_MUN",
            u"PROVA_MEAN_MAT_I_MUN",
            u"PROVA_MEAN_MAT_T_MUN",
        ]  # noqa
        print(self._get_column_types(Session, resource_id))
        assert self._get_column_types(Session, resource_id) == [
            u"int4",
            u"tsvector",
        ] + [u"text"] * (len(records[0]) - 1)

    def test_german(self, Session):
        csv_filepath = get_sample_filepath("german_sample.csv")
        resource = factories.Resource()
        resource_id = resource['id']
        loader.load_csv(
            csv_filepath,
            resource_id=resource_id,
            mimetype="text/csv",
            logger=logger,
        )

        records = self._get_records(Session, resource_id)
        print(records)
        assert records[0] == (
            1,
            u"Zürich",
            u"68260",
            u"65444",
            u"62646",
            u"6503",
            u"28800",
            u"1173",
            u"6891",
            u"24221",
            u"672",
        )
        print(self._get_column_names(Session, resource_id))
        assert self._get_column_names(Session, resource_id) == [
            u"_id",
            u"_full_text",
            u"Stadtname",
            u"Schuler_Total_2010/2011",
            u"Schuler_Total_2000/2001",
            u"Schuler_Total_1990/1991",
            u"Schuler_Vorschule_2010/2011",
            u"Schuler_Obligatorische Primar- und Sekundarstufe I_2010/2011",
            u"Schuler_Sekundarstufe II, Ubergangsausbildung Sek I. - Sek. II_",
            u"Schuler_Maturitatsschulen_2010/2011",
            u"Schuler_Berufsausbildung_2010/2011",
            u"Schuler_andere allgemeinbildende Schulen_2010/2011",
        ]
        print(self._get_column_types(Session, resource_id))
        assert self._get_column_types(Session, resource_id) == [
            u"int4",
            u"tsvector",
        ] + [u"text"] * (len(records[0]) - 1)

    def test_with_blanks(self, Session):
        csv_filepath = get_sample_filepath("sample_with_blanks.csv")
        resource = factories.Resource()
        resource_id = resource['id']
        loader.load_csv(
            csv_filepath,
            resource_id=resource_id,
            mimetype="text/csv",
            logger=logger,
        )
        assert len(self._get_records(Session, resource_id)) == 3

    def test_with_empty_lines(self, Session):
        csv_filepath = get_sample_filepath("sample_with_empty_lines.csv")
        resource = factories.Resource()
        resource_id = resource['id']
        loader.load_csv(
            csv_filepath,
            resource_id=resource_id,
            mimetype="text/csv",
            logger=logger,
        )
        assert len(self._get_records(Session, resource_id)) == 6

    def test_with_quoted_commas(self, Session):
        csv_filepath = get_sample_filepath("sample_with_quoted_commas.csv")
        resource = factories.Resource()
        resource_id = resource['id']
        loader.load_csv(
            csv_filepath,
            resource_id=resource_id,
            mimetype="text/csv",
            logger=logger,
        )
        assert len(self._get_records(Session, resource_id)) == 3

    def test_with_mixed_quotes(self, Session):
        csv_filepath = get_sample_filepath("sample_with_mixed_quotes.csv")
        resource = factories.Resource()
        resource_id = resource['id']
        loader.load_csv(
            csv_filepath,
            resource_id=resource_id,
            mimetype="text/csv",
            logger=logger,
        )
        assert len(self._get_records(Session, resource_id)) == 2

    def test_with_mixed_types(self, Session):
        csv_filepath = get_sample_filepath("mixed_numeric_string_sample.csv")
        resource = factories.Resource()
        resource_id = resource['id']
        loader.load_csv(
            csv_filepath,
            resource_id=resource_id,
            mimetype="text/csv",
            logger=logger,
        )
        assert len(self._get_records(Session, resource_id)) == 6

    def test_reload(self, Session):
        csv_filepath = get_sample_filepath("simple.csv")
        resource = factories.Resource()
        resource_id = resource['id']
        loader.load_csv(
            csv_filepath,
            resource_id=resource_id,
            mimetype="text/csv",
            logger=logger,
        )

        # Load it again unchanged
        loader.load_csv(
            csv_filepath,
            resource_id=resource_id,
            mimetype="text/csv",
            logger=logger,
        )

        assert len(self._get_records(Session, resource_id)) == 6
        assert self._get_column_names(Session, resource_id) == [
            u"_id",
            u"_full_text",
            u"date",
            u"temperature",
            u"place",
        ]
        assert self._get_column_types(Session, resource_id) == [
            u"int4",
            u"tsvector",
            u"text",
            u"text",
            u"text",
        ]

    @pytest.mark.skipif(
        not p.toolkit.check_ckan_version(min_version="2.7"),
        reason="Requires CKAN 2.7 - see https://github.com/ckan/ckan/pull/3557",
    )
    def test_reload_with_overridden_types(self, Session):
        csv_filepath = get_sample_filepath("simple.csv")
        resource = factories.Resource()
        resource_id = resource['id']
        loader.load_csv(
            csv_filepath,
            resource_id=resource_id,
            mimetype="text/csv",
            logger=logger,
        )
        # Change types, as it would be done by Data Dictionary
        rec = p.toolkit.get_action("datastore_search")(
            None, {"resource_id": resource_id, "limit": 0}
        )
        fields = [f for f in rec["fields"] if not f["id"].startswith("_")]
        fields[0]["info"] = {"type_override": "timestamp"}
        fields[1]["info"] = {"type_override": "numeric"}
        p.toolkit.get_action("datastore_create")(
            {"ignore_auth": True},
            {"resource_id": resource_id, "force": True, "fields": fields},
        )

        # Load it again with new types
        fields = loader.load_csv(
            csv_filepath,
            resource_id=resource_id,
            mimetype="text/csv",
            logger=logger,
        )
        loader.create_column_indexes(
            fields=fields, resource_id=resource_id, logger=logger
        )

        assert len(self._get_records(Session, resource_id)) == 6
        assert self._get_column_names(Session, resource_id) == [
            u"_id",
            u"_full_text",
            u"date",
            u"temperature",
            u"place",
        ]
        assert self._get_column_types(Session, resource_id) == [
            u"int4",
            u"tsvector",
            u"timestamp",
            u"numeric",
            u"text",
        ]

        # check that rows with nulls are indexed correctly
        records = self._get_records(
            Session, resource_id, exclude_full_text_column=False
        )
        print(records)
        assert records[4][1] == "'berkeley':1"
        assert records[5][1] == "'-01':2 '-03':3 '00':4,5,6 '2011':1 '5':7"

    def test_encode_headers(self):
        test_string_headers = [u"id", u"namé"]
        test_float_headers = [u"id", u"näme", 2.0]
        test_int_headers = [u"id", u"nóm", 3]
        test_result_string_headers = loader.encode_headers(test_string_headers)
        test_result_float_headers = loader.encode_headers(test_float_headers)
        test_result_int_headers = loader.encode_headers(test_int_headers)

        assert "id" in test_result_string_headers
        assert "name" in test_result_string_headers
        assert "id" in test_result_float_headers
        assert "name" in test_result_float_headers
        assert "2.0" in test_result_float_headers
        assert "id" in test_result_int_headers
        assert "nom" in test_result_int_headers
        assert "3" in test_result_int_headers

    def test_column_names(self, Session):
        csv_filepath = get_sample_filepath("column_names.csv")
        resource = factories.Resource()
        resource_id = resource['id']
        loader.load_csv(
            csv_filepath,
            resource_id=resource_id,
            mimetype="text/csv",
            logger=logger,
        )

        assert self._get_column_names(Session, resource_id)[2:] == [
            u"d@t$e",
            u"t^e&m*pe!r(a)t?u:r%%e",
            r"p\l/a[c{e%",
        ]
        assert self._get_records(Session, resource_id)[0] == (
            1,
            u"2011-01-01",
            u"1",
            u"Galway",
        )


class TestLoadUnhandledTypes(TestLoadBase):
    def test_kml(self):
        filepath = get_sample_filepath("polling_locations.kml")
        resource = factories.Resource()
        resource_id = resource['id']
        with pytest.raises(LoaderError) as exception:
            loader.load_csv(
                filepath,
                resource_id=resource_id,
                mimetype="text/csv",
                logger=logger,
            )
        assert "Error with field definition" in str(exception.value)
        assert (
            '"<?xml version="1.0" encoding="utf-8" ?>" is not a valid field name'
            in str(exception.value)
        )

    def test_geojson(self):
        filepath = get_sample_filepath("polling_locations.geojson")
        resource = factories.Resource()
        resource_id = resource['id']
        with pytest.raises(LoaderError) as exception:
            loader.load_csv(
                filepath,
                resource_id=resource_id,
                mimetype="text/csv",
                logger=logger,
            )
        assert "Error with field definition" in str(exception.value)
        assert (
            '"{"type":"FeatureCollection"" is not a valid field name'
            in str(exception.value)
        )

    @pytest.mark.skipif(
        six.PY3,
        reason="In Python 3, tabulator will unzip archives and load the first "
               "file found (if possible)."
    )
    def test_shapefile_zip_python2(self):
        filepath = get_sample_filepath("polling_locations.shapefile.zip")
        resource = factories.Resource()
        resource_id = resource['id']
        with pytest.raises(LoaderError):
            loader.load_csv(
                filepath,
                resource_id=resource_id,
                mimetype="text/csv",
                logger=logger,
            )

    @pytest.mark.skipif(
        six.PY2,
        reason="In Python 2, tabulator will not load a zipped archive, so the "
               "loader will raise a LoaderError."
    )
    def test_shapefile_zip_python3(self, Session):
        # tabulator unzips the archive and tries to load the first file it
        # finds, 'Polling_Locations.cpg'. This file only contains the
        # following data: `UTF-8`.
        filepath = get_sample_filepath("polling_locations.shapefile.zip")
        resource = factories.Resource()
        resource_id = resource['id']
        loader.load_csv(
            filepath,
            resource_id=resource_id,
            mimetype="text/csv",
            logger=logger,
        )

        assert self._get_records(Session, resource_id) == []
        assert self._get_column_names(Session, resource_id) == [
            '_id',
            '_full_text',
            'UTF-8'
        ]


class TestLoadTabulator(TestLoadBase):
    def test_simple(self, Session):
        csv_filepath = get_sample_filepath("simple.xls")
        resource = factories.Resource()
        resource_id = resource['id']
        loader.load_table(
            csv_filepath,
            resource_id=resource_id,
            mimetype="xls",
            logger=logger,
        )

        assert (
            "'galway':"
            in self._get_records(
                Session, resource_id, limit=1, exclude_full_text_column=False
            )[0][1]
        )
        # Indexed record looks like this (depending on CKAN version?):
        #   "'-01':2,3 '00':4,5,6 '1':7 '2011':1 'galway':8"
        #   "'-01':4,5 '00':6,7,8 '1':1 '2011':3 'galway':2"
        #   "'-01':2,3 '00':5,6 '1':7 '2011':1 'galway':8 't00':4"

        assert self._get_records(Session, resource_id) == [
            (1, datetime.datetime(2011, 1, 1, 0, 0), Decimal("1"), u"Galway",),
            (
                2,
                datetime.datetime(2011, 1, 2, 0, 0),
                Decimal("-1"),
                u"Galway",
            ),
            (3, datetime.datetime(2011, 1, 3, 0, 0), Decimal("0"), u"Galway",),
            (
                4,
                datetime.datetime(2011, 1, 1, 0, 0),
                Decimal("6"),
                u"Berkeley",
            ),
            (
                5,
                datetime.datetime(2011, 1, 2, 0, 0),
                Decimal("8"),
                u"Berkeley",
            ),
            (
                6,
                datetime.datetime(2011, 1, 3, 0, 0),
                Decimal("5"),
                u"Berkeley",
            ),
        ]
        assert self._get_column_names(Session, resource_id) == [
            u"_id",
            u"_full_text",
            u"date",
            u"temperature",
            u"place",
        ]
        assert self._get_column_types(Session, resource_id) == [
            u"int4",
            u"tsvector",
            u"timestamp",
            u"numeric",
            u"text",
        ]

    def test_simple_large_file(self, Session):
        csv_filepath = get_sample_filepath("simple-large.csv")
        resource = factories.Resource()
        resource_id = resource['id']
        loader.load_table(
            csv_filepath,
            resource_id=resource_id,
            mimetype="text/csv",
            logger=logger,
        )
        assert self._get_column_types(Session, resource_id) == [
            u"int4",
            u"tsvector",
            u"numeric",
            u"text",
        ]

    def test_with_mixed_types(self, Session):
        csv_filepath = get_sample_filepath("mixed_numeric_string_sample.csv")
        resource = factories.Resource()
        resource_id = resource['id']
        loader.load_table(
            csv_filepath,
            resource_id=resource_id,
            mimetype="text/csv",
            logger=logger,
        )
        assert len(self._get_records(Session, resource_id)) == 6

        assert self._get_column_types(Session, resource_id) == [
            u'int4',
            u'tsvector',
            u'text',
            u'text',
            u'text',
            u'numeric'
        ]

    # test disabled by default to avoid adding large file to repo and slow test
    @pytest.mark.skip
    def test_boston_311_complete(self):
        # to get the test file:
        # curl -o ckanext/xloader/tests/samples/boston_311.csv https://data.boston.gov/dataset/8048697b-ad64-4bfc-b090-ee00169f2323/resource/2968e2c0-d479-49ba-a884-4ef523ada3c0/download/311.csv  # noqa
        csv_filepath = get_sample_filepath("boston_311.csv")
        resource = factories.Resource()
        resource_id = resource['id']
        import time

        t0 = time.time()
        print(
            "{} Start load".format(
                time.strftime("%H:%M:%S", time.localtime(t0))
            )
        )
        loader.load_table(
            csv_filepath,
            resource_id=resource_id,
            mimetype="csv",
            logger=logger,
        )
        print("Load: {}s".format(time.time() - t0))

    # test disabled by default to avoid adding large file to repo and slow test
    @pytest.mark.skip
    def test_boston_311_sample5(self):
        # to create the test file:
        # head -n 100001 ckanext/xloader/tests/samples/boston_311.csv > ckanext/xloader/tests/samples/boston_311_sample5.csv
        csv_filepath = get_sample_filepath("boston_311_sample5.csv")
        resource = factories.Resource()
        resource_id = resource['id']
        import time

        t0 = time.time()
        print(
            "{} Start load".format(
                time.strftime("%H:%M:%S", time.localtime(t0))
            )
        )
        loader.load_table(
            csv_filepath,
            resource_id=resource_id,
            mimetype="csv",
            logger=logger,
        )
        print("Load: {}s".format(time.time() - t0))

    def test_boston_311(self, Session):
        csv_filepath = get_sample_filepath("boston_311_sample.csv")
        resource = factories.Resource()
        resource_id = resource['id']
        loader.load_table(
            csv_filepath,
            resource_id=resource_id,
            mimetype="csv",
            logger=logger,
        )

        records = self._get_records(Session, resource_id)
        print(records)
        assert records == [
            (
                1,
                Decimal("101002153891"),
                datetime.datetime(2017, 7, 6, 23, 38, 43),
                datetime.datetime(2017, 7, 21, 8, 30),
                u"",
                u"ONTIME",
                u"Open",
                u" ",
                u"Street Light Outages",
                u"Public Works Department",
                u"Street Lights",
                u"Street Light Outages",
                u"PWDx_Street Light Outages",
                u"PWDx",
                u"",
                u"",
                u"480 Harvard St  Dorchester  MA  02124",
                Decimal("8"),
                Decimal("7"),
                Decimal("4"),
                u"B3",
                u"Greater Mattapan",
                Decimal("9"),
                u"Ward 14",
                Decimal("1411"),
                u"480 Harvard St",
                Decimal("2124"),
                Decimal("42.288"),
                Decimal("-71.0927"),
                u"Citizens Connect App",
            ),  # noqa
            (
                2,
                Decimal("101002153890"),
                datetime.datetime(2017, 7, 6, 23, 29, 13),
                datetime.datetime(2017, 9, 11, 8, 30),
                u"",
                u"ONTIME",
                u"Open",
                u" ",
                u"Graffiti Removal",
                u"Property Management",
                u"Graffiti",
                u"Graffiti Removal",
                u"PROP_GRAF_GraffitiRemoval",
                u"PROP",
                u" https://mayors24.cityofboston.gov/media/boston/report/photos/595f0000048560f46d94b9fa/report.jpg",
                u"",
                u"522 Saratoga St  East Boston  MA  02128",
                Decimal("1"),
                Decimal("9"),
                Decimal("1"),
                u"A7",
                u"East Boston",
                Decimal("1"),
                u"Ward 1",
                Decimal("110"),
                u"522 Saratoga St",
                Decimal("2128"),
                Decimal("42.3807"),
                Decimal("-71.0259"),
                u"Citizens Connect App",
            ),  # noqa
            (
                3,
                Decimal("101002153889"),
                datetime.datetime(2017, 7, 6, 23, 24, 20),
                datetime.datetime(2017, 9, 11, 8, 30),
                u"",
                u"ONTIME",
                u"Open",
                u" ",
                u"Graffiti Removal",
                u"Property Management",
                u"Graffiti",
                u"Graffiti Removal",
                u"PROP_GRAF_GraffitiRemoval",
                u"PROP",
                u" https://mayors24.cityofboston.gov/media/boston/report/photos/595efedb048560f46d94b9ef/report.jpg",
                u"",
                u"965 Bennington St  East Boston  MA  02128",
                Decimal("1"),
                Decimal("9"),
                Decimal("1"),
                u"A7",
                u"East Boston",
                Decimal("1"),
                u"Ward 1",
                Decimal("112"),
                u"965 Bennington St",
                Decimal("2128"),
                Decimal("42.386"),
                Decimal("-71.008"),
                u"Citizens Connect App",
            ),
        ]  # noqa
        print(self._get_column_names(Session, resource_id))
        assert self._get_column_names(Session, resource_id) == [
            u"_id",
            u"_full_text",
            u"CASE_ENQUIRY_ID",
            u"open_dt",
            u"target_dt",
            u"closed_dt",
            u"OnTime_Status",
            u"CASE_STATUS",
            u"CLOSURE_REASON",
            u"CASE_TITLE",
            u"SUBJECT",
            u"REASON",
            u"TYPE",
            u"QUEUE",
            u"Department",
            u"SubmittedPhoto",
            u"ClosedPhoto",
            u"Location",
            u"Fire_district",
            u"pwd_district",
            u"city_council_district",
            u"police_district",
            u"neighborhood",
            u"neighborhood_services_district",
            u"ward",
            u"precinct",
            u"LOCATION_STREET_NAME",
            u"LOCATION_ZIPCODE",
            u"Latitude",
            u"Longitude",
            u"Source",
        ]  # noqa
        print(self._get_column_types(Session, resource_id))
        assert self._get_column_types(Session, resource_id) == [
            u"int4",
            u"tsvector",
            u"numeric",
            u"timestamp",
            u"timestamp",
            u"text",
            u"text",
            u"text",
            u"text",
            u"text",
            u"text",
            u"text",
            u"text",
            u"text",
            u"text",
            u"text",
            u"text",
            u"text",
            u"numeric",
            u"numeric",
            u"numeric",
            u"text",
            u"text",
            u"numeric",
            u"text",
            u"numeric",
            u"text",
            u"numeric",
            u"numeric",
            u"numeric",
            u"text",
        ]  # noqa

    def test_no_entries(self):
        csv_filepath = get_sample_filepath("no_entries.csv")
        # no datastore table is created - we need to except, or else
        # datastore_active will be set on a non-existent datastore table
        resource = factories.Resource()
        resource_id = resource['id']
        with pytest.raises(LoaderError):
            loader.load_table(
                csv_filepath,
                resource_id=resource_id,
                mimetype="csv",
                logger=logger,
            )

    def test_with_quoted_commas(self, Session):
        csv_filepath = get_sample_filepath("sample_with_quoted_commas.csv")
        resource = factories.Resource()
        resource_id = resource['id']
        loader.load_table(
            csv_filepath,
            resource_id=resource_id,
            mimetype="text/csv",
            logger=logger,
        )
        assert len(self._get_records(Session, resource_id)) == 3

    def test_with_iso_8859_1(self, Session):
        csv_filepath = get_sample_filepath("non_utf8_sample.csv")
        resource = factories.Resource()
        resource_id = resource['id']
        loader.load_table(
            csv_filepath,
            resource_id=resource_id,
            mimetype="text/csv",
            logger=logger,
        )
        assert len(self._get_records(Session, resource_id)) == 266

    def test_with_mixed_quotes(self, Session):
        csv_filepath = get_sample_filepath("sample_with_mixed_quotes.csv")
        resource = factories.Resource()
        resource_id = resource['id']
        loader.load_table(
            csv_filepath,
            resource_id=resource_id,
            mimetype="text/csv",
            logger=logger,
        )
        assert len(self._get_records(Session, resource_id)) == 2

    def test_preserving_time_ranges(self, Session):
        """ Time ranges should not be treated as timestamps
        """
        csv_filepath = get_sample_filepath("non_timestamp_sample.csv")
        resource = factories.Resource()
        resource_id = resource['id']
        loader.load_table(
            csv_filepath,
            resource_id=resource_id,
            mimetype="text/csv",
            logger=logger,
        )
        assert self._get_records(Session, resource_id) == [
            (1, "Adavale", 4474, Decimal("-25.9092582"), Decimal("144.5975769"),
             "8:00", "16:00", datetime.datetime(2018, 7, 19)),
            (2, "Aramac", 4726, Decimal("-22.971298"), Decimal("145.241481"),
             "9:00-13:00", "14:00-16:45", datetime.datetime(2018, 7, 17)),
            (3, "Barcaldine", 4725, Decimal("-23.55327901"), Decimal("145.289156"),
             "9:00-12:30", "13:30-16:30", datetime.datetime(2018, 7, 20))
        ]
