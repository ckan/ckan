# encoding: utf-8

import ckan.plugins as p

from ckanext.datastore.interfaces import IDatastoreDump
from ckanext.datastore.writer import csv_writer

ALWAYS_INVALID_REASON = "Always invalid format"


def invalid_validate(resource_id):
    """Validator that always rejects the format.

    Used by tests to confirm that a ``validate`` callable on a
    registered format flows through to the helper, the blueprint, and
    the resource-read template.
    """
    return ALWAYS_INVALID_REASON


def valid_validate(resource_id):
    """Validator that always approves.

    Used by tests to cover the branch where a format declares a
    ``validate`` callable but the resource passes it (the validator
    runs, returns ``None``, and the format stays available).
    """
    return None


class SampleDumpPlugin(p.SingletonPlugin):
    """Test plugin exercising :class:`IDatastoreDump`.

    Registers:

    * ``faux`` — a no-validator format reusing ``csv_writer``.
    * ``gated`` — a format whose ``validate`` callable always rejects
      (covers the "validator returns reason" path).
    * ``passes`` — a format whose ``validate`` callable always
      approves (covers the "validator returns None" path).
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
            # Include an always invalid format for testing
            "gated": {
                "label": "Gated",
                "writer_factory": csv_writer,
                "records_format": "csv",
                "content_type": "application/x-gated; charset=utf-8",
                "file_extension": "gated",
                "validate": invalid_validate,
            },
            # Validator present but always approves — exercises the
            # "validate returned None" branch in core.
            "passes": {
                "label": "Passes",
                "writer_factory": csv_writer,
                "records_format": "csv",
                "content_type": "application/x-passes; charset=utf-8",
                "file_extension": "passes",
                "validate": valid_validate,
            },
            "xml": None,
        }
