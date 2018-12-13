import os
import sys

PY33 = sys.version_info >= (3, 3)

if PY33:
    from importlib import machinery
else:
    from six.moves import reload_module as reload


def import_path(fullpath):
    """ Import a file with full path specification. Allows one to
        import from anywhere, something __import__ does not do.
    """
    if PY33:
        name = os.path.splitext(os.path.basename(fullpath))[0]
        return machinery.SourceFileLoader(
            name, fullpath).load_module(name)
    else:
        # http://zephyrfalcon.org/weblog/arch_d7_2002_08_31.html
        path, filename = os.path.split(fullpath)
        filename, ext = os.path.splitext(filename)
        sys.path.append(path)
        try:
            module = __import__(filename)
            reload(module)  # Might be out of date during tests
            return module
        finally:
            del sys.path[-1]
