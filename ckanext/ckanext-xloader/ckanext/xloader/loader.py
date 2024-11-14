'Load a CSV into postgres'
from __future__ import absolute_import

import datetime
import itertools
from six import text_type as str, binary_type
import os
import os.path
import tempfile
from decimal import Decimal

import psycopg2
from chardet.universaldetector import UniversalDetector
from six.moves import zip
from tabulator import config as tabulator_config, EncodingError, Stream, TabulatorException
from unidecode import unidecode

import ckan.plugins as p

from .job_exceptions import FileCouldNotBeLoadedError, LoaderError
from .parser import CSV_SAMPLE_LINES, TypeConverter
from .utils import datastore_resource_exists, headers_guess, type_guess

from ckan.plugins.toolkit import config

import ckanext.datastore.backend.postgres as datastore_db

get_write_engine = datastore_db.get_write_engine
create_indexes = datastore_db.create_indexes
_drop_indexes = datastore_db._drop_indexes

MAX_COLUMN_LENGTH = 63
tabulator_config.CSV_SAMPLE_LINES = CSV_SAMPLE_LINES

SINGLE_BYTE_ENCODING = 'cp1252'


class UnknownEncodingStream(object):
    """ Provides a context manager that wraps a Tabulator stream
    and tries multiple encodings if one fails.

    This is particularly relevant in cases like Latin-1 encoding,
    which is usually ASCII and thus the sample could be sniffed as UTF-8,
    only to run into problems later in the file.
    """

    def __init__(self, filepath, file_format, decoding_result, **kwargs):
        self.filepath = filepath
        self.file_format = file_format
        self.stream_args = kwargs
        self.decoding_result = decoding_result  # {'encoding': 'EUC-JP', 'confidence': 0.99}

    def __enter__(self):
        try:

            if (self.decoding_result and self.decoding_result['confidence'] and self.decoding_result['confidence'] > 0.7):
                self.stream = Stream(self.filepath, format=self.file_format, encoding=self.decoding_result['encoding'],
                                     ** self.stream_args).__enter__()
            else:
                self.stream = Stream(self.filepath, format=self.file_format, ** self.stream_args).__enter__()

        except (EncodingError, UnicodeDecodeError):
            self.stream = Stream(self.filepath, format=self.file_format,
                                 encoding=SINGLE_BYTE_ENCODING, **self.stream_args).__enter__()
        return self.stream

    def __exit__(self, *args):
        return self.stream.__exit__(*args)


def detect_encoding(file_path):
    detector = UniversalDetector()
    with open(file_path, 'rb') as file:
        for line in file:
            detector.feed(line)
            if detector.done:
                break
    detector.close()
    return detector.result  # e.g. {'encoding': 'EUC-JP', 'confidence': 0.99}


def _fields_match(fields, existing_fields, logger):
    ''' Check whether all columns have the same names and types as previously,
    independent of ordering.
    '''
    # drop the generated '_id' field
    for index in range(len(existing_fields)):
        if existing_fields[index]['id'] == '_id':
            existing_fields.pop(index)
            break

    # fail fast if number of fields doesn't match
    field_count = len(fields)
    if field_count != len(existing_fields):
        logger.info("Fields do not match; there are now %s fields but previously %s", field_count, len(existing_fields))
        return False

    # ensure each field is present in both collections with the same type
    for index in range(field_count):
        field_id = fields[index]['id']
        for existing_index in range(field_count):
            existing_field_id = existing_fields[existing_index]['id']
            if field_id == existing_field_id:
                if fields[index]['type'] == existing_fields[existing_index]['type']:
                    break
                else:
                    logger.info("Fields do not match; new type for %s field is %s but existing type is %s",
                                field_id, fields[index]["type"], existing_fields[existing_index]['type'])
                    return False
        else:
            logger.info("Fields do not match; no existing entry found for %s", field_id)
            return False
    return True


def _clear_datastore_resource(resource_id):
    ''' Delete all records from the datastore table, without dropping the table itself.
    '''
    engine = get_write_engine()
    with engine.begin() as conn:
        conn.execute("SET LOCAL lock_timeout = '5s'")
        conn.execute('TRUNCATE TABLE "{}"'.format(resource_id))


