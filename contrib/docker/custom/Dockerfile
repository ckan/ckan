FROM clementmouchet/ckan
MAINTAINER Open Knowledge

ENV CKAN_HOME /usr/lib/ckan/default
ENV CONFIG_OPTIONS custom_options.ini
ADD ./$CONFIG_OPTIONS $CKAN_CONFIG/$CONFIG_OPTIONS

# copy the conf.d for supervisor & cron
ADD ./supervisor.d/ /etc/supervisor/conf.d/
ADD ./cron.d/ /etc/cron.d/

# Configure runit
ADD ./my_init.d/ /etc/my_init.d/
ADD ./svc/ /etc/service/
