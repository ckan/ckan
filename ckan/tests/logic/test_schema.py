# encoding: utf-8

'''

We *don't* write tests for the schemas defined in :py:mod:`ckan.logic.schema`.
The validation done by the schemas is instead tested indirectly by the action
function tests.  The reason for this is that CKAN actually does validation in
multiple places: some validation is done using schemas, some validation is done
in the action functions themselves, some is done in dictization, and some in
the model.  By testing all the different valid and invalid inputs at the action
function level, we catch it all in one place.

'''
