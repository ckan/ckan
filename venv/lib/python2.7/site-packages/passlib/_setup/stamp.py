"""update version string during build"""
#=============================================================================
# imports
#=============================================================================
from __future__ import with_statement
# core
import os
import re
import time
from distutils.dist import Distribution
# pkg
# local
__all__ = [
    "stamp_source",
    "stamp_distutils_output",
]
#=============================================================================
# helpers
#=============================================================================
def get_command_class(opts, name):
    return opts['cmdclass'].get(name) or Distribution().get_command_class(name)

def stamp_source(base_dir, version, dry_run=False):
    """update version string in passlib dist"""
    path = os.path.join(base_dir, "passlib", "__init__.py")
    with open(path) as fh:
        input = fh.read()
    output, count = re.subn('(?m)^__version__\s*=.*$',
                    '__version__ = ' + repr(version),
                    input)
    assert count == 1, "failed to replace version string"
    if not dry_run:
        os.unlink(path) # sdist likes to use hardlinks
        with open(path, "w") as fh:
            fh.write(output)

def stamp_distutils_output(opts, version):

    # subclass buildpy to update version string in source
    _build_py = get_command_class(opts, "build_py")
    class build_py(_build_py):
        def build_packages(self):
            _build_py.build_packages(self)
            stamp_source(self.build_lib, version, self.dry_run)
    opts['cmdclass']['build_py'] = build_py

    # subclass sdist to do same thing
    _sdist = get_command_class(opts, "sdist")
    class sdist(_sdist):
        def make_release_tree(self, base_dir, files):
            _sdist.make_release_tree(self, base_dir, files)
            stamp_source(base_dir, version, self.dry_run)
    opts['cmdclass']['sdist'] = sdist

#=============================================================================
# eof
#=============================================================================
