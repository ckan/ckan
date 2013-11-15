==========================
Creating another Solr core
==========================

If you have multiple different versions of CKAN running on the same machine, or
even if you have two CKAN sites running the same version of CKAN on the same
machine, you'll probably want each CKAN instance to have its own Solr core.
Having a separate Solr core for each CKAN instance means that the instances can
use different ``schema.xml`` files (required if they use different versions of
CKAN that have different schema files, or if they use different schema file
customizations).


.. The name of the second CKAN instance that we're going to setup a second core
   for:
.. |ckan| replace:: my-second-ckan-instance

.. The name of the second CKAN core we're going to set up:
.. |core| replace:: my-second-solr-core

In this example we'll assume you've installed a second instance of CKAN in a
second virtual environment at /usr/lib/ckan/|ckan|, and now want to setup a
second Solr core for it. (You can ofcourse follow these instructions again to
setup further Solr cores.) If you followed the :ref:`setup solr` instructions
when installing your first CKAN instance, then to create a second Solr core for
your second CKAN instance:


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
    sudo ln -s /usr/lib/ckan/|ckan|/src/ckan/ckan/config/solr/schema-2.0.xml /etc/solr/|core|/conf/schema.xml

#. Create the /usr/share/solr/|core| directory and put a symlink to the
   ``conf`` directory in it:

   .. parsed-literal::

    sudo mkdir /usr/share/solr/|core|
    sudo ln -s /etc/solr/|core|/conf /usr/share/solr/|core|/conf

#. Restart Jetty::

    sudo service jetty restart

   You should now see both your Solr cores when you open
   http://localhost:8983/solr/ in your web browser.

#. Finally, change the ``solr_url`` setting in your
   /etc/ckan/|ckan|/development.ini or /etc/ckan/|ckan|/production.ini file to
   point to your new Solr core:

   .. parsed-literal::

    solr_url = http://127.0.0.1:8983/solr/|core|

If you have trouble when setting up Solr, see :ref:`solr troubleshooting`.
