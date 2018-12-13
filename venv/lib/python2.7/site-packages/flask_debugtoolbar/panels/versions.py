import os
from distutils.sysconfig import get_python_lib

from flask import __version__ as flask_version
from flask_debugtoolbar.panels import DebugPanel

_ = lambda x: x


def relpath(location, python_lib):
    location = os.path.normpath(location)
    relative = os.path.relpath(location, python_lib)
    if relative == os.path.curdir:
        return ''
    elif relative.startswith(os.path.pardir):
        return location
    return relative


class VersionDebugPanel(DebugPanel):
    """
    Panel that displays the Flask version.
    """
    name = 'Version'
    has_content = True

    def nav_title(self):
        return _('Versions')

    def nav_subtitle(self):
        return 'Flask %s' % flask_version

    def url(self):
        return ''

    def title(self):
        return _('Versions')

    def content(self):
        try:
            import pkg_resources
        except ImportError:
            packages = []
        else:
            packages = sorted(pkg_resources.working_set,
                              key=lambda p: p.project_name.lower())

        return self.render('panels/versions.html', {
            'packages': packages,
            'python_lib': os.path.normpath(get_python_lib()),
            'relpath': relpath,
        })
