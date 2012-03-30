''' This file is part of a plan to clean up the ckan.lib.helpers whilst
keeping existing versions of ckan from breaking.


When it is decided that we will make the template var cleanup
permanent we will need to implement this using __all__ = [...] in
lib.helpers itself.  Unused imports can also be removed at this time.

yes, yes `from ... import ...` is the work of Satan but this is just a
short term botch :)

'''


from ckan.lib.helpers import (
    # functions defined in ckan.lib.helpers
           redirect_to,
           url,
           url_for,
           url_for_static,
           lang,
           flash,
           flash_error,
           flash_notice,
           flash_success,
           nav_link,
           nav_named_link,
           subnav_link,
           subnav_named_route,
           default_group_type,
           facet_items,
           facet_title,
         #  am_authorized, # depreciated
           check_access,
           linked_user,
           linked_authorization_group,
           group_name_to_title,
           markdown_extract,
           icon,
           icon_html,
           icon_url,
           resource_icon,
           format_icon,
           linked_gravatar,
           gravatar,
           pager_url,
           render_datetime,
           date_str_to_datetime,
           datetime_to_date_str,
           parse_rfc_2822_date,
           time_ago_in_words_from_str,
           button_attr,
           dataset_display_name,
           dataset_link,
           resource_display_name,
           resource_link,
           tag_link,
           group_link,
           dump_json,
           auto_log_message,
    # imported into ckan.lib.helpers
           literal,
           link_to,
           get_available_locales,
           get_locales_dict,
           truncate,
           file,
           mail_to,
           radio,
           submit,
)


# these are potentially used by templates but hopefully are not
imported_functions = [
           'are_there_flash_messages',
           'auto_discovery_link',
          # 'beaker_cache',
           'checkbox',
          # 'ckan',
          # 'config',
           'convert_boolean_attrs',
           'css_classes',
           'date',
           'datetime',
           'email',
           'end_form',
           'escape',
           'form',
           'fromstring',
           'hidden',
           'i18n',
           'image',
           'javascript_link',
           'json',
           'link_to_if',
           'link_to_unless',
           'markdown',
           'ol',
           'paginate',
           'password',
          # 're',
           'request',
           'required_legend',
           'select',
           'stylesheet_link',
           'text',
           'textarea',
           'th_sortable',
           'title',
           'ul',
           'url_escape',
           'urllib',
           'xml_declaration',
]

