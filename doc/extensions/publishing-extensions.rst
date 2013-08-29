Publishing extensions
=====================

CKAN extensions are just Python packages like any other Python package,
they can be published, downloaded and installed using the usual methods.
For example, why not get a free `github.com <https://github.com/>`_ account,
create a new git repo and push your extension code to it?
See `help.github.com <https://help.github.com/>`_ for documentation on using
git and GitHub.

.. note::

   There are a few files in the ``ckanext-iauthfunctions`` directory that you
   shouldn't publish or commit to your git repository or other version control
   repo. Don't commit:

   * the ``ckanext_iauthfunctions.egg-info`` directory, or
   * any of the ``*.pyc`` files.

   You should create a `.gitignore file
   <https://help.github.com/articles/ignoring-files>`_ to tell git to ignore
   these files, and commit the ``.gitignore`` file to your git repo.

   *Do* commit the ``setup.py`` file, the ``test.ini`` file and all the
   ``__init__.py`` files.

Once it's been published to GitHub, users can then install your extension by
activating their CKAN virtual environment then running a command like this::

    pip install -e git+https://github.com/{USER}/ckanext-iauthfunctions.git#egg=ckanext-iauthfunctions

(replacing ``{USER}`` with the name of the GitHub account that the extension
was published to). They can then simply add your plugin to the ``ckan.plugins``
setting in the config file, restart CKAN, and your plugin should be running.

