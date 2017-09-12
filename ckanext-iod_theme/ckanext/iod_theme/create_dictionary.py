#!/usr/bin/env python
import urllib2
import urllib
import json
import pprint

# Put the details of the vocabularies we're going to create into a dict.
vocabulary_dict = open('vocabularies.json')

# Use the json module to dump the dictionary to a string for posting.
data_string = urllib.quote(json.loads(vocabulary_dict))

# We'll use the package_create function to create a new vocabulary.
request = urllib2.Request(
    'http://www.my_ckan_site.com/api/action/vocabulary_create')

# Creating a vocabulary requires an authorization header.
# Replace *** with your API key, from your user account on the CKAN site
# that you're creating the vocabulary on.
request.add_header('X-CKAN-API-Key', '64856b4a-3049-4e4f-8fd0-811e55af3a26')

# Make the HTTP request.
response = urllib2.urlopen(request, data_string)
assert response.code == 200

# Use the json module to load CKAN's response into a dictionary.
response_dict = json.loads(response.read())
assert response_dict['success'] is True

# vocabulary_create returns the created vocabulary as its result.
created_vocabulary = response_dict['result']
pprint.pprint(created_vocabulary)
