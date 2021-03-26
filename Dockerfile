# See CKAN docs on installation from Docker Compose on usage
FROM python:3.7.0-alpine
MAINTAINER Open Knowledge

# Install required system packages
RUN apk update \
    && apk upgrade \
    && apk add  --no-cache \
        python3-dev \
        musl-dev \
        libxml2-dev \
        libxslt-dev \
        libffi-dev \
        libmagic \
        postgresql-client \
        postgresql-dev \
        git \
        vim \
        wget \
        curl \
        gcc

# Define environment variables
ENV CKAN_HOME /usr/lib/ckan
ENV CKAN_VENV $CKAN_HOME/venv
ENV CKAN_CONFIG /etc/ckan
ENV CKAN_STORAGE_PATH=/var/lib/ckan

# Build-time variables specified by docker-compose.yml / .env
ARG CKAN_SITE_URL

# Create ckan user
RUN addgroup -g 900 -S ckan && \
    adduser -S -u 900 -G ckan -D -h $CKAN_HOME -s /bin/false ckan

# Setup virtual environment for CKAN
RUN mkdir -p $CKAN_VENV $CKAN_CONFIG $CKAN_STORAGE_PATH && \
    python -m venv $CKAN_VENV
#    ln -s $CKAN_VENV/bin/pip /usr/local/bin/pip
#    ln -s $CKAN_VENV/bin/paster /usr/local/bin/ckan-paster &&\
#    ln -s $CKAN_VENV/bin/ckan /usr/local/bin/ckan && \
#    ls -lha $CKAN_VENV/bin

# Setup CKAN
COPY . $CKAN_VENV/src/ckan/
RUN pip install -U pip && \
    pip install --no-cache-dir -r $CKAN_VENV/src/ckan/requirement-setuptools.txt && \
    pip install --no-cache-dir -r $CKAN_VENV/src/ckan/requirements.txt && \
    pip install -e $CKAN_VENV/src/ckan/ && \
    ln -s $CKAN_VENV/src/ckan/ckan/config/who.ini $CKAN_CONFIG/who.ini && \
    cp -v $CKAN_VENV/src/ckan/contrib/docker/ckan-entrypoint.sh /ckan-entrypoint.sh && \
    chmod +x /ckan-entrypoint.sh && \
    chown -R ckan:ckan $CKAN_HOME $CKAN_VENV $CKAN_CONFIG $CKAN_STORAGE_PATH

ENTRYPOINT ["/ckan-entrypoint.sh"]

USER ckan
EXPOSE 5000

CMD ["ckan","-c","/etc/ckan/production.ini", "run", "--host", "0.0.0.0"]
