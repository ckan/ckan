---------------
Installing CKAN
---------------

Before you can use CKAN on your own computer, you need to install it. There are
two ways to install CKAN, from package, or from source.

From package is the quickest and easiest way to install CKAN, but it requires
Ubuntu 12.04 64-bit. **You should install CKAN from package if**:

* You want to install CKAN on an Ubuntu 12.04, 64-bit server, *and*
* You only want to run one CKAN website per server, *and*
* You want to run CKAN, |solr| and |postgres| on the same server

See :doc:`install-from-package`.

**You should install CKAN from source if**:

* You want to install CKAN on a 32-bit computer, *or*
* You want to install CKAN on a different version of Ubuntu, not 12.04, *or*
* You want to install CKAN on another operating system
  (eg. RedHat, CentOS, OS X), *or*
* You want to run multiple CKAN websites on the same server, *or*
* You want to run CKAN, |solr| and |postgres| on different servers, *or*
* You want to install CKAN for development

See :doc:`install-from-source`.

If you've already setup a CKAN website and want to upgrade it to a newer
version of CKAN, see :doc:`upgrading`.

------------

.. toctree::
   :maxdepth: 1

   install-from-package
   install-from-source
   deployment
