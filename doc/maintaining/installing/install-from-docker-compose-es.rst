.. include:: /\_substitutions.rst

# ===================================&#xD;&#xA;Instalación de CKAN con Docker Compose

Este capítulo es un tutorial sobre cómo instalar el último CKAN (master o cualquier versión estable)
con Docker Compose. El escenario que se muestra aquí es uno de los muchos escenarios y entornos posibles
en el que CKAN se puede utilizar con Docker.

Este capítulo tiene como objetivo proporcionar una implementación simple pero totalmente personalizable, más fácil de configurar que
una instalación de origen, más personalizable que una instalación de paquete.

La configuración discutida puede ser útil como un entorno de desarrollo / ensayo; cuidados adicionales tienen que ser
tomado para utilizar esta configuración en producción.

.. nota: Algunas decisiones de diseño son de opinión (ver notas), lo que no significa que el
las alternativas son peores.
Algunas decisiones pueden o no ser adecuadas para escenarios de producción, por ejemplo, el uso de CKAN master.
En particular, este tutorial no utiliza Docker Swarm; Es posible que sea necesario tomar medidas adicionales para adaptarse
la configuración para usar Docker Swarm.

***

1.  Medio ambiente

***

Este tutorial fue probado en Ubuntu 20.04 LTS.
Los hosts pueden ser entornos locales o máquinas virtuales en la nube. Se supone que el usuario tiene acceso directo
(vía terminal/ssh) a los sistemas y permisos root.

un. Almacenamiento

Al usar una máquina virtual basada en la nube, los volúmenes de almacenamiento externo son más baratos que las máquinas virtuales y fáciles de respaldar.
En nuestro caso de uso, utilizamos una máquina virtual basada en la nube con 16 GB de almacenamiento, hemos montado una btrfs de 100 GB con formato btrfs
volumen de almacenamiento externo y symlinked `/var/lib/docker` al volumen externo.
Esto nos permite almacenar la carga voluminosa y / o preciosa: imágenes de Docker, volúmenes de datos de Docker
que contiene las bases de datos CKAN, el almacén de archivos y la configuración, en un servicio más barato.
Por otro lado, un sistema de archivos de instantáneas como btrfs es ideal para realizar copias de seguridad.
La misma consideración de costos podría aplicarse a otros proveedores basados en la nube.

.. Nota:: Esta configuración almacena datos en volúmenes con nombre, asignados a ubicaciones de carpetas que pueden ser
almacenamiento en red o local.
Una alternativa sería reescribir `docker-compose.yml` para asignar el almacenamiento local
directamente, omitiendo volúmenes con nombre. Ambas soluciones guardarán los datos en una ubicación especificada.

Lecturas adicionales: `Docker Volumes <https://docs.docker.com/engine/tutorials/dockervolumes/>`\_.

b. Estibador

Docker se instala en todo el sistema siguiendo el `Docker CE installation guidelines <https://docs.docker.com/engine/installation/linux/docker-ce/ubuntu/>`\_.

Para comprobar una instalación correcta de Docker, ejecute `docker run hello-world`.
`docker version` debe generar versiones para el cliente y el servidor.

c. Docker Compose

Docker Compose se instala en todo el sistema siguiendo el `Docker Compose installation
guidelines <https://docs.docker.com/compose/install/>`\_.
Alternativamente, Docker Compose se puede instalar dentro de un virtualenv,
que estaría completamente separado del virtualenv utilizado dentro del contenedor CKAN, y
tendría que activarse antes de ejecutar los comandos de Docker Compose.

Para comprobar que la instalación correcta de Docker Compose, ejecute `docker-compose version`.

d. Fuente CKAN

Clone CKAN en un directorio de su elección:

    cd /path/to/my/projects
    git clone https://github.com/ckan/ckan.git

Esto utilizará el último maestro CKAN, que puede no ser lo suficientemente estable para el uso de producción.
Para usar una versión estable, retire la etiqueta respectiva, por ejemplo:

    .. parsed-literal::

        git checkout tags/|latest_release_tag|

***

2.  Crear imágenes de Docker

***

En este paso construiremos las imágenes de Docker y crearemos volúmenes de datos de Docker con definidos por el usuario,
configuración confidencial (por ejemplo, contraseñas de base de datos).

un. Configuración confidencial y variables de entorno

Copiar `contrib/docker/.env.template` Para `contrib/docker/.env` y siga las instrucciones
dentro para establecer contraseñas y otras variables sensibles o definidas por el usuario.
Los valores predeterminados funcionarán bien en un entorno de desarrollo en Linux. Para Windows y OSX, el `CKAN_SITE_URL` debe actualizarse.

