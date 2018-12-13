"""Base DebugPanel class"""


class DebugPanel(object):
    """
    Base class for debug panels.
    """
    # name = Base

    # If content returns something, set to true in subclass
    has_content = False

    # If the client is able to activate/de-activate the panel
    user_enable = False

    # We'll maintain a local context instance so we can expose our template
    # context variables to panels which need them:
    context = {}

    # Panel methods
    def __init__(self, jinja_env, context={}):
        self.context.update(context)
        self.jinja_env = jinja_env

        # If the client enabled the panel
        self.is_active = False

    def render(self, template_name, context):
        template = self.jinja_env.get_template(template_name)
        return template.render(**context)

    def dom_id(self):
        return 'flDebug%sPanel' % (self.name.replace(' ', ''))

    def nav_title(self):
        """Title showing in toolbar"""
        raise NotImplementedError

    def nav_subtitle(self):
        """Subtitle showing until title in toolbar"""
        return ''

    def title(self):
        """Title showing in panel"""
        raise NotImplementedError

    def url(self):
        raise NotImplementedError

    def content(self):
        raise NotImplementedError

    # Standard middleware methods
    def process_request(self, request):
        pass

    def process_view(self, request, view_func, view_kwargs):
        pass

    def process_response(self, request, response):
        pass
