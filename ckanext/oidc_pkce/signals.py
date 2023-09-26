try:
    import ckan.plugins.toolkit as tk

    ckanext = tk.signals.ckanext
except AttributeError:
    from blinker import Namespace

    ckanext = Namespace()

user_exist = ckanext.signal("oidc_pkce:user_exist")
"""Existing up-to-date user account found during login.
Params:
    sender: user ID
"""

user_sync = ckanext.signal("oidc_pkce:user_sync")
"""Outdated user account found during login.
Params:
    sender: user ID
"""


user_create = ckanext.signal("oidc_pkce:user_create")
"""User account was created during login.
Params:
    sender: user ID
"""
