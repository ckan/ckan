==========
Extensions
==========

CKAN can be customised with 'extensions'. These are a simple way to extend
core CKAN functionality.  Extensions allow you to customise CKAN for your
own requirements, without interfering with the basic CKAN system.

Core Extensions
---------------

CKAN comes with some extensions built-in.  We call these `Core Extensions`
and you can just enable them.  There is no need to install them first.

* datastore - ???
* jsonpreview - Preview json resources
* multilingual - ???
* pdfpreview - Preview pdf resources via JavaScript library
* reclinepreview - Preview resources via recline library, graphs etc
* resourceproxy - ????
* stats - Show stats and visuals about datasets

Non-Core Extensions
-------------------

Many other extensions are available and may be used with CKAN.  These will
need to be installed.  Every extension should include instructions on how to
install and configure it.

Enabling an Extension
---------------------

1. Add the names of the extension's plugins to the CKAN config file in the
   '[app:main]' section under 'ckan.plugins'. If your extension implements
   multiple different plugin interfaces, separate them with spaces e.g.::

       [app:main]
       ckan.plugins = stats jsonpreview

2. To have this configuration change take effect it may be necessary to
   restart CKAN, which usually means restarting Apache::

       sudo /etc/init.d/apache2 restart

Your extension should now be enabled. You can disable it at any time by
removing it from the list of ckan.plugins in the config file and restarting
CKAN.

Extensions are run in the order defined in the config.
