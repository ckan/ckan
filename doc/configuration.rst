===================
Config File Options
===================


You can set many important options in the CKAN config file. By default, the
configuration file is located at ``/etc/ckan/development.ini`` or
``/etc/ckan/production.ini``. This section documents all of the config file
settings, for reference.

.. todo::

   Insert cross-ref to section about location of config file?

.. note:: After editing your config file, you need to restart your webserver
   for the changes to take effect.

.. note:: Unless otherwise noted, all configuration options should be set inside
   the ``[app:main]`` section of the config file (i.e. after the ``[app:main]``
   line)::

        [DEFAULT]

        ...

        [server:main]
        use = egg:Paste#http
        host = 0.0.0.0
        port = 5000

        # This setting will not work, because it's outside of [app:main].
        ckan.site_logo = /images/masaq.png

        [app:main]
        # This setting will work.
        ckan.plugins = stats text_preview recline_preview

   If the same option is set more than once in your config file, the last
   setting given in the file will override the others.


.. config::

