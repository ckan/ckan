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

   Your CKAN instance should be upgraded straight away.

   .. note::

      If you have changed the |apache|, |nginx| or ``who.ini`` configuration
      files, you will get a prompt like the following, asking whether to keep
      your local changes or replace the files. You generally would like to keep
      your local changes (option ``N``, which is the default), but you can look
      at the differences between versions by selecting option ``D``::

       Configuration file `/etc/apache2/sites-available/ckan_default'
        ==> File on system created by you or by a script.
        ==> File also in package provided by package maintainer.
          What would you like to do about it ?  Your options are:
           Y or I  : install the package maintainer's version
           N or O  : keep your currently-installed version
             D     : show the differences between the versions
             Z     : start a shell to examine the situation
        The default action is to keep your current version.
       *** ckan_default (Y/I/N/O/D/Z) [default=N] ?

      Your local CKAN configuration file in |config_dir| will not be replaced.

   .. note::

     The install process will uninstall any existing CKAN extensions or other
     libraries located in the ``src`` directory of the CKAN virtualenv. To
     enable them again, the installation process will iterate all folders in
     the ``src`` directory, reinstall the requirements listed in
     ``pip-requirements.txt`` and ``requirements.txt`` files and run
     ``python setup.py develop`` for each. If you are using a custom extension
     which does not use this requirements file names or is located elsewhere,
     you will need to manually reenable it.


#. Finally, restart uWSGI and Nginx:

   .. parsed-literal::

    |restart_uwsgi|
    sudo service nginx restart

#. You're done!

You should now be able to visit your CKAN website in your web browser and see
that it's running the new version of CKAN.

