"""MIME-Type Parser

This module provides basic functions for handling mime-types. It can handle
matching mime-types against a list of media-ranges. See section 14.1 of
the HTTP specification [RFC 2616] for a complete explanation.

   http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.1

Based on mimeparse 0.1.2 by Joe Gregorio:

    http://code.google.com/p/mimeparse/

Contents:
    - parse_mime_type():   Parses a mime-type into its component parts.
    - parse_media_range(): Media-ranges are mime-types with wild-cards and a 'q' quality parameter.
    - quality():           Determines the quality ('q') of a mime-type when compared against a list of media-ranges.
    - quality_parsed():    Just like quality() except the second parameter must be pre-parsed.
    - best_match():        Choose the mime-type with the highest quality ('q') from a list of candidates.
    - desired_matches():   Filter against a list of desired mime-types in the order the server prefers.

"""


def parse_mime_type(mime_type):
    """Carves up a mime-type and returns a tuple of the
       (type, subtype, params) where 'params' is a dictionary
       of all the parameters for the media range.
       For example, the media range 'application/xhtml;q=0.5' would
       get parsed into:

       ('application', 'xhtml', {'q', '0.5'})
       """
    type = mime_type.split(';')
    type, plist = type[0], type[1:]
    try:
        type, subtype = type.split('/', 1)
    except ValueError:
        type, subtype = type.strip() or '*', '*'
    else:
        type = type.strip() or '*'
        subtype = subtype.strip() or '*'
    params = {}
    for param in plist:
        param = param.split('=', 1)
        if len(param) == 2:
            key, value = param[0].strip(), param[1].strip()
            if key and value:
                params[key] = value
    return type, subtype, params

def parse_media_range(range):
    """Carves up a media range and returns a tuple of the
       (type, subtype, params) where 'params' is a dictionary
       of all the parameters for the media range.
       For example, the media range 'application/*;q=0.5' would
       get parsed into:

       ('application', '*', {'q', '0.5'})

       In addition this function also guarantees that there
       is a value for 'q' in the params dictionary, filling it
       in with a proper default if necessary.
       """
    type, subtype, params = parse_mime_type(range)
    try:
        if not 0 <= float(params['q']) <= 1:
            raise ValueError
    except (KeyError, ValueError):
        params['q'] = '1'
    return type, subtype, params

def fitness_and_quality_parsed(mime_type, parsed_ranges):
    """Find the best match for a given mime-type against
       a list of media_ranges that have already been
       parsed by parse_media_range(). Returns a tuple of
       the fitness value and the value of the 'q' quality
       parameter of the best match, or (-1, 0) if no match
       was found. Just as for quality_parsed(), 'parsed_ranges'
       must be a list of parsed media ranges."""
    best_fitness, best_fit_q = -1, 0
    target_type, target_subtype, target_params = parse_media_range(mime_type)
    for type, subtype, params in parsed_ranges:
        if (type == target_type
                    or type == '*' or target_type == '*') and (
                subtype == target_subtype
                    or subtype == '*' or target_subtype == '*'):
            fitness = 0
            if type == target_type:
                fitness += 100
            if subtype == target_subtype:
                fitness += 10
            for key in target_params:
                if key != 'q' and key in params:
                    if params[key] == target_params[key]:
                        fitness += 1
            if fitness > best_fitness:
                best_fitness = fitness
                best_fit_q = params['q']
    return best_fitness, float(best_fit_q)

def quality_parsed(mime_type, parsed_ranges):
    """Find the best match for a given mime-type against
    a list of media_ranges that have already been
    parsed by parse_media_range(). Returns the
    'q' quality parameter of the best match, 0 if no
    match was found. This function behaves the same as quality()
    except that 'parsed_ranges' must be a list of
    parsed media ranges."""
    return fitness_and_quality_parsed(mime_type, parsed_ranges)[1]

def quality(mime_type, ranges):
    """Returns the quality 'q' of a mime-type when compared
    against the media-ranges in ranges. For example:

    >>> quality('text/html','text/*;q=0.3, text/html;q=0.7, text/html;level=1, text/html;level=2;q=0.4, */*;q=0.5')
    0.7

    """
    parsed_ranges = map(parse_media_range, ranges.split(','))
    return quality_parsed(mime_type, parsed_ranges)

def best_match(supported, header):
    """Takes a list of supported mime-types and finds the best
    match for all the media-ranges listed in header. In case of
    ambiguity, whatever comes first in the list will be chosen.
    The value of header must be a string that conforms to the format
    of the HTTP Accept: header. The value of 'supported' is a list
    of mime-types.

    >>> best_match(['application/xbel+xml', 'text/xml'], 'text/*;q=0.5,*/*; q=0.1')
    'text/xml'
    """
    if not supported:
        return ''
    parsed_header = map(parse_media_range, header.split(','))
    best_type = max([
            (fitness_and_quality_parsed(mime_type, parsed_header), -n)
            for n, mime_type in enumerate(supported)])
    return best_type[0][1] and supported[-best_type[1]] or ''

def desired_matches(desired, header):
    """Takes a list of desired mime-types in the order the server prefers to
    send them regardless of the browsers preference.

    Browsers (such as Firefox) technically want XML over HTML depending on how
    one reads the specification. This function is provided for a server to
    declare a set of desired mime-types it supports, and returns a subset of
    the desired list in the same order should each one be Accepted by the
    browser.

    >>> desired_matches(['text/html', 'application/xml'], \
    ...     'text/xml,application/xml,application/xhtml+xml,text/html;q=0.9,text/plain;q=0.8,image/png')
    ['text/html', 'application/xml']
    >>> desired_matches(['text/html', 'application/xml'], 'application/xml,application/json')
    ['application/xml']
    """
    parsed_ranges = map(parse_media_range, header.split(','))
    return [mimetype for mimetype in desired
        if quality_parsed(mimetype, parsed_ranges)]

