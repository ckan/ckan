==============
Add Extensions
==============

This is where it gets interesting! The CKAN software can be customised with 'extensions'. These are a simple way to extend core CKAN functions. 

Extensions allow you to customise CKAN for your own requirements, without interfering with the basic CKAN system.

.. warning:: This is an advanced topic. At the moment, you need to have prepared your system to work with extensions, as described in :doc:`prepare-extensions`. We are working to make the most popular extensions more easily available as Debian packages. 

Finding Extensions
------------------

Many CKAN extensions are listed on the CKAN wiki's `List of Extensions <http://wiki.ckan.net/List_of_Extensions>`_. All CKAN extensions can be found at `OKFN's bitbucket page <https://bitbucket.org/okfn/>`_, prefaced with ``ckanext-``.

Some popular extensions include: 

* `ckanext-apps <https://bitbucket.org/okfn/ckanext-apps>`_: Apps and ideas catalogue extension for CKAN.
* `ckanext-deliverance <https://bitbucket.org/okfn/ckanext-deliverance>`_: Extends CKAN to use the Deliverance HTTP proxy, which can request and render web pages from * an external site (e.g. a CMS like Drupal or Wordpress). 
* `ckanext-disqus <https://bitbucket.org/okfn/ckanext-disqus>`_: Allows users to comment on dataset pages with Disqus. 
* `ckanext-follower <https://bitbucket.org/okfn/ckanext-follower>`_: Allow users to follow datasets.
* `ckanext-googleanalytics <https://bitbucket.org/okfn/ckanext-googleanalytics>`_: Integrates Google Analytics data into CKAN. Gives download stats on dataset pages, list * of most popular datasets, etc.
* `ckanext-qa <https://bitbucket.org/okfn/ckanext-qa>`_: Provides link checker, 5 stars of openness and other Quality Assurance features.
* `ckanext-rdf <https://bitbucket.org/okfn/ckanext-rdf>`_: Consolidated handling of RDF export and import for CKAN. 
* `ckanext-stats <https://bitbucket.org/okfn/ckanext-stats>`_: Statistics (and visuals) about the datasets in a CKAN instance.
* `ckanext-wordpresser <https://bitbucket.org/okfn/ckanext-wordpresser>`_: CKAN plugin / WSGI middleware for combining CKAN with a Wordpress site. 

Installing an Extension
-----------------------

You can install an extension on a CKAN instance as follows.

1. First, ensure you are working within your virtualenv (see :doc:`prepare-extensions` if you are not sure what this means)::

   . /home/ubuntu/pyenv/bin/activate

2. Install the extension package code using ``pip``.

 For example, to install the Disqus extension, which allows users to comment on datasets::

       pip install -E ~/var/srvc/ckan.net/pyenv hg+http://bitbucket.org/okfn/ckanext-disqus

 The ``-E`` parameter is for your CKAN Python environment (e.g. ``~/var/srvc/ckan.net/pyenv``). 

 Prefix the source URL with the repo type (``hg+`` for Mercurial, ``git+`` for Git).
 
 The dependency you've installed will appear in the ``src/`` directory under your Python environment. 

3. Add the names of any plugin implementations the extension uses to the CKAN
config file. You can find these in the plugin's ``setup.py`` file under ``[ckan.plugins]``.

 The config plugins variable is in the '[app:main]' section under 'ckan.plugins'. e.g.::

       [app:main]
       ckan.plugins = disqus

 If your extension implements multiple different plugin interfaces, separate them with spaces::

       ckan.plugins = disqus amqp myplugin

4. If necessary, restart WSGI, which usually means restarting Apache::

       sudo /etc/init.d/apache2 restart

Your extension should now be installed.
