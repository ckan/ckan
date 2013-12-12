"""
Simple accept header parsing to determins which content type we should deliver
back to the caller. This is mostly used by the rdf export functionality
"""
import re
import operator

# For parsing {name};q=x and {name} style fields from the accept header
accept_re = re.compile("^(?P<ct>[^;]+)[ \t]*(;[ \t]*q=(?P<q>[0-9.]+)){0,1}$")

accept_types = {
    #   Name         : ContentType,             Is Markup?, Extension
    "text/html": ("text/html; charset=utf-8",  True,  'html'),
    "text/n3": ("text/n3; charset=utf-8",    False, 'n3'),
    "application/rdf+xml": ("application/rdf+xml; charset=utf-8", True, 'rdf'),
}
accept_by_extension = {
    "rdf": "application/rdf+xml",
    "n3": "text/n3"
}


def parse_extension(file_ext):
    """
    If provided an extension, this function will return the details
    for that extension, if we know about it.
    """
    ext = accept_by_extension.get(file_ext, None)
    if ext:
        return accept_types[ext]
    return (None, None, None,)


def parse_header(accept_header=''):
    """
    Parses the supplied accept header and tries to determine
    which content types we can provide the response in that will keep the
    client happy.

    We will always provide html as the default if we can't see anything else
    but we will also need to take into account the q score.

    The return values are be content-type,is-markup,extension
    """
    if accept_header is None:
        accept_header = ""

    acceptable = {}
    for typ in accept_header.split(','):
        m = accept_re.match(typ)
        if m:
            key = m.groups(0)[0]
            qscore = m.groups(0)[2] or 1.0
            acceptable[key] = float(qscore)

    for ctype in sorted(acceptable.iteritems(),
                        key=operator.itemgetter(1),
                        reverse=True):
        if ctype[0] in accept_types:
            return accept_types[ctype[0]]

    return accept_types["text/html"]
