:huérfano:

.. nota::

    If you are facing a problem in case postgresql is not running, 
    execute the command ``sudo service postgresql start`` 

Comprueba que |postgres| se instaló correctamente al enumerar las bases de datos existentes:

    sudo -u postgres psql -l

Comprobar que la codificación de las bases de datos es `UTF8`, si no, es posible que encuentre problemas más adelante
con la internacionalización. Desde que se cambió la codificación de |postgres| puede significar
eliminar las bases de datos existentes, se sugiere que esto se corrija antes de continuar con
la instalación de CKAN.

A continuación, deberá crear un usuario de base de datos si aún no existe uno.
Cree un nuevo |postgres| el usuario llamó a |database_user| e introduzca un
contraseña para el usuario cuando se le solicite. Necesitarás esta contraseña más adelante:

.. parsed-literal::

    sudo -u postgres createuser -S -D -R -P |database_user|

Cree un nuevo |postgres| base de datos, denominada |base de datos|, propiedad de la
usuario de base de datos que acaba de crear:

.. parsed-literal::

    sudo -u postgres createdb -O |database_user| |database| -E utf-8

.. nota::

    If PostgreSQL is run on a separate server, you will need to edit
    `postgresql.conf` and `pg_hba.conf`. On Ubuntu, these
    files are located in `etc/postgresql/{Postgres version}/main`.

    Uncomment the `listen_addresses` parameter and specify a comma-separated
    list of IP addresses of the network interfaces PostgreSQL should listen on
    or '*' to listen on all interfaces. For example,

    ``listen_addresses = 'localhost,192.168.1.21'``

    Add a line similar to the line below to the bottom of `pg_hba.conf` to
    allow the machine running the web server to connect to PostgreSQL. Please change
    the IP address as desired according to your network settings.

    ``host    all             all             192.168.1.22/32                 md5``
