===================
Adding static files
===================

---------------------------------------------------
Adding static files using a simple public directory
---------------------------------------------------

You may need to add some custom *static files* to your CKAN site and use them
from your templates, for example image files, PDF files, or any other static
files that should be returned as-is by the webserver (as opposed to Jinja
template files, which CKAN renders before returning them to the user).

By adding a directory to CKAN's :ref:`extra_public_paths` config setting,
a plugin can make a directory of static files available to be used or linked to
by templates. Let's add a static image file, and change the home page template
to use our file as the promoted image on the front page.

.. note::

   If you're adding |javascript| or CSS files, consider using Fanstatic instead
   of :ref:`extra_public_paths`, to take advantage of extra features.
   See :ref:`fanstatic tutorial` below.

First, create a ``public`` directory in your extension with a
``promoted-image.jpg`` file in it::

 ckanext-example_theme/
   public/
     promoted-image.jpg

``promoted-image.jpg`` should be a 420x220px JPEG image file. You could use
this image file for example:

.. image:: /../ckanext/example_theme/v12_extra_public_dir/public/promoted-image.jpg
   :alt: An example promoted image
   :height: 220px
   :width: 420px

Then in ``plugin.py``, register your ``public`` directory with CKAN by calling
the :py:func:`~ckan.plugins.toolkit.add_public_directory` function. Add this
line to the :py:func:`~ckan.ckanext.example_theme.v11_extra_public_directory.plugin.update_config`
function:

.. literalinclude:: /../ckanext/example_theme/v12_extra_public_dir/plugin.py
   :pyobject: ExampleThemePlugin.update_config

If you now browse to `127.0.0.1:5000/promoted-image.jpg <http://127.0.0.1:5000/promoted-image.jpg>`_,
you should see your image file.

To replace the image on the front page with your custom image, we need to
override the ``promoted.html`` template snippet. Create the following directory
and file::

 ckanext-example_theme/
   templates/
     home/
       snippets/
         promoted.html

Edit your new ``promoted.html`` snippet, and insert these contents:

.. literalinclude:: /../ckanext/example_theme/v12_extra_public_dir/templates/home/snippets/promoted.html

After calling ``{% ckan_extends %}`` to declare that it extends (rather than
completely replaces) the default ``promoted.html`` snippet, this custom snippet
overrides two of ``promoted.html``'s template blocks. The first block replaces
the caption text of the promoted image. The second block replaces the ``<img>``
tag itself, pointing it at our custom static image file:

.. literalinclude:: /../ckanext/example_theme/v12_extra_public_dir/templates/home/snippets/promoted.html
   :start-after: {# Replace the promoted image. #}

If you now reload the `CKAN front page`_ in your browser, you should see the
promoted image replaced with our custom one.


.. _fanstatic tutorial:

------------------------------------------------
Adding |javascript| and CSS file using Fanstatic
------------------------------------------------

If you're adding |javascript| or CSS files to your theme, you can add them
using `Fanstatic <http://www.fanstatic.org/>`_ rather than the simple
:ref:`extra_public_paths` method described above (`JavaScript modules
<javascript modules>`_ *must* be added using Fanstatic). Using Fanstatic to add
|javascript| and CSS files allows you to take advantage of Fanstatic's
features, such as automatically serving minified files in production, caching
and bundling files together to reduce page load times, specifying dependencies
between files so that the files a page needs (and only the files it needs) are
always loaded, and other tricks to optimize page load times.

.. note::

   CKAN will only serve ``*.js`` and ``*.css`` files as Fanstatic resources,
   other types of static files (eg. image files, PDF files) must be added
   using the :ref:`extra_public_paths` method described above.

Adding a custom |javascript| or CSS file to CKAN is using Fanstatic is simple:

.. todo:: Turn this into a real working example.

1. First, create a fanstatic directory in your extension with the CSS and
   |javascript| files in it::

    ckanext-example_theme/
      fanstatic/
        my_style.css
        my_script.js

2. Use CKAN's ``add_resource()`` function to register your fanstatic
   directory with CKAN. Edit the ``update_config()`` method in your
   ``plugin.py`` file::

        def update_config(self, config):

            # Add this plugin's templates dir to CKAN's extra_template_paths, so
            # that CKAN will use this plugin's custom templates.
            toolkit.add_template_directory(config, 'templates')

            # Add this plugin's public dir to CKAN's extra_public_paths, so
            # that CKAN will use this plugin's custom static files.
            toolkit.add_public_directory(config, 'public')

            toolkit.add_resource('fanstatic', 'example_theme')

   The second argument to ``add_resource()``, ``'example_theme'``, is the name
   that you'll need to use to refer to your custom Fanstatic library from
   templates (you can pass whatever name you want here).

3. Finally, use CKAN's custom Jinja2 tag ``{% resource %}`` to import the file
   in the template that needs it::

     {% resource 'example_theme/my_script.js' %}
     {% resource 'example_theme/my_style.css' %}

   You can put the ``{% resource %}`` tag anywhere in the template, and
   Fanstatic will insert and necessary ``<style>`` and ``<script>`` tags to
   include your |javascript| and CSS files and their dependencies in the right
   places in the HTML output (CSS files in the HTML ``<head>``, |javascript|
   files at the bottom of the page).

.. todo:: Add a note about Fanstatic resource configuration file.

----------------------------------
Fanstatic resource troubleshooting
----------------------------------

``AttributeError``
==================