.. nota:: Lectura relacionada:

*   `Docker-compose .env file <https://docs.docker.com/compose/env-file/>`\_
*   `Environment variables in Compose <https://docs.docker.com/compose/environment-variables/>`\_
*   Los recién llegados a Docker deben leer el excelente artículo en
    `Docker variables <http://vsupalov.com/docker-env-vars/>`\_ por Vladislav Supalov (GitHub @th4t)

b. Crear las imágenes

Dentro del directorio CKAN:

    cd contrib/docker
    docker-compose up -d --build

Para el resto de este capítulo, asumimos que `docker-compose` Todos los comandos se ejecutan dentro
`contrib/docker`Dónde `docker-compose.yml` y `.env` se encuentran.

En las primeras ejecuciones, el contenedor postgres podría necesitar más tiempo para inicializar el clúster de base de datos que
el contenedor ckan esperará. Este lapso de tiempo depende en gran medida de los recursos disponibles del sistema.
Si los registros de CKAN muestran problemas para conectarse a la base de datos, reinicie el contenedor ckan varias veces:

    docker-compose restart ckan
    docker ps | grep ckan
    docker-compose logs -f ckan

.. nota:: Versiones anteriores de `ckan-entrypoint.sh` Se utiliza para esperar y hacer ping al contenedor de base de datos
utilizando credenciales de base de datos detalladas (host, puerto, usuario, contraseña).
Si bien este retraso a veces funcionó, también ofuscó otros posibles problemas.
Sin embargo, el clúster de base de datos debe inicializarse solo una vez y se inicia rápidamente en el siguiente
Funciona. Esta configuración eligió la opción muy obstinada de eliminar el retraso por completo en
favor de fracasar temprano.

Después de este paso, CKAN debería estar ejecutándose en `CKAN_SITE_URL`.

Debe haber cinco contenedores en ejecución (`docker ps`):

*   `ckan`: CKAN con extensiones estándar
*   `db`: Base de datos de CKAN, más tarde también ejecutando la base de datos de CKAN
*   `redis`: Una imagen de Redis preconstruida.
*   `solr`: Una imagen SolR preconstruida configurada para CKAN.
*   `datapusher`: Una imagen CKAN Datapusher preconstruida.

Debe haber cuatro volúmenes Docker con nombre (`docker volume ls | grep docker`). Serán
con el prefijo del nombre del proyecto Docker Compose (valor predeterminado: `docker` o el valor del entorno de host
variable `COMPOSE_PROJECT_NAME`.)

*   `docker_ckan_config`: casa de producción.ini
*   `docker_ckan_home`: hogar de ckan venv y fuente, más tarde también extensiones adicionales de CKAN
*   `docker_ckan_storage`: inicio del almacén de archivos de CKAN (archivos de recursos)
*   `docker_pg_data`: inicio de los archivos de base de datos para las bases de datos predeterminadas y de almacén de datos de CKAN

Es necesario realizar una copia de seguridad de la ubicación de estos volúmenes con nombre en un entorno de producción.
Para migrar datos CKAN entre diferentes hosts, simplemente transfiera el contenido de los volúmenes con nombre.
Un caso de uso detallado de la transferencia de datos se discutirá en el paso 5.

Tiene la opción de usar variables de entorno en lugar de codificar la docker real
nombre del contenedor. Por ejemplo, si desea quitar el nombre del contenedor "db", reemplace "db" por
nombre de la variable de entorno en docker-compose.yml:

     links:
      - db

     depends_on:
      - db

     db:
       container_name: ${POSTGRES_HOST}

c. Conveniencia: rutas a volúmenes con nombre

Los archivos dentro de los volúmenes con nombre residen en una ruta larga en el host.
Puramente por conveniencia, definiremos variables de entorno para estas rutas.
Usaremos un prefijo `VOL_` Para evitar anular variables en `docker-compose.yml`.::

    # Find the path to a named volume
    docker volume inspect docker_ckan_home | jq -c '.[] | .Mountpoint'
    # "/var/lib/docker/volumes/docker_ckan_config/_data"

    export VOL_CKAN_HOME=`docker volume inspect docker_ckan_home | jq -r -c '.[] | .Mountpoint'`
    echo $VOL_CKAN_HOME

    export VOL_CKAN_CONFIG=`docker volume inspect docker_ckan_config | jq -r -c '.[] | .Mountpoint'`
    echo $VOL_CKAN_CONFIG

    export VOL_CKAN_STORAGE=`docker volume inspect docker_ckan_storage | jq -r -c '.[] | .Mountpoint'`
    echo $VOL_CKAN_STORAGE

