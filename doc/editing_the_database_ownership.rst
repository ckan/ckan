==============================
Editing the database ownership
==============================

This tutorial shows you how to change a CKAN database's ownership. 

Now that multiple CKAN instances on the same server are now supported you have a different database and database user for each instance. If you want to load one database dump into another database, you therefore have to change the ownership of the tables to match the instance. I've written some simple SQL to help. Here's a brief tutorial to show how to restore a database dump to a different instance...

Let's copy a database dump from the "live" database to our new instance called "test" for testing.

1. First stop Apache so there are no active database connections::

    sudo /etc/init.d/apache2 stop

2. Drop the old database and restore the new one (setting up the plpgsql language as you do)::

    sudo -u postgres dropdb test
    sudo -u postgres createdb test
    sudo -u postgres createlang plpgsql test
    sudo -u postgres psql test -f to_restore.pg_dump

3. Change the table permissions (in this case the old instance name was called live, the new one is test)::

    sudo -u postgres psql test

Then from the psql command line interface run::

 begin;
 CREATE OR REPLACE FUNCTION changeowner(text, text)
 RETURNS TEXT STRICT VOLATILE AS '
 DECLARE
   old ALIAS FOR $1;
   new ALIAS FOR $2;
   rel record;
   sql text;
 BEGIN
   FOR rel IN select * from pg_tables where tableowner=old
   LOOP sql :=  ''ALTER TABLE "'' || rel.tablename || ''" OWNER to '' || new;
       RAISE NOTICE ''%'', sql;
       EXECUTE sql;
   END LOOP;
   RETURN ''OK'';
 END;
 ' LANGUAGE 'plpgsql';
 SELECT  changeowner('live', 'test');
 commit;
 \q

You will need to change the call to ``changeowner('live', 'test');`` to reflect the old and new names of the database owner. Now your test instance has the correct permissions.
