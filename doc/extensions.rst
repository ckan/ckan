==============
Add Extensions
==============

The CKAN software can be customised with 'extensions'. These are a simple way to extend core CKAN functions. 

Extensions allow you to customise CKAN for your own requirements, without interfering with the basic CKAN system.

Popular CKAN extensions are listed on the `CKAN wiki <http://wiki.ckan.net/Main_Page>`_. All CKAN extensions can be found at `OKFN's bitbucket page <https://bitbucket.org/okfn/>`_, prefaced with ``ckanext-``.

.. warning:: This is an advanced topic. At the moment, you need to have installed a developer version of CKAN to work with extensions, as described in :doc:`developer-install`. If you need help, contact the `ckan-discuss mailing list <http://lists.okfn.org/mailman/listinfo/ckan-discuss>`_. We are working to make the most popular extensions more easily available as Debian packages. 


Installing an Extension
-----------------------

To install an extension on a CKAN instance:

1. Install the extension package code using ``pip``.

 For example, to install the Disqus extension, which allows users to comment on datasets::

       pip install -E ~/var/srvc/ckan.net/pyenv hg+http://bitbucket.org/okfn/ckanext-disqus

 The ``-E`` parameter is for your CKAN Python environment (e.g. ``~/var/srvc/ckan.net/pyenv``). 

 Prefix the source URL with the repo type (``hg+`` for Mercurial, ``git+`` for Git).
 

2. Add the names of any plugin implementations the extension uses to the CKAN
config file. You can find these in the plugin's ``setup.py`` file under ``[ckan.plugins]``.

 The config plugins variable is in the '[app:main]' section under 'ckan.plugins'. e.g.::

       [app:main]
       ckan.plugins = disqus

 If your extension implements multiple different plugin interfaces, separate them with spaces::

       ckan.plugins = disqus amqp myplugin

3. If necessary, restart WSGI, which usually means restarting Apache::

       sudo /etc/init.d/apache2 restart

Your extension should now be installed.
