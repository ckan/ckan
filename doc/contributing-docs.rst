=======================================
How to Contribute to this Documentation
=======================================

.. note::

 Getting started with contributing to the CKAN docs is a little complicated.
 An easier way to contribute documentation to CKAN is to contribute to the
 `CKAN Wiki <https://github.com/okfn/ckan/wiki>`_. Docs started on the wiki
 can make it into this documentation later.

This documentation is created using `Sphinx <http://sphinx-doc.org/>`_.
The source files are in
`the doc directory of the CKAN git repo <https://github.com/okfn/ckan/tree/master/doc>`_.
To edit these docs:

1. If you haven't already, create a
   `Python virtual environment <http://pypi.python.org/pypi/virtualenv>`_
   (virtualenv), activate it and clone the CKAN git repo into it. In this
   example we'll create a virtualenv in a folder called ``pyenv``::

    virtualenv --no-site-packages pyenv
    . pyenv/bin/activate
    pip install -e 'git+https://github.com/okfn/ckan.git#egg=ckan'

2. Install the Python dependencies necessary for building the CKAN docs into
   your virtualenv::

    pip install -r pyenv/src/ckan/pip-requirements-docs.txt

3. Fetch the git submodule that contains CKAN's custom Sphinx theme::

    cd pyenv/src/ckan
    git submodule init
    git submodule update

   .. note::

    You may occassionally have to run ``git submodule update`` again, when
    someone updates the submodule.

4. Make changes to the documentation by using your text editor to edit the
   ``pyenv/src/ckan/doc/*.rst`` files.

5. Build the documentation locally, to preview your changes::

    python setup.py build_sphinx

   Now you can open the built HTML files in
   ``pyenv/src/ckan/build/sphinx/html`` to see your changes, e.g.:
   ``firefox pyenv/src/ckan/build/sphinx/html/index.html``.

6. Finally, when you're ready to submit your contributions to the CKAN
   project, follow the same process as for contributing code:
   :doc:`contributing`.
