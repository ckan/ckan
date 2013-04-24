Resources
=========

.. Note::
    Resources are only supported in the new Jinja2 style templates in CKAN 2.0
    and above.

Resources are .css and .js files that may be included in an html page.
Resources are included in the page by using the ``{% resource %}`` tag and
CKAN uses `Fanstatic <http://www.fanstatic.org/en/latest/>`_ to serve these resources.

::

 {% resource 'library_name/resource_name' %}

Resources are grouped into libraries and the full resource name consists of
``<library name>/<resource name>``. For example:

::

 {% resource 'my_fanstatic_library/my_javascript_file.js' %}

It is important to note that these resources will be added to the page as
defined by the resources, not in the location of the ``{% resource %}`` tag.
Duplicate resources will not be added and any dependencies will be included as
well as the resources, all in the correct order (see below for details).

Libraries can be added to CKAN from extensions using a helper function
within the toolkit. See below.

In debug mode resources are served un-minified and unbundled (each resource is
served separately). In non-debug mode the files are served minified and bundled
(where allowed).

.. Important::
    .js and .css resources must be supplied as un-minified files.  Minified
    files will be created.  It is advised to include a .gitignore file to
    prevent minified files being added to the repository.

Resources within extensions
---------------------------

To add a resource within a extension helper function ``add_resource(path, name)``:

::

 ckan.plugins.toolkit.add_resource('path/to/my/fanstatic/library/dir',
        'my_fanstatic_library')

The first argument, ``path``, is the path to the resource directory relative to
the file calling the function. The second argument, ``name`` is the name of the
library (to be used by templates when they want to include a resource from the
library using the ``{% resource %}`` tag as shown above).

Resources will be created for the library for any .js and .css files found
in the directory or it's subfolders. The resource name being the name of the
file including any path needed to get to it from the resource directory.  For
greater control of the creation a ``resource.config`` file can be created and
placed in the resource directory (see below for details).

resource.config
---------------

This file is used to define the resources in a directory and is sub folders.
Here is an example file.  The general layout of the file and allowed syntax is
the same as for the .ini config file.

::

    # Example resource.config file

    [main]

    dont_bundle = jquery.js
    force_top = html5.js
    order = jquery.js jed.js

    [IE conditional]

    lte IE 8 = html5.js block_html5_shim
    IE 7 = font-awesome/css/font-awesome-ie7.css
    others = html5.js

    [custom render order]

    block_html5_shim = 1
    html5.js = 2
    select2/select2.css = 9

    [inline scripts]

    block_html5_shim =
        var html5 = {shivMethods: false};

    [depends]

    vendor = jquery.js

    [groups]

    vendor =
        jed.js
        html5.js
        select2/select2.js
        select2/select2.css
        bootstrap/js/bootstrap-transition.js
        bootstrap/js/bootstrap-modal.js
        bootstrap/js/bootstrap-alert.js
        bootstrap/js/bootstrap-tab.js
        bootstrap/js/bootstrap-button.js
        font-awesome/css/font-awesome-ie7.css


[main]
~~~~~~

This can contain the following values

**force_top**

The resources listed will be placed in the head of the page.  This is only relevant
to .js files which will by default will be added to the bottom of the page.

**dont_bundle**

Bundeling resources causes them to be served to the browser as a single
resource to prevent multiple requests to the server.  The resources listed will
not be bundled.  By default items will be bundled where possible.  Note that
.css files can only be bundled if they are in the same directory.

**order**

This is used to make sure that resources are created in the order specified.  It
should not generally be needed but is available if there are problems.


[IE conditional]
~~~~~~~~~~~~~~~~

This allows IE conditionals to be wrapped around resources

eg ``<!--[if IE lte 8]--><script src="my_script.js"></script><![end if]-->``

The condition is supplied followed by a list of resources that need that condition.

**others**

This is a special condition that means that the resource will also be available
for none IE browsers.

[custom render order]
~~~~~~~~~~~~~~~~~~~~~

By default resources have a render order this is 10 for .css and 20 for .js
resources.  Sometimes we need to add resources before or after they would be
included an example being the html5shim.js that needs including before .css
resources.  By providing a custom render order for the resource it's placement
can be altered.  Lower numbered resources are rendered earlier.  Note that
resources rendered in the head will still be placed before ones rendered in the
body.

[inline scripts]
~~~~~~~~~~~~~~~~

It is possible to define inline scripts in the resource.config file this can be
helpful in some situations but is probably best avoided if possible.

[depends]
~~~~~~~~~

Some times one resource depends on another eg many scripts need jquery.js
included in the page before them. External resource libraries will
automatically depend on the core CKAN JavaScript modules so do not need to
specify this.

[groups]
~~~~~~~~

Groups of resources can be specified this allows the group to be included by
just using it's name rather than having to specify each resource individuality
when requesting them.  The order that items are added to a group will be used
to order the resources when added to the page but other factors such as
dependencies, custom render order and resource type can affect the final order
used.


Groups can be referred to in many places in the
resource.config file eg. [depends]
