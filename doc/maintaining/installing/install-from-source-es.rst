.. include:: /\_substitutions.rst

# ===========================&#xD;&#xA;Instalación de CKAN desde el origen

En esta sección se describe cómo instalar CKAN desde el origen. Aunque
:d oc:`install-from-package` es más simple, requiere Ubuntu 18.04 de 64 bits o
Ubuntu 16.04 de 64 bits. La instalación de CKAN desde el origen funciona con otros
versiones de Ubuntu y con otros sistemas operativos (por ejemplo, RedHat, Fedora, CentOS, OS X).
Si instala CKAN desde el origen en su propio sistema operativo, comparta su
experiencias en nuestro `How to Install CKAN <https://github.com/ckan/ckan/wiki/How-to-Install-CKAN>`\_
página wiki.

**Para las instalaciones de Python 3, la versión mínima de Python requerida es 3.7**

*   **Ubuntu 20.04** Incluye **Python 3.8** como parte de su distribución
*   **Ubuntu 18.04** Incluye **Python 3.6** como parte de su distribución

Desde la fuente también es el método de instalación adecuado para los desarrolladores que desean
trabajar en CKAN.

***

1.  Instalar los paquetes necesarios

***

Si está utilizando un sistema operativo basado en Debian (como Ubuntu), instale el
paquetes requeridos con este comando:

    sudo apt-get install python3-dev postgresql libpq-dev python3-pip python3-venv git-core solr-tomcat openjdk-8-jdk redis-server

Si no está utilizando un sistema operativo basado en Debian, encuentre la mejor manera de
Instale los siguientes paquetes en su sistema operativo (consulte
nuestro `How to Install CKAN <https://github.com/ckan/ckan/wiki/How-to-Install-CKAN>`\_
página wiki para ayuda):

\=====================  ===============================================
Descripción del paquete
\=====================  ===============================================
Pitón                 `The Python programming language, v3.7 or newer <https://www.python.org/getit/>`\_
|postgres|             `The PostgreSQL database system, v10 or newer <https://www.postgresql.org/docs/10/libpq.html>`\_
libpq                  `The C programmer's interface to PostgreSQL <http://www.postgresql.org/docs/8.1/static/libpq.html>`\_
pepita                    `A tool for installing and managing Python packages <https://pip.pypa.io/en/stable/>`\_
python3-venv           `The Python3 virtual environment builder (or for Python 2 use 'virtualenv' instead) <https://virtualenv.pypa.io/en/latest/>`\_
Git                    `A distributed version control system <https://git-scm.com/book/en/v2/Getting-Started-Installing-Git>`\_
Apache Solr            `A search platform <https://lucene.apache.org/solr/>`\_
Embarcadero                  `An HTTP server <https://www.eclipse.org/jetty/>`\_ (usado para Solr).
OpenJDK JDK            `The Java Development Kit <https://openjdk.java.net/install/>`\_ (utilizado por Jetty)
Redis                  `An in-memory data structure store <https://redis.io/>`\_
\=====================  ===============================================

.. \_install-ckan-in-virtualenv:

***

2.  Instalar CKAN en un entorno virtual Python

***

.. Propina::

Si está instalando CKAN para el desarrollo y desea que se instale en
su directorio principal, puede enlazar los directorios utilizados en este
documentación a su directorio de inicio. De esta manera, puede copiar y pegar el
comandos de ejemplo de esta documentación sin tener que modificarlos, y
todavía tiene CKAN instalado en su directorio de inicio:

.. parsed-literal::

     mkdir -p ~/ckan/lib
     sudo ln -s ~/ckan/lib |virtualenv_parent_dir|
     mkdir -p ~/ckan/etc
     sudo ln -s ~/ckan/etc |config_parent_dir|

un. Crear un Python `virtual environment <https://virtualenv.pypa.io/en/latest/>`\_
(virtualenv) para instalar CKAN y activarlo:

