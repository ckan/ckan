import collections
import json
import sys
import uuid

from flask import (
    template_rendered, request, g,
    Response, current_app, abort, url_for
)
from flask_debugtoolbar import module
from flask_debugtoolbar.panels import DebugPanel

_ = lambda x: x


class TemplateDebugPanel(DebugPanel):
    """
    Panel that displays the time a response took in milliseconds.
    """
    name = 'Template'
    has_content = True

    # save the context for the 5 most recent requests
    template_cache = collections.deque(maxlen=5)

    @classmethod
    def get_cache_for_key(self, key):
        for cache_key, value in self.template_cache:
            if key == cache_key:
                return value
        raise KeyError(key)

    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)
        self.key = str(uuid.uuid4())
        self.templates = []
        template_rendered.connect(self._store_template_info)

    def _store_template_info(self, sender, **kwargs):
        # only record in the cache if the editor is enabled and there is
        # actually a template for this request
        if not self.templates and is_editor_enabled():
            self.template_cache.append((self.key, self.templates))
        self.templates.append(kwargs)

    def process_request(self, request):
        pass

    def process_response(self, request, response):
        pass

    def nav_title(self):
        return _('Templates')

    def nav_subtitle(self):
        return "%d rendered" % len(self.templates)

    def title(self):
        return _('Templates')

    def url(self):
        return ''

    def content(self):
        return self.render('panels/template.html', {
            'key': self.key,
            'templates': self.templates,
            'editable': is_editor_enabled(),
        })


def is_editor_enabled():
    return current_app.config.get('DEBUG_TB_TEMPLATE_EDITOR_ENABLED')


def require_enabled():
    if not is_editor_enabled():
        abort(403)


def _get_source(template):
    with open(template.filename, 'rb') as fp:
        source = fp.read()
    return source.decode(_template_encoding())


def _template_encoding():
    return getattr(current_app.jinja_loader, 'encoding', 'utf-8')


@module.route('/template/<key>')
def template_editor(key):
    require_enabled()
    # TODO set up special loader that caches templates it loads
    # and can override template contents
    templates = [t['template'] for t in
                 TemplateDebugPanel.get_cache_for_key(key)]
    return g.debug_toolbar.render('panels/template_editor.html', {
        'static_path': url_for('_debug_toolbar.static', filename=''),
        'request': request,
        'templates': [
            {'name': t.name, 'source': _get_source(t)}
            for t in templates
        ]
    })


@module.route('/template/<key>/save', methods=['POST'])
def save_template(key):
    require_enabled()
    template = TemplateDebugPanel.get_cache_for_key(key)[0]['template']
    content = request.form['content'].encode(_template_encoding())
    with open(template.filename, 'wb') as fp:
        fp.write(content)
    return 'ok'


@module.route('/template/<key>', methods=['POST'])
def template_preview(key):
    require_enabled()
    context = TemplateDebugPanel.get_cache_for_key(key)[0]['context']
    content = request.form['content']
    env = current_app.jinja_env.overlay(autoescape=True)
    try:
        template = env.from_string(content)
        return template.render(context)
    except Exception as e:
        tb = sys.exc_info()[2]
        try:
            while tb.tb_next:
                tb = tb.tb_next
            msg = {'lineno': tb.tb_lineno, 'error': str(e)}
            return Response(json.dumps(msg), status=400,
                            mimetype='application/json')
        finally:
            del tb
