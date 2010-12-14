================
Package Importer
================


Introduction
============

This part of the CKAN web interface provides an easy way to import packages 
into CKAN in bulk via a spreadsheet. It fills the gap between entry via a 
simple form (/package/new) and the RESTful API (/api/rest).

** NB: This feature is not currently available. **


Details
=======

Importing a package with the same name as one that exists in the CKAN database results in the new package overwriting the existing one. There is a warning for this.

To perform an import, the user must be logged in. To add a package to a group, the user must have priviledges to edit the particular group.

Format
======

The details of the packages should be stored in an Excel spreadsheet or CSV file. In Excel format, the package details should be the first (or only) sheet of a workbook.

The importer looks for a header row (which must contain 'name' or 'title') and below that all the rows are the package details. The header row can contain any or all of the field names, but must include 'name' or 'title'. If the 'name' is not specified then a unique name will be generated from the title.

Example
=======

+-------+-----------+-----------+--------------------------------+------------------------+---+
|       | A         | B         | C                              | D                      | E |
+=======+===========+===========+================================+========================+===+
| **1** | Packages  |           |                                |                        |   |
+-------+-----------+-----------+--------------------------------+------------------------+---+
| **2** |           |           |                                |                        |   |
+-------+-----------+-----------+--------------------------------+------------------------+---+
| **3** | name      | title     | resource-0-url                 | tags                   |   |
+-------+-----------+-----------+--------------------------------+------------------------+---+
| **4** | wikipedia | Wikipedia | http://download.wikimedia.org/ | encyclopedia reference |   |
+-------+-----------+-----------+--------------------------------+------------------------+---+
| **5** | tviv      | TV IV     | http://tviv.org/Category:Grids | tv  encyclopaedia      |   |
+-------+-----------+-----------+--------------------------------+------------------------+---+
| **6** |           |           |                                |                        |   |
+-------+-----------+-----------+--------------------------------+------------------------+---+

Fields
======

Each package has many fields.

+------------------------+----------------------------------------+------------------------------------+
| Name                   | Example value                          | Notes                              |
+========================+========================================+====================================+
| name                   | wikipedia-blind                        |                                    |
+------------------------+----------------------------------------+------------------------------------+
| title                  | Wikipedia for the Blind                |                                    |
+------------------------+----------------------------------------+------------------------------------+
| notes                  | Maintained until 2008                  |                                    |
+------------------------+----------------------------------------+------------------------------------+
| url                    | http://blind.wikipedia.org/            |                                    |
+------------------------+----------------------------------------+------------------------------------+
| resource-0-url         | http://blind.wikipedia.org/dump-en.csv | Number resources from 0.           |
+------------------------+----------------------------------------+------------------------------------+
| resource-0-format      | csv                                    |                                    |
+------------------------+----------------------------------------+------------------------------------+
| resource-0-description | English version                        |                                    |
+------------------------+----------------------------------------+------------------------------------+
| resource-0-hash        | e0d123e5f31                            | Hash of the resource               |
+------------------------+----------------------------------------+------------------------------------+
| resource-1-url         | http://blind.wikipedia.org/dump-fr.csv |                                    |
+------------------------+----------------------------------------+------------------------------------+
| resource-1-format      | csv                                    |                                    |
+------------------------+----------------------------------------+------------------------------------+
| resource-1-description | French version                         |                                    |
+------------------------+----------------------------------------+------------------------------------+
| resource-1-hash        | 78bfdf5a008                            |                                    |
+------------------------+----------------------------------------+------------------------------------+
| tags                   | encyclopedia blind format-csv          | Space separated list               |
+------------------------+----------------------------------------+------------------------------------+
| author                 | John Doe                               |                                    |
+------------------------+----------------------------------------+------------------------------------+
| author_url             | john@doe.com                           |                                    |
+------------------------+----------------------------------------+------------------------------------+
| maintainer             | John Doe                               |                                    |
+------------------------+----------------------------------------+------------------------------------+
| maintainer_url         | john@doe.com                           |                                    |
+------------------------+----------------------------------------+------------------------------------+
| license                | OKD Compliant::UK Click Use PSI        | License name                       |
+------------------------+----------------------------------------+------------------------------------+
| [arbitrary]            |                                        | Any field name and a string value. |
+------------------------+----------------------------------------+------------------------------------+
| groups                 | blind-picks                            | Space separated list of group      |
|                        |                                        | names to add package to.           |
+------------------------+----------------------------------------+------------------------------------+

