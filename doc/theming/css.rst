======================
Customizing CKAN's CSS
======================

.. seealso::

   There's nothing special about CSS in CKAN, once you've got started with
   editing CSS in CKAN (by following the tutorial below), then you just use the
   usual tools and techniques to explore and hack the CSS. We recommend using
   your browser's web development tools to explore and experiment with the CSS,
   then using any good text editor to edit your extension's CSS files as
   needed. For example:

   `Firefox developer tools <https://developer.mozilla.org/en-US/docs/Tools>`_
     These include a Page Inspector and a Style Editor

   `Firebug <https://www.getfirebug.com/>`_
     Another web development toolkit for Firefox

   `Chrome developer tools <https://developers.google.com/chrome-developer-tools/>`_
     Tools for inspecting and editing CSS in Google Chrome

   `Mozilla Developer Network's CSS section <https://developer.mozilla.org/en-US/docs/Web/CSS>`_
     A good collection of CSS documentation and tutorials

Extensions can add their own CSS files to modify or extend CKAN's default CSS.
Create an ``example_theme.css`` file in your extension's ``public`` directory::

    ckanext-example_theme/
      ckanext/
        example_theme/
          public/
            example_theme.css

Add this CSS into the ``example_theme.css`` file, to change the color of CKAN's
"account masthead" (the bar across the top of the site that shows the logged-in
user's account info):

.. literalinclude:: /../ckanext/example_theme_docs/v13_custom_css/public/example_theme.css
   :language: css

If you restart the development web server  you should be able to open this file
at http://127.0.0.1:5000/example_theme.css in a web browser.

To make CKAN use our custom CSS we need to override the ``base.html`` template,
this is the base template which the templates for all CKAN pages extend, so if
we include a CSS file in this base template then the file will be included in
every page of your CKAN site. Create the file::

    ckanext-example_theme/
      ckanext/
        example_theme/
          templates/
            base.html

and put this Jinja code in it:

.. literalinclude:: /../ckanext/example_theme_docs/v13_custom_css/templates/base.html
   :language: django

The default ``base.html`` template defines a ``styles`` block which can be
extended to link to custom CSS files (any code in the styles block will appear
in the ``<head>`` of the HTML page).

Restart the development web server and reload the CKAN page in your browser,
and you should see the background color of the account masthead change:

.. image:: /images/custom-css.png
   :alt: The account masthead with some custom CSS.

This custom color should appear on all pages of your CKAN site.

Now that we have CKAN using our CSS file, we can add more CSS rules to the file
and customize CKAN's CSS as much as we want.
Let's add a bit more code to our ``example_theme.css`` file. This CSS
implements a partial imitation of the `datahub.io <http://datahub.io/>`_ theme
(circa 2013):

.. image:: /images/more-custom-css.png
   :alt: A partial imitation of the datahub.io theme, circa 2013.

.. literalinclude:: /../ckanext/example_theme_docs/v14_more_custom_css/public/example_theme.css
   :language: css
