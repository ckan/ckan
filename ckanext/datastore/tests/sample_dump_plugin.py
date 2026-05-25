# encoding: utf-8

import ckan.plugins as p

from ckanext.datastore.interfaces import IDatastoreDump
from ckanext.datastore.writer import csv_writer

ALWAYS_INVALID_REASON = "Always invalid format"


def invalid_validate(context):
    """Validator that always rejects the format.

    Used by tests to confirm that a ``validate`` callable on a
    registered format flows through to the helper, the blueprint, and
    the resource-read template. Receives the dump context dict (see
    :class:`~ckanext.datastore.interfaces.IDatastoreDump`).
    """
    return ALWAYS_INVALID_REASON


def valid_validate(context):
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
    * ``capped`` — a format with declarative ``max_rows``/``max_columns``
      and no ``validate`` callable (covers the framework-evaluated path).
      ``max_rows`` is 1 so any resource with more than one (post-filter)
      row trips it.
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
            # Declarative limits evaluated by core (no validate callable).
            # max_rows=1 lets tests trip the row limit with a 2-row
            # resource and confirm a filter can bring it back under.
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
