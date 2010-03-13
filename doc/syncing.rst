==============================
Syncing Between CKAN Instances
==============================

Aim: to support pulling and pushing metadata between different CKAN registries.

This is, in essence, a distributed database problem.

Use cases
=========

1. data.gov.uk and ckan.net
---------------------------

Want to make data on data.gov.uk (hmg.ckan.net) available in a public CKAN instance. We will therefore end up with:

  1. Package on data.gov.uk
  2. Package on ckan.net

Need to keep these two representations of the package in "sync".

Remarks: This is easy if we only edit in one place.  But what if we want to let community edit on ckan.net? Two options:

  1. have 2 copies on ckan.net one community owned and one locked down
    * Pro: easy to keep stuff separate
    * Con: terrible user experience and still have issue that two items can diverge
  2. Have one copy that is world editable into which gets *merged back* into the official data every so often

