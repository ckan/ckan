Database Dumps
==============

It's often useful to allow users to download a complete CKAN database in a dumpfile. 

For example, you can download ckan.net's daily dump at: http://ckan.net/dump/ in JSON format. The file is called ``ckan.net-daily.json.gz``.

Creating a Dump
-----------------

Your dump script needs to run the ``paster`` command. If you are using a Python environment, as part of a development installation, it should also enable the environment.

For example, you could create ``/home/okfn/var/srvc/ckan.net/dump.sh`` as follows::

 . /home/okfn/var/srvc/ckan.net/pyenv/bin/activate || exit 1
 paster --plugin=ckan db simple-dump-json /home/okfn/var/srvc/ckan.net/dumps/ckan.net-daily.json --config=/home/okfn/var/srvc/ckan.net/ckan.net.ini
 gzip /home/okfn/var/srvc/ckan.net/dumps/ckan.net-daily.json

Change ``simple-dump-json`` to ``simple-dump-csv`` if you want CSV format instead of JSON. 

These dump functions dump the entire database as it is stored in CKAN, omitting user account details.

Daily Dumps
-----------

You can set the dump to be created daily with a cron job.

Edit your user's cron config::

 $ crontab -e

Now add a line such as this::

 0 21 * * * /home/okfn/var/srvc/ckan.net/dump.sh

Serving the Files
-----------------

Some simple additions to the Apache config can serve the files to users in a directory listing. 

To do this, add these lines to your virtual host config (e.g. `/etc/apache2/sites-enabled/ckan.net`)::

    Alias /dump/ /home/okfn/var/srvc/ckan.net/dumps/

    # Disable the mod_python handler for static files
    <Location /dump>
        SetHandler None
        Options +Indexes
    </Location>
