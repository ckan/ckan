import os

from ckan.lib.commands import CkanCommand
from ckan.lib.commands.less import LessCommand
from ckan.lib.commands.minify import MinifyCommand
from ckan.lib.commands.translations import TranslationsCommand


class FrontEndBuildCommand(CkanCommand):
    '''Creates and minifies css and JavaScript files

    Usage:

        paster front-end-build
    '''

    summary = __doc__.split('\n')[0]
    usage = __doc__
    min_args = 0

    def command(self):
        self._load_config()

        # Less css
        cmd = LessCommand('less')
        cmd.command()

        # js translation strings
        cmd = TranslationsCommand('trans')
        cmd.options = self.options
        cmd.args = ('js',)
        cmd.command()

        # minification
        cmd = MinifyCommand('minify')
        cmd.options = self.options
        root = os.path.join(os.path.dirname(__file__), '..', 'public', 'base')
        root = os.path.abspath(root)
        ckanext = os.path.join(os.path.dirname(__file__),
                               '..', '..', 'ckanext')
        ckanext = os.path.abspath(ckanext)
        cmd.args = (root, ckanext)
        cmd.command()