def load_csv(csv_filepath, resource_id, mimetype='text/csv', logger=None):
    '''Loads a CSV into DataStore. Does not create the indexes.'''

    decoding_result = detect_encoding(csv_filepath)
    logger.info("load_csv: Decoded encoding: %s", decoding_result)
    # Determine the header row
    try:
        file_format = os.path.splitext(csv_filepath)[1].strip('.')
        with UnknownEncodingStream(csv_filepath, file_format, decoding_result) as stream:
            header_offset, headers = headers_guess(stream.sample)
    except TabulatorException:
        try:
            file_format = mimetype.lower().split('/')[-1]
            with UnknownEncodingStream(csv_filepath, file_format, decoding_result) as stream:
                header_offset, headers = headers_guess(stream.sample)
        except TabulatorException as e:
            raise LoaderError('Tabulator error: {}'.format(e))
    except Exception as e:
        raise FileCouldNotBeLoadedError(e)

    # Some headers might have been converted from strings to floats and such.
    headers = encode_headers(headers)

    # Get the list of rows to skip. The rows in the tabulator stream are
    # numbered starting with 1.
    skip_rows = list(range(1, header_offset + 1))
    skip_rows.append({'type': 'preset', 'value': 'blank'})

    # Get the delimiter used in the file
    delimiter = stream.dialect.get('delimiter')
    if delimiter is None:
        logger.warning('Could not determine delimiter from file, use default ","')
        delimiter = ','

    headers = [
        header.strip()[:MAX_COLUMN_LENGTH].strip()
        for header in headers
        if header.strip()
    ]

    # TODO worry about csv header name problems
    # e.g. duplicate names

    # encoding (and line ending?)- use chardet
    # It is easier to reencode it as UTF8 than convert the name of the encoding
    # to one that pgloader will understand.
    logger.info('Ensuring character coding is UTF8')
    f_write = tempfile.NamedTemporaryFile(suffix=file_format, delete=False)
    try:
        save_args = {'target': f_write.name, 'format': 'csv', 'encoding': 'utf-8', 'delimiter': delimiter}
        try:
            with UnknownEncodingStream(csv_filepath, file_format, decoding_result,
                                       skip_rows=skip_rows) as stream:
                stream.save(**save_args)
        except (EncodingError, UnicodeDecodeError):
            with Stream(csv_filepath, format=file_format, encoding=SINGLE_BYTE_ENCODING,
                        skip_rows=skip_rows) as stream:
                stream.save(**save_args)
        csv_filepath = f_write.name

        # datastore db connection
        engine = get_write_engine()

        # get column info from existing table
        existing = datastore_resource_exists(resource_id)
        existing_info = {}
        if existing:
            existing_fields = existing.get('fields', [])
            existing_info = dict((f['id'], f['info'])
                                 for f in existing_fields
                                 if 'info' in f)

            # Column types are either set (overridden) in the Data Dictionary page
            # or default to text type (which is robust)
            fields = [
                {'id': header_name,
                 'type': existing_info.get(header_name, {})
                    .get('type_override') or 'text',
                 }
                for header_name in headers]

            # Maintain data dictionaries from matching column names
            for f in fields:
                if f['id'] in existing_info:
                    f['info'] = existing_info[f['id']]

            '''
            Delete or truncate existing datastore table before proceeding,
            depending on whether any fields have changed.
            Otherwise the COPY will append to the existing table.
            And if the fields have significantly changed, it may also fail.
            '''
            if _fields_match(fields, existing_fields, logger):
                logger.info('Clearing records for "%s" from DataStore.', resource_id)
                _clear_datastore_resource(resource_id)
            else:
                logger.info('Deleting "%s" from DataStore.', resource_id)
                delete_datastore_resource(resource_id)
        else:
            fields = [
                {'id': header_name,
                 'type': 'text'}
                for header_name in headers]

        logger.info('Fields: %s', fields)

        # Create table
        from ckan import model
        context = {'model': model, 'ignore_auth': True}
        data_dict = dict(
            resource_id=resource_id,
            fields=fields,
        )
        data_dict['records'] = None  # just create an empty table
        data_dict['force'] = True  # TODO check this - I don't fully
        # understand read-only/datastore resources
        try:
            p.toolkit.get_action('datastore_create')(context, data_dict)
        except p.toolkit.ValidationError as e:
            if 'fields' in e.error_dict:
                # e.g. {'message': None, 'error_dict': {'fields': [u'"***" is not a valid field name']}, '_error_summary': None}  # noqa
                error_message = e.error_dict['fields'][0]
                raise LoaderError('Error with field definition: {}'
                                  .format(error_message))
            else:
                raise LoaderError(
                    'Validation error when creating the database table: {}'
                    .format(str(e)))
        except Exception as e:
            raise LoaderError('Could not create the database table: {}'
                              .format(e))
        connection = context['connection'] = engine.connect()

        # datstore_active is switched on by datastore_create - TODO temporarily
        # disable it until the load is complete
        _disable_fulltext_trigger(connection, resource_id)
        _drop_indexes(context, data_dict, False)

        logger.info('Copying to database...')

        # Options for loading into postgres:
        # 1. \copy - can't use as that is a psql meta-command and not accessible
        #    via psycopg2
        # 2. COPY - requires the db user to have superuser privileges. This is
        #    dangerous. It is also not available on AWS, for example.
        # 3. pgloader method? - as described in its docs:
        #    Note that while the COPY command is restricted to read either from
        #    its standard input or from a local file on the server's file system,
        #    the command line tool psql implements a \copy command that knows
        #    how to stream a file local to the client over the network and into
        #    the PostgreSQL server, using the same protocol as pgloader uses.
        # 4. COPY FROM STDIN - not quite as fast as COPY from a file, but avoids
        #    the superuser issue. <-- picked

        raw_connection = engine.raw_connection()
        try:
            cur = raw_connection.cursor()
            try:
                with open(csv_filepath, 'rb') as f:
                    # can't use :param for table name because params are only
                    # for filter values that are single quoted.
                    try:
                        cur.copy_expert(
                            "COPY \"{resource_id}\" ({column_names}) "
                            "FROM STDIN "
                            "WITH (DELIMITER '{delimiter}', FORMAT csv, HEADER 1, "
                            "      ENCODING '{encoding}');"
                            .format(
                                resource_id=resource_id,
                                column_names=', '.join(['"{}"'.format(h)
                                                        for h in headers]),
                                delimiter=delimiter,
                                encoding='UTF8',
                            ),
                            f)
                    except psycopg2.DataError as e:
                        # e is a str but with foreign chars e.g.
                        # 'extra data: "paul,pa\xc3\xbcl"\n'
                        # but logging and exceptions need a normal (7 bit) str
                        error_str = str(e)
                        logger.warning(error_str)
                        raise LoaderError('Error during the load into PostgreSQL:'
                                          ' {}'.format(error_str))

            finally:
                cur.close()
        finally:
            raw_connection.commit()
    finally:
        os.remove(csv_filepath)  # i.e. the tempfile

    logger.info('...copying done')

    logger.info('Creating search index...')
    _populate_fulltext(connection, resource_id, fields=fields)
    logger.info('...search index created')

    return fields


