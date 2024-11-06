'''
Abstracts a database. Used for storing logging when it xloaders a resource into
DataStore.

Loosely based on ckan-service-provider's db.py
'''

import datetime
import json

import six
import sqlalchemy


ENGINE = None
_METADATA = None
JOBS_TABLE = None
METADATA_TABLE = None
LOGS_TABLE = None


def init(config, echo=False):
    """Initialise the database.

    Initialise the sqlalchemy engine, metadata and table objects that we use to
    connect to the database.

    Create the database and the database tables themselves if they don't
    already exist.

    :param uri: the sqlalchemy database URI
    :type uri: string

    :param echo: whether or not to have the sqlalchemy engine log all
        statements to stdout
    :type echo: bool

    """
    global ENGINE, _METADATA, JOBS_TABLE, METADATA_TABLE, LOGS_TABLE
    db_uri = config.get('ckanext.xloader.jobs_db.uri',
                        'sqlite:////tmp/xloader_jobs.db')
    ENGINE = sqlalchemy.create_engine(db_uri, echo=echo, convert_unicode=True)
    _METADATA = sqlalchemy.MetaData(ENGINE)
    JOBS_TABLE = _init_jobs_table()
    METADATA_TABLE = _init_metadata_table()
    LOGS_TABLE = _init_logs_table()
    _METADATA.create_all(ENGINE)


def drop_all():
    """Delete all the database tables (if they exist).

    This is for tests to reset the DB. Note that this will delete *all* tables
    in the database, not just tables created by this module (for example
    apscheduler's tables will also be deleted).

    """
    if _METADATA:
        _METADATA.drop_all(ENGINE)


def get_job(job_id):
    """Return the job with the given job_id as a dict.

    The dict also includes any metadata or logs associated with the job.

    Returns None instead of a dict if there's no job with the given job_id.

    The keys of a job dict are:

    "job_id": The unique identifier for the job (unicode)

    "job_type": The name of the job function that will be executed for this
        job (unicode)

    "status": The current status of the job, e.g. "pending", "running",
        "running_but_viewable", complete", or "error" (unicode)

    "data": Any output data returned by the job if it has completed
        successfully. This may be any JSON-serializable type, e.g. None, a
        string, a dict, etc.

    "error": If the job failed with an error this will be a dict with a
        "message" key whose value is a string error message. The dict may also
        have other keys specific to the particular type of error. If the job
        did not fail with an error then "error" will be None.

    "requested_timestamp": The time at which the job was requested (string)

    "finished_timestamp": The time at which the job finished (string)

    "sent_data": The input data for the job, provided by the client site.
        This may be any JSON-serializable type, e.g. None, a string, a dict,
        etc.

    "result_url": The callback URL that CKAN Service Provider will post the
        result to when the job finishes (unicode)

    "api_key": The API key that CKAN Service Provider will use when posting
        the job result to the result_url (unicode or None). A None here doesn't
        mean that there was no API key: CKAN Service Provider deletes the API
        key from the database after it has posted the result to the result_url.

    "metadata": Any custom metadata associated with the job (dict)

    "logs": Any logs associated with the job (list)

    """
    # Avoid SQLAlchemy "Unicode type received non-unicode bind param value"
    # warnings.
    if job_id:
        job_id = six.text_type(job_id)

    result = ENGINE.execute(
        JOBS_TABLE.select().where(JOBS_TABLE.c.job_id == job_id)).first()

    if not result:
        return None

    # Turn the result into a dictionary representation of the job.
    result_dict = {}
    for field in list(result.keys()):
        value = getattr(result, field)
        if value is None:
            result_dict[field] = value
        elif field in ('sent_data', 'data', 'error'):
            result_dict[field] = json.loads(value)
        elif isinstance(value, datetime.datetime):
            result_dict[field] = value.isoformat()
        else:
            result_dict[field] = six.text_type(value)

    result_dict['metadata'] = _get_metadata(job_id)
    result_dict['logs'] = _get_logs(job_id)

    return result_dict


