# encoding: utf-8

import click
import os
import ckan.include.rjsmin as rjsmin
import ckan.include.rcssmin as rcssmin

_exclude_dirs = [u'vendor']


@click.command(name=u'minify')
@click.option(
    u'--clean', is_flag=True, help=u'remove any minified files in the path.')
@click.argument(u'path', nargs=-1, type=click.Path())
def minify(clean, path):
    u'''Create minified versions of the given Javascript and CSS files.'''
    for base_path in path:
        if os.path.isfile(base_path):
            if clean:
                _clear_minifyed(base_path)
            else:
                _minify_file(base_path)
        elif os.path.isdir(base_path):
            for root, dirs, files in os.walk(base_path):
                dirs[:] = [d for d in dirs if d not in _exclude_dirs]
                for filename in files:
                    path = os.path.join(root, filename)
                    if clean:
                        _clear_minifyed(path)
                    else:
                        _minify_file(path)
        else:
            # Path is neither a file or a dir?
            continue


def _clear_minifyed(path):
    u'''Remove the minified version of the file'''
    path_only, extension = os.path.splitext(path)

    if extension not in (u'.css', u'.js'):
        # This is not a js or css file.
        return

    if path_only.endswith(u'.min'):
        click.echo(u'removing {}'.format(path))
        os.remove(path)


def _minify_file(path):
    u'''Create the minified version of the given file.

    If the file is not a .js or .css file (e.g. it's a .min.js or .min.css
    file, or it's some other type of file entirely) it will not be
    minifed.

    :param path: The path to the .js or .css file to minify

    '''
    import ckan.lib.fanstatic_resources as fanstatic_resources
    path_only, extension = os.path.splitext(path)

    if path_only.endswith(u'.min'):
        # This is already a minified file.
        return

    if extension not in (u'.css', u'.js'):
        # This is not a js or css file.
        return

    path_min = fanstatic_resources.min_path(path)

    source = open(path, u'r').read()
    f = open(path_min, u'w')
    if path.endswith(u'.css'):
        f.write(rcssmin.cssmin(source))
    elif path.endswith(u'.js'):
        f.write(rjsmin.jsmin(source))
    f.close()
    click.echo(u"Minified file '{}'".format(path))
