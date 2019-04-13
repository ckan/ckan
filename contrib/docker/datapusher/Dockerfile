FROM python:2.7-stretch

WORKDIR /usr/src

ARG DATAPUSHER_VERSION

# Download datapusher
RUN wget https://github.com/ckan/datapusher/archive/${DATAPUSHER_VERSION}.zip
RUN unzip ${DATAPUSHER_VERSION}.zip && rm ${DATAPUSHER_VERSION}.zip

# Adding Requirements
RUN pip install -r datapusher-${DATAPUSHER_VERSION}/requirements.txt
RUN pip install -e datapusher-${DATAPUSHER_VERSION}/

WORKDIR /usr/src/datapusher-${DATAPUSHER_VERSION}

# Adding SSl Verify
# RUN echo "SSL_VERIFY = False" >> /usr/src/datapusher/deployment/datapusher_settings.py

# Export LC_ALL
ENV LC_ALL=C

# USER
USER root

# EXPOSE
EXPOSE 8800

# COMMAND
CMD ["python", "datapusher/main.py", "deployment/datapusher_settings.py"]
