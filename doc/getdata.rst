========================
'Getdata' import scripts
========================


Introduction
============

'Getdata' is a collection of custom scripts for importing batches of records from a spreadsheet into a CKAN database. You customize one for reading/downloading data in the form of CSV or XML (for example) and it adds or updates CKAN database records accordingly. Because each one is a custom importer, they can be written to be very flexible and powerful.

Overview
========

The scripts are stored in::
 ckan/getdata

The basics of operation are:

1. Read in a record from the new/updated external data.

2. Check to see if a Package for this record already exists in the CKAN database. If so, edit it, otherwise create a new Package.

3. Edit the Package according to the external data. 'key-value' pairs (Extra fields) can be added as necessary.

4. Loop back to 1 until all the records have been edited.

5. Create a new_revision for these changes.

6. Commit the changes to the database.

A script is run on the paster commandline. A new script has to be setup in ckan/lib/cli.py and this is run like this::

$ paster db load-data4nr data.csv

Notes
=====

There is a complication in the revision system to watch out for. When you query the CKAN database, wise to (and therefore automatic to) flush the database session first. For revisioned objects (such as Package or PackageTag) these can only be committed when a Revision is open. So it is best to avoid queries whilst editing a Package object. This can be difficult to avoid as when you add a tag to a package, it needs to see if the Tag object already exists before it creates a new one. In this case you can consider telling the query not to autoflush like this::

  pkg.add_tag_by_name(tag, autoflush=False)

But of course you need to avoid adding duplicate tags before you do flush. So in this case it makes sense using a new revision for each record, and therefore doing a commit_and_remove() for each record too.