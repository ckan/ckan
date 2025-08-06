# Extensible Datastore Dump Formats

This document describes the new extensible dump format system for CKAN's datastore plugin.

## Overview

The datastore plugin now supports configurable and extensible dump formats through the `IDatastoreDump` interface. This allows:

1. **Configurable formats**: Dump formats are no longer hardcoded
2. **Overrideable defaults**: Default formats (CSV, TSV, JSON, XML) can be overridden by plugins
3. **Extensible formats**: External plugins can add new dump formats (e.g., XLSX, ODS, etc.)

## Architecture

### IDatastoreDump Interface

The new `IDatastoreDump` interface allows plugins to register custom dump formats:

```python
from ckanext.datastore.interfaces import IDatastoreDump

class MyPlugin(p.SingletonPlugin):
    p.implements(IDatastoreDump)

    def register_dump_formats(self) -> dict[str, dict[str, Any]]:
        return {
            'xlsx': {
                'writer_factory': xlsx_writer,
                'records_format': 'objects',
                'content_type': b'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'file_extension': 'xlsx'
            }
        }
```

### Format Configuration

Each dump format must provide:

- **writer_factory**: A context manager function that creates a writer object
- **records_format**: The format for records ('csv', 'tsv', 'lists', 'objects')
- **content_type**: The MIME type for HTTP responses (bytes)
- **file_extension**: The file extension for downloads

### Dynamic Format Resolution

The system dynamically discovers available formats at runtime by:

1. Starting with default formats (CSV, TSV, JSON, XML)
2. Iterating through all plugins implementing `IDatastoreDump`
3. Collecting and merging format registrations
4. Later plugin registrations can override earlier ones

## Usage Examples

### Adding XLSX Support

See `example_xlsx_plugin.py` for a complete example of adding XLSX export capability.

### Overriding Default Formats

A plugin can override the default CSV format:

```python
def custom_csv_writer(fields, bom=False):
    # Custom CSV implementation
    pass

class MyPlugin(p.SingletonPlugin):
    p.implements(IDatastoreDump)

    def register_dump_formats(self):
        return {
            'csv': {
                'writer_factory': custom_csv_writer,
                'records_format': 'csv',
                'content_type': b'text/csv; charset=utf-8',
                'file_extension': 'csv'
            }
        }
```

### Multiple Format Plugin

A single plugin can register multiple formats:

```python
class MultiFormatPlugin(p.SingletonPlugin):
    p.implements(IDatastoreDump)

    def register_dump_formats(self):
        return {
            'xlsx': {
                'writer_factory': xlsx_writer,
                'records_format': 'objects',
                'content_type': b'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'file_extension': 'xlsx'
            },
            'ods': {
                'writer_factory': ods_writer,
                'records_format': 'objects',
                'content_type': b'application/vnd.oasis.opendocument.spreadsheet',
                'file_extension': 'ods'
            }
        }
```

## Writer Implementation

Writers must implement the context manager protocol and provide these methods:

```python
@contextmanager
def my_writer(fields, bom=False):
    writer = MyWriter(fields, bom)
    yield writer

class MyWriter:
    def write_records(self, records: list) -> bytes:
        """Write a batch of records and return bytes for streaming"""
        pass

    def end_file(self) -> bytes:
        """Finalize the file and return any remaining bytes"""
        pass
```

## Migration

This change is backward compatible. Existing code will continue to work without modification, as the default formats are still available through the new system.

## Benefits

1. **Extensibility**: Easy to add new export formats
2. **Customization**: Default formats can be overridden
3. **Modularity**: Format-specific code is contained in plugins
4. **Maintainability**: No need to modify core datastore code for new formats
5. **Configuration**: Formats are determined at runtime based on loaded plugins
