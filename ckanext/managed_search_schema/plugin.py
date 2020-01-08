# -*- coding: utf-8 -*-

import ckan.plugins as p
import ckanext.managed_search_schema.cli as cli

field_types = [{
    u"name": u"string",
    u"class": u"solr.StrField",
    u"sortMissingLast": u"true",
    u"omitNorms": u"true"
}, {
    u"name": u"boolean",
    u"class": u"solr.BoolField",
    u"sortMissingLast": u"true",
    u"omitNorms": u"true"
}, {
    u"name": u"binary",
    u"class": u"solr.BinaryField"
}, {
    u"name": u"int",
    u"class": u"solr.IntPointField",
    u"omitNorms": u"true",
    u"positionIncrementGap": u"0"
}, {
    u"name": u"float",
    u"class": u"solr.FloatPointField",
    u"omitNorms": u"true",
    u"positionIncrementGap": u"0"
}, {
    u"name": u"long",
    u"class": u"solr.LongPointField",
    u"omitNorms": u"true",
    u"positionIncrementGap": u"0"
}, {
    u"name": u"double",
    u"class": u"solr.DoublePointField",
    u"omitNorms": u"true",
    u"positionIncrementGap": u"0"
}, {
    u"name": u"pint",
    u"class": u"solr.IntPointField",
    u"omitNorms": u"true",
    u"positionIncrementGap": u"0"
}, {
    u"name": u"pfloat",
    u"class": u"solr.FloatPointField",
    u"omitNorms": u"true",
    u"positionIncrementGap": u"0"
}, {
    u"name": u"plong",
    u"class": u"solr.LongPointField",
    u"omitNorms": u"true",
    u"positionIncrementGap": u"0"
}, {
    u"name": u"pdouble",
    u"class": u"solr.DoublePointField",
    u"omitNorms": u"true",
    u"positionIncrementGap": u"0"
}, {
    u"name": u"date",
    u"class": u"solr.DatePointField",
    u"omitNorms": u"true",
    u"positionIncrementGap": u"0"
}, {
    u"name": u"pdate",
    u"class": u"solr.DatePointField",
    u"omitNorms": u"true",
    u"positionIncrementGap": u"0"
}, {
    u"name": u"pdates",
    u"class": u"solr.DatePointField",
    u"positionIncrementGap": u"0",
    u"multiValued": u"true"
}, {
    u"name": u"booleans",
    u"class": u"solr.BoolField",
    u"sortMissingLast": u"true",
    u"multiValued": u"true"
}, {
    u"name": u"pints",
    u"class": u"solr.IntPointField",
    u"positionIncrementGap": u"0",
    u"multiValued": u"true"
}, {
    u"name": u"pfloats",
    u"class": u"solr.FloatPointField",
    u"positionIncrementGap": u"0",
    u"multiValued": u"true"
}, {
    u"name": u"plongs",
    u"class": u"solr.LongPointField",
    u"positionIncrementGap": u"0",
    u"multiValued": u"true"
}, {
    u"name": u"pdoubles",
    u"class": u"solr.DoublePointField",
    u"positionIncrementGap": u"0",
    u"multiValued": u"true"
}, {
    u"name": u"text",
    u"class": u"solr.TextField",
    u"positionIncrementGap": u"100",
    u"indexAnalyzer": {
        u"tokenizer": {
            u"class": u"solr.WhitespaceTokenizerFactory",
        },
        u"filters": [
            {
                u"class": u"solr.WordDelimiterFilterFactory",
                u"generateWordParts": u"1",
                u"generateNumberParts": u"1",
                u"catenateWords": u"1",
                u"catenateNumbers": u"1",
                u"catenateAll": u"0",
                u"splitOnCaseChange": u"1"
            },
            {
                u"class": u"solr.LowerCaseFilterFactory"
            },
            {
                u"class": u"solr.SnowballPorterFilterFactory",
                u"language": u"English",
                u"protected": u"protwords.txt"
            },
            {
                u"class": u"solr.ASCIIFoldingFilterFactory"
            },
        ]
    },
    u"queryAnalyzer": {
        u"tokenizer": {
            u"class": u"solr.WhitespaceTokenizerFactory"
        },
        u"filters": [
            {
                u"class": u"solr.SynonymFilterFactory",
                u"synonyms": u"synonyms.txt",
                u"ignoreCase": u"true",
                u"expand": u"true",
            },
            {
                u"class": u"solr.WordDelimiterFilterFactory",
                u"generateWordParts": u"1",
                u"generateNumberParts": u"1",
                u"catenateWords": u"0",
                u"catenateNumbers": u"0",
                u"catenateAll": u"0",
                u"splitOnCaseChange": u"1"
            },
            {
                u"class": u"solr.LowerCaseFilterFactory",
            },
            {
                u"class": u"solr.SnowballPorterFilterFactory",
                u"language": u"English",
                u"protected": u"protwords.txt",
            },
            {
                u"class": u"solr.ASCIIFoldingFilterFactory",
            },
        ]
    },
}, {
    u"name": u"text_general",
    u"class": u"solr.TextField",
    u"positionIncrementGap": u"100",
    u"indexAnalyzer": {
        u"tokenizer": {
            u"class": u"solr.WhitespaceTokenizerFactory",
        },
        u"filters": [{
            u"class": u"solr.WordDelimiterFilterFactory",
            u"generateWordParts": u"1",
            u"generateNumberParts": u"1",
            u"catenateWords": u"1",
            u"catenateNumbers": u"1",
            u"catenateAll": u"0",
            u"splitOnCaseChange": u"0",
        }, {
            u"class": u"solr.LowerCaseFilterFactory",
        }]
    },
    u"queryAnalyzer": {
        u"tokenizer": {
            u"class": u"solr.WhitespaceTokenizerFactory"
        },
        u"filters": [
            {
                u"class": u"solr.SynonymFilterFactory",
                u"synonyms": u"synonyms.txt",
                u"ignoreCase": u"true",
                u"expand": u"true",
            },
            {
                u"class": u"solr.WordDelimiterFilterFactory",
                u"generateWordParts": u"1",
                u"generateNumberParts": u"1",
                u"catenateWords": u"0",
                u"catenateNumbers": u"0",
                u"catenateAll": u"0",
                u"splitOnCaseChange": u"0",
            },
            {
                u"class": u"solr.LowerCaseFilterFactory",
            },
        ]
    },
}, {
    u"name": u"text_ngram",
    u"class": u"solr.TextField",
    u"positionIncrementGap": u"100",
    u"indexAnalyzer": {
        u"tokenizer": {
            u"class": u"solr.NGramTokenizerFactory",
            u"minGramSize": u"2",
            u"maxGramSize": u"10",
        },
        u"filters": [{
            u"class": u"solr.LowerCaseFilterFactory",
        }]
    },
    u"queryAnalyzer": {
        u"tokenizer": {
            u"class": u"solr.WhitespaceTokenizerFactory"
        },
        u"filters": [{
            u"class": u"solr.LowerCaseFilterFactory",
        }]
    },
}]

