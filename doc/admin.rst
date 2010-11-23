Administrators and User Rights
==============================

CKAN allows for certain users to be given administrative rights, i.e. to perform all actions irrespective of their object-specific permissions. 


Creating and Removing Admins via the Command Line
-------------------------------------------------

If you have CKAN installed, a ``paster`` command line utility will allow you to create new administrators or to remove administrative privileges from existing users. To add an administrator, run::

 paster --plugin=ckan sysadmin -c my.ckan.net.ini create USERNAME

Where ``my.ckan.net.ini`` is the name of the configuration file you wish to use. If you've checked out the source code and are developing, you can also execute the same command in the base directory, dropping the ``--plugin`` argument. 

Removing administrative access from users works the same::

 paster --plugin=ckan sysadmin -c my.ckan.net.ini remove USERNAME


