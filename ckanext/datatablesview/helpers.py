# encoding: utf-8
import ckan.plugins.toolkit as toolkit

LANGUAGE_MAP = {
    "zh_Hant_TW": "zh_Hant",
    "zh_Hans_CN": "zh_CN",
    "nb_NO": "no",
}


def datatablesview_null_label() -> str:
    """
    Get the label used to display NoneType values for the front-end

    :returns: The label.
    :rtype: str
    """
    label = toolkit.config.get("ckan.datatables.null_label")
    return toolkit._(label) if label else ""


def datatablesview_get_language_file_path(lang: str) -> str:
    """
    Get the language file path for the given language.

    If the language is not in the LANGUAGE_MAP, use the language as is.
    If the language is "en", return an empty string, cause we don't need
    to load the i18n file.

    :param lang: The language to get the language file path for.
    :type lang: str

    :returns: The language file path.
    :rtype: str
    """
    if lang == "en":
        return ""

    return toolkit.h.url_for_static(
        f"datatablesview/i18n/{LANGUAGE_MAP.get(lang, lang)}.json"
    )