fields = [
    {
        u"name": u"index_id",
        u"type": u"string",
        u"indexed": u"true",
        u"stored": u"true",
        u"required": u"true",
    },
    {
        u"name": u"id",
        u"type": u"string",
        u"indexed": u"true",
        u"stored": u"true",
        u"required": u"true",
    },
    {
        u"name": u"site_id",
        u"type": u"string",
        u"indexed": u"true",
        u"stored": u"true",
        u"required": u"true",
    },
    {
        u"name": u"title",
        u"type": u"text",
        u"indexed": u"true",
        u"stored": u"true"
    },
    {
        u"name": u"title_ngram",
        u"type": u"text_ngram",
        u"indexed": u"true",
        u"stored": u"true"
    },
    {
        u"name": u"entity_type",
        u"type": u"string",
        u"indexed": u"true",
        u"stored": u"true",
        u"omitNorms": u"true",
    },
    {
        u"name": u"dataset_type",
        u"type": u"string",
        u"indexed": u"true",
        u"stored": u"true"
    },
    {
        u"name": u"state",
        u"type": u"string",
        u"indexed": u"true",
        u"stored": u"true",
        u"omitNorms": u"true",
    },
    {
        u"name": u"name",
        u"type": u"string",
        u"indexed": u"true",
        u"stored": u"true",
        u"omitNorms": u"true",
    },
    {
        u"name": u"name_ngram",
        u"type": u"text_ngram",
        u"indexed": u"true",
        u"stored": u"true"
    },
    {
        u"name": u"revision_id",
        u"type": u"string",
        u"indexed": u"true",
        u"stored": u"true",
        u"omitNorms": u"true",
    },
    {
        u"name": u"version",
        u"type": u"string",
        u"indexed": u"true",
        u"stored": u"true"
    },
    {
        u"name": u"url",
        u"type": u"string",
        u"indexed": u"true",
        u"stored": u"true",
        u"omitNorms": u"true",
    },
    {
        u"name": u"ckan_url",
        u"type": u"string",
        u"indexed": u"true",
        u"stored": u"true",
        u"omitNorms": u"true",
    },
    {
        u"name": u"download_url",
        u"type": u"string",
        u"indexed": u"true",
        u"stored": u"true",
        u"omitNorms": u"true",
    },
    {
        u"name": u"notes",
        u"type": u"text",
        u"indexed": u"true",
        u"stored": u"true"
    },
    {
        u"name": u"author",
        u"type": u"text_general",
        u"indexed": u"true",
        u"stored": u"true"
    },
    {
        u"name": u"author_email",
        u"type": u"text_general",
        u"indexed": u"true",
        u"stored": u"true"
    },
    {
        u"name": u"maintainer",
        u"type": u"text_general",
        u"indexed": u"true",
        u"stored": u"true"
    },
    {
        u"name": u"maintainer_email",
        u"type": u"text_general",
        u"indexed": u"true",
        u"stored": u"true"
    },
    {
        u"name": u"license",
        u"type": u"string",
        u"indexed": u"true",
        u"stored": u"true"
    },
    {
        u"name": u"license_id",
        u"type": u"string",
        u"indexed": u"true",
        u"stored": u"true"
    },
    {
        u"name": u"ratings_count",
        u"type": u"int",
        u"indexed": u"true",
        u"stored": u"false"
    },
    {
        u"name": u"ratings_average",
        u"type": u"float",
        u"indexed": u"true",
        u"stored": u"false"
    },
    {
        u"name": u"tags",
        u"type": u"string",
        u"indexed": u"true",
        u"stored": u"true",
        u"multiValued": u"true",
    },
    {
        u"name": u"groups",
        u"type": u"string",
        u"indexed": u"true",
        u"stored": u"true",
        u"multiValued": u"true",
    },
    {
        u"name": u"organization",
        u"type": u"string",
        u"indexed": u"true",
        u"stored": u"true",
        u"multiValued": u"false",
    },
    {
        u"name": u"capacity",
        u"type": u"string",
        u"indexed": u"true",
        u"stored": u"true",
        u"multiValued": u"false",
    },
    {
        u"name": u"permission_labels",
        u"type": u"string",
        u"indexed": u"true",
        u"stored": u"false",
        u"multiValued": u"true",
    },
    {
        u"name": u"res_name",
        u"type": u"text_general",
        u"indexed": u"true",
        u"stored": u"true",
        u"multiValued": u"true",
    },
    {
        u"name": u"res_description",
        u"type": u"text_general",
        u"indexed": u"true",
        u"stored": u"true",
        u"multiValued": u"true",
    },
    {
        u"name": u"res_format",
        u"type": u"string",
        u"indexed": u"true",
        u"stored": u"true",
        u"multiValued": u"true",
    },
    {
        u"name": u"res_url",
        u"type": u"string",
        u"indexed": u"true",
        u"stored": u"true",
        u"multiValued": u"true",
    },
    {
        u"name": u"res_type",
        u"type": u"string",
        u"indexed": u"true",
        u"stored": u"true",
        u"multiValued": u"true",
    },
    {
        u"name": u"text",
        u"type": u"text",
        u"indexed": u"true",
        u"stored": u"false",
        u"multiValued": u"true",
    },
    {
        u"name": u"urls",
        u"type": u"text",
        u"indexed": u"true",
        u"stored": u"false",
        u"multiValued": u"true",
    },
    {
        u"name": u"depends_on",
        u"type": u"text",
        u"indexed": u"true",
        u"stored": u"false",
        u"multiValued": u"true",
    },
    {
        u"name": u"dependency_of",
        u"type": u"text",
        u"indexed": u"true",
        u"stored": u"false",
        u"multiValued": u"true",
    },
    {
        u"name": u"derives_from",
        u"type": u"text",
        u"indexed": u"true",
        u"stored": u"false",
        u"multiValued": u"true",
    },
    {
        u"name": u"has_derivation",
        u"type": u"text",
        u"indexed": u"true",
        u"stored": u"false",
        u"multiValued": u"true",
    },
    {
        u"name": u"links_to",
        u"type": u"text",
        u"indexed": u"true",
        u"stored": u"false",
        u"multiValued": u"true",
    },
    {
        u"name": u"linked_from",
        u"type": u"text",
        u"indexed": u"true",
        u"stored": u"false",
        u"multiValued": u"true",
    },
    {
        u"name": u"child_of",
        u"type": u"text",
        u"indexed": u"true",
        u"stored": u"false",
        u"multiValued": u"true",
    },
    {
        u"name": u"parent_of",
        u"type": u"text",
        u"indexed": u"true",
        u"stored": u"false",
        u"multiValued": u"true",
    },
    {
        u"name": u"views_total",
        u"type": u"int",
        u"indexed": u"true",
        u"stored": u"false"
    },
    {
        u"name": u"views_recent",
        u"type": u"int",
        u"indexed": u"true",
        u"stored": u"false"
    },
    {
        u"name": u"resources_accessed_total",
        u"type": u"int",
        u"indexed": u"true",
        u"stored": u"false"
    },
    {
        u"name": u"resources_accessed_recent",
        u"type": u"int",
        u"indexed": u"true",
        u"stored": u"false"
    },
    {
        u"name": u"metadata_created",
        u"type": u"date",
        u"indexed": u"true",
        u"stored": u"true",
        u"multiValued": u"false",
    },
    {
        u"name": u"metadata_modified",
        u"type": u"date",
        u"indexed": u"true",
        u"stored": u"true",
        u"multiValued": u"false",
    },
    {
        u"name": u"indexed_ts",
        u"type": u"date",
        u"indexed": u"true",
        u"stored": u"true",
        u"default": u"NOW",
        u"multiValued": u"false",
    },
    {
        u"name": u"title_string",
        u"type": u"string",
        u"indexed": u"true",
        u"stored": u"false"
    },
    {
        u"name": u"data_dict",
        u"type": u"string",
        u"indexed": u"false",
        u"stored": u"true"
    },
    {
        u"name": u"validated_data_dict",
        u"type": u"string",
        u"indexed": u"false",
        u"stored": u"true"
    },
    {
        u"name": u"_versionu",
        u"type": u"string",
        u"indexed": u"true",
        u"stored": u"true"
    },
]

