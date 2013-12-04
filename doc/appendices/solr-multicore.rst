.. _multicore solr setup:

====================
Multicore Solr setup
====================

Solr can be set up to have multiple configurations and search indexes on the
same machine. Each configuration is called a Solr *core*. Having multiple cores
is useful when you want different applications or different versions of CKAN to
share the same Solr instance, each application can have its own Solr core so
each can use a different ``schema.xml`` file. This is necessary, for example,
if you want two CKAN instances to share the same |solr| server and those two
instances are running different versions of CKAN that require differemt
``schema.xml`` files, or if the two instances have different |solr| schema
customizations.

Each |solr| core in a multicore setup will have a different URL, for example::

    http://localhost:8983/solr/ckan_default
    http://localhost:8983/solr/some_other_site

This section will show you how to create a multicore |solr| setup and create
your first core. If you already have a multicore setup and now you've setup a
second CKAN instance on the same machine and want to create a second |solr|
core for it, see :ref:`creating another solr core`.

#. Create the file ``/usr/share/solr/solr.xml``, with the following contents::

    <solr persistent="true" sharedLib="lib">
        <cores adminPath="/admin/cores">
            <core name="ckan_default" instanceDir="ckan_default"> 
                <property name="dataDir" value="/var/lib/solr/data/ckan_default" />
            </core>
        </cores>
    </solr>

   This file lists the different Solr cores, in this example we have just a
   single core called ``ckan_default``.

#. Create the data directory for your Solr core, run this command in a
   terminal::

    sudo -u jetty mkdir /var/lib/solr/data/ckan_default

   This is the directory where Solr will store the search index files for
   our core.

#. Create the directory ``/etc/solr/ckan_default``, and move the
   ``/etc/solr/conf`` directory into it::

    sudo mkdir /etc/solr/ckan_default
    sudo mv /etc/solr/conf /etc/solr/ckan_default/

   This directory holds the configuration files for your Solr core.

#. Replace the ``/etc/solr/ckan_default/schema.xml`` file with a symlink to
   CKAN's ``schema.xml`` file::

    sudo mv /etc/solr/ckan_default/conf/schema.xml /etc/solr/ckan_default/conf/schema.xml.bak
    sudo ln -s /usr/lib/ckan/default/src/ckan/ckan/config/solr/schema.xml /etc/solr/ckan_default/conf/schema.xml

#. Edit ``/etc/solr/ckan_default/conf/solrconfig.xml`` and change the
   ``<dataDir>`` tag to this::

    <dataDir>${dataDir}</dataDir>

   This configures our ``ckan_default`` core to use the data directory you
   specified for it in ``solr.xml``.

#. Create the directory ``/usr/share/solr/ckan_default`` and put a symlink
   to the ``conf`` directory in it::

    sudo mkdir /usr/share/solr/ckan_default
    sudo ln -s /etc/solr/ckan_default/conf /usr/share/solr/ckan_default/conf

#. Restart Solr:

   .. parsed-literal::

      |restart_solr|

   You should now see your newly created ``ckan_default`` core if you open
   http://localhost:8983/solr/ckan_default/admin/ in your web browser.
   You can click on the *schema* link on this page to check that the core is
   using the right schema (you should see ``<schema name="ckan" version="2.0">``
   near the top of the ``schema.xml`` file). The http://localhost:8983/solr/
   page will list all of your configured Solr cores.

#. Finally, change the ``solr_url`` setting in your |development.ini| or
   |production.ini| file to point to your new Solr core, for example::

    solr_url = http://127.0.0.1:8983/solr/ckan_default

If you have trouble when setting up Solr, see
:ref:`multicore solr troubleshooting` below.


.. _creating another solr core:

--------------------------
Creating another Solr core
--------------------------

.. The name of the second CKAN instance that we're going to setup a second core
   for:
.. |ckan| replace:: my-second-ckan-instance

.. The name of the second CKAN core we're going to set up:
.. |core| replace:: my-second-solr-core

In this example we'll assume that:

#. You've followed the instructions in :ref:`multicore solr setup` to create
   a multicore setup and create your first core for your first CKAN instance.

#. You've installed a second instance of CKAN in a second virtual environment
   at /usr/lib/ckan/|ckan|, and now want to setup a second Solr core for it.

You can of course follow these instructions again to setup further Solr cores.

#. Add the core to ``/usr/share/solr/solr.xml``. This file should now list
   two cores. For example:

   .. parsed-literal::

    <solr persistent="true" sharedLib="lib">
        <cores adminPath="/admin/cores">
            <core name="ckan_default" instanceDir="ckan_default">
                <property name="dataDir" value="/var/lib/solr/data/ckan_default" />
            </core>
            <core name="|core|" instanceDir="|core|">
                <property name="dataDir" value="/var/lib/solr/data/|core|" />
            </core>
        </cores>
    </solr>

#. Create the data directory for your new core:

   .. parsed-literal::

    sudo -u jetty mkdir /var/lib/solr/data/|core|

#. Create the configuration directory for your new core, and copy the config
   from your first core into it:

   .. parsed-literal::

    sudo mkdir /etc/solr/|core|
    sudo cp -R /etc/solr/ckan_default/conf /etc/solr/|core|/

#. Replace the /etc/solr/|core|/schema.xml file with a symlink to the
   ``schema.xml`` file from your second CKAN instance:

   .. parsed-literal::

    sudo rm /etc/solr/|core|/conf/schema.xml
    sudo ln -s /usr/lib/ckan/|ckan|/src/ckan/ckan/config/solr/schema.xml /etc/solr/|core|/conf/schema.xml

#. Create the /usr/share/solr/|core| directory and put a symlink to the
   ``conf`` directory in it:

   .. parsed-literal::

    sudo mkdir /usr/share/solr/|core|
    sudo ln -s /etc/solr/|core|/conf /usr/share/solr/|core|/conf

#. Restart |solr|:

   .. parsed-literal::

      |restart_solr|

   You should now see both your Solr cores when you open
   http://localhost:8983/solr/ in your web browser.

#. Finally, change the :ref:`solr_url` setting in your
   /etc/ckan/|ckan|/development.ini or /etc/ckan/|ckan|/production.ini file to
   point to your new Solr core:

   .. parsed-literal::

    solr_url = http://127.0.0.1:8983/solr/|core|

If you have trouble when setting up Solr, see
:ref:`multicore solr troubleshooting`.


.. _multicore solr troubleshooting:

--------------------------------------
Multicore |solr| setup troubleshooting
--------------------------------------

.. seealso::

   :ref:`Troubleshooting for single-core Solr setups <solr troubleshooting>`
     Most of these tips also apply to multi-core setups.

No cores shown on |solr| index page
===================================

If no cores are shown when you visit the |solr| index page, and the admin
interface returns a 404 error, check the web server error log
(``/var/log/jetty/<date>.stderrout.log`` if you're using Jetty, or
``/var/log/tomcat6/catalina.<date>.log`` for Tomcat). If you can find an error
similar to this one::

 WARNING: [iatiregistry.org] Solr index directory '/usr/share/solr/iatiregistry.org/data/index' doesn't exist. Creating new index...
 07-Dec-2011 18:06:33 org.apache.solr.common.SolrException log
 SEVERE: java.lang.RuntimeException: Cannot create directory: /usr/share/solr/iatiregistry.org/data/index
 [...]

Then ``dataDir`` is not properly configured. With our setup the data directory
should be under ``/var/lib/solr/data``. Make sure that you defined the correct
``dataDir`` in the ``solr.xml`` file and that in the ``solrconfig.xml`` file
you have the following configuration option::

    <dataDir>${dataDir}</dataDir>