def create_column_indexes(fields, resource_id, logger):
    logger.info('Creating column indexes (a speed optimization for queries)...')
    from ckan import model
    context = {'model': model, 'ignore_auth': True}
    data_dict = dict(
        resource_id=resource_id,
        fields=fields,
    )
    engine = get_write_engine()
    connection = context['connection'] = engine.connect()

    create_indexes(context, data_dict)
    _enable_fulltext_trigger(connection, resource_id)

    logger.info('...column indexes created.')


def load_table(table_filepath, resource_id, mimetype='text/csv', logger=None):
    '''Loads an Excel file (or other tabular data recognized by tabulator)
    into Datastore and creates indexes.

    Largely copied from datapusher - see below. Is slower than load_csv.
    '''

    # Determine the header row
    logger.info('Determining column names and types')
    decoding_result = detect_encoding(table_filepath)
    logger.info("load_table: Decoded encoding: %s", decoding_result)
    try:
        file_format = os.path.splitext(table_filepath)[1].strip('.')
        with UnknownEncodingStream(table_filepath, file_format, decoding_result,
                                   skip_rows=[{'type': 'preset', 'value': 'blank'}],
                                   post_parse=[TypeConverter().convert_types]) as stream:
            header_offset, headers = headers_guess(stream.sample)
    except TabulatorException:
        try:
            file_format = mimetype.lower().split('/')[-1]
            with UnknownEncodingStream(table_filepath, file_format, decoding_result,
                                       skip_rows=[{'type': 'preset', 'value': 'blank'}],
                                       post_parse=[TypeConverter().convert_types]) as stream:
                header_offset, headers = headers_guess(stream.sample)
        except TabulatorException as e:
            raise LoaderError('Tabulator error: {}'.format(e))
    except Exception as e:
        raise FileCouldNotBeLoadedError(e)

    existing = datastore_resource_exists(resource_id)
    existing_info = None
    if existing:
        existing_fields = existing.get('fields', [])
        existing_info = dict(
            (f['id'], f['info'])
            for f in existing_fields if 'info' in f)

    # Some headers might have been converted from strings to floats and such.
    headers = encode_headers(headers)

    # Get the list of rows to skip. The rows in the tabulator stream are
    # numbered starting with 1. We also want to skip the header row.
    skip_rows = list(range(1, header_offset + 2))
    skip_rows.append({'type': 'preset', 'value': 'blank'})

    TYPES, TYPE_MAPPING = get_types()
    strict_guessing = p.toolkit.asbool(
        config.get('ckanext.xloader.strict_type_guessing', True))
    types = type_guess(stream.sample[1:], types=TYPES, strict=strict_guessing)

    # override with types user requested
    if existing_info:
        types = [
            {
                'text': str,
                'numeric': Decimal,
                'timestamp': datetime.datetime,
            }.get(existing_info.get(h, {}).get('type_override'), t)
            for t, h in zip(types, headers)]

    headers = [header.strip()[:MAX_COLUMN_LENGTH] for header in headers if header.strip()]
    type_converter = TypeConverter(types=types)

    with UnknownEncodingStream(table_filepath, file_format, decoding_result,
                               skip_rows=skip_rows,
                               post_parse=[type_converter.convert_types]) as stream:
        def row_iterator():
            for row in stream:
                data_row = {}
                for index, cell in enumerate(row):
                    data_row[headers[index]] = cell
                yield data_row
        result = row_iterator()

        headers_dicts = [dict(id=field[0], type=TYPE_MAPPING[str(field[1])])
                         for field in zip(headers, types)]

        # Maintain data dictionaries from matching column names
        if existing_info:
            for h in headers_dicts:
                if h['id'] in existing_info:
                    h['info'] = existing_info[h['id']]
                    # create columns with types user requested
                    type_override = existing_info[h['id']].get('type_override')
                    if type_override in list(_TYPE_MAPPING.values()):
                        h['type'] = type_override

        logger.info('Determined headers and types: %s', headers_dicts)

        '''
        Delete or truncate existing datastore table before proceeding,
        depending on whether any fields have changed.
        Otherwise 'datastore_create' will append to the existing datastore.
        And if the fields have significantly changed, it may also fail.
        '''
        if existing:
            if _fields_match(headers_dicts, existing_fields, logger):
                logger.info('Clearing records for "%s" from DataStore.', resource_id)
                _clear_datastore_resource(resource_id)
            else:
                logger.info('Deleting "%s" from datastore.', resource_id)
                delete_datastore_resource(resource_id)

        logger.info('Copying to database...')
        count = 0
        # Some types cannot be stored as empty strings and must be converted to None,
        # https://github.com/ckan/ckanext-xloader/issues/182
        non_empty_types = ['timestamp', 'numeric']
        for i, records in enumerate(chunky(result, 250)):
            count += len(records)
            logger.info('Saving chunk %s', i)
            for row in records:
                for column_index, column_name in enumerate(row):
                    if headers_dicts[column_index]['type'] in non_empty_types and row[column_name] == '':
                        row[column_name] = None
            send_resource_to_datastore(resource_id, headers_dicts, records)
        logger.info('...copying done')

    if count:
        logger.info('Successfully pushed %s entries to "%s".', count, resource_id)
    else:
        # no datastore table is created
        raise LoaderError('No entries found - nothing to load')


