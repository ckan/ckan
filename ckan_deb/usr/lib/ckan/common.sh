#!/bin/bash

ckan_log () {
    echo "ckan: " $1
}

#_echo="echo"
ckan_maintenance_on () {
    local INSTANCE
    INSTANCE=$1
    $_echo a2dissite ${INSTANCE}
    $_echo a2ensite  ${INSTANCE}.maint
    $_echo service apache2 reload
}

ckan_maintenance_off () {
    local INSTANCE
    INSTANCE=$1
    $_echo a2dissite ${INSTANCE}.maint
    $_echo a2ensite  ${INSTANCE}
    $_echo service apache2 reload
}

ckan_set_log_file_permissions () {
    local INSTANCE
    INSTANCE=$1
    sudo chown www-data:ckan${INSTANCE} /var/log/ckan/${INSTANCE}
    sudo chmod g+w /var/log/ckan/${INSTANCE}
    sudo touch /var/log/ckan/${INSTANCE}/${INSTANCE}.log
    sudo touch /var/log/ckan/${INSTANCE}/${INSTANCE}1.log
    sudo touch /var/log/ckan/${INSTANCE}/${INSTANCE}2.log
    sudo touch /var/log/ckan/${INSTANCE}/${INSTANCE}3.log
    sudo touch /var/log/ckan/${INSTANCE}/${INSTANCE}4.log
    sudo touch /var/log/ckan/${INSTANCE}/${INSTANCE}5.log
    sudo touch /var/log/ckan/${INSTANCE}/${INSTANCE}6.log
    sudo touch /var/log/ckan/${INSTANCE}/${INSTANCE}7.log
    sudo touch /var/log/ckan/${INSTANCE}/${INSTANCE}8.log
    sudo touch /var/log/ckan/${INSTANCE}/${INSTANCE}9.log
    sudo chmod g+w /var/log/ckan/${INSTANCE}/${INSTANCE}*.log
    sudo chown www-data:ckan${INSTANCE} /var/log/ckan/${INSTANCE}/${INSTANCE}*.log
}

ckan_ensure_users_and_groups () {
    local INSTANCE
    INSTANCE=$1
    COMMAND_OUTPUT=`cat /etc/group | grep "ckan${INSTANCE}:"`
    if ! [[ "$COMMAND_OUTPUT" =~ "ckan${INSTANCE}:" ]] ; then
        echo "Creating the 'ckan${INSTANCE}' group ..." 
        sudo groupadd --system "ckan${INSTANCE}"
    fi
    COMMAND_OUTPUT=`cat /etc/passwd | grep "ckan${INSTANCE}:"`
    if ! [[ "$COMMAND_OUTPUT" =~ "ckan${INSTANCE}:" ]] ; then
        echo "Creating the 'ckan${INSTANCE}' user ..." 
        sudo useradd  --system  --gid "ckan${INSTANCE}" --home /var/lib/ckan/${INSTANCE} -M  --shell /usr/sbin/nologin ckan${INSTANCE}
    fi
}

ckan_make_ckan_directories () {
    local INSTANCE
    if [ "X$1" = "X" ] ; then
        echo "ERROR: call the function make_ckan_directories with an INSTANCE name, e.g." 
        echo "       dgu"
        exit 1
    else
        INSTANCE=$1
        mkdir -p -m 0755 /etc/ckan/${INSTANCE}
        mkdir -p -m 0750 /var/lib/ckan/${INSTANCE}{,/static}
        mkdir -p -m 0770 /var/{backup,log}/ckan/${INSTANCE} /var/lib/ckan/${INSTANCE}/{data,sstore,static/dump}
        sudo chown ckan${INSTANCE}:ckan${INSTANCE} /etc/ckan/${INSTANCE}
        sudo chown www-data:ckan${INSTANCE} /var/{backup,log}/ckan/${INSTANCE} /var/lib/ckan/${INSTANCE} /var/lib/ckan/${INSTANCE}/{data,sstore,static/dump}
        sudo chmod g+w /var/log/ckan/${INSTANCE} /var/lib/ckan/${INSTANCE}/{data,sstore,static/dump}
    fi
}

ckan_create_who_ini () {
    local INSTANCE
    if [ "X$1" = "X" ] ; then
        echo "ERROR: call the function create_who_ini function with an INSTANCE name, e.g." 
        echo "       dgu"
        exit 1
    else
        INSTANCE=$1
        if ! [ -f /etc/ckan/$0/who.ini ] ; then
            cp -n /usr/share/pyshared/ckan/config/who.ini /etc/ckan/${INSTANCE}/who.ini
            sed -e "s,%(here)s,/var/lib/ckan/${INSTANCE}," \
                -i /etc/ckan/${INSTANCE}/who.ini
            chown ckan${INSTANCE}:ckan${INSTANCE} /etc/ckan/${INSTANCE}/who.ini
        fi
    fi
}