No necesitaremos acceder a los archivos que contiene `docker_pg_data` directamente, por lo que omitiremos la creación del acceso directo.
Como se muestra más adelante, podemos usar `psql` desde el interior del `ckan` contenedor para ejecutar comandos
contra la base de datos e importar / exportar archivos desde `$VOL_CKAN_HOME`.

***

3.  Almacén de datos y datapusher

***

La base de datos del almacén de datos y el usuario se crean cuando el `db` El contenedor se inicia primero, sin embargo, debemos realizar alguna configuración adicional antes de habilitar la configuración del almacén de datos y el generador de datos en el `production.ini`.

un. Configurar la base de datos del almacén de datos

Con la ejecución de contenedores CKAN, ejecute el script de configuración integrado en el `db` contenedor::

    docker exec ckan /usr/local/bin/ckan -c /etc/ckan/production.ini datastore set-permissions | docker exec -i db psql -U ckan

Las canalizaciones de script en la salida de `ckan datastore set-permissions` - sin embargo,
como esta salida puede cambiar en futuras versiones de CKAN, establecemos los permisos directamente.
El efecto de este script se conserva en el volumen con nombre `docker_pg_data`.

.. Nota: Reutilizamos el usuario predeterminado ya privilegiado de la base de datos CKAN como usuario de lectura/escritura
para el almacén de datos. El usuario de la base de datos (`ckan`) está codificado, la contraseña se proporciona a través de
el`.env` variable `POSTGRES_PASSWORD`.
Un nuevo usuario `datastore_ro` se crea (y también se codifica) como usuario de sólo lectura con contraseña
`DATASTORE_READONLY_USER`.
La codificación rígida de la tabla de base de datos y los nombres de usuario permite preparar el script SQL set-permissions,
sin exponer información confidencial al mundo fuera del entorno de host de Docker.

Después de este paso, la base de datos del almacén de datos está lista para habilitarse en el `production.ini`.

b. Habilitar el almacén de datos y el explorador de datos en `production.ini`

Edite el `production.ini` (nota: requiere sudo)::

    sudo vim $VOL_CKAN_CONFIG/production.ini

Agregar `datastore datapusher` Para `ckan.plugins` y habilitar la opción datapusher
`ckan.datapusher.formats`.

La configuración restante requerida para el almacén de datos y datapusher ya está atendida:

*   `ckan.storage_path` (`/var/lib/ckan`) está codificado en `ckan-entrypoint.sh`,
    `docker-compose.yml` y CKAN's `Dockerfile`. Esta ruta está codificada de forma rígida, ya que sigue siendo interna
    a los contenedores, y cambiarlo no tendría ningún efecto en el sistema host.
*   `ckan.datastore.write_url = postgresql://ckan:POSTGRES_PASSWORD@db/datastore` y
    `ckan.datastore.read_url = postgresql://datastore:DATASTORE_READONLY_PASSWORD@db/datastore`
    son proporcionados por `docker-compose.yml`.

Reinicie el `ckan` contenedor para aplicar cambios a la `production.ini`::

    docker-compose restart ckan

Ahora la API del almacén de datos debe devolver contenido al visitar:

    CKAN_SITE_URL/api/3/action/datastore_search?resource_id=_table_metadata

***

4.  Crear usuario administrador de CKAN

***

Con todas las imágenes en funcionamiento, cree el usuario administrador de CKAN (johndoe en este ejemplo)::

    docker exec -ti ckan /usr/local/bin/ckan -c /etc/ckan/production.ini sysadmin add johndoe

Ahora debería poder iniciar sesión en el nuevo CKAN vacío.
La clave de API del usuario administrador será fundamental para transferir datos de otras instancias.

***

5.  Migrar datos

***

En esta sección se ilustra la migración de datos desde una instancia CKAN existente `SOURCE_CKAN`
en nuestra nueva instancia de Docker Compose CKAN asumiendo acceso directo (ssh) a `SOURCE_CKAN`.

un. Transferir archivos de recursos

Suponiendo que el directorio de almacenamiento CKAN en `SOURCE_CKAN` se encuentra en `/path/to/files` (conteniendo
archivos de recursos e imágenes cargadas en `resources` y `storage`), simplemente lo haremos `rsync`
`SOURCE_CKAN`Directorio de almacenamiento de 's en el volumen con nombre `docker_ckan_storage`::

    sudo rsync -Pavvr USER@SOURCE_CKAN:/path/to/files/ $VOL_CKAN_STORAGE

