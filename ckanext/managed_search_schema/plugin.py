# -*- coding: utf-8 -*-

import ckan.plugins as p
import ckanext.managed_search_schema.cli as cli

field_types = [{
    "name": "string",
    "class": "solr.StrField",
    "sortMissingLast": "true",
    "omitNorms": "true"
}, {
    "name": "boolean",
    "class": "solr.BoolField",
    "sortMissingLast": "true",
    "omitNorms": "true"
}, {
    "name": "binary",
    "class": "solr.BinaryField"
}, {
    "name": "int",
    "class": "solr.IntPointField",
    "omitNorms": "true",
    "positionIncrementGap": "0"
}, {
    "name": "float",
    "class": "solr.FloatPointField",
    "omitNorms": "true",
    "positionIncrementGap": "0"
}, {
    "name": "long",
    "class": "solr.LongPointField",
    "omitNorms": "true",
    "positionIncrementGap": "0"
}, {
    "name": "double",
    "class": "solr.DoublePointField",
    "omitNorms": "true",
    "positionIncrementGap": "0"
}, {
    "name": "pint",
    "class": "solr.IntPointField",
    "omitNorms": "true",
    "positionIncrementGap": "0"
}, {
    "name": "pfloat",
    "class": "solr.FloatPointField",
    "omitNorms": "true",
    "positionIncrementGap": "0"
}, {
    "name": "plong",
    "class": "solr.LongPointField",
    "omitNorms": "true",
    "positionIncrementGap": "0"
}, {
    "name": "pdouble",
    "class": "solr.DoublePointField",
    "omitNorms": "true",
    "positionIncrementGap": "0"
}, {
    "name": "date",
    "class": "solr.DatePointField",
    "omitNorms": "true",
    "positionIncrementGap": "0"
}, {
    "name": "pdate",
    "class": "solr.DatePointField",
    "omitNorms": "true",
    "positionIncrementGap": "0"
}, {
    "name": "pdates",
    "class": "solr.DatePointField",
    "positionIncrementGap": "0",
    "multiValued": "true"
}, {
    "name": "booleans",
    "class": "solr.BoolField",
    "sortMissingLast": "true",
    "multiValued": "true"
}, {
    "name": "pints",
    "class": "solr.IntPointField",
    "positionIncrementGap": "0",
    "multiValued": "true"
}, {
    "name": "pfloats",
    "class": "solr.FloatPointField",
    "positionIncrementGap": "0",
    "multiValued": "true"
}, {
    "name": "plongs",
    "class": "solr.LongPointField",
    "positionIncrementGap": "0",
    "multiValued": "true"
}, {
    "name": "pdoubles",
    "class": "solr.DoublePointField",
    "positionIncrementGap": "0",
    "multiValued": "true"
}, {
    "name": "text",
    "class": "solr.TextField",
    "positionIncrementGap": "100",
    "indexAnalyzer": {
        "tokenizer": {
            "class": "solr.WhitespaceTokenizerFactory",
        },
        "filters": [
            {
                "class": "solr.WordDelimiterFilterFactory",
                "generateWordParts": "1",
                "generateNumberParts": "1",
                "catenateWords": "1",
                "catenateNumbers": "1",
                "catenateAll": "0",
                "splitOnCaseChange": "1"
            },
            {
                "class": "solr.LowerCaseFilterFactory"
            },
            {
                "class": "solr.SnowballPorterFilterFactory",
                "language": "English",
                "protected": "protwords.txt"
            },
            {
                "class": "solr.ASCIIFoldingFilterFactory"
            },
        ]
    },
    "queryAnalyzer": {
        "tokenizer": {
            "class": "solr.WhitespaceTokenizerFactory"
        },
        "filters": [
            {
                "class": "solr.SynonymFilterFactory",
                "synonyms": "synonyms.txt",
                "ignoreCase": "true",
                "expand": "true",
            },
            {
                "class": "solr.WordDelimiterFilterFactory",
                "generateWordParts": "1",
                "generateNumberParts": "1",
                "catenateWords": "0",
                "catenateNumbers": "0",
                "catenateAll": "0",
                "splitOnCaseChange": "1"
            },
            {
                "class": "solr.LowerCaseFilterFactory",
            },
            {
                "class": "solr.SnowballPorterFilterFactory",
                "language": "English",
                "protected": "protwords.txt",
            },
            {
                "class": "solr.ASCIIFoldingFilterFactory",
            },
        ]
    },
}, {
    "name": "text_general",
    "class": "solr.TextField",
    "positionIncrementGap": "100",
    "indexAnalyzer": {
        "tokenizer": {
            "class": "solr.WhitespaceTokenizerFactory",
        },
        "filters": [{
            "class": "solr.WordDelimiterFilterFactory",
            "generateWordParts": "1",
            "generateNumberParts": "1",
            "catenateWords": "1",
            "catenateNumbers": "1",
            "catenateAll": "0",
            "splitOnCaseChange": "0",
        }, {
            "class": "solr.LowerCaseFilterFactory",
        }]
    },
    "queryAnalyzer": {
        "tokenizer": {
            "class": "solr.WhitespaceTokenizerFactory"
        },
        "filters": [
            {
                "class": "solr.SynonymFilterFactory",
                "synonyms": "synonyms.txt",
                "ignoreCase": "true",
                "expand": "true",
            },
            {
                "class": "solr.WordDelimiterFilterFactory",
                "generateWordParts": "1",
                "generateNumberParts": "1",
                "catenateWords": "0",
                "catenateNumbers": "0",
                "catenateAll": "0",
                "splitOnCaseChange": "0",
            },
            {
                "class": "solr.LowerCaseFilterFactory",
            },
        ]
    },
}, {
    "name": "text_ngram",
    "class": "solr.TextField",
    "positionIncrementGap": "100",
    "indexAnalyzer": {
        "tokenizer": {
            "class": "solr.NGramTokenizerFactory",
            "minGramSize": "2",
            "maxGramSize": "10",
        },
        "filters": [{
            "class": "solr.LowerCaseFilterFactory",
        }]
    },
    "queryAnalyzer": {
        "tokenizer": {
            "class": "solr.WhitespaceTokenizerFactory"
        },
        "filters": [{
            "class": "solr.LowerCaseFilterFactory",
        }]
    },
}]

