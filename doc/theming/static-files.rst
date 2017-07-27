===================
Adding static files
===================

You may need to add some custom *static files* to your CKAN site and use them
from your templates, for example image files, PDF files, or any other static
files that should be returned as-is by the webserver (as opposed to Jinja
template files, which CKAN renders before returning them to the user).

By adding a directory to CKAN's :ref:`extra_public_paths` config setting,
a plugin can make a directory of static files available to be used or linked to
by templates. Let's add a static image file, and change the home page template
to use our file as the promoted image on the front page.

.. seealso::

   :doc:`fanstatic`

    If you're adding CSS files consider using Fanstatic instead of
    :ref:`extra_public_paths`, to take advantage of extra features.
    See :doc:`fanstatic`. If you're adding |javascript| modules you have to
    use Fanstatic, see :doc:`javascript`.

First, create a ``public`` directory in your extension with a
``promoted-image.jpg`` file in it::

 ckanext-example_theme/
   ckanext/
      example_theme/
         public/
            promoted-image.jpg

``promoted-image.jpg`` should be a 420x220px JPEG image file. You could use
this image file for example:

.. image:: /../ckanext/example_theme_docs/v12_extra_public_dir/public/promoted-image.jpg
   :alt: An example promoted image
   :height: 220px
   :width: 420px

Then in ``plugin.py``, register your ``public`` directory with CKAN by calling
the :py:func:`~ckan.plugins.toolkit.add_public_directory` function. Add this
line to the :py:func:`~ckan.ckanext.example_theme_docs.v11_extra_public_directory.plugin.update_config`
function:

.. literalinclude:: /../ckanext/example_theme_docs/v12_extra_public_dir/plugin.py
   :pyobject: ExampleThemePlugin.update_config

If you now browse to `127.0.0.1:5000/promoted-image.jpg <http://127.0.0.1:5000/promoted-image.jpg>`_,
you should see your image file.

To replace the image on the front page with your custom image, we need to
override the ``promoted.html`` template snippet. Create the following directory
and file::

 ckanext-example_theme/
   ckanext/
     example_theme/
       templates/
         home/
           snippets/
             promoted.html

Edit your new ``promoted.html`` snippet, and insert these contents:

.. literalinclude:: /../ckanext/example_theme_docs/v12_extra_public_dir/templates/home/snippets/promoted.html
   :language: django

After calling ``{% ckan_extends %}`` to declare that it extends (rather than
completely replaces) the default ``promoted.html`` snippet, this custom snippet
overrides two of ``promoted.html``'s template blocks. The first block replaces
the caption text of the promoted image. The second block replaces the ``<img>``
tag itself, pointing it at our custom static image file:

.. literalinclude:: /../ckanext/example_theme_docs/v12_extra_public_dir/templates/home/snippets/promoted.html
   :language: django
   :start-after: {# Replace the promoted image. #}

If you now restart the development web server and reload the `CKAN front page`_
in your browser, you should see the promoted image replaced with our custom
one:


.. image:: /images/extra-public-dir.png
   :alt: The custom promoted image.
