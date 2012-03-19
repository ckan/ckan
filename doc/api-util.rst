========
Util API
========

The Util API provides various utility APIs -- e.g. auto-completion APIs used by
front-end javascript.

All Util APIs are read-only. The response format is JSON. Javascript calls may
want to use the JSONP formatting.

.. Note::

  Some CKAN deployments have the API deployed at a different domain to the main CKAN website. To make sure that the AJAX calls in the Web UI work, you'll need to configue the ckan.api_url. e.g.::

    ckan.api_url = http://api.example.com/


dataset autocomplete
````````````````````

There an autocomplete API for package names which matches on name or title.

This URL:

::

    /api/2/util/dataset/autocomplete?incomplete=a%20novel

Returns:

::

    {"ResultSet": {"Result": [{"match_field": "title", "match_displayed": "A Novel By Tolstoy (annakarenina)", "name": "annakarenina", "title": "A Novel By Tolstoy"}]}}


tag autocomplete
````````````````

There is also an autocomplete API for tags which looks like this:

This URL:

::

    /api/2/util/tag/autocomplete?incomplete=ru

Returns:

::

    {"ResultSet": {"Result": [{"Name": "russian"}]}}

resource format autocomplete
````````````````````````````

Similarly, there is an autocomplete API for the resource format field
which is available at:

::

    /api/2/util/resource/format_autocomplete?incomplete=cs

This returns:

::

    {"ResultSet": {"Result": [{"Format": "csv"}]}}

markdown
````````

Takes a raw markdown string and returns a corresponding chunk of HTML. CKAN uses the basic Markdown format with some modifications (for security) and useful additions (e.g. auto links to datasets etc. e.g. ``dataset:river-quality``).

Example::

    /api/util/markdown?q=<http://ibm.com/>

Returns::

    "<p><a href="http://ibm.com/" target="_blank" rel="nofollow">http://ibm.com/</a>\n</p>"

is slug valid
`````````````

Checks a name is valid for a new dataset (package) or group, with respect to it being used already.

Example::

    /api/2/util/is_slug_valid?slug=river-quality&type=package

Response::

    {"valid": true}

munge package name
``````````````````

For taking an readable identifier and munging it to ensure it is a valid dataset id. Symbols and whitespeace are converted into dashes. Example::

    /api/util/dataset/munge_name?name=police%20spending%20figures%202009

Returns::

    "police-spending-figures-2009"

munge title to package name
```````````````````````````

For taking a title of a package and munging it to a readable and valid dataset id. Symbols and whitespeace are converted into dashes, with multiple dashes collapsed. Ensures that long titles with a year at the end preserves the year should it need to be shortened. Example::

    /api/util/dataset/munge_title_to_name?title=police:%20spending%20figures%202009

Returns::

    "police-spending-figures-2009"


munge tag
`````````

For taking a readable word/phrase and munging it to a valid tag (name). Symbols and whitespeace are converted into dashes. Example::

    /api/util/tag/munge?tag=water%20quality

Returns::

    "water-quality"

