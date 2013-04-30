========
Overview
========

.. Intro para
    - Remember you're not selling CKAN this is for sysadmins
    - What is CKAN?
    - What does it have and what makes it ideal for what?
    - Who is CKAN "aimed at"
    - Who is it developed by
    - Open source
    - What is this page?
    - Link to ckan.org

    the world’s leading open-source data portal platform 

    the open source data portal software

    CKAN is a powerful data management system that makes data **accessible** – by
    providing tools to streamline **publishing**, sharing, **finding** and **using** data. CKAN
    is aimed at data publishers (national and regional governments, companies and
    organizations) wanting to make their data open and available.

    Used to power both official and community data portals, CKAN was developed by
    the non-profit Open Knowledge Foundation to run the Datahub.io. It now powers
    more than 40 data hubs around the world, including portals for local, national
    and international government, such as the UK’s data.gov.uk and the European
    Union’s publicdata.eu.

    * * *

Welcome to CKAN's documentation. This section will give an overview of CKAN,
including it's major features and key concepts.


--------------------
Datasets & Resources
--------------------

Data in CKAN is published as datasets, which contain resources. A CKAN
**resource** is a data file (such as a CSV or Excel file) that is either linked
to from CKAN or uploaded to CKAN, or a link to a data API, plus some associated
metadata (name, description, etc). A **dataset** is a collection of one or more
resources, plus some associated metadata (title, description, license, etc).
Datasets and resources can be added to CKAN using the web interface, or over
the API.


-------------
Web Interface
-------------

.. Publishing data: web interface, API, harvester.
With CKAN's web interface, users can easily add and edit datasets and
resources.


---------
FileStore
---------

If a data file has already been published on another site, a user can enter a
link to the file into a CKAN resource. If they would like to publish the file
using CKAN, CKAN's FileStore adds an *Upload* button and can upload files to
the CKAN server itself or to cloud storage such as Amazon S3 or Google Cloud
Storage.


---------
DataStore
---------

Whether a resource file has been linked-to from CKAN or uploaded to CKAN, the
data contained within the file can be pulled into CKAN's DataStore. The
DataStore is a database for structured storage of data, that provides an API
for applications to search and update the data without having to download the
entire data file. CKAN's data previewer uses the DataStore API to provide
table, graph and map visualisations of data.

.. todo:: How does data get into the datastore?


------
Search
------

CKAN's **search** interface lets you search for datasets using quick
‘Google-style’ key word searches. You can filter search results according to
the datasets' organizations, groups, tags, file formats, or licenses, and sort
search results by relevance, modification time, or name.

.. _solr: http://lucene.apache.org/solr/


----------------------------
Activity Streams & Following
----------------------------

As datasets, groups and organizations are added and updated, CKAN logs each
activity in an activity stream. You can follow a users, datasets, groups and
organizations and get notified on your CKAN dashboard or (optionally) by email
when they have new activity.

.. todo:

   The history pages/revisions aren't mentioned here, because they aren't
   exposed in the web interface in 2.0. Once we decide what to do with the
   history pages (put them back in? or merged them with activity streams?)
   we can update these.


-------------------------------
Data Preview and Visualisations
-------------------------------

CKAN's built-in data viewer displays previews and visualisations of data from
CKAN resources, including:

Table view: If structured data is uploaded or linked to CKAN as a .csv or Excel table, the DataStore loads it into a database, allowing CKAN to give a range of ways to view and process the data. Initially it is displayed as a table. The user can sort the data on particular columns, filter or facet by values, or hide columns entirely.

Graphing data: You can also display the data on a graph, choosing the variables on the axes and comparing a number of variables by graphing them together on the same y-axis.

Mapping data: If the table has columns that CKAN recognises as latitude and longitude, it can plot the data points on a map, which can be panned (dragged) and zoomed. Selecting a data point displays all the field values in the corresponding row.

Image data: CKAN’s previewing is not restricted to tabular data. Common image formats will be displayed, and if a resource is a web page, it will also be previewed directly in the CKAN dataset.

Roll your own: CKAN’s built-in previews use the DataStore’s API. If you have your own data previewing tools or are planning to build them, it’s easy to plug them into the API so that you can create visualisations on the fly, without the need for users to download the data. 


---------------
Tags and Groups
---------------

Datasets in CKAN can be sorted into tags and groups. **Tags** are free-form way
to sort datasets, anyone who can edit a dataset can add any tag to that
dataset, and can create new tags. **Groups** are more controlled, only group
members can add datasets to a group, and group admins add new members to
groups.

.. todo:: Tag vocabularies?


-----------------------------
Organizations & Authorization
-----------------------------

**Organizations** are the primary way of controlling access to datasets in
CKAN. Organization admins add users to organizations, and only members of
organizations can add datasets to the organization or update the organization's
datasets. **Private datasets** can only be seen by members of the datasets'
organizations. When they're ready to publish, organization admins make datasets
public. As with tags and groups, users can browse and search datasets by
organization.


-------------
Configuration
-------------

CKAN sysadmins can configure CKAN using a simple web interface. More advanced
configuration options can be set in CKAN's configuration file.

-------
Theming
-------

If you're comfortable with HTML and CSS, you can create your own custom CKAN
theme. CKAN themes have complete freedom to modify and override all the
templates, so you can make it look however you want.


----------
Extensions
----------


---
API
---

-----------------------------------------
Command-Line Interface for Administrators
-----------------------------------------

For sysadmins, CKAN provides a command-line interface