dynamic_fields = [
    {
        u"name": u"*_date",
        u"type": u"date",
        u"indexed": u"true",
        u"stored": u"true",
        u"multiValued": u"false"
    },
    {
        u"name": u"extras_u",
        u"type": u"text",
        u"indexed": u"true",
        u"stored": u"true",
        u"multiValued": u"false"
    },
    {
        u"name": u"res_extras_u",
        u"type": u"text",
        u"indexed": u"true",
        u"stored": u"true",
        u"multiValued": u"true"
    },
    {
        u"name": u"vocab_u",
        u"type": u"string",
        u"indexed": u"true",
        u"stored": u"true",
        u"multiValued": u"true"
    },
    {
        u"name": u"u",
        u"type": u"string",
        u"indexed": u"true",
        u"stored": u"false",
    },
]

copy_fields = [
    {
        u"source": u"url",
        u"dest": u"urls"
    },
    {
        u"source": u"title",
        u"dest": u"title_ngram"
    },
    {
        u"source": u"name",
        u"dest": u"name_ngram"
    },
    {
        u"source": u"ckan_url",
        u"dest": u"urls"
    },
    {
        u"source": u"download_url",
        u"dest": u"urls"
    },
    {
        u"source": u"res_url",
        u"dest": u"urls"
    },
    {
        u"source": u"extras_u",
        u"dest": u"text"
    },
    {
        u"source": u"res_extras_u",
        u"dest": u"text"
    },
    {
        u"source": u"vocab_u",
        u"dest": u"text"
    },
    {
        u"source": u"urls",
        u"dest": u"text"
    },
    {
        u"source": u"name",
        u"dest": u"text"
    },
    {
        u"source": u"title",
        u"dest": u"text"
    },
    {
        u"source": u"text",
        u"dest": u"text"
    },
    {
        u"source": u"license",
        u"dest": u"text"
    },
    {
        u"source": u"notes",
        u"dest": u"text"
    },
    {
        u"source": u"tags",
        u"dest": u"text"
    },
    {
        u"source": u"groups",
        u"dest": u"text"
    },
    {
        u"source": u"organization",
        u"dest": u"text"
    },
    {
        u"source": u"res_name",
        u"dest": u"text"
    },
    {
        u"source": u"res_description",
        u"dest": u"text"
    },
    {
        u"source": u"maintainer",
        u"dest": u"text"
    },
    {
        u"source": u"author",
        u"dest": u"text"
    },
]


class ManagedSearchSchemaPlugin(p.SingletonPlugin):
    p.implements(p.ISearchSchema)
    p.implements(p.IClick)

    # ISearchSchema

    def update_search_schema_definitions(self, definitions):
        definitions[u'field-type'].extend(field_types)
        definitions[u'field'].extend(fields)
        definitions[u'dynamic-field'].extend(dynamic_fields)
        definitions[u'copy-field'].extend(copy_fields)

    # IClick

    def get_commands(self):
        return cli.get_commands()
