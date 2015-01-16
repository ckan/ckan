import os

import ckan.include.rjsmin as rjsmin
import ckan.include.rcssmin as rcssmin
import ckan.lib.fanstatic_resources as fanstatic_resources

from ckan.lib.commands import CkanCommand


class MinifyCommand(CkanCommand):
    '''Create minified versions of the given Javascript and CSS files.

    Usage:

        paster minify [--clean] PATH

    for example:

        paster minify ckan/public/base
        paster minify ckan/public/base/css/*.css
        paster minify ckan/public/base/css/red.css

    if the --clean option is provided any minified files will be removed.

    '''
    summary = __doc__.split('\n')[0]
    usage = __doc__
    min_args = 1

    exclude_dirs = ['vendor']

    def __init__(self, name):

        super(MinifyCommand, self).__init__(name)

        self.parser.add_option('--clean', dest='clean',
                               action='store_true', default=False,
                               help='remove any minified files in the path')

    def command(self):
        clean = getattr(self.options, 'clean', False)
        self._load_config()
        for base_path in self.args:
            if os.path.isfile(base_path):
                if clean:
                    self.clear_minifyed(base_path)
                else:
                    self.minify_file(base_path)
            elif os.path.isdir(base_path):
                for root, dirs, files in os.walk(base_path):
                    dirs[:] = [d for d in dirs if d not in self.exclude_dirs]
                    for filename in files:
                        path = os.path.join(root, filename)
                        if clean:
                            self.clear_minifyed(path)
                        else:
                            self.minify_file(path)
            else:
                # Path is neither a file or a dir?
                continue

    def clear_minifyed(self, path):
        path_only, extension = os.path.splitext(path)

        if extension not in ('.css', '.js'):
            # This is not a js or css file.
            return

        if path_only.endswith('.min'):
            print 'removing %s' % path
            os.remove(path)

    def minify_file(self, path):
        '''Create the minified version of the given file.

        If the file is not a .js or .css file (e.g. it's a .min.js or .min.css
        file, or it's some other type of file entirely) it will not be
        minifed.

        :param path: The path to the .js or .css file to minify

        '''
        path_only, extension = os.path.splitext(path)

        if path_only.endswith('.min'):
            # This is already a minified file.
            return

        if extension not in ('.css', '.js'):
            # This is not a js or css file.
            return

        path_min = fanstatic_resources.min_path(path)

        source = open(path, 'r').read()
        f = open(path_min, 'w')
        if path.endswith('.css'):
            f.write(rcssmin.cssmin(source))
        elif path.endswith('.js'):
            f.write(rjsmin.jsmin(source))
        f.close()
        print "Minified file '{0}'".format(path)
