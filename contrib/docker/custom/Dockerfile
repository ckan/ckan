FROM ckan_ckan
MAINTAINER Open Knowledge

ENV CONFIG_OPTIONS custom_options.ini
ADD ./$CONFIG_OPTIONS $CKAN_CONFIG/$CONFIG_OPTIONS

# Install CKAN Plugins in the parent container (i.e. root Dockerfile)
# & build it as per the instructions below
# examples:

# # pages
# RUN $CKAN_HOME/bin/pip install \
#       -e git+https://github.com/ckan/ckanext-pages.git#egg=ckanext-pages
# # viewhelpers
# RUN $CKAN_HOME/bin/pip install \
#       -e git+https://github.com/ckan/ckanext-viewhelpers.git#egg=ckanext-viewhelpers
# RUN $CKAN_HOME/bin/pip install \
#       -e git+https://github.com/ckan/ckanext-basiccharts.git#egg=ckanext-basiccharts
# RUN $CKAN_HOME/bin/pip install \
#       -e git+https://github.com/ckan/ckanext-dashboard.git#egg=ckanext-dashboard
# RUN $CKAN_HOME/bin/pip install \
#       -e git+https://github.com/ckan/ckanext-mapviews.git#egg=ckanext-mapviews

# # archiver
# RUN . $CKAN_HOME && \
#     $CKAN_HOME/bin/pip install \
#       -e git+http://github.com/ckan/ckanext-archiver.git#egg=ckanext-archiver && \
#     $CKAN_HOME/bin/pip install \
#       -r $CKAN_HOME/src/ckanext-archiver/pip-requirements.txt

# ## spatial
# RUN . $CKAN_HOME && \
#     $CKAN_HOME/bin/pip install \
#       -e git+https://github.com/ckan/ckanext-spatial.git#egg=ckanext-spatial && \
#     $CKAN_HOME/bin/pip install \
#       -r $CKAN_HOME/src/ckanext-spatial/pip-requirements.txt

# ## harvest
# RUN . $CKAN_HOME && \
#     $CKAN_HOME/bin/pip install \
#       -e git+https://github.com/ckan/ckanext-harvest.git#egg=ckanext-harvest && \
#     $CKAN_HOME/bin/pip install \
#       -r $CKAN_HOME/src/ckanext-harvest/pip-requirements.txt

# ## searchhistory
# RUN . $CKAN_HOME && \
#     $CKAN_HOME/bin/pip install \
#       -e git+https://github.com/ckan/ckanext-searchhistory.git#egg=ckanext-searchhistory

# ## dcat
# RUN . $CKAN_HOME && \
#     $CKAN_HOME/bin/pip install \
#       -e git+https://github.com/ckan/ckanext-dcat.git#egg=ckanext-dcat

# copy the conf.d for supervisor & cron
ADD ./supervisor.d/ /etc/supervisor/conf.d/
ADD ./cron.d/ /etc/cron.d/

# Configure runit
ADD ./my_init.d/ /etc/my_init.d/