def add_pending_job(job_id, job_type, api_key,
                    data=None, metadata=None, result_url=None):
    """Add a new job with status "pending" to the jobs table.

    All code that adds jobs to the jobs table should go through this function.
    Code that adds to the jobs table manually should be refactored to use this
    function.

    May raise unspecified exceptions from Python core, SQLAlchemy or JSON!
    TODO: Document and unit test these!

    :param job_id: a unique identifier for the job, used as the primary key in
        ckanserviceprovider's "jobs" database table
    :type job_id: unicode

    :param job_type: the name of the job function that will be executed for
        this job
    :type job_type: unicode

    :param api_key: the client site API key that ckanserviceprovider will use
        when posting the job result to the result_url
    :type api_key: unicode

    :param data: The input data for the job (called sent_data elsewhere)
    :type data: Any JSON-serializable type

    :param metadata: A dict of arbitrary (key, value) metadata pairs to be
        stored along with the job. The keys should be strings, the values can
        be strings or any JSON-encodable type.
    :type metadata: dict

    :param result_url: the callback URL that ckanserviceprovider will post the
        job result to when the job has finished
    :type result_url: unicode

    """
    if not data:
        data = {}
    data = json.dumps(data)

    # Turn strings into unicode to stop SQLAlchemy
    # "Unicode type received non-unicode bind param value" warnings.
    if job_id:
        job_id = six.text_type(job_id)
    if job_type:
        job_type = six.text_type(job_type)
    if result_url:
        result_url = six.text_type(result_url)
    if api_key:
        api_key = six.text_type(api_key)
    data = six.text_type(data)

    if not metadata:
        metadata = {}

    with ENGINE.begin() as conn:
        conn.execute(JOBS_TABLE.insert().values(
            job_id=job_id,
            job_type=job_type,
            status='pending',
            requested_timestamp=datetime.datetime.utcnow(),
            sent_data=data,
            result_url=result_url,
            api_key=api_key))

        # Insert any (key, value) metadata pairs that the job has into the
        # metadata table.
        inserts = []
        for key, value in list(metadata.items()):
            type_ = 'string'
            if not isinstance(value, six.string_types):
                value = json.dumps(value)
                type_ = 'json'

            # Turn strings into unicode to stop SQLAlchemy
            # "Unicode type received non-unicode bind param value" warnings.
            key = six.text_type(key)
            value = six.text_type(value)

            inserts.append(
                {"job_id": job_id,
                 "key": key,
                 "value": value,
                 "type": type_}
            )
        if inserts:
            conn.execute(METADATA_TABLE.insert(), inserts)


class InvalidErrorObjectError(Exception):
    pass


def _validate_error(error):
    """Validate and return the given error object.

    Based on the given error object, return either None or a dict with a
    "message" key whose value is a string (the dict may also have any other
    keys that it wants).

    The given "error" object can be:

    - None, in which case None is returned

    - A string, in which case a dict like this will be returned:
      {"message": error_string}

    - A dict with a "message" key whose value is a string, in which case the
      dict will be returned unchanged

    :param error: the error object to validate

    :raises InvalidErrorObjectError: If the error object doesn't match any of
        the allowed types

    """
    if error is None:
        return None
    elif isinstance(error, six.string_types):
        return {"message": error}
    else:
        try:
            message = error["message"]
            if isinstance(message, six.string_types):
                return error
            else:
                raise InvalidErrorObjectError(
                    "error['message'] must be a string")
        except (TypeError, KeyError):
            raise InvalidErrorObjectError(
                "error must be either a string or a dict with a message key")


def _update_job(job_id, job_dict):
    """Update the database row for the given job_id with the given job_dict.

    All functions that update rows in the jobs table do it by calling this
    helper function.

    job_dict is a dict with values corresponding to the database columns that
    should be updated, e.g.:

      {"status": "complete", "data": ...}

    """
    # Avoid SQLAlchemy "Unicode type received non-unicode bind param value"
    # warnings.
    if job_id:
        job_id = six.text_type(job_id)

    if "error" in job_dict:
        job_dict["error"] = _validate_error(job_dict["error"])
        job_dict["error"] = json.dumps(job_dict["error"])
        # Avoid SQLAlchemy "Unicode type received non-unicode bind param value"
        # warnings.
        job_dict["error"] = six.text_type(job_dict["error"])

    # Avoid SQLAlchemy "Unicode type received non-unicode bind param value"
    # warnings.
    if "data" in job_dict:
        job_dict["data"] = six.text_type(job_dict["data"])

    ENGINE.execute(
        JOBS_TABLE.update()
        .where(JOBS_TABLE.c.job_id == job_id)
        .values(**job_dict))


def mark_job_as_completed(job_id, data=None):
    """Mark a job as completed successfully.

    :param job_id: the job_id of the job to be updated
    :type job_id: unicode

    :param data: the output data returned by the job
    :type data: any JSON-serializable type (including None)

    """
    update_dict = {
        "status": "complete",
        "data": json.dumps(data),
        "finished_timestamp": datetime.datetime.utcnow(),
    }
    _update_job(job_id, update_dict)


def mark_job_as_missed(job_id):
    """Mark a job as missed because it was in the queue for too long.

    :param job_id: the job_id of the job to be updated
    :type job_id: unicode

    """
    update_dict = {
        "status": "error",
        "error": "Job delayed too long, service full",
        "finished_timestamp": datetime.datetime.utcnow(),
    }
    _update_job(job_id, update_dict)


