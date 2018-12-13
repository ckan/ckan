#!/usr/bin/python

raise ImportError("""\
_jsmin has been removed from WebHelpers due to licensing issues
Details are in this module's comments.
A standalone "jsmin" package is available in PyPI.""")

# This module used to contain an algorithm for compressing Javascript code
# to minimize network bandwidth. It was written in C by Douglas Crockford
# (www.crockford.com) in 1992. Baruch Even later ported it to Python, and
# that version was added to WebHelpers. However, it retained Crockford's
# license, which was MIT-style but contained the clause, "The Software shall be
# used for Good, not Evil."  Fedora's lawyers have declared this clause
# incompatible with its free-software distribution guidelines. Debian and
# other distributions have similar guidelines. Thus, it can't be included in
# popular Linux distributions we want WebHelpers to be in. The legal argument
# is that while the clause is unenforceably vague ("What is an Evil purpose?"),
# it's an implied restriction on use, which could expose users to trivial
# harassment.  Both the WebHelpers maintainer and Fedora maintainers contacted
# Mr Crockford and asked him to change the license. He refused, and so we have
# removed his code.
