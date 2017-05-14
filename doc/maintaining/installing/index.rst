---------------
Installing CKAN
---------------

Before you can use CKAN on your own computer, you need to install it. There are
three ways to install CKAN:

#. Install from an operating system package
#. Install from source

From package is the quickest and easiest way to install CKAN, but it requires
Ubuntu 14.04 64-bit or Ubuntu 12.04 64-bit. **You should install CKAN from package if**:

* You want to install CKAN on an Ubuntu 14.04 or 12.04, 64-bit server, *and*
* You only want to run one CKAN website per server

See :doc:`install-from-package`.

**You should install CKAN from source if**:

* You want to install CKAN on a 32-bit computer, *or*
* You want to install CKAN on a different version of Ubuntu, not 14.04 or 12.04, *or*
* You want to install CKAN on another operating system
  (eg. RHEL, CentOS, OS X), *or*
* You want to run multiple CKAN websites on the same server, *or*
* You want to install CKAN for development

See :doc:`install-from-source`.

If you've already setup a CKAN website and want to upgrade it to a newer
version of CKAN, see :doc:`/maintaining/upgrading/index`.


.. note::
   There **used** to be an 'official' Docker install of CKAN.  There are legacy
   docker images at https://hub.docker.com/u/ckan/ which are not maintained and
   use out-of-date unpatched versions of CKAN. Information about them is
   archived here:
   <https://github.com/ckan/ckan/blob/4a3b375/doc/maintaining/installing/install-using-docker.rst>

------------

.. toctree::
   :maxdepth: 1

   install-from-package
   install-from-source
   deployment
