***

## Instalación de CKAN

Antes de que pueda usar CKAN en su propia computadora, debe instalarlo.
Hay tres formas de instalar CKAN:

\#. Instalar desde un paquete de sistema operativo
\#. Instalar desde el origen
\#. Instalar desde Docker Compose

CKAN 2.9 soporta Python 3.7 y Python 3.8 más 2.7. La próxima versión de CKAN
solo admitirá Python 3.

Se pueden encontrar consejos de implementación adicionales en nuestro wiki, como los recomendados
`Hardware Requirements <https://github.com/ckan/ckan/wiki/Hardware-Requirements>`\_.

La instalación desde el paquete es la forma más rápida y fácil de instalar CKAN, pero requiere
Ubuntu 18.04 de 64 bits o Ubuntu 20.04 de 64 bits.

**Debe instalar CKAN desde el paquete si**:

*   Desea instalar CKAN en un servidor Ubuntu 18.04 o 20.04, de 64 bits, *y*
*   Solo desea ejecutar un sitio web CKAN por servidor

Véase :d oc:`install-from-package`.

**Debe instalar CKAN desde el origen si**:

*   Desea instalar CKAN en un equipo de 32 bits, *o*
*   Desea instalar CKAN en una versión diferente de Ubuntu, no 18.04 o 20.04, *o*
*   Desea instalar CKAN en otro sistema operativo (por ejemplo. RHEL, CentOS, OS X), *o*
*   Desea ejecutar varios sitios web de CKAN en el mismo servidor, *o*
*   Desea instalar CKAN para el desarrollo

Véase :d oc:`install-from-source`.

La configuración proporcionada de Docker Compose proporciona una forma limpia y rápida de implementar un CKAN vainilla
sin extensiones, sin dejar de permitir la adición (y personalización) de extensiones.
Esta opción viene con la advertencia de que se deben tomar algunos pasos adicionales para implementar un
CKAN listo para la producción. **Debe instalar CKAN desde Docker Compose si**:

*   Desea instalar CKAN con menos esfuerzo que una instalación de origen y más flexibilidad que una
    instalación del paquete, **o**
*   Desea ejecutar o incluso desarrollar extensiones con el mínimo esfuerzo de configuración, **o**
*   Desea ver si y cómo encajarán CKAN, Docker y su respectiva infraestructura
    junto.

Véase :d oc:`install-from-docker-compose`.

Si ya ha configurado un sitio web de CKAN y desea actualizarlo a uno más reciente
versión de CKAN, véase :d oc:`/maintaining/upgrading/index`.

***

.. toctree::
:maxdepth: 1

instalar desde-paquete
instalar desde el origen
install-from-docker-compose
despliegue