_TYPE_MAPPING = {
    "<type 'str'>": 'text',
    "<type 'unicode'>": 'text',
    "<type 'bytes'>": 'text',
    "<type 'bool'>": 'text',
    "<type 'int'>": 'numeric',
    "<type 'float'>": 'numeric',
    "<class 'decimal.Decimal'>": 'numeric',
    "<type 'datetime.datetime'>": 'timestamp',
    "<class 'str'>": 'text',
    "<class 'unicode'>": 'text',
    "<class 'bytes'>": 'text',
    "<class 'bool'>": 'text',
    "<class 'int'>": 'numeric',
    "<class 'float'>": 'numeric',
    "<class 'datetime.datetime'>": 'timestamp',
}


def get_types():
    _TYPES = [int, bool, str, binary_type, datetime.datetime, float, Decimal]
    TYPE_MAPPING = config.get('TYPE_MAPPING', _TYPE_MAPPING)
    return _TYPES, TYPE_MAPPING


def encode_headers(headers):
    encoded_headers = []
    for header in headers:
        try:
            encoded_headers.append(unidecode(header))
        except AttributeError:
            encoded_headers.append(unidecode(str(header)))

    return encoded_headers


def chunky(iterable, n):
    """
    Generates chunks of data that can be loaded into ckan

    :param n: Size of each chunks
    :type n: int
    """
    it = iter(iterable)
    item = list(itertools.islice(it, n))
    while item:
        yield item
        item = list(itertools.islice(it, n))


