:huérfano:

CKAN utiliza Solr\_ como motor de búsqueda y utiliza un archivo de esquema Solr personalizado
que tenga en cuenta las necesidades de búsqueda específicas de CKAN. Ahora que tenemos CKAN
instalado, necesitamos instalar y configurar Solr.

.. advertencia:: CKAN soporta **Solr 8**. A partir de CKAN 2.10 esta es la única versión de Solr compatible. CKAN 2.9 puede ejecutarse con Solr 8 siempre que esté parcheado a al menos 2.9.5. CKAN 2.9 también puede ejecutarse con Solr 6, pero esto no se recomienda ya que esta versión de Solr ya no recibe actualizaciones de seguridad.

Hay dos formas compatibles de instalar Solr.

1.  Usando las imágenes oficiales de Docker\_ de CKAN. Este es generalmente el más fácil y el recomendado si está desarrollando CKAN localmente.
2.  Instalar Solr localmente y configurarlo con el esquema CKAN. Puede usar esta opción si no puede o no desea usar Docker.

# Instalación de Solr mediante Docker

Deberá tener Docker instalado. Por favor, consulte su `installation documentation <https://docs.docker.com/engine/install/>`\_ para más detalles.

Hay imágenes de Docker preconfiguradas para Solr para cada versión de CKAN. Asegúrese de elegir la etiqueta de imagen que coincida con su versión CKAN (se denominan `ckan/ckan-solr:<Major version>.<Minor version>`). Para iniciar un servicio Solr local, puede ejecutar:

.. parsed-literal::

    docker run --name ckan-solr -p 8983:8983 -d ckan/ckan-solr:2.10

.. todo:: Cambiar a `|current_minor_version|` cuando nos ramificamos `dev-v2.10`

Ahora puede saltar al `Next steps <#next-steps-with-solr>`\_ sección.

# Instalación manual de Solr

\#. Descargue la última versión compatible desde el `Solr downloads page <https://solr.apache.org/downloads.html>`\_. CKAN soporta Solr versión 8.x.

\#. Extraiga el archivo descargado a la ubicación deseada (ajuste el número de versión de Solr al que está utilizando)::

    tar xzf solr-8.11.0.tgz

\#. Cambie al directorio extraído:

    cd solr-8.11.0/

\#. Inicio Solr::

    bin/solr start

\#. Cree un nuevo núcleo para CKAN:

    bin/solr create -c ckan

\#. Reemplace el esquema estándar ubicado en `server/solr/ckan/conf/managed-schema` con el CKAN:

.. parsed-literal::

    wget -O server/solr/ckan/conf/managed-schema https://raw.githubusercontent.com/ckan/ckan/master/ckan/config/solr/schema.xml

.. todo:: Cambiar a `|current_release_tag|` cuando nos ramificamos `dev-v2.10`

\#. Reinicie Solr::

    bin/solr restart

# Próximos pasos con Solr

Para comprobar que Solr comenzó puedes visitar la interfaz web en http://localhost:8983/solr

.. advertencia: Los dos métodos de instalación anteriores lo dejarán con una configuración que está bien para el desarrollo local, pero Solr nunca debe exponerse públicamente en un sitio de producción. Por favor, consulte el `Solr documentation <https://solr.apache.org/guide/securing-solr.html>`\_ para aprender a proteger su instancia de Solr.

Si siguió alguna de las instrucciones anteriores, el núcleo CKAN Solr estará disponible en http://localhost:8983/solr/ckan. Si por alguna razón terminó con uno diferente (por ejemplo, con un puerto, host o nombre de núcleo diferente), debe cambiar el :ref:`solr_url` en su :ref:`config_file` (|ckan.ini|) para apuntar a su servidor Solr, por ejemplo:

       solr_url=http://my-solr-host:8080/solr/ckan-2.10

.. \_Solr: https://solr.apache.org/
.. \_Docker: https://www.docker.com/
