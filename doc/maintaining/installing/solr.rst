:orphan:

CKAN uses Solr_ as its search platform, and uses a customized Solr schema file
that takes into account CKAN's specific search needs. Now that we have CKAN
installed, we need to install and configure Solr.

.. _Solr: http://lucene.apache.org/solr/

.. note::

   These instructions explain how to deploy Solr using the Jetty web
   server, but CKAN doesn't require Jetty - you can deploy Solr to another web
   server, such as Tomcat, if that's convenient on your operating system.

#. Edit the Jetty configuration file (``/etc/default/jetty8`` or
   ``/etc/default/jetty``) and change the following variables::

    NO_START=0            # (line 4)
    JETTY_HOST=127.0.0.1  # (line 16)
    JETTY_PORT=8983       # (line 19)

   .. note::

    This ``JETTY_HOST`` setting will only allow connections from the same machine.
    If CKAN is not installed on the same machine as Jetty/Solr you will need to
    change it to the relevant host or to 0.0.0.0 (and probably set up your firewall
    accordingly).

   Start or restart the Jetty server.

   For Ubuntu 16.04::

    sudo service jetty8 restart

   Or for Ubuntu 14.04::

    sudo service jetty restart

   .. note::

    Ignore any warning that it wasn't already running - some Ubuntu
    distributions choose not to start Jetty on install, but it's not important.

   You should now see a welcome page from Solr if you open
   http://localhost:8983/solr/ in your web browser (replace localhost with
   your server address if needed).

   .. note::

    If you get the message ``Could not start Jetty servlet engine because no
    Java Development Kit (JDK) was found.`` then you will have to edit the
    ``JAVA_HOME`` setting in ``/etc/default/jetty`` to point to your machine's
    JDK install location. For example::

        JAVA_HOME=/usr/lib/jvm/java-6-openjdk-amd64/

    or::

        JAVA_HOME=/usr/lib/jvm/java-6-openjdk-i386/

#. Replace the default ``schema.xml`` file with a symlink to the CKAN schema
   file included in the sources.

   .. parsed-literal::

      sudo mv /etc/solr/conf/schema.xml /etc/solr/conf/schema.xml.bak
      sudo ln -s |virtualenv|/src/ckan/ckan/config/solr/schema.xml /etc/solr/conf/schema.xml

   Now restart Solr:

   For Ubuntu 16.04::

    sudo service jetty8 restart

   or for Ubuntu 14.04::

    sudo service jetty restart

   Check that Solr is running by opening http://localhost:8983/solr/.


#. Finally, change the :ref:`solr_url` setting in your :ref:`config_file` (|production.ini|) to
   point to your Solr server, for example::

       solr_url=http://127.0.0.1:8983/solr