ckan_create_config_file () {
    local INSTANCE password LOCAL_DB
    if [ "X$1" = "X" ] || [ "X$2" = "X" ] ; then
        echo "ERROR: call the function create_config_file function with an INSTANCE name, and a password for postgresql e.g."
        echo " dgu 1U923hjkh8"
        exit 1
    else
        INSTANCE=$1
        password=$2
        LOCAL_DB=$3
        # Create an install settings file if it doesn't exist
        if [ -f /etc/ckan/${INSTANCE}/${INSTANCE}.ini ] ; then
            mv /etc/ckan/${INSTANCE}/${INSTANCE}.ini "/etc/ckan/${INSTANCE}/${INSTANCE}.ini.`date +%F_%T`.bak"
        fi
        paster make-config ckan /etc/ckan/${INSTANCE}/${INSTANCE}.ini

        if [[ ( "$LOCAL_DB" == "yes" ) ]]
        then
            sed -e "s,^\(sqlalchemy.url\)[ =].*,\1 = postgresql://${INSTANCE}:${password}@localhost/${INSTANCE}," \
                -i /etc/ckan/${INSTANCE}/${INSTANCE}.ini
        fi
        sed -e "s,^\(email_to\)[ =].*,\1 = root," \
            -e "s,^\(error_email_from\)[ =].*,\1 = ckan-${INSTANCE}@`hostname`," \
            -e "s,# ckan\.site_id = ckan.net,ckan.site_id = ${INSTANCE}," \
            -e "s,^\(cache_dir\)[ =].*,\1 = /var/lib/ckan/${INSTANCE}/data," \
            -e "s,^\(who\.config_file\)[ =].*,\1 = /etc/ckan/${INSTANCE}/who.ini," \
            -e "s,\"ckan\.log\",\"/var/log/ckan/${INSTANCE}/${INSTANCE}.log\"," \
            -e "s,#solr_url = http://127.0.0.1:8983/solr,solr_url = http://127.0.0.1:8983/solr," \
            -i /etc/ckan/${INSTANCE}/${INSTANCE}.ini
        sudo chown ckan${INSTANCE}:ckan${INSTANCE} /etc/ckan/${INSTANCE}/${INSTANCE}.ini
    fi
}

ckan_add_or_replace_database_user () {
    local INSTANCE password
    if [ "X$1" = "X" ] || [ "X$2" = "X" ] ; then
        echo "ERROR: call the function ckan_add_or_replace_database_user function with an INSTANCE name, and a password for postgresql e.g." 
        echo "       dgu 1U923hjkh8"
        echo "       You can generate a password like this: "
        echo "           < /dev/urandom tr -dc _A-Z-a-z-0-9 | head -c10"
        exit 1
    else
        INSTANCE=$1
        password=$2
        COMMAND_OUTPUT=`sudo -u postgres psql -c "SELECT 'True' FROM pg_user WHERE usename='${INSTANCE}'"`
        if ! [[ "$COMMAND_OUTPUT" =~ True ]] ; then
            echo "Creating the ${INSTANCE} user ..."
            sudo -u postgres psql -c "CREATE USER \"${INSTANCE}\" WITH PASSWORD '${password}'"
        else
            echo "Setting the ${INSTANCE} user password ..."
            sudo -u postgres psql -c "ALTER USER \"${INSTANCE}\" WITH PASSWORD '${password}'"
        fi
    fi
}

ckan_ensure_db_exists () {
    local INSTANCE
    if [ "X$1" = "X" ] ; then
        echo "ERROR: call the function ensure_db_exists function with an INSTANCE name, e.g." 
        echo "       dgu"
        exit 1
    else
        INSTANCE=$1
        COMMAND_OUTPUT=`sudo -u postgres psql -c "select datname from pg_database where datname='$INSTANCE'"`
        if ! [[ "$COMMAND_OUTPUT" =~ ${INSTANCE} ]] ; then
            echo "Creating the database ..."
            sudo -u postgres createdb -O ${INSTANCE} ${INSTANCE}
            paster --plugin=ckan db init --config=/etc/ckan/${INSTANCE}/${INSTANCE}.ini
        fi
    fi
}

