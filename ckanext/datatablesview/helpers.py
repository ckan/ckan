# encoding: utf-8
import ckan.plugins.toolkit as toolkit


def datatablesview_null_label() -> str:
    """
    Get the label used to display NoneType values for the front-end

    :returns: The label.
    :rtype: str
    """
    label = toolkit.config.get("ckan.datatables.null_label")
    return toolkit._(label) if label else ""