fields = [
    {
        "name": "index_id",
        "type": "string",
        "indexed": "true",
        "stored": "true",
        "required": "true",
    },
    {
        "name": "id",
        "type": "string",
        "indexed": "true",
        "stored": "true",
        "required": "true",
    },
    {
        "name": "site_id",
        "type": "string",
        "indexed": "true",
        "stored": "true",
        "required": "true",
    },
    {
        "name": "title",
        "type": "text",
        "indexed": "true",
        "stored": "true"
    },
    {
        "name": "title_ngram",
        "type": "text_ngram",
        "indexed": "true",
        "stored": "true"
    },
    {
        "name": "entity_type",
        "type": "string",
        "indexed": "true",
        "stored": "true",
        "omitNorms": "true",
    },
    {
        "name": "dataset_type",
        "type": "string",
        "indexed": "true",
        "stored": "true"
    },
    {
        "name": "state",
        "type": "string",
        "indexed": "true",
        "stored": "true",
        "omitNorms": "true",
    },
    {
        "name": "name",
        "type": "string",
        "indexed": "true",
        "stored": "true",
        "omitNorms": "true",
    },
    {
        "name": "name_ngram",
        "type": "text_ngram",
        "indexed": "true",
        "stored": "true"
    },
    {
        "name": "revision_id",
        "type": "string",
        "indexed": "true",
        "stored": "true",
        "omitNorms": "true",
    },
    {
        "name": "version",
        "type": "string",
        "indexed": "true",
        "stored": "true"
    },
    {
        "name": "url",
        "type": "string",
        "indexed": "true",
        "stored": "true",
        "omitNorms": "true",
    },
    {
        "name": "ckan_url",
        "type": "string",
        "indexed": "true",
        "stored": "true",
        "omitNorms": "true",
    },
    {
        "name": "download_url",
        "type": "string",
        "indexed": "true",
        "stored": "true",
        "omitNorms": "true",
    },
    {
        "name": "notes",
        "type": "text",
        "indexed": "true",
        "stored": "true"
    },
    {
        "name": "author",
        "type": "text_general",
        "indexed": "true",
        "stored": "true"
    },
    {
        "name": "author_email",
        "type": "text_general",
        "indexed": "true",
        "stored": "true"
    },
    {
        "name": "maintainer",
        "type": "text_general",
        "indexed": "true",
        "stored": "true"
    },
    {
        "name": "maintainer_email",
        "type": "text_general",
        "indexed": "true",
        "stored": "true"
    },
    {
        "name": "license",
        "type": "string",
        "indexed": "true",
        "stored": "true"
    },
    {
        "name": "license_id",
        "type": "string",
        "indexed": "true",
        "stored": "true"
    },
    {
        "name": "ratings_count",
        "type": "int",
        "indexed": "true",
        "stored": "false"
    },
    {
        "name": "ratings_average",
        "type": "float",
        "indexed": "true",
        "stored": "false"
    },
    {
        "name": "tags",
        "type": "string",
        "indexed": "true",
        "stored": "true",
        "multiValued": "true",
    },
    {
        "name": "groups",
        "type": "string",
        "indexed": "true",
        "stored": "true",
        "multiValued": "true",
    },
    {
        "name": "organization",
        "type": "string",
        "indexed": "true",
        "stored": "true",
        "multiValued": "false",
    },
    {
        "name": "capacity",
        "type": "string",
        "indexed": "true",
        "stored": "true",
        "multiValued": "false",
    },
    {
        "name": "permission_labels",
        "type": "string",
        "indexed": "true",
        "stored": "false",
        "multiValued": "true",
    },
    {
        "name": "res_name",
        "type": "text_general",
        "indexed": "true",
        "stored": "true",
        "multiValued": "true",
    },
    {
        "name": "res_description",
        "type": "text_general",
        "indexed": "true",
        "stored": "true",
        "multiValued": "true",
    },
    {
        "name": "res_format",
        "type": "string",
        "indexed": "true",
        "stored": "true",
        "multiValued": "true",
    },
    {
        "name": "res_url",
        "type": "string",
        "indexed": "true",
        "stored": "true",
        "multiValued": "true",
    },
    {
        "name": "res_type",
        "type": "string",
        "indexed": "true",
        "stored": "true",
        "multiValued": "true",
    },
    {
        "name": "text",
        "type": "text",
        "indexed": "true",
        "stored": "false",
        "multiValued": "true",
    },
    {
        "name": "urls",
        "type": "text",
        "indexed": "true",
        "stored": "false",
        "multiValued": "true",
    },
    {
        "name": "depends_on",
        "type": "text",
        "indexed": "true",
        "stored": "false",
        "multiValued": "true",
    },
    {
        "name": "dependency_of",
        "type": "text",
        "indexed": "true",
        "stored": "false",
        "multiValued": "true",
    },
    {
        "name": "derives_from",
        "type": "text",
        "indexed": "true",
        "stored": "false",
        "multiValued": "true",
    },
    {
        "name": "has_derivation",
        "type": "text",
        "indexed": "true",
        "stored": "false",
        "multiValued": "true",
    },
    {
        "name": "links_to",
        "type": "text",
        "indexed": "true",
        "stored": "false",
        "multiValued": "true",
    },
    {
        "name": "linked_from",
        "type": "text",
        "indexed": "true",
        "stored": "false",
        "multiValued": "true",
    },
    {
        "name": "child_of",
        "type": "text",
        "indexed": "true",
        "stored": "false",
        "multiValued": "true",
    },
    {
        "name": "parent_of",
        "type": "text",
        "indexed": "true",
        "stored": "false",
        "multiValued": "true",
    },
    {
        "name": "views_total",
        "type": "int",
        "indexed": "true",
        "stored": "false"
    },
    {
        "name": "views_recent",
        "type": "int",
        "indexed": "true",
        "stored": "false"
    },
    {
        "name": "resources_accessed_total",
        "type": "int",
        "indexed": "true",
        "stored": "false"
    },
    {
        "name": "resources_accessed_recent",
        "type": "int",
        "indexed": "true",
        "stored": "false"
    },
    {
        "name": "metadata_created",
        "type": "date",
        "indexed": "true",
        "stored": "true",
        "multiValued": "false",
    },
    {
        "name": "metadata_modified",
        "type": "date",
        "indexed": "true",
        "stored": "true",
        "multiValued": "false",
    },
    {
        "name": "indexed_ts",
        "type": "date",
        "indexed": "true",
        "stored": "true",
        "default": "NOW",
        "multiValued": "false",
    },
    {
        "name": "title_string",
        "type": "string",
        "indexed": "true",
        "stored": "false"
    },
    {
        "name": "data_dict",
        "type": "string",
        "indexed": "false",
        "stored": "true"
    },
    {
        "name": "validated_data_dict",
        "type": "string",
        "indexed": "false",
        "stored": "true"
    },
    {
        "name": "_version_",
        "type": "string",
        "indexed": "true",
        "stored": "true"
    },
]

