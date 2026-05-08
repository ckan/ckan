# encoding: utf-8

import ckan.plugins as p

from ckanext.datastore.interfaces import IDatastoreDump
from ckanext.datastore.writer import csv_writer


class SampleDumpPlugin(p.SingletonPlugin):
    """Test plugin exercising :class:`IDatastoreDump`.

    Registers a fake ``faux`` format (reusing ``csv_writer`` so we don't
    need a real implementation) and removes the built-in ``xml`` format
    via the ``None`` sentinel.
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
            "xml": None,
        }