b. Transferir usuarios

Los usuarios se pueden exportar utilizando el paquete python `ckanapi`, pero sus hashes de contraseña serán
Excluidos. Para transferir usuarios que conservan sus contraseñas, necesitamos volcar y restaurar el `user`
mesa.

En el host CKAN de origen con acceso a la base de datos de origen `ckan_default`, exporte el `user` mesa::

    pg_dump -h CKAN_DBHOST -P CKAN_DBPORT -U CKAN_DBUSER -a -O -t user -f user.sql ckan_default

En el host de destino, haga `user.sql` accesible al contenedor CKAN de origen.
Transferir .sql usuario al volumen con nombre `docker_ckan_home` y `chown` a través del usuario de docker::

    rsync -Pavvr user@ckan-source-host:/path/to/user.sql $VOL_CKAN_HOME/venv/src

    # $VOL_CKAN_HOME is owned by the user "ckan" (UID 900) as created in the CKAN Dockerfile
    sudo ls -l $VOL_CKAN_HOME
    # drwxr-xr-x 1 900 900 62 Jul 17 16:13 venv

    # Chown user.sql to the owner of $CKAN_HOME (ckan, UID 900)
    sudo chown 900:900 $VOL_CKAN_HOME/venv/src/user.sql

Ahora el archivo `user.sql` es accesible desde dentro del `ckan` contenedor::

    docker exec -it ckan /bin/bash -c "export TERM=xterm; exec bash"

    ckan@eca111c06788:/$ psql -U ckan -h db -f $CKAN_VENV/src/user.sql

c. Exportar y cargar grupos, organizaciones, conjuntos de datos

Uso del paquete python `ckanapi` volcaremos organizaciones, grupos y conjuntos de datos de la fuente CKAN
y, a continuación, utilice `ckanapi` para cargar los datos exportados en la instancia de destino.
El datapusher ingerirá automáticamente recursos CSV en el almacén de datos.

d. Reconstruir el índice de búsqueda

Desencadenar una reconstrucción del índice Solr::

    docker exec -it ckan /usr/local/bin/ckan -c /etc/ckan/production.ini search-index rebuild

***

6.  Agregar extensiones

***

Hay dos escenarios para agregar extensiones:

*   Los mantenedores de instancias de producción necesitan extensiones para formar parte de la `ckan` imagen y un
    manera fácil de habilitarlos en el `production.ini`.
    Automatización de la instalación de extensiones existentes (sin necesidad de cambiar su origen)
    requiere personalizar CKAN's `Dockerfile` y post-procesamiento guionado del `production.ini`.
*   Los desarrolladores necesitan leer, modificar y usar el control de versiones en la fuente de las extensiones. Esto añade
    pasos adicionales al flujo de trabajo de los mantenedores.

Para los mantenedores, el proceso es en resumen:

*   Ejecutar un shell bash dentro de la ejecución `ckan` contenedor, descargar e instalar extensión.
    Alternativamente, agregue un `pip install` paso para la extensión en un Dockerfile CKAN personalizado.
*   Reanudar `ckan` servicio, leer registros.

un. Descargue e instale la extensión desde dentro `ckan` contenedor en `docker_ckan_home` volumen

El proceso es muy similar a la instalación de extensiones en una instalación de origen. La única diferencia es
que los pasos de instalación se llevarán a cabo dentro del contenedor en ejecución y usarán el comando
virtualenv creado dentro de la imagen ckan por Dockerfile de CKAN.

Los archivos descargados e instalados se conservarán en el volumen con nombre `docker_ckan_home`.

En este ejemplo entraremos en la ejecución `ckan` contenedor para instalar
`ckanext-geoview <https://github.com/ckan/ckanext-geoview>`\_ de la fuente,
`ckanext-showcase <https://github.com/ckan/ckanext-showcase>`\_ de GitHub,
y `ckanext-envvars <https://github.com/okfn/ckanext-envvars>`\_ de PyPi::

    # Enter the running ckan container:
    docker exec -it ckan /bin/bash -c "export TERM=xterm; exec bash"

    # Inside the running container, activate the virtualenv
    source $CKAN_VENV/bin/activate && cd $CKAN_VENV/src/

    # Option 1: From source
    git clone https://github.com/ckan/ckanext-geoview.git
    cd ckanext-geoview
    pip install -r pip-requirements.txt
    python setup.py install
    python setup.py develop
    cd ..

    # Option 2: Pip install from GitHub
    pip install -e "git+https://github.com/ckan/ckanext-showcase.git#egg=ckanext-showcase"

    # Option 3: Pip install from PyPi
    pip install ckanext-envvars

    # exit the ckan container:
    exit

