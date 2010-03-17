=====================================================
Distributed Data Version Control: Format and Protocol
=====================================================

See also: http://knowledgeforge.net/ckan/trac/wiki/DistributingChanges

Aim
===

Facilitate collaboration and information sharing via the use of data versioning and the transmission of associated changesets between multiple peer nodes. It is the P2P nature of this model (as opposed to classic server-client approach) that leads to it being termed: "Distributed Version Control".

We are particularly interested in transmitting "structured" data (i.e. not BLOBs) especially data coming from a specified domain model.


Existing Work
=============

Distributed Revision/Version Control Systems (DVCS) such as Mercurial_ and Git_ perform a very similar function in versioning of files and filesytem trees to what we seek to do with data.

Given this similarity, the protocol and format specified here directly reuse many of the concepts and approach of these existing solutions.

More on the analogies can be found on the wiki page which details the specific application of this protocol to CKAN: http://knowledgeforge.net/ckan/trac/wiki/DistributingChanges 

Further details of the distributed revision control systems for code can be found in the appendix below.

.. _Mercurial: http://mercurial.selenic.com/
.. _Git: http://git-scm.com/


Use cases
=========

1. data.gov.uk and ckan.net
---------------------------

One specific use case is pulling and pushing metadata between different CKAN registries.

In particular we Want to make data on data.gov.uk (hmg.ckan.net) available in a public CKAN instance. We will therefore end up with:

  1. Package on data.gov.uk
  2. Package on ckan.net

Need to keep these two representations of the package in "sync".

Remarks: This is easy if we only edit in one place.  But what if we want to let community edit on ckan.net? Two options:

  1. have 2 copies on ckan.net one community owned and one locked down
    * Pro: easy to keep stuff separate
    * Con: terrible user experience and still have issue that two items can diverge
  2. Have one copy that is world editable into which gets *merged back* into the official data every so often


Abstract Problem Description
============================

Let us consider three different nodes: A,B,C

Setup 0:
--------

Simple 1-way::

  A ----> B

Setup 1:
--------

Simple bi-directional::

  A <---> B

Setup 3:
--------

3-node single way::

  A ----> B
   \     /
    \   /
      V
      C

In words:

  1. Changes go directly from A to C
  2. Changes go directly from A to B. Then changes from B are pulled to C

One must avoid duplicating changes pushed directly to C from A again when pushing changes from B to C.

Setup 4:
--------

Full bidirectional 3-node::

  A <-----> B
   A       A
    \     / 
     \   /
       V
       C

Terminology
===========

  * Revision: metadata about a change(set)
  * Patch: payload of a change(set) - description of the changes to the data/domain model 
  * Changeset: the combination of a Revision and its associated Patch
  * Node/Repository: a given standalone instance containing data/domain objects.

Remarks:

  * Changeset's Revision records the ID of its Parents.
  * The set of changesets in a given Repository fomr a directed acyclic graph
  * The "leaves" of this graph are termed Heads

Formats
=======

Revision Format
---------------

  * id: uuid OR sha1 hash of patch + parent rev ids (like mercurial)
  * timestamp
  * parent ids
  * author - free text field
  * message
  * ddvc format no (e.g. 1.0)
  * (extras: arbitrary addtional attributes - like X-headers)

Patch Format
------------

  * Patch format identifier (e.g. text diff plus manifest diff for normal source version control)
  * Patch format version
  * Payload: patch in format specified by patch format

For CKAN patch format is as follows:
  * List of object ids
  * For each object id diff of all fields presented as JSON-encoded strings


Protocol
========

The most complex part of this specification is the definition of the protocl especiall the patch application protocol and the merge process.

TODO


Appendix: Distributed Revision Control for Source Code
======================================================

Mercurial
---------

Basic overview of the Mercurial model: http://mercurial.selenic.com/wiki/UnderstandingMercurial

Git
---

Glossary: http://www.kernel.org/pub/software/scm/git/docs/gitglossary.html

Technical Docs: http://repo.or.cz/w/git.git?a=tree;f=Documentation/technical;hb=HEAD

