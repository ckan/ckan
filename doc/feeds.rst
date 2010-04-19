==========
CKAN Feeds
==========

Introduction
============

Access to the CKAN metadata is provided in the RESTful API, but to help users in touch with changes to the data, CKAN also provides feeds. The main feed provides a list of recent changes to all packages, and there are also individual feeds for each package.

Requests
========

The main feed is at::

/revision/list?format=atom&days=1

For example, to see all the changes made to packages on ckan.net in the past day, browse address: `<http://ckan.net/revision/list?format=atom&days=1>`_

In addition, each package has a feed at::

/package/history/PACKAGENAME?format=atom&days=7

You might want to keep track of developments of the Ordnance Survey open data seen here `<http://ckan.net/package/ordnance_survey>`_, for example. Here is the corresponding URL you'd add to your RSS/Atom Reader: `<http://ckan.net/package/history/ordnance_survey?format=atom&days=7>`_

Format
======

The feeds are in Atom format.

Each 'entry' in the feed corresponds to a Revision, which is a set of changes. 

The Package feed is a subset of the Main Feed, with only the Revisions that reflect a change in that particular package.

The details given for each Revision are:

+===========+=====================================+
| field     | Description                         |
+===========+=====================================+
| updated / | Date & time of the change, given    | 
| published | in ISO format.                      |
+-----------+-------------------------------------+
| author    | 'name' is login name or IP address. |
+-----------+-------------------------------------+
| link      | Link to Revision in the web         |
|           | interface.                          |
+-----------+-------------------------------------+
| summary   | Log message for the revision. Also, |
|           | for the main feed, details of       |
|           | packages changes, created and       |
|           | deleted. See below.                 |
+-----------+-------------------------------------+

Example main feed::

  <?xml version="1.0" encoding="utf-8"?>
  <feed xmlns="http://www.w3.org/2005/Atom" xml:lang="None">
    <title>CKAN Package Revision History</title>
    <link href="/revision/list/" rel="alternate"></link>
    <id>/revision/list/</id>
    <updated>2010-04-18T21:17:57Z</updated>
    <entry>
      <title>rdbc6b54d-1fd1-4b13-b250-340a01646909 [pgcanada:]</title>
      <link href="/revision/read/dbc6b54d-1fd1-4b13-b250-340a01646909" rel="alternate"></link>
      <updated>2010-04-18T21:17:57Z</updated>
      <author><name>208.65.246.156</name></author>
      <id>tag:,2010-04-18:/revision/read/dbc6b54d-1fd1-4b13-b250-340a01646909</id>
      <summary type="html">Packages affected: [pgcanada:].</summary>
    </entry>
    <!-- ...other entries... -->
  </feed>

Example package feed for package 'water_voles'::

 <?xml version="1.0" encoding="utf-8"?>
 <feed xmlns="http://www.w3.org/2005/Atom" xml:lang="None">
   <title>CKAN Package Revision History</title>
   <link href="/revision/read/water_voles" rel="alternate"></link>
   <id>/revision/read/water_voles</id>
   <updated>2010-04-19T15:32:28Z</updated>
   <entry>
     <title>Creating test data.</title>
     <link href="/revision/read/2bad6982-2394-4187-b289-2ed77ad25d65" rel="alternate"></link>
     <updated>2010-04-19T15:30:00Z</updated>
     <published>2010-04-19T15:30:00Z</published>
     <author><name>http://someone.somecompany.com</name></author>
     <id>tag:,2010-04-19:/revision/read/2bad6982-2394-4187-b289-2ed77ad25d65</id>
     <summary type="html">Log message: Added a test package.</summary>
   </entry>
   <!-- ...other entries... -->
 </feed>

Main feed summary
=================

The main field provides a little more detail to the edits made to packages. In each entry summary, there is a list of packages affected, and the change to each is described as 'created', 'updated' or 'deleted'. For example::

 <summary type="html>Packages affected: [hospital_performance:created].</summary>

For package updates, some further information is provided if there are changes to the package's resources, or the 'date_updated' extra field. For example::

 Packages affected: [water_voles:updated:resources].

or::

 Packages affected: [water_voles:updated:date_updated].

(The date_updated field is highlighted for a particular use of CKAN and this feature may be generalised in the future.)

A revision may have changes to several packages, particularly if it was created using the API. In this case, the package list is space separated::

 Packages affected: [hospital_performance:created water_voles:edited bus_stops:edited:resources].</summary>