Algunas extensiones requieren actualizaciones de la base de datos, a menudo a través de la CLI de ckan.
P. ej.. `ckanext-spatial <https://github.com/ckan/ckanext-spatial.git>`\_::

    # Enter the running ckan container:
    docker exec -it ckan /bin/bash -c "export TERM=xterm; exec bash"

    # Inside the running ckan container
    source $CKAN_VENV/bin/activate && cd $CKAN_VENV/src/
    git clone https://github.com/ckan/ckanext-spatial.git
    cd ckanext-spatial
    pip install -r pip-requirements.txt
    python setup.py install && python setup.py develop
    exit

    # On the host
    docker exec -it db psql -U ckan -f /docker-entrypoint-initdb.d/20_postgis_permissions.sql
    docker exec -it ckan /usr/local/bin/ckan -c /etc/ckan/production.ini spatial initdb 

    sudo vim $VOL_CKAN_CONFIG/production.ini

    # Inside production.ini, add to [plugins]:
    spatial_metadata spatial_query

    ckanext.spatial.search_backend = solr

b. Modificar la configuración de CKAN

Siga las instrucciones de la extensión respectiva para establecer las variables de configuración de CKAN:

    sudo vim $VOL_CKAN_CONFIG/production.ini

.. todo:: Demostrar cómo establecer `production.ini` configuración de variables de entorno mediante
`ckanext-envvars`.

c. Recargar y depurar

::

    docker-compose restart ckan
    docker-compose logs ckan

d. Desarrollar extensiones: modificar el origen, instalar, usar el control de versiones

Mientras que los mantenedores preferirán usar versiones estables de extensiones existentes, los desarrolladores de
las extensiones necesitarán acceso al origen de las extensiones y podrán usar el control de versiones.

El uso de Docker y la encapsulación inherente de archivos y permisos hace que el desarrollo de
extensiones más difíciles que una instalación de origen CKAN.

En primer lugar, la ausencia de claves SSH privadas dentro de los contenedores Docker hará que la interacción con
GitHub mucho más difícil. Por otro lado, la autenticación de dos factores en GitHub rompe BasicAuth
(HTTPS, nombre de usuario y contraseña) y requiere un "token de acceso personal" en lugar de la contraseña.

Para usar el control de versiones desde el contenedor de Docker:

*   Clona la versión HTTPS del repositorio de GitHub.
*   En GitHub, cree un token de acceso personal con "control total de repositorios privados".
*   Copie el código del token y úselo como contraseña al ejecutarlo `git push`.

En segundo lugar, la fuente de extensión persistente en `VOL_CKAN_HOME` es propiedad del contenedor CKAN
`docker` usuario (UID 900) y, por lo tanto, no se puede escribir en la cuenta de usuario host del desarrollador mediante
predeterminado. Hay varias soluciones. Se puede acceder a la fuente de extensión desde fuera y
dentro del contenedor.

Opción 1: Acceso a la fuente desde el interior del contenedor:

    docker exec -it ckan /bin/bash -c "export TERM=xterm; exec bash"
    source $CKAN_VENV/bin/activate && cd $CKAN_VENV/src/
    # ... work on extensions, use version control ...
    # in extension folder:
    python setup.py install
    exit
    # ... edit extension settings in production.ini and restart ckan container
    sudo vim $VOL_CKAN_CONFIG/production.ini
    docker-compose restart ckan

Opción 2: Acceso a la fuente desde fuera del contenedor utilizando `sudo`::

    sudo vim $VOL_CKAN_CONFIG/production.ini
    sudo vim $VOL_CKAN_HOME/venv/src/ckanext-datawagovautheme/ckanext/datawagovautheme/templates/package/search.html

Opción 3: El paquete de Ubuntu `bindfs` Hace que los volúmenes protegidos contra escritura sean accesibles para un sistema
usuario::

    sudo apt-get install bindfs
    mkdir ~/VOL_CKAN_HOME
    sudo chown -R `whoami`:docker $VOL_CKAN_HOME
    sudo bindfs --map=900/`whoami` $VOL_CKAN_HOME ~/VOL_CKAN_HOME

    cd ~/VOL_CKAN_HOME/venv/src

    # Do this with your own extension fork
    # Assumption: the host user running git clone (you) has write access to the repository
    git clone https://github.com/parksandwildlife/ckanext-datawagovautheme.git

    # ... change files, use version control...

