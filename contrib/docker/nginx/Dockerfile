FROM nginx:alpine

ENV NGINX_DIR=/etc/nginx

COPY index.html /usr/share/nginx/html/index.html

RUN mkdir -p ${NGINX_DIR}/sites-available
RUN mkdir -p ${NGINX_DIR}/sites-enabled

COPY setup/nginx.conf ${NGINX_DIR}
COPY setup/sites-available/* ${NGINX_DIR}/sites-available

RUN ln -s ${NGINX_DIR}/sites-available/ckan.conf ${NGINX_DIR}/sites-enabled/ckan.conf

EXPOSE 80