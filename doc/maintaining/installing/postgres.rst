:orphan:

Check that |postgres| was installed correctly by listing the existing databases::

    sudo -u postgres psql -l

Check that the encoding of databases is ``UTF8``, if not internationalisation
may be a problem. Since changing the encoding of |postgres| may mean deleting
existing databases, it is suggested that this is fixed before continuing with
the CKAN install.

Next you'll need to create a database user if one doesn't already exist.
Create a new |postgres| database user called |database_user|, and enter a
password for the user when prompted. You'll need this password later:

.. parsed-literal::

    sudo -u postgres createuser -S -D -R -P |database_user|

Create a new |postgres| database, called |database|, owned by the
database user you just created:

.. parsed-literal::

    sudo -u postgres createdb -O |database_user| |database| -E utf-8

.. note::

    If PostgreSQL is run on a separate server, you will need to edit
    `postgresql.conf` and `pg_hba.conf`. For PostgreSQL 9.1 on Ubuntu, these
    files are located in `etc/postgresql/9.1/main`.

    Uncomment the `listen_addresses` parameter and specify a comma-separated
    list of IP addresses of the network interfaces PostgreSQL should listen on
    or '*' to listen on all interfaces. For example,

    ``listen_addresses = 'localhost,192.168.1.21'``

    Add a line similar to the line below to the bottom of `pg_hba.conf` to
    allow the machine running Apache to connect to PostgreSQL. Please change
    the IP address as desired according to your network settings.

    ``host    all             all             192.168.1.22/32                 md5``

