"""HTML generation helpers.

All public objects in the ``webhelpers.html.builder`` subpackage are also
available in the ``webhelpers.html`` namespace.  Most programs will want
to put this line in their code::

    from webhelpers.html import *

Or you can import the most frequently-used objects explicitly::

    from webhelpers.html import HTML, escape, literal
"""

from webhelpers.html.builder import *
