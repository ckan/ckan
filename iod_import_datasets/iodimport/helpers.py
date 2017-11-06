import sys
import click
import validators
from datetime import date, datetime
PYTHON2 = str is bytes
if PYTHON2:
    import simplejson as json
else:
    import json

DATE_FORMAT = '%Y-%m-%d'
NAIVE_DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'

def compact_json(r, sort_keys=False):
    """
    JSON as small as we can make it, with UTF-8
    """
    return json.dumps(r, ensure_ascii=False, separators=(',', ':'),
        sort_keys=sort_keys).encode('utf-8')


def parse_string_to_array(string_values):

    if string_values:
        tags = string_values.split(' | ')
        cleaned = []
        for t in tags:
            if t == '':
                pass
            else:
                cleaned.append(t.strip())
        return cleaned

    else:
        return []

def validate_url(url, row, required=False):

    if url and validators.url(url):
        return url
    elif required:
        click.echo('Line: %d' % row)
        click.echo(url)
        sys.exit("Resource URL is malformed or missing, line %d" % row)
    else:
        return ''

def validate_not_empty(value, field, row):
    if value:
        return value
    else:
        sys.exit("Field %s must not be empty, line %d" % (field, row))


def strftime(obj, field, row):

    if type(obj) is date:
        return obj.strftime(DATE_FORMAT)

    if type(obj) is datetime:
        return obj.strftime(NAIVE_DATETIME_FORMAT)

    if type(obj) is unicode:
        try:
            datetime.strptime(obj, '%Y/%m/%d')
            return obj
        except ValueError:
            sys.exit("Incorrect data format for field %s, should be YYYY/MM/DD, line %d" % (field, row))


def tags_string_to_list(tags_string):

    if isinstance(tags_string, unicode):
        tags_string = [tags_string]

    out = []
    for tag in tags_string:
        tag = tag.strip()
        if tag:
            out.append({'name': tag,
                        'state': 'active'})
    return out


