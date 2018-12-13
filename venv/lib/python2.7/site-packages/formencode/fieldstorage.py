## FormEncode, a  Form processor
## Copyright (C) 2003, Ian Bicking <ianb@colorstudy.com>
"""
Wrapper class for use with cgi.FieldStorage types for file uploads
"""

import cgi


def convert_fieldstorage(fs):
    return fs if fs.filename else None
