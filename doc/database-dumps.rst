Database Dumps
==============

It's often useful to allow users to download a complete CKAN database in a dumpfile.

In addition, a CKAN administrator would like to easily backup and restore a CKAN database.

Creating a Dump
-----------------

We provide two ``paster`` methods to create dumpfiles.

* ``db simple-dump-json`` - A simple dumpfile, useful to create a public listing of the datasets with no user information. All datasets are dumped, including deleted datasets and ones with strict authorization. These may be in JSON or CSV format.
* ``db dump`` -  A more complicated dumpfile, useful for backups. Replicates the database completely, including users, their personal info and API keys, and hence should be kept private. This is in the format of SQL commands.

For more information on paster, see :doc:`paster`.

Using db simple-dump-json 
+++++++++++++++++++++++++

If you are using a Python environment, as part of a development installation, first enable the environment::

 . /home/okfn/var/srvc/ckan.net/pyenv/bin/activate || exit 1

Then create and zip the dumpfile::

 paster --plugin=ckan db simple-dump-json /var/srvc/ckan/dumps/ckan.net-daily.json --config=/etc/ckan/std/std.ini
 gzip /var/srvc/ckan/dumps/ckan.net-daily.json

Change ``simple-dump-json`` to ``simple-dump-csv`` if you want CSV format instead of JSON. 

Backing up - db dump
++++++++++++++++++++

If you are using a Python environment, as part of a development installation, first enable the environment::

 . /var/srvc/ckan/pyenv/bin/activate || exit 1

Then create and zip the dumpfile::

 paster --plugin=ckan db dump /var/srvc/ckan/dumps/ckan.net-daily --config=/etc/ckan/std/std.ini
 gzip /var/srvc/ckan/dumps/ckan.net-daily

Restoring a database - db load
++++++++++++++++++++++++++++++

To restore the dump to the database, us ``db load``. 

You either need a freshly created database (i.e. using createdb) or take the existing one and clean (wipe) it::

 paster --plugin=ckan db clean --config=/etc/ckan/std/std.ini

Now you can 'db load' the dump file::

 paster --plugin=ckan db load /var/srvc/ckan/dumps/ckan.net-daily --config=/etc/ckan/std/std.ini


Daily Dumps
-----------

You can set the dump(s) to be created daily with a cron job.

Edit your user's cron config::

 $ crontab -e

Now add a line such as this::

 0 21 * * * /home/okfn/var/srvc/ckan.net/dump.sh

Now create the dump.sh to contain the paster db dump command from above.

Serving the Files
-----------------

Some simple additions to the Apache config can serve the files to users in a directory listing. This is ideal for the JSON/CSV simple dumps, but obviously not ideal for the SQL dump containing private user information.

To do this, add these lines to your virtual host config (e.g. ``/etc/apache2/sites-enabled/ckan.net``)::

    Alias /dump/ /home/okfn/var/srvc/ckan.net/dumps/

    # Disable the mod_python handler for static files
    <Location /dump>
        SetHandler None
        Options +Indexes
    </Location>
