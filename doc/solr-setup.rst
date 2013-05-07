.. _setting up solr:

===============
Setting up Solr
===============

CKAN uses Solr_ as search platform. This document describes different
topics related with the deployment and management of Solr from a CKAN
point of view.

.. _Solr: http://lucene.apache.org/solr/

CKAN uses customized schema files that take into account its specific
search needs. Different versions of the schema file are found in
``ckan/ckan/config/solr``

The following instructions apply to Ubuntu 12.04 (Precise), the recommended
platform by the CKAN team. Other versions or distributions may need
slightly different instructions.

.. note::

    The following instructions deploy Solr on the Jetty server, but CKAN does
    not require it, you can use Tomcat if that is more convenient on your
    distribution.


.. _solr-single:

Single Solr instance
--------------------

In this case, there will be only one Solr endpoint that uses a single schema file.
This can be useful for a Solr server used by only a single CKAN instance, or
different instances that share the same schema version.

To install Solr (if you are following the :doc:`install-from-source` or
:doc:`install-from-package` instructions, you already did this)::

 sudo apt-get install solr-jetty openjdk-6-jdk

You'll need to edit the Jetty configuration file (``/etc/default/jetty``) with
the suitable values::

 NO_START=0            # (line 4)
 JETTY_HOST=127.0.0.1  # (line 15)
 JETTY_PORT=8983       # (line 18)

Start the Jetty server::

 sudo service jetty start

You should see welcome page from Solr when visiting (replace localhost with your
server address if needed)::

 http://localhost:8983/solr/

and the admin site::

 http://localhost:8983/solr/admin

.. note::

    If you get the message ``Could not start Jetty servlet engine because no
    Java Development Kit (JDK) was found.`` then you will have to edit the
    ``JAVA_HOME`` setting in ``/etc/default/jetty`` to point to your machine's
    JDK install location. For example::

        JAVA_HOME=/usr/lib/jvm/java-6-openjdk-amd64/

    or::

        JAVA_HOME=/usr/lib/jvm/java-6-openjdk-i386/

This default setup will use the following locations in your file system:

``/usr/share/solr``
  Solr home, with a symlink pointing to the configuration dir in ``/etc``.
``/etc/solr/conf``
  Solr configuration files. The more important ones are ``schema.xml`` and 
  ``solrconfig.xml``.
``/var/lib/solr/data/``
  This is where the index files are physically stored.

You will obviously need to replace the default ``schema.xml`` file with the
CKAN one. To do so, create a symbolic link to the schema file in the config
folder.  Use the latest schema version supported by the CKAN version you are
installing (it will generally be the highest one):

.. parsed-literal::

 sudo mv /etc/solr/conf/schema.xml /etc/solr/conf/schema.xml.bak
 sudo ln -s |virtualenv|/src/ckan/ckan/config/solr/schema-2.0.xml /etc/solr/conf/schema.xml

Now restart jetty::

 sudo service jetty restart

And check that Solr is running by browsing http://localhost:8983/solr/ which should offer the Administration link.


.. _solr-multi-core:

Multiple Solr cores
-------------------

Solr can also be set up to have multiple configurations and indexes on the
same instance. This is specially useful when you want other applications than CKAN
or different CKAN versions to use the same Solr instance. The different cores
will have different paths in the Solr server URL::

 http://localhost:8983/solr/ckan-schema-1.2       # Used by CKAN up to 1.5
 http://localhost:8983/solr/ckan-schema-1.3       # Used by CKAN 1.5.1
 http://localhost:8983/solr/ckan-schema-1.4       # Used by CKAN 1.7
 http://localhost:8983/solr/ckan-schema-2.0       # Used by CKAN 2.0
 http://localhost:8983/solr/some-other-site  # Used by another site

To set up a multicore Solr instance, repeat the steps on the previous section
to configure a single Solr instance.

Create a ``solr.xml`` file in ``/usr/share/solr``. This file will list the
different cores, and allows also to define some configuration options.
This is how cores are defined::

    <solr persistent="true" sharedLib="lib">
        <cores adminPath="/admin/cores">
            <core name="ckan-schema-1.4" instanceDir="ckan-schema-1.4">
                <property name="dataDir" value="/var/lib/solr/data/ckan-schema-1.4" />
            </core>
            <core name="ckan-schema-2.0" instanceDir="ckan-schema-2.0"> 
                <property name="dataDir" value="/var/lib/solr/data/ckan-schema-2.0" />
            </core>
        </cores>
    </solr>

Adjust the names to match the CKAN schema versions you want to run.

Note that each core is configured with its own data directory. This is really important to prevent conflicts between cores. Now create them like this::

    sudo -u jetty mkdir /var/lib/solr/data/ckan-schema-1.4
    sudo -u jetty mkdir /var/lib/solr/data/ckan-schema-2.0

