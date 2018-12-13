from flask import current_app
from flask_debugtoolbar.panels import DebugPanel

_ = lambda x: x


class ConfigVarsDebugPanel(DebugPanel):
    """
    A panel to display all variables from Flask configuration
    """
    name = 'ConfigVars'
    has_content = True

    def nav_title(self):
        return _('Config')

    def title(self):
        return _('Config')

    def url(self):
        return ''

    def content(self):
        context = self.context.copy()
        context.update({
            'config': current_app.config,
        })

        return self.render('panels/config_vars.html', context)
