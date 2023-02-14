.. include:: /_substitutions.rst

# ============================&#xD;&#xA;Instalación de CKAN desde el paquete

En esta sección se describe cómo instalar CKAN desde el paquete. Este es el más rápido
y la forma más fácil de instalar CKAN, pero requiere **Ubuntu 18.04 o 20.04 de 64 bits**. Si
no está utilizando ninguna de estas versiones de Ubuntu, o si está instalando CKAN para
desarrollo, debe seguir :d oc:`install-from-source` en lugar de.

Al final del proceso de instalación, terminará con dos web en ejecución
aplicaciones, la propia CKAN y el DataPusher, un servicio separado para
importar datos a :d oc de CKAN:`/maintaining/datastore`. Además, habrá un proceso que ejecutará el trabajador para ejecutar :d oc:`/maintaining/background-tasks`. Todos estos procesos serán gestionados por `Supervisor <https://supervisord.org/>`\_.

Para las instalaciones de Python 3, la versión mínima de Python requerida es 3.6.

*   **Ubuntu 20.04** Incluye **Python 3.8** como parte de su distribución
*   **Ubuntu 18.04** Incluye **Python 3.6** como parte de su distribución

Requisitos de puertos host:

    +------------+------------+-----------+
    | Service    | Port       | Used for  |
    +============+============+===========+
    | NGINX      | 80         | Proxy     |
    +------------+------------+-----------+
    | uWSGI      | 8080       | Web Server|
    +------------+------------+-----------+
    | uWSGI      | 8800       | DataPusher|
    +------------+------------+-----------+
    | Solr/Jetty | 8983       | Search    |
    +------------+------------+-----------+
    | PostgreSQL | 5432       | Database  |
    +------------+------------+-----------+
    | Redis      | 6379       | Search    |
    +------------+------------+-----------+

.. \_run-package-installer:

***

1.  Instalar el paquete CKAN

***

En su sistema Ubuntu, abra un terminal y ejecute estos comandos para instalar
CKAN:

\#. Actualice el índice de paquetes de Ubuntu:

    sudo apt update

\#. Instale los paquetes de Ubuntu que CKAN requiere (y 'git', para permitirle instalar extensiones CKAN)::

    sudo apt install -y libpq5 redis-server nginx supervisor

\#. Descargue el paquete CKAN:

    - On Ubuntu 18.04:

       .. parsed-literal::

           wget \https://packaging.ckan.org/|latest_package_name_bionic|

     - On Ubuntu 20.04, for Python 3 (recommended):

       .. parsed-literal::

           wget \https://packaging.ckan.org/|latest_package_name_focal_py3|

\#. Instale el paquete CKAN:

*   En Ubuntu 18.04:

    .. parsed-literal::

          sudo dpkg -i |latest_package_name_bionic|

*   En Ubuntu 20.04, para Python 3:

    .. parsed-literal::

          sudo dpkg -i |latest_package_name_focal_py3|

***

2.  Instalar y configurar PostgreSQL

***

.. Propina::

Puede instalar |postgres| y CKAN en diferentes servidores. Justo
cambiar el :ref:`sqlalchemy.url` configuración en su
|ckan.ini| para hacer referencia a su |postgres| servidor.

.. nota::

Los comandos mencionados a continuación se prueban para el sistema Ubuntu

Instale |postgres|, ejecutando este comando en un terminal:

    sudo apt install -y postgresql

.. include:: postgres.rst

Edite el :ref:`sqlalchemy.url` en su :ref:`config_file` (|ckan.ini|) archivo y
establecer la contraseña, la base de datos y el usuario de la base de datos correctos.

***

3.  Instalar y configurar Solr

***

.. Propina::

Puede instalar |solr| y CKAN en diferentes servidores. Justo
cambiar el :ref:`solr_url` configuración en su
|producción.ini| |ckan.ini| para hacer referencia a su |solr| servidor.

.. incluye:: solr.rst

***

4.  Actualizar la configuración e inicializar la base de datos

***

\#. Edite el :ref:`config_file` (|ckan.ini|) para configurar las siguientes opciones:

    site_id
      Each CKAN site should have a unique ``site_id``, for example::

        ckan.site_id = default

    site_url
      Provide the site's URL. For example::

        ckan.site_url = http://demo.ckan.org

\#. Inicialice la base de datos CKAN ejecutando este comando en un terminal:

    sudo ckan db init

\#. Opcionalmente, configure datastore y DataPusher siguiendo el
instrucciones en :d oc:`/maintaining/datastore`.

\#. También opcionalmente, puede habilitar las cargas de archivos siguiendo el
instrucciones en :d oc:`/maintaining/filestore`.

***

5.  Inicie el servidor web y reinicie Nginx

***

Vuelva a cargar el demonio Supervisor para que se recojan los nuevos procesos:

    sudo supervisorctl reload

Después de unos segundos ejecute el siguiente comando para comprobar el estado de los procesos:

    sudo supervisorctl status

Debería ver tres procesos ejecutándose sin errores:

    ckan-datapusher:ckan-datapusher-00   RUNNING   pid 1963, uptime 0:00:12
    ckan-uwsgi:ckan-uwsgi-00             RUNNING   pid 1964, uptime 0:00:12
    ckan-worker:ckan-worker-00           RUNNING   pid 1965, uptime 0:00:12

Si algunos de los procesos informan de un error, asegúrese de haber ejecutado todos los pasos anteriores y compruebe los registros ubicados en `/var/log/ckan` para más detalles.

Reinicie Nginx ejecutando este comando:

    sudo service nginx restart

***

6.  ¡Ya está!

***

Abra http://localhost en su navegador web. Deberías ver el frente CKAN
página, que se verá algo como esto:

.. imagen :: /images/9.png
:ancho: 807px

|

Ahora puede pasar a :d oc:`/maintaining/getting-started` para empezar a usar y personalizar
su sitio CKAN.

.. Nota:: La configuración de autorización predeterminada en una nueva instalación es deliberada
restrictivo. Los usuarios habituales no podrán crear conjuntos de datos u organizaciones.
Debe verificar el :d oc:`/maintaining/authorization` documentación, configure CKAN en consecuencia
y conceder a otros usuarios los permisos pertinentes mediante el :ref:`sysadmin account <create-admin-user>`.

.. nota::

Puede haber un `PermissionError: [Errno 13] Permission denied:` mensaje al reiniciar el supervisor o
accediendo a CKAN a través de un navegador por primera vez. Esto sucede cuando se utiliza un usuario diferente para ejecutar
el proceso del servidor web que el usuario que instaló CKAN y el software de soporte. Una solución alternativa sería
Abra los permisos en el cuadro de diálogo `/usr/lib/ckan/default/src/ckan/ckan/public/base/i18n/` directorio
para que este usuario pudiera escribir los archivos .js en él. El acceso a CKAN generará estos archivos para un nuevo
instalar, o podría ejecutar `ckan -c /etc/ckan/default/ckan.ini translation js` para generarlos explícitamente.
