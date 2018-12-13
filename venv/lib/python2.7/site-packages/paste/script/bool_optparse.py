# (c) 2005 Ian Bicking and contributors; written for Paste (http://pythonpaste.org)
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
"""
A subclass of ``optparse.OptionParser`` that allows boolean long
options (like ``--verbose``) to also take arguments (like
``--verbose=true``).  Arguments *must* use ``=``.
"""

import optparse
try:
    _ = optparse._
except AttributeError:
    from gettext import gettext as _

class BoolOptionParser(optparse.OptionParser):

    def _process_long_opt(self, rargs, values):
        arg = rargs.pop(0)

        # Value explicitly attached to arg?  Pretend it's the next
        # argument.
        if "=" in arg:
            (opt, next_arg) = arg.split("=", 1)
            rargs.insert(0, next_arg)
            had_explicit_value = True
        else:
            opt = arg
            had_explicit_value = False

        opt = self._match_long_opt(opt)
        option = self._long_opt[opt]
        if option.takes_value():
            nargs = option.nargs
            if len(rargs) < nargs:
                if nargs == 1:
                    self.error(_("%s option requires an argument") % opt)
                else:
                    self.error(_("%s option requires %d arguments")
                               % (opt, nargs))
            elif nargs == 1:
                value = rargs.pop(0)
            else:
                value = tuple(rargs[0:nargs])
                del rargs[0:nargs]

        elif had_explicit_value:
            value = rargs[0].lower().strip()
            del rargs[0:1]
            if value in ('true', 'yes', 'on', '1', 'y', 't'):
                value = None
            elif value in ('false', 'no', 'off', '0', 'n', 'f'):
                # Don't process
                return
            else:
                self.error(_('%s option takes a boolean value only (true/false)') % opt)

        else:
            value = None

        option.process(opt, value, values, self)
