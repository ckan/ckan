CKAN Configuration
==================

A CKAN instance is configured with the .ini file in the root ckan directory. The most important parameter to set is the `sqlalchemy.url` giving the database connection. But there are also several additional options to change the way the CKAN site operates.

On a production machine the file will be probably be named after the site name. e.g. `ca.ckan.net.ini` On a development machine it is probably `development.ini`

On a new installation of ckan, you have to create a new config file from the template, something like this::

  paster --plugin ckan make-config ckan ca.ckan.net.ini

This creates ca.ckan.net.ini based on the template for this file in ckan/config/deployment.ini_tmpl

There are several general Pylons options, and all the CKAN-specific ones are in the `[app:main]` section.

Once the config file is changed, Apache needs to be restarted to read in the new changes.


sqlalchemy.url
--------------

Example::

 sqlalchemy.url = postgres://tester:pass@localhost/ckantest3

This defines the database that CKAN is to use. The format is::

 sqlalchemy.url = postgres://USERNAME:PASSWORD@HOST/DBNAME


package_form
------------

Example::

 package_form = ca

Default::

 package_form = standard

This sets the name of the form to use when editing a package. This can be a form defined in the core CKAN code or in another setuputils-managed python module. The only requirement is that the setup.py has an entrypoint for the form defined in the `ckan.forms` section. See :doc:`package_forms`


ckan_host
---------

Example::

 ckan_host = ckan.net

By telling CKAN what hostname it is served at, it can provide backlinks to packages in two places:

1. The REST API: when you read a package register it contains a property giving a link to the package on CKAN. e.g. `"ckan_url": "http://ckan.net/package/pollution-2008"`

2. The backend RDF generator can use the CKAN package URLs for the subject in the triples.


rdf_packages
------------

Example::

 rdf_packages = http://semantic.ckan.net/package/

Configure this if you have an RDF store of the same packages as are in your CKAN instance. It will provide three sorts of links from each package page to the equivalent RDF URL given in `rdf_packages`:

1. 303 redirects for clients that content-negotiate rdf-xml. e.g. client GETs `http://ckan.net/package/pollution-2008` with accept header `application/rdf+xml`. CKAN's response is a 303 redirect to `http://semantic.ckan.net/package/pollution-2008`

2. Embedded links for browsers that are aware. e.g. `<link rel="alternate" type="application/rdf+xml" href="http://semantic.ckan.net/package/pollution-2008">`

3. A visible RDF link on the page in the 'Alternative metadata formats' box. e.g. `<a href="http://semantic.ckan.net/package/pollution-2008">`

enable_caching
--------------

Example::

 enable_caching = 1

The presence of this option turns on the caching of package details for when a search is done over the API and all_fields is switched on. To disable this, remove the option completely.


licenses_group_url
------------------

Example::
 
 licenses_group_url = http://licenses.opendefinition.org/2.0/ckan_canada

This specifies a CKAN license service. It determines which licenses are offered when you create or edit a package.

The URL in the option should point to a store of license information (in JSON format) that has been deployed by the CKAN License package and served over HTTP. If you don't specify this then it displays the full list from the CKAN License module.


lang
----

Example::

 lang=de

Use this to specify the default language of the text displayed in the CKAN web UI. The default is English (en).


extra_template_paths
--------------------

Example::

 extra_template_paths=/home/okfn/brazil_ckan_config/templates

To customise the display of CKAN you can supply replacements for the Genshi template files. Use this option to specify where CKAN should look for them, before reverting to the 'ckan/templates' folder. You can supply more than one folder, separating the paths with a comma (,).

The example value for the extra_template_paths option could, for example, be used to override CKAN templates with these ones:

 * /home/okfn/brazil_ckan_config/templates/layout.html
 * /home/okfn/brazil_ckan_config/templates/package/edit.html

More details about this feature are found at: http://wiki.okfn.org/ckan/doc/theme


extra_template_paths
--------------------

Example::

 extra_public_paths = /home/okfn/brazil_ckan_config/public

To customise the display of CKAN you can supply replacements for staticly served files such as HTML, CSS, script and PNG files. Use this option to specify where CKAN should look for them, before reverting to the 'ckan/public' folder. You can supply more than one folder, separating the paths with a comma (,).

The example value for the extra_public_paths option could, for example, be used to provide an image and stylesheet:

 * /home/okfn/brazil_ckan_config/public/images/brazil.png
 * /home/okfn/brazil_ckan_config/public/css/extra.css

More details about this feature are found at: http://wiki.okfn.org/ckan/doc/theme