Los cambios en las plantillas HTML y CSS serán visibles de inmediato.
Para los cambios en el código, tendremos que desmontar el directorio, cambiar la propiedad de nuevo a la `ckan`
y siga los pasos anteriores para `python setup.py install` y
`pip install -r requirements.txt` desde el contenedor en ejecución, modifique el icono `production.ini`
y reinicie el contenedor:

    sudo umount ~/VOL_CKAN_HOME
    sudo chown -R 900:900 $VOL_CKAN_HOME
    # Follow steps a-c

.. NOTA:: Montar carpetas de host como volúmenes en lugar de utilizar volúmenes con nombre puede resultar en una simplificación más sencilla
flujo de trabajo de desarrollo. Sin embargo, los volúmenes con nombre son la forma canónica de Docker para conservar los datos.
Los pasos que se muestran arriba son solo algunos de los varios enfoques posibles.

***

7.  Variables de entorno

***

La configuración confidencial se puede administrar de (al menos) dos maneras, ya sea como variables de entorno o como
`Docker secrets <https://docs.docker.com/engine/swarm/secrets/>`\_.
Esta sección ilustra el uso de variables de entorno proporcionadas por Docker Compose `.env`
archivo.

Esta sección está dirigida a los mantenedores de CKAN que buscan una comprensión más profunda de las variables,
y en CKAN desarrolladores que buscan tener en cuenta la configuración como nueva `.env` Variables.

La sustitución de variables se propaga de la siguiente manera:

*   `.env.template` contiene los valores predeterminados y las instrucciones de uso de las variables.
*   El mantenedor copia `.env` De `.env.template` y lo modifica siguiendo las instrucciones.
*   Docker Compose interpola variables en `docker-compose.yml` De `.env`.
*   Docker Compose puede pasar estas variables a los contenedores como variables de tiempo de compilación
    (al construir las imágenes) y / o como variables de tiempo de ejecución (al ejecutar los contenedores).
*   `ckan-entrypoint.sh` tiene acceso a todas las variables de tiempo de ejecución del `ckan` servicio.
*   `ckan-entrypoint.sh` inyecta variables de entorno (por ejemplo, `CKAN_SQLALCHEMY_URL`) en el
    corriente `ckan` contenedor, reemplazando las variables de configuración CKAN de `production.ini`.

Véase :d oc:`/maintaining/configuration` para obtener una lista de variables de entorno
(por ejemplo, `CKAN_SQLALCHEMY_URL`) que CKAN aceptará anular `production.ini`.

Después de agregar nuevo o cambiar el existente `.env` variables, imágenes construidas localmente y volúmenes pueden
necesitan ser abandonados y reconstruidos. De lo contrario, docker reutilizará imágenes en caché con imágenes antiguas o faltantes
Variables::

    docker-compose down
    docker-compose up -d --build

    # if that didn't work, try:
    docker rmi $(docker images -q -f dangling=true)
    docker-compose up -d --build

    # if that didn't work, try:
    docker rmi $(docker images -q -f dangling=true)
    docker volume prune
    docker-compose up -d --build

.. warning:: La eliminación de volúmenes con nombre destruirá los datos.
`docker volume prune` eliminará los volúmenes no conectados a un contenedor en ejecución(!).
Haga una copia de seguridad de todos los datos antes de hacer esto en un entorno de producción.

***

8.  Pasos hacia la producción

***

Como se mencionó anteriormente, algunas decisiones de diseño pueden no ser adecuadas para una configuración de producción.

Un posible camino hacia un entorno listo para la producción es:

*   Utilice la configuración anterior para crear imágenes de Docker.
*   Agregar y configurar extensiones.
*   Asegúrese de que no haya configuraciones confidenciales codificadas dentro de las imágenes.
*   Inserte las imágenes en un repositorio de Docker.
*   Crear una "producción" separada `docker-compose.yml` que utiliza las imágenes personalizadas.
*   Ejecutar la "producción" `docker-compose.yml` en el servidor de producción con la configuración adecuada.
*   Transferir datos de producción al nuevo servidor como se describe anteriormente mediante orquestación de volúmenes
    herramientas o transferencia de archivos directamente.
*   Bono: contribuya con una redacción de las configuraciones de producción en funcionamiento a la documentación de CKAN.
