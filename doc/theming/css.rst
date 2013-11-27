======================
Customizing CKAN's CSS
======================

Extensions can add their own CSS files to modify or extend CKAN's default CSS.
Create an ``example_theme.css`` file in your extension's ``public`` directory::

    ckanext-example_theme/
      public/
        example_theme.css

Add this CSS into the ``example_theme.css`` file, to change the color of CKAN's
"account masthead" (the bar across the top of the site that shows the logged-in
user's account info):

.. literalinclude:: /../ckanext/example_theme/v13_custom_css/public/example_theme.css

If you restart the development web server  you should be able to open this file
at http://127.0.0.1:5000/example_theme.css in a web browser.

To make CKAN use our custom CSS we need to override the ``base.html`` template,
this is the base template which the templates for all CKAN pages extend, so if
we include a CSS file in this base template then the file will be included in
every page of your CKAN site. Create the file::

    ckanext-example_theme/
      templates/
        base.html

and put this Jinja code in it:

.. literalinclude:: /../ckanext/example_theme/v13_custom_css/templates/base.html

The default ``base.html`` template defines a ``styles`` block which can be
extended to link to custom CSS files (any code in the styles block will appear
in the ``<head>`` of the HTML page).

Restart the development web server and reload the CKAN page in your browser,
and you should see the background color of the account masthead change. This
custom color should appear on all pages of your CKAN site.

Now that we have CKAN using our CSS file, we can add more CSS rules to the file
and customize CKAN's CSS as much as we want. There's nothing special about CSS
in CKAN, you just use the usual tools and techniques to explore and hack the
CSS.

.. todo:: Link to some tools?

   e.g. Firefox inspector etc (or Chrome? Firebug?)

   e.g. Some online CSS reference.

Let's add a bit more code to our ``example_theme.css`` file. This CSS
implements a partial imitation of the `datahub.io <http://datahub.io/>`_ theme
(circa 2013):

.. literalinclude:: /../ckanext/example_theme/v14_more_custom_css/public/example_theme.css

.. todo::

   We use LESS for the CKAN core CSS. Do we want to mention that here?