def mark_job_as_errored(job_id, error_object):
    """Mark a job as failed with an error.

    :param job_id: the job_id of the job to be updated
    :type job_id: unicode

    :param error_object: the error returned by the job
    :type error_object: either a string or a dict with a "message" key whose
        value is a string

    """
    update_dict = {
        "status": "error",
        "error": error_object,
        "finished_timestamp": datetime.datetime.utcnow(),
    }
    _update_job(job_id, update_dict)


def mark_job_as_failed_to_post_result(job_id):
    """Mark a job as 'failed to post result'.

    This happens when a job completes (either successfully or with an error)
    then trying to post the job result back to the job's callback URL fails.

    FIXME: This overwrites any error from the job itself!

    :param job_id: the job_id of the job to be updated
    :type job_id: unicode

    """
    update_dict = {
        "error":
            "Process completed but unable to post to result_url",
    }
    _update_job(job_id, update_dict)


def delete_api_key(job_id):
    """Delete the given job's API key from the database.

    The API key is used when posting the job's result to the client's callback
    URL. This function should be called to delete the API key after the result
    has been posted - the API key is no longer needed.

    """
    _update_job(job_id, {"api_key": None})


def _init_jobs_table():
    """Initialise the "jobs" table in the db."""
    _jobs_table = sqlalchemy.Table(
        'jobs', _METADATA,
        sqlalchemy.Column('job_id', sqlalchemy.UnicodeText, primary_key=True),
        sqlalchemy.Column('job_type', sqlalchemy.UnicodeText),
        sqlalchemy.Column('status', sqlalchemy.UnicodeText, index=True),
        sqlalchemy.Column('data', sqlalchemy.UnicodeText),
        sqlalchemy.Column('error', sqlalchemy.UnicodeText),
        sqlalchemy.Column('requested_timestamp', sqlalchemy.DateTime),
        sqlalchemy.Column('finished_timestamp', sqlalchemy.DateTime),
        sqlalchemy.Column('sent_data', sqlalchemy.UnicodeText),
        # Callback URL:
        sqlalchemy.Column('result_url', sqlalchemy.UnicodeText),
        # CKAN API key:
        sqlalchemy.Column('api_key', sqlalchemy.UnicodeText),
    )
    return _jobs_table


def _init_metadata_table():
    """Initialise the "metadata" table in the db."""
    _metadata_table = sqlalchemy.Table(
        'metadata', _METADATA,
        sqlalchemy.Column(
            'job_id', sqlalchemy.ForeignKey("jobs.job_id", ondelete="CASCADE"),
            nullable=False, primary_key=True),
        sqlalchemy.Column('key', sqlalchemy.UnicodeText, primary_key=True),
        sqlalchemy.Column('value', sqlalchemy.UnicodeText, index=True),
        sqlalchemy.Column('type', sqlalchemy.UnicodeText),
    )
    return _metadata_table


def _init_logs_table():
    """Initialise the "logs" table in the db."""
    _logs_table = sqlalchemy.Table(
        'logs', _METADATA,
        sqlalchemy.Column(
            'job_id', sqlalchemy.ForeignKey("jobs.job_id", ondelete="CASCADE"),
            nullable=False),
        sqlalchemy.Column('timestamp', sqlalchemy.DateTime),
        sqlalchemy.Column('message', sqlalchemy.UnicodeText),
        sqlalchemy.Column('level', sqlalchemy.UnicodeText),
        sqlalchemy.Column('module', sqlalchemy.UnicodeText),
        sqlalchemy.Column('funcName', sqlalchemy.UnicodeText),
        sqlalchemy.Column('lineno', sqlalchemy.Integer)
    )
    return _logs_table


def _get_metadata(job_id):
    """Return any metadata for the given job_id from the metadata table."""
    # Avoid SQLAlchemy "Unicode type received non-unicode bind param value"
    # warnings.
    job_id = six.text_type(job_id)

    results = ENGINE.execute(
        METADATA_TABLE.select().where(
            METADATA_TABLE.c.job_id == job_id)).fetchall()
    metadata = {}
    for row in results:
        value = row['value']
        if row['type'] == 'json':
            value = json.loads(value)
        metadata[row['key']] = value
    return metadata


def _get_logs(job_id):
    """Return any logs for the given job_id from the logs table."""
    # Avoid SQLAlchemy "Unicode type received non-unicode bind param value"
    # warnings.
    job_id = six.text_type(job_id)

    results = ENGINE.execute(
        LOGS_TABLE.select().where(LOGS_TABLE.c.job_id == job_id)).fetchall()

    results = [dict(result) for result in results]

    for result in results:
        result.pop("job_id")

    return results
