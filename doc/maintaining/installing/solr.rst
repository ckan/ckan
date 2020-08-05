:orphan:

CKAN uses Solr_ as its search platform, and uses a customized Solr schema file
that takes into account CKAN's specific search needs. Now that we have CKAN
installed, we need to install and configure Solr.

.. _Solr: http://lucene.apache.org/solr/

.. note::

   These instructions explain how to deploy Solr using the Tomcat web
   server, but CKAN doesn't require Tomcat - you can deploy Solr to another web
   server, such as Jetty, if that's convenient on your operating system.

#. Change the default port Tomcat runs on (8080) to the one expected by CKAN. To do so change the following line in the ``/etc/tomcat9/server.xml`` file (``tomcat8`` in older Ubuntu versions)::

        From:

        <Connector port="8080" protocol="HTTP/1.1"


        To:

        <Connector port="8983" protocol="HTTP/1.1"


   .. note:: This is not required by CKAN, you can keep the default Tomcat port or use a different one, just make sure to update the :ref:`solr_url` setting in your :ref:`config_file` accordingly.

#. Replace the default ``schema.xml`` file with a symlink to the CKAN schema
   file included in the sources.

   .. parsed-literal::

      sudo mv /etc/solr/conf/schema.xml /etc/solr/conf/schema.xml.bak
      sudo ln -s |virtualenv|/src/ckan/ckan/config/solr/schema.xml /etc/solr/conf/schema.xml

#. Now restart Solr (use ``tomcat8`` on older Ubuntu versions)::

    sudo service tomcat9 restart

   Check that Solr is running by opening http://localhost:8983/solr/

   .. note:: On Ubuntu 18.04 and older, instead of the Solr UI you may see an Internal Server Error page with a message containing:

   .. parsed-literal::

    java.io.IOException: Cannot create directory: /var/lib/solr/data/index

   This is caused by a `bug <https://bugs.launchpad.net/ubuntu/+source/lucene-solr/+bug/1829611>`_ and you need to run some extra commands to fix it:


   .. parsed-literal::

        sudo mv /etc/systemd/system/tomcat9.d /etc/systemd/system/tomcat9.service.d
        sudo systemctl daemon-reload
        sudo service tomcat9 restart


#. Finally, change the :ref:`solr_url` setting in your :ref:`config_file` (|ckan.ini|) to point to your Solr server, for example::

       solr_url=http://127.0.0.1:8983/solr
