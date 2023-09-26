from __future__ import annotations

from typing import Optional

from flask.wrappers import Response

import ckan.plugins as p
import ckan.plugins.toolkit as tk
from ckan import model
from ckan.common import session

from . import helpers, interfaces, utils, views

try:
    config_declarations = tk.blanket.config_declarations
except AttributeError:
    def config_declarations(cls):
        return cls


@config_declarations
class OidcPkcePlugin(p.SingletonPlugin):
    p.implements(p.IBlueprint)
    p.implements(p.ITemplateHelpers)
    p.implements(interfaces.IOidcPkce, inherit=True)

    # IBlueprint
    def get_blueprint(self):
        return views.get_blueprints()

    # ITemplateHelpers
    def get_helpers(
        self,
    ):
        return helpers.get_helpers()

    if not tk.check_ckan_version("2.10"):
        p.implements(p.IAuthenticator, inherit=True)

        # IAuthenticator
        def identify(self) -> Optional[Response]:
            user = model.User.get(session.get(utils.SESSION_USER))
            if user:
                tk.g.user = user.name
                tk.g.userobj = user

        def logout(self):
            session.pop(utils.SESSION_USER, None)
