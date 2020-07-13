Safe dataset updates with ``package_revise``: This is a new API action for safe concurrent changes
to datasets and resources. ``package_revise`` allows assertions about current package metadata,
selective update and removal of fields at any level, and multiple file uploads in a single call.
See the documentation at :py:func:`~ckan.logic.action.update.package_revise`