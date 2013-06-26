=========================================================
Upgrading a CKAN 2 package install to a new patch release
=========================================================

.. note::

   Before upgrading CKAN you should check the compatibility of any custom
   themes or extensions you're using, check the changelog, and backup your
   database. See :ref:`upgrading`.

:ref:`Patch releases <releases>` are distributed in the same package as the
minor release they belong to, so for example CKAN ``2.0``, ``2.0.1``,
``2.0.2``, etc.  will all be installed using the CKAN ``2.0`` package
(``python-ckan_2.0_amd64.deb``):

#. Download the CKAN package::

    wget http://packaging.ckan.org/python-ckan_2.0_amd64.deb

   You can check the actual CKAN version from a package running the following
   command::

    dpkg --info python-ckan_2.0_amd64.deb

   Look for the ``Version`` field in the output::

    ...
    Package: python-ckan
    Version: 2.0.1-3
    ...

#. Install the package with the following command::

    sudo dpkg -i python-ckan_2.0_amd64.deb

   This will **not** replace or modify any configuration files that you already
   have on the server, including the CKAN config file or any |apache| or
   |nginx| configuration files.

   Your CKAN instance should be upgraded straight away.

   .. note::

      When upgrading from 2.0 to 2.0.1 you may see some vdm related warnings
      when installing the package::

        dpkg: warning: unable to delete old directory '/usr/lib/ckan/default/src/vdm': Directory not empty

      These are due to vdm not longer being installed from source. You can
      ignore them and delete the folder manually if you want.

#. You're done!

You should now be able to visit your CKAN website in your web browser and see
that it's running the new version of CKAN.

