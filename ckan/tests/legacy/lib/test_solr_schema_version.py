# encoding: utf-8

import os


class TestSolrSchemaVersionCheck(object):
    root_dir = os.path.dirname(os.path.realpath(__file__))

    def _get_current_schema(self):

        current_schema = os.path.join(
            self.root_dir, "..", "..", "..", "config", "solr", "schema.xml"
        )

        return current_schema

    def test_current_schema_exists(self):

        current_schema = self._get_current_schema()

        assert os.path.exists(current_schema)

    def test_solr_schema_version_check(self):

        from ckan.lib.search import check_solr_schema_version, SearchError

        schema_file = self._get_current_schema()

        # Check that current schema version schema is supported
        assert check_solr_schema_version(schema_file)

        # An exception is thrown if version could not be extracted
        try:
            schema_file = os.path.join(
                self.root_dir, "solr", "schema-no-version.xml"
            )
            check_solr_schema_version(schema_file)

            # Should not happen
            assert False
        except SearchError as e:
            assert "Could not extract version info" in str(e)

        # An exception is thrown if the schema version is not supported
        try:
            schema_file = os.path.join(
                self.root_dir, "solr", "schema-wrong-version.xml"
            )
            check_solr_schema_version(schema_file)

            # Should not happen
            assert False
        except SearchError as e:
            assert "SOLR schema version not supported" in str(e)