dynamic_fields = [
    {
        "name": "*_date",
        "type": "date",
        "indexed": "true",
        "stored": "true",
        "multiValued": "false"
    },
    {
        "name": "extras_*",
        "type": "text",
        "indexed": "true",
        "stored": "true",
        "multiValued": "false"
    },
    {
        "name": "res_extras_*",
        "type": "text",
        "indexed": "true",
        "stored": "true",
        "multiValued": "true"
    },
    {
        "name": "vocab_*",
        "type": "string",
        "indexed": "true",
        "stored": "true",
        "multiValued": "true"
    },
    {
        "name": "*",
        "type": "string",
        "indexed": "true",
        "stored": "false",
    },
]

copy_fields = [
    {
        "source": "url",
        "dest": "urls"
    },
    {
        "source": "title",
        "dest": "title_ngram"
    },
    {
        "source": "name",
        "dest": "name_ngram"
    },
    {
        "source": "ckan_url",
        "dest": "urls"
    },
    {
        "source": "download_url",
        "dest": "urls"
    },
    {
        "source": "res_url",
        "dest": "urls"
    },
    {
        "source": "extras_*",
        "dest": "text"
    },
    {
        "source": "res_extras_*",
        "dest": "text"
    },
    {
        "source": "vocab_*",
        "dest": "text"
    },
    {
        "source": "urls",
        "dest": "text"
    },
    {
        "source": "name",
        "dest": "text"
    },
    {
        "source": "title",
        "dest": "text"
    },
    {
        "source": "text",
        "dest": "text"
    },
    {
        "source": "license",
        "dest": "text"
    },
    {
        "source": "notes",
        "dest": "text"
    },
    {
        "source": "tags",
        "dest": "text"
    },
    {
        "source": "groups",
        "dest": "text"
    },
    {
        "source": "organization",
        "dest": "text"
    },
    {
        "source": "res_name",
        "dest": "text"
    },
    {
        "source": "res_description",
        "dest": "text"
    },
    {
        "source": "maintainer",
        "dest": "text"
    },
    {
        "source": "author",
        "dest": "text"
    },
]


class ManagedSearchSchemaPlugin(p.SingletonPlugin):
    p.implements(p.ISearchSchema)
    p.implements(p.IClick)

    # ISearchSchema

    def update_search_schema_definitions(self, definitions):
        definitions['field-type'].extend(field_types)
        definitions['field'].extend(fields)
        definitions['dynamic-field'].extend(dynamic_fields)
        definitions['copy-field'].extend(copy_fields)

    # IClick

    def get_commands(self):
        return cli.get_commands()
