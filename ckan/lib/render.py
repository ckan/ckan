import os
import re
import logging

from pylons import config

log = logging.getLogger(__name__)

_template_info_cache = {}

def reset_template_info_cache():
    '''Reset the template cache'''
    _template_info_cache.clear()

def find_template(template_name):
    ''' looks through the possible template paths to find a template
    returns the full path is it exists. '''
    template_paths = config['pylons.app_globals'].template_paths
    for path in template_paths:
        if os.path.exists(os.path.join(path, template_name.encode('utf-8'))):
            return os.path.join(path, template_name)

def template_type(template_path):
    ''' returns best guess for template type
    returns 'jinja2', 'genshi', 'genshi-text' '''
    if template_path.endswith('.txt'):
        return 'genshi-text'
    try:
        f = open(template_path, 'r')
    except IOError:
        # do the import here due to circular import hell functions like
        # abort should be in a none circular importing file but that
        # refactor has not yet happened
        import ckan.lib.base as base
        base.abort(404)
    source = f.read()
    f.close()
    if re.search('genshi\.edgewall\.org', source):
        return 'genshi'
    return 'jinja2'

class TemplateNotFound(Exception):
    pass

def template_info(template_name):
    ''' Returns the path and type for a template '''

    if template_name in _template_info_cache:
        t_data = _template_info_cache[template_name]
        return t_data['template_path'], t_data['template_type']

    template_path = find_template(template_name)
    if not template_path:
        raise TemplateNotFound('Template %s cannot be found' % template_name)
    t_type = template_type(template_path)

    # if in debug mode we always want to search for templates so we
    # don't want to store it.
    if not config.get('debug', False):
        t_data = {'template_path' : template_path,
                  'template_type' : t_type,}
        _template_info_cache[template_name] = t_data
    return template_path, t_type


def deprecated_lazy_render(target_template, snippet_template, render,
        message):
    '''
    If either target_template is a genshi template this function renders
    immediately and returns a string, otherwise an object that will lazily
    render when {{ the_object | safe }} is used in the jinja template
    is returned.

    :param target_template: name of jinja or genshi template
        that may include the object returned
    :param snippet_template: name of jinja or genshi template
        that will be rendered
    :param render: function to call to render the template snippet
    :param message: message to log.warn() if render is called
    '''
    lazy = DeprecatedLazyRenderer(render, message)
    t_path, t_type = template_info(target_template)
    if t_type.startswith('genshi'):
        return lazy.__html__()
    return lazy

class DeprecatedLazyRenderer(object):
    '''
    An object that will defer rendering until absolutely necessary to
    pass to a template that might do {{ the_object | safe }}.

    Used maintain backwards compatibility with templates that used to
    expect a pre-rendered HTML snippet but have been updated to use
    a normal {% snippet %} tag.
    '''
    def __init__(self, render, message):
        self._html = None
        self._render = render
        self._message = message

    def __html__(self):
        if not self._html:
            log.warn(self._message)
            self._html = self._render()
        return self._html