.. parsed-literal::

       sudo mkdir -p |virtualenv|
       sudo chown \`whoami\` |virtualenv|
       python3 -m venv |virtualenv|
       |activate|

.. importante::

El comando final anterior activa su virtualenv. El virtualenv tiene que
permanecer activo durante el resto del proceso de instalación e implementación,
o los comandos fallarán. Puede saber cuándo está activo el virtualenv porque
su nombre aparece delante de su indicador de shell, algo como esto:

     (default) $ _

Por ejemplo, si cierra la sesión y vuelve a iniciar sesión, o si cierra el terminal
y ábralo de nuevo, su virtualenv ya no se activará. Tú
Siempre se puede reactivar el virtualenv con este comando:

.. parsed-literal::

       |activate|

b. Instalar lo recomendado `setuptools` versión y pip actualizado:

.. parsed-literal::

       pip install setuptools==\ |min_setuptools_version|
       pip install --upgrade pip

c. Instale el código fuente de CKAN en su virtualenv.

Para instalar la última versión estable de CKAN (CKAN |current_release_version|),
correr:

.. parsed-literal::

      pip install -e 'git+\ |git_url|\@\ |current_release_tag|\#egg=ckan[requirements]'

Si está instalando CKAN para el desarrollo, es posible que desee instalar el
última versión de desarrollo (la confirmación más reciente en la rama maestra de
el repositorio git de CKAN). En ese caso, ejecute este comando en su lugar:

.. parsed-literal::

       pip install -e 'git+\ |git_url|\#egg=ckan[requirements,dev]'

.. advertencia::

      The development version may contain bugs and should not be used for
      production websites! Only install this version if you're doing CKAN
      development.

d. Desactive y reactive su virtualenv, para asegurarse de que está utilizando el
Copias de comandos de virtualenv como `ckan` en lugar de cualquier sistema
copias instaladas:

.. parsed-literal::

        deactivate
        |activate|

.. \_postgres:

***

3.  Configurar una base de datos PostgreSQL

***

.. include:: postgres.rst

***

4.  Crear un archivo de configuración CKAN

***

Cree un directorio que contenga los archivos de configuración del sitio:

.. parsed-literal::

    sudo mkdir -p |config_dir|
    sudo chown -R \`whoami\` |config_parent_dir|/

Cree el archivo de configuración CKAN:

.. parsed-literal::

    ckan generate config |ckan.ini|

Edite el `ckan.ini` en un editor de texto, cambiando lo siguiente
Opciones:

sqlalchemy.url
Esto debe referirse a la base de datos que creamos en `3. Setup a PostgreSQL
  database`\_ arriba:

.. parsed-literal::

    sqlalchemy.url = postgresql://|database_user|:pass@localhost/|database|

Reemplazar `pass` con la contraseña que creó en `3. Setup a
  PostgreSQL database`\_ arriba.

.. Propina::

    If you're using a remote host with password authentication rather than SSL
    authentication, use:

    .. parsed-literal::

      sqlalchemy.url = postgresql://|database_user|:pass@<remotehost>/|database|?sslmode=disable

site_id
Cada sitio de CKAN debe tener un sitio único `site_id`por ejemplo::

ckan.site_id = predeterminado

site_url
Proporcione la URL del sitio (utilizada al colocar enlaces al sitio en el
FileStore, correos electrónicos de notificación, etc.). Por ejemplo::

    ckan.site_url = http://demo.ckan.org

No agregue una barra diagonal final a la dirección URL.

.. \_setting arriba solr:

***

5.  Configuración de Solr

***

.. incluye:: solr.rst

.. \_postgres-init:

***

6.  Enlace a `who.ini`

***

`who.ini` (el archivo de configuración Repoze.who) debe ser accesible en el cuadro de diálogo
mismo directorio que su archivo de configuración CKAN, así que cree un enlace simbólico a él:

.. parsed-literal::

    ln -s |virtualenv|/src/ckan/who.ini |config_dir|/who.ini

***

7.  Crear tablas de base de datos

***

Ahora que tiene un archivo de configuración que tiene la configuración correcta para su
base de datos, puede :ref:`create the database tables <db init>`:

.. parsed-literal::

    cd |virtualenv|/src/ckan
    ckan -c |ckan.ini| db init

Deberías ver `Initialising DB: SUCCESS`.

.. Propina::

    If the command prompts for a password it is likely you haven't set up the
    ``sqlalchemy.url`` option in your CKAN configuration file properly.
    See `4. Create a CKAN config file`_.

***

8.  Configurar el almacén de datos

***

.. nota::
La configuración del almacén de datos es opcional. Sin embargo, si omite este paso,
el :d oc:`DataStore features </maintaining/datastore>` no estará disponible
y se producirá un error en las pruebas del almacén de datos.

Siga las instrucciones de :d oc:`/maintaining/datastore` Para crear lo necesario
bases de datos y usuarios, establezca los permisos correctos y establezca los valores apropiados
en el archivo de configuración de CKAN.

Una vez que haya configurado el DataStore, es posible que desee configurar DataPusher o XLoader
extensiones para agregar datos al almacén de datos. Para instalar DataPusher consulte este enlace:
https://github.com/ckan/datapusher e instalar XLoader consulte este enlace:
https://github.com/ckan/ckanext-xloader

***

9.  ¡Ya está!

***

Ahora puede ejecutar CKAN desde la línea de comandos.  Esta es una forma simple y liviana de servir a CKAN que es
útil para el desarrollo y las pruebas:

.. parsed-literal::

    cd |virtualenv|/src/ckan
    ckan -c |ckan.ini| run

Abra http://127.0.0.1:5000/ en un navegador web y debería ver el frente CKAN
página.

Ahora que ha instalado CKAN, debe:

*   Ejecute las pruebas de CKAN para asegurarse de que todo funciona, consulte :d oc:`/contributing/test`.

*   Si desea utilizar su sitio CKAN como un sitio de producción, no solo para pruebas
    o con fines de desarrollo, a continuación, implemente CKAN utilizando un servidor web de producción como
    como uWSGI o Nginx. Véase :d oc:`deployment`.

*   Comience a usar y personalizar su sitio, consulte :d oc:`/maintaining/getting-started`.

.. Nota:: La configuración de autorización predeterminada en una nueva instalación es deliberada
restrictivo. Los usuarios habituales no podrán crear conjuntos de datos u organizaciones.
Debe verificar el :d oc:`/maintaining/authorization` documentación, configure CKAN en consecuencia
y conceder a otros usuarios los permisos pertinentes mediante el :ref:`sysadmin account <create-admin-user>`.

***

## Solución de problemas de instalación de origen

.. \_solr solución de problemas:

# Solución de problemas de configuración de Solr

Las solicitudes y errores de Solr se registran en los archivos de registro del servidor web.

*   Para los servidores Jetty, los archivos de registro son:

    /var/log/embarcadero/<date>.stderrout.log

*   Para los servidores Tomcat, son:

    /var/log/tomcat6/catalina.<date>.log

## No se puede encontrar un compilador javac

Si al ejecutar Solr dice:

No se puede encontrar un compilador javac; com.sun.tools.javac.Main no está en la ruta de clases. Tal vez JAVA_HOME no apunta al JDK.

Ver la nota en :ref:`setting up solr` acerca de `JAVA_HOME`.
Alternativamente, es posible que no haya instalado el JDK.
Compruebe si `javac` está instalado::

     which javac

Si `javac` no está instalado, haga::

     sudo apt-get install openjdk-8-jdk

y luego reinicie Solr:

Para Ubuntu 18.04:

     sudo service jetty9 restart

o para Ubuntu 16.04::

     sudo service jetty8 restart

## AttributeError: el objeto 'module' no tiene ningún atributo 'css/main.debug.css'

Es probable que este error aparezca cuando `debug` se establece en `True`. Para solucionar esto
error, instalar dependencias frontend. Véase :d oc:`/contributing/frontend/index`.

Después de instalar las dependencias, ejecute `npm run build` y luego iniciar ckan
servidor de nuevo.

Si no desea compilar CSS, también puede copiar el principal.css a
main.debug.css para ejecutar CKAN::

    cp /usr/lib/ckan/default/src/ckan/ckan/public/base/css/main.css \
    /usr/lib/ckan/default/src/ckan/ckan/public/base/css/main.debug.css

## ImportError: No hay módulo llamado 'flask_debugtoolbar'

Esto puede aparecer si ha habilitado el modo de depuración en el archivo de configuración. Simplemente
instalar los requisitos de desarrollo:

    pip install -r /usr/lib/ckan/default/src/ckan/dev-requirements.txt
