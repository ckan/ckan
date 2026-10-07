# encoding: utf-8

import ckan.plugins as p

from ckanext.datastore.interfaces import IDatastoreDump
from ckanext.datastore.writer import csv_writer

ALWAYS_INVALID_REASON = "Always invalid format"


def invalid_validate(context):
    """Validator that always rejects (tests the reason path)."""
    return ALWAYS_INVALID_REASON


def valid_validate(context):
    """Validator that always approves (tests the None path)."""
    return None


class SampleDumpPlugin(p.SingletonPlugin):
    """Test plugin exercising :class:`IDatastoreDump`.

    Registers:

    * ``faux`` - no validator, reuses ``csv_writer``.
    * ``gated`` - ``validate`` always rejects (reason path).
    * ``passes`` - ``validate`` always approves (None path).
    * ``capped`` - declarative ``max_rows``/``max_columns`` (framework path).
    * Removes the built-in ``xml`` format via the ``None`` sentinel.
    """

    p.implements(IDatastoreDump)

    def register_dump_formats(self):
        return {
            "faux": {
                "label": "Faux",
                "writer_factory": csv_writer,
                "records_format": "csv",
                "content_type": "application/x-faux; charset=utf-8",
                "file_extension": "faux",
            },
            "gated": {
                "label": "Gated",
                "writer_factory": csv_writer,
                "records_format": "csv",
                "content_type": "application/x-gated; charset=utf-8",
                "file_extension": "gated",
                "validate": invalid_validate,
            },
            "passes": {
                "label": "Passes",
                "writer_factory": csv_writer,
                "records_format": "csv",
                "content_type": "application/x-passes; charset=utf-8",
                "file_extension": "passes",
                "validate": valid_validate,
            },
            "capped": {
                "label": "Capped",
                "writer_factory": csv_writer,
                "records_format": "csv",
                "content_type": "application/x-capped; charset=utf-8",
                "file_extension": "capped",
                "max_rows": 1,
                "max_columns": 5,
            },
            "xml": None,
        }