ckan_create_wsgi_handler () {
    local INSTANCE
    if [ "X$1" = "X" ] ; then
        echo "ERROR: call the function create_wsgi_handler function with an INSTANCE name, e.g." 
        echo "       dgu"
        exit 1
    else
        INSTANCE=$1
        if [ ! -f "/var/lib/ckan/${INSTANCE}/wsgi.py" ]
        then
            sudo mkdir /var/lib/ckan/${INSTANCE}/pyenv
            sudo chown -R ckan${INSTANCE}:ckan${INSTANCE} /var/lib/ckan/${INSTANCE}/pyenv
            sudo -u ckan${INSTANCE} virtualenv --setuptools /var/lib/ckan/${INSTANCE}/pyenv
            echo "Attempting to install 'pip' 1.0 from pypi.python.org into pyenv to be used for extensions ..."
            sudo -u ckan${INSTANCE} /var/lib/ckan/${INSTANCE}/pyenv/bin/easy_install --upgrade "pip>=1.0" "pip<=1.0.99"
            echo "done."
            cat <<- EOF > /var/lib/ckan/${INSTANCE}/packaging_version.txt
	1.5
	EOF
            cat <<- EOF > /var/lib/ckan/${INSTANCE}/wsgi.py
	import os
	instance_dir = '/var/lib/ckan/${INSTANCE}'
	config_dir = '/etc/ckan/${INSTANCE}'
	config_file = '${INSTANCE}.ini'
	pyenv_bin_dir = os.path.join(instance_dir, 'pyenv', 'bin')
	activate_this = os.path.join(pyenv_bin_dir, 'activate_this.py')
	execfile(activate_this, dict(__file__=activate_this))
	# this is werid but without importing ckanext first import of paste.deploy will fail
	#import ckanext
	config_filepath = os.path.join(config_dir, config_file)
	if not os.path.exists(config_filepath):
	    raise Exception('No such file %r'%config_filepath)
	from paste.deploy import loadapp
	from paste.script.util.logging_config import fileConfig
	fileConfig(config_filepath)
	application = loadapp('config:%s' % config_filepath)
	from apachemiddleware import MaintenanceResponse
	application = MaintenanceResponse(application)
	EOF
        sudo chmod +x /var/lib/ckan/${INSTANCE}/wsgi.py
        fi
   fi
}

ckan_overwrite_apache_config () {
    local INSTANCE ServerName
    if [ "X$1" = "X" ] ; then
        echo "ERROR: call the function overwrite_apache_config function with an INSTANCE name, the server name and a server aliase e.g." 
        echo "       dgu catalogue.data.gov.uk dgu-live.okfn.org"
        exit 1
    else
        INSTANCE=$1
        ServerName=$2
        #rm /etc/apache2/sites-available/${INSTANCE}.common
        cat <<EOF > /etc/apache2/sites-available/${INSTANCE}.common

    # WARNING: Do not manually edit this file, it is desgined to be 
    #          overwritten at any time by the postinst script of 
    #          dependent packages

    # These are common settings used for both the normal and maintence modes

    DocumentRoot /var/lib/ckan/${INSTANCE}/static
    ServerName ${ServerName}

    <Directory />
        # XXX Should this be deny? We get a "Client denied by server configuration" without it
        allow from all
    </Directory>

    <Directory /etc/ckan/${INSTANCE}/>
        allow from all
    </Directory>

    <Directory /var/lib/ckan/${INSTANCE}/static>
        allow from all
    </Directory>

    Alias /dump /var/lib/ckan/${INSTANCE}/static/dump

    # Disable the mod_python handler for static files
    <Location /dump>
        SetHandler None
        Options +Indexes
    </Location>

    # this is our app
    WSGIScriptAlias / /var/lib/ckan/${INSTANCE}/wsgi.py

    # pass authorization info on (needed for rest api)
    WSGIPassAuthorization On

    # Deploy as a daemon (avoids conflicts between CKAN instances)
    # WSGIDaemonProcess ${INSTANCE} display-name=${INSTANCE} processes=4 threads=15 maximum-requests=10000
    # WSGIProcessGroup ${INSTANCE}

    ErrorLog /var/log/apache2/${INSTANCE}.error.log
    CustomLog /var/log/apache2/${INSTANCE}.custom.log combined
EOF
        #rm /etc/apache2/sites-available/${INSTANCE}
        cat <<EOF > /etc/apache2/sites-available/${INSTANCE} 
<VirtualHost *:80>
    # WARNING: Do not manually edit this file, it is desgined to be 
    #          overwritten at any time by the postinst script of 
    #          dependent packages
    Include /etc/apache2/sites-available/${INSTANCE}.common
</VirtualHost>
EOF
        #rm /etc/apache2/sites-available/${INSTANCE}.maint
        cat <<EOF > /etc/apache2/sites-available/${INSTANCE}.maint
<VirtualHost *:80>
    # WARNING: Do not manually edit this file, it is desgined to be 
    #          overwritten at any time by the postinst script of 
    #          dependent packages
    Include /etc/apache2/sites-available/${INSTANCE}.common

    # Maintenance mode
    RewriteEngine On
    RewriteRule ^(.*)/new /return_503 [PT,L]
    RewriteRule ^(.*)/create /return_503 [PT,L]      
    RewriteRule ^(.*)/authz /return_503 [PT,L]
    RewriteRule ^(.*)/edit /return_503 [PT,L]
    RewriteCond %{REQUEST_METHOD} !^GET$ [NC]
    RewriteRule (.*) /return_503 [PT,L]
</VirtualHost>
EOF
    fi
}
