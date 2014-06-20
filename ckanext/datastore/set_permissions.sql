/*
This script configures the permissions for the datastore. If you are seeing this
as a result of running `paster datastore set-permissions`, then depending on the
configuration of your database, you can either:

a) Copy and paste this script and execute it as a database superuser by hand.
   This mechanism is preferred, especially if your database is on a different
   server from CKAN, as you do not need to configure superuser access to your
   database over the network.

b) If you have superuser access to your database over the network, AND ARE AWARE
   OF THE SECURITY IMPLICATIONS OF SUCH A CONFIGURATION, you can re-run `paster
   datastore set-permissions` with the "--execute" argument to connect to the
   database and run the script.

The script ensures that the datastore read-only user will only be able to select
from the datastore database but has no create/write/edit permission or any
permissions on other databases.
*/

-- revoke permissions for the read-only user
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
REVOKE USAGE ON SCHEMA public FROM PUBLIC;

GRANT CREATE ON SCHEMA public TO "{mainuser}";
GRANT USAGE ON SCHEMA public TO "{mainuser}";

GRANT CREATE ON SCHEMA public TO "{writeuser}";
GRANT USAGE ON SCHEMA public TO "{writeuser}";

-- take connect permissions from main db
REVOKE CONNECT ON DATABASE "{maindb}" FROM "{readuser}";

-- grant select permissions for read-only user
GRANT CONNECT ON DATABASE "{datastoredb}" TO "{readuser}";
GRANT USAGE ON SCHEMA public TO "{readuser}";

-- grant access to current tables and views to read-only user
GRANT SELECT ON ALL TABLES IN SCHEMA public TO "{readuser}";

-- grant access to new tables and views by default
ALTER DEFAULT PRIVILEGES FOR USER "{writeuser}" IN SCHEMA public
   GRANT SELECT ON TABLES TO "{readuser}";