def send_resource_to_datastore(resource_id, headers, records):
    """
    Stores records in CKAN datastore
    """
    request = {'resource_id': resource_id,
               'fields': headers,
               'force': True,
               'records': records}

    from ckan import model
    context = {'model': model, 'ignore_auth': True}
    try:
        p.toolkit.get_action('datastore_create')(context, request)
    except p.toolkit.ValidationError as e:
        raise LoaderError('Validation error writing rows to db: {}'
                          .format(str(e)))


def delete_datastore_resource(resource_id):
    from ckan import model
    context = {'model': model, 'user': '', 'ignore_auth': True}
    try:
        p.toolkit.get_action('datastore_delete')(context, dict(
            id=resource_id, force=True))
    except p.toolkit.ObjectNotFound:
        # this is ok
        return
    return


def fulltext_function_exists(connection):
    '''Check to see if the fulltext function is set-up in postgres.
    This is done during install of CKAN if it is new enough to have:
    https://github.com/ckan/ckan/pull/3786
    or otherwise it is checked on startup of this plugin.
    '''
    res = connection.execute('''
        select * from pg_proc where proname = 'populate_full_text_trigger';
        ''')
    return bool(res.rowcount)


def fulltext_trigger_exists(connection, resource_id):
    '''Check to see if the fulltext trigger is set-up on this resource's table.
    This will only be the case if your CKAN is new enough to have:
    https://github.com/ckan/ckan/pull/3786
    '''
    res = connection.execute('''
        SELECT pg_trigger.tgname FROM pg_class
        JOIN pg_trigger ON pg_class.oid=pg_trigger.tgrelid
        WHERE pg_class.relname={table}
        AND pg_trigger.tgname='zfulltext';
        '''.format(
        table=literal_string(resource_id)))
    return bool(res.rowcount)


def _disable_fulltext_trigger(connection, resource_id):
    connection.execute('ALTER TABLE {table} DISABLE TRIGGER zfulltext;'
                       .format(table=identifier(resource_id)))


def _enable_fulltext_trigger(connection, resource_id):
    connection.execute('ALTER TABLE {table} ENABLE TRIGGER zfulltext;'
                       .format(table=identifier(resource_id)))


def _populate_fulltext(connection, resource_id, fields):
    '''Populates the _full_text column. i.e. the same as datastore_run_triggers
    but it runs in 1/9 of the time.

    The downside is that it reimplements the code that calculates the text to
    index, breaking DRY. And its annoying to pass in the column names.

    fields: list of dicts giving the each column's 'id' (name) and 'type'
            (text/numeric/timestamp)
    '''
    sql = \
        u'''
        UPDATE {table}
        SET _full_text = to_tsvector({cols});
        '''.format(
            # coalesce copes with blank cells
            table=identifier(resource_id),
            cols=" || ' ' || ".join(
                'coalesce({}, \'\')'.format(
                    identifier(field['id'])
                    + ('::text' if field['type'] != 'text' else '')
                )
                for field in fields
                if not field['id'].startswith('_')
            )
        )
    connection.execute(sql)


def calculate_record_count(resource_id, logger):
    '''
    Calculate an estimate of the record/row count and store it in
    Postgresql's pg_stat_user_tables. This number will be used when
    specifying `total_estimation_threshold`
    '''
    logger.info('Calculating record count (running ANALYZE on the table)')
    engine = get_write_engine()
    conn = engine.connect()
    conn.execute("ANALYZE \"{resource_id}\";"
                 .format(resource_id=resource_id))


def identifier(s):
    # "%" needs to be escaped, otherwise connection.execute thinks it is for
    # substituting a bind parameter
    return u'"' + s.replace(u'"', u'""').replace(u'\0', '').replace('%', '%%')\
        + u'"'


def literal_string(s):
    return u"'" + s.replace(u"'", u"''").replace(u'\0', '') + u"'"