For each core, we will create a folder in ``/usr/share/solr``,
with a symbolic link to a specific configuration folder in ``/etc/solr/``.
Copy the existing conf directory to the core directory and link it from
the home dir like this::

    sudo mkdir /etc/solr/ckan-schema-1.4
    sudo mv /etc/solr/conf /etc/solr/ckan-schema-1.4/

    sudo mkdir /usr/share/solr/ckan-schema-1.4
    sudo ln -s /etc/solr/ckan-schema-1.4/conf /usr/share/solr/ckan-schema-1.4/conf

Now configure the core to use the data directory you have created. Edit ``/etc/solr/ckan-schema-1.4/conf/solrconfig.xml`` and change the ``<dataDir>`` to this variable::

    <dataDir>${dataDir}</dataDir>

This will ensure the core uses the data directory specified earlier in ``solr.xml``.

Once you have your first core configured, to create new ones, you just need to
add them to the ``solr.xml`` file and copy the existing configuration dir::

    sudo mkdir /etc/solr/ckan-schema-2.0
    sudo cp -R /etc/solr/ckan-schema-1.4/conf /etc/solr/ckan-schema-2.0

    sudo mkdir /usr/share/solr/ckan-schema-2.0
    sudo ln -s /etc/solr/ckan-schema-2.0/conf /usr/share/solr/ckan-schema-2.0/conf

Remember to ensure that each core points to the correct CKAN schema. To link
each schema to the relevant file on the CKAN source use the following:

.. parsed-literal::

    sudo rm /etc/solr/ckan-schema-2.0/conf/schema.xml 
    sudo ln -s |virtualenv|/src/ckan/ckan/config/solr/schema-2.0.xml /etc/solr/ckan-schema-2.0/conf/schema.xml

Now restart jetty::

 sudo service jetty restart

And check that Solr is listing all the cores when browsing http://localhost:8983/solr/

Troubleshooting
---------------

Solr requests and errors are logged in the web server log.

* For jetty servers, they are located in::

    /var/log/jetty/<date>.stderrout.log

* For Tomcat servers, they are located in::

    /var/log/tomcat6/catalina.<date>.log

Some problems that can be found during the install:

* When setting up a multi-core Solr instance, no cores are shown when visiting the
  Solr index page, and the admin interface returns a 404 error.

  Check the web server error log if you can find an error similar to this one::

      WARNING: [iatiregistry.org] Solr index directory '/usr/share/solr/iatiregistry.org/data/index' doesn't exist. Creating new index...
      07-Dec-2011 18:06:33 org.apache.solr.common.SolrException log
      SEVERE: java.lang.RuntimeException: Cannot create directory: /usr/share/solr/iatiregistry.org/data/index
            [...]

  The ``dataDir`` is not properly configured. With our setup the data directory should
  be under ``/var/lib/solr/data``. Make sure that you defined the correct ``dataDir``
  in the ``solr.xml`` file and that in the ``solrconfig.xml`` file you have the
  following configuration option::

    <dataDir>${dataDir}</dataDir>

* When running Solr it says ``Unable to find a javac compiler; com.sun.tools.javac.Main is not on the classpath. Perhaps JAVA_HOME does not point to the JDK.``

  See the note above about ``JAVA_HOME``. Alternatively you may not have installed the JDK. Check by seeing if javac is installed::

     which javac

  If it isn't do::

     sudo apt-get install openjdk-6-jdk

  and restart Solr.

Handling changes in the CKAN schema
-----------------------------------

At some point, changes in new CKAN versions will mean modifications in the schema
to support new features or fix defects. These changes won't be always backwards
compatible, so some changes in the Solr servers will need to be performed.

If a CKAN instance is using a Solr server for itself, the schema can just be updated
on the Solr server and the index rebuilt. But if a Solr server is shared between
different CKAN instances, there may be conflicts if the schema is updated.

CKAN uses the following conventions for supporting different schemas:

* If needed, create a new schema file when releasing a new version of CKAN (i.e if there
  are two or more different modifications in the schema file between CKAN releases,
  only one new schema file is created).

* Keep different versions of the Solr schema in the CKAN source, with a naming convention,
  `schema-<version>.xml`::

    ckan/config/solr/schema-1.2.xml
    ckan/config/solr/schema-1.3.xml
    ckan/config/solr/schema-2.0.xml

* Each new version of the schema file must include its version in the main `<schema>` tag::

    <schema name="ckan" version="2.0">

* Solr servers used by more than one CKAN instance should be configured as multiple cores,
  and provide a core for each schema version needed. The cores should be named following the
  convention `schema-<version>`, e.g.::

    http://<solr-server>/solr/ckan-schema-1.4/
    http://<solr-server>/solr/ckan-schema-2.0/

When a new version of the schema becomes available, a new core is created, with a link to the
latest schema.xml file in the CKAN source. That way, CKAN instances that use an older version
of the schema can still point to the core that uses it, while more recent versions can point
to the latest one. When old versions of CKAN are updated, they only need to change their
:ref:`solr_url` setting to point to the suitable Solr core.
