#!/bin/bash

# Run the prerun script to init CKAN and create the default admin user
sudo -u ckan -EH python prerun.py

# Run any startup scripts provided by images extending this one
if [[ -d "/docker-entrypoint.d" ]]
then
    for f in /docker-entrypoint.d/*; do
        case "$f" in
            *.sh)     echo "$0: Running init file $f"; . "$f" ;;
            *.py)     echo "$0: Running init file $f"; python "$f"; echo ;;
            *)        echo "$0: Ignoring $f (not an sh or py file)" ;;
        esac
        echo
    done
fi

# Set the common uwsgi options
UWSGI_OPTS="--plugins http,python,gevent --socket /tmp/uwsgi.sock --uid 92 --gid 92 --http :5000 --master --enable-threads --paste config:/srv/app/production.ini --paste-logger --lazy-apps --gevent 2000 -p 2 -L"

# Check whether http basic auth password protection is enabled and enable basicauth routing on uwsgi respecfully
if [ $? -eq 0 ]
then
  if [ "$PASSWORD_PROTECT" = true ]
  then
    if [ "$HTPASSWD_USER" ] || [ "$HTPASSWD_PASSWORD" ]
    then
      # Generate htpasswd file for basicauth
      htpasswd -d -b -c /srv/app/.htpasswd $HTPASSWD_USER $HTPASSWD_PASSWORD
      # Start supervisord
      supervisord --configuration /etc/supervisord.conf &
      # Start uwsgi with basicauth
      sudo -u ckan -EH uwsgi --ini /srv/app/uwsgi.conf --pcre-jit $UWSGI_OPTS
    else
      echo "Missing HTPASSWD_USER or HTPASSWD_PASSWORD environment variables. Exiting..."
      exit 1
    fi
  else
    # Start supervisord
    supervisord --configuration /etc/supervisord.conf &
    # Start uwsgi
    sudo -u ckan -EH uwsgi $UWSGI_OPTS
  fi
else
  echo "[prerun] failed...not starting CKAN."
fi
