#!/bin/sh

if [ ! -f /var/www/html ]; then
    mkdir -p /var/www/html
fi
 
if [ -n "$DOMAIN" ] && [ "$DOMAIN" != "localhost" ]; then
	certbot certonly \
			--config-dir ${LETSENCRYPT_DIR:-/etc/letsencrypt} \
			--dry-run \
			--agree-tos \
			--domains "$DOMAIN" \
			--email $EMAIL \
			--expand \
			--noninteractive \
			--webroot \
			--webroot-path /var/www/html \
			$OPTIONS || true

	if [ -f ${LETSENCRYPT_DIR:-/etc/letsencrypt}/live/$DOMAIN/privkey.pem ]; then
		chmod +rx ${LETSENCRYPT_DIR:-/etc/letsencrypt}/live
		chmod +rx ${LETSENCRYPT_DIR:-/etc/letsencrypt}/archive
		chmod +r  ${LETSENCRYPT_DIR:-/etc/letsencrypt}/archive/${DOMAIN}/fullchain*.pem
		chmod +r  ${LETSENCRYPT_DIR:-/etc/letsencrypt}/archive/${DOMAIN}/privkey*.pem
		cp ${LETSENCRYPT_DIR:-/etc/letsencrypt}/live/$DOMAIN/privkey.pem /usr/share/nginx/certificates/privkey.pem
		cp ${LETSENCRYPT_DIR:-/etc/letsencrypt}/live/$DOMAIN/fullchain.pem /usr/share/nginx/certificates/fullchain.pem
		echo "Copied new certificate to /usr/share/nginx/certificates"
	fi
fi
