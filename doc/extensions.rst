==============
Add Extensions
==============

This is where it gets interesting! The CKAN software can be customised with 'extensions'. These are a simple way to extend core CKAN functions. 

Extensions allow you to customise CKAN for your own requirements, without interfering with the basic CKAN system.

.. warning:: This is an advanced topic.

Choosing Extensions
-------------------

All CKAN extensions are listed on the official `Extension listing on the CKAN
wiki <http://wiki.ckan.net/List_of_Extensions>`_.

Some popular extensions include:

.. note::

   Those marked with (x) are 'core' extensions and are shipped as part of the core CKAN distribution

* ckanext-stats (x): Statistics (and visuals) about the datasets in a CKAN instance.
* `ckanext-apps <https://github.com/okfn/ckanext-apps>`_: Apps and ideas catalogue extension for CKAN.
* `ckanext-disqus <https://github.com/okfn/ckanext-disqus>`_: Allows users to comment on dataset pages with Disqus. 
* `ckanext-follower <https://github.com/okfn/ckanext-follower>`_: Allow users to follow datasets.
* `ckanext-googleanalytics <https://github.com/okfn/ckanext-googleanalytics>`_: Integrates Google Analytics data into CKAN. Gives download stats on dataset pages, list * of most popular datasets, etc.
* `ckanext-qa <https://github.com/okfn/ckanext-qa>`_: Provides link checker, 5 stars of openness and other Quality Assurance features.
* `ckanext-rdf <https://github.com/okfn/ckanext-rdf>`_: Consolidated handling of RDF export and import for CKAN. 
* `ckanext-wordpresser <https://github.com/okfn/ckanext-wordpresser>`_: CKAN plugin / WSGI middleware for combining CKAN with a Wordpress site. 
* `ckanext-spatial <https://github.com/okfn/ckanext-spatial>`_: Adds geospatial capabilities to CKAN datasets, including a spatial search API. 

Installing an Extension
-----------------------

You can install an extension on a CKAN instance as follows.

.. note::

  'Core' extensions do not need to be installed -- just enabled (see below).

#. Locate your CKAN virtual environment (pyenv) in your filesystem. It is usually in a directory similar to this: ``/var/lib/ckan/INSTANCE_NAME/pyenv``

If it is not here, to get the definitive answer, check your CKAN Apache configuration (``/etc/apache2/sites-enabled``) for your WSGIScriptAlias (e.g. ``/var/lib/ckan/colorado/wsgi.py``) which has an ``execfile`` instruction. The first parameter is the pyenv directory plus ``/bin/activate_this.py``. e.g. ``/var/lib/ckan/colorado/pyenv/bin/activate_this.py`` means the pyenv dir is: ``/var/lib/ckan/colorado/pyenv``.

#. Install the extension package code into your pyenv using ``pip``.

 For example, to install the Disqus extension, which allows users to comment on datasets (replacing "INSTANCE_NAME" with the name of your CKAN instance)::

       sudo -u ckanINSTANCE_NAME /var/lib/ckan/INSTANCE_NAME/pyenv/bin/pip install -E /var/lib/ckan/INSTANCE_NAME/pyenv -e git+https://github.com/okfn/ckanext-disqus.git#egg=ckanext-disqus --log=/tmp/pip-log.txt

 Prefix the source URL with the repo type (``hg+`` for Mercurial, ``git+`` for Git).
 
 The dependency you've installed will appear in the ``src/`` directory under your Python environment. 

Now the extension is installed, so now you can enable it.


Enabling an Extension
---------------------

1. Add the names of the extension's plugins to the CKAN config file in the '[app:main]' section under 'ckan.plugins'. e.g.::

       [app:main]
       ckan.plugins = disqus

   If your extension implements multiple different plugin interfaces, separate them with spaces::

       ckan.plugins = disqus amqp myplugin

   .. note::

     Finding out the name of an extension's plugins: this information should
     usually be provided in the extension's documentation, but you can also
     find this information in the plugin's ``setup.py`` file under
     ``[ckan.plugins]``.
   
2. To have this configuration change take effect it may be necessary to restart
   WSGI, which usually means restarting Apache::

       sudo /etc/init.d/apache2 restart

Your extension should now be enabled. You can disable it at any time by
removing it from the list of ckan.plugins in the config file.


Enabling an Extension with Background Tasks
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Some extensions need to run tasks in the background. See
:doc:`background-tasks` for how to enable background tasks.

