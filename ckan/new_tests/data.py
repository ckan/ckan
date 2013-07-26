'''A collection of static data for use in tests.

These are functions that return objects because the data is intended to be
read-only: if they were simply module-level objects then one test may modify
eg. a dict or list and then break the tests that follow it.

'''


def typical_user():
    '''Return a dictionary representation of a typical, valid CKAN user.'''

    return {'name': 'fred',
            'email': 'fred@fred.com',
            'password': 'wilma',
            }


def validator_data_dict():
    '''Return a data dict with some arbitrary data in it, suitable to be passed
    to validator functions for testing.

    '''
    return {('other key',): 'other value'}


def validator_errors_dict():
    '''Return an errors dict with some arbitrary errors in it, suitable to be
    passed to validator functions for testing.

    '''
    return {('other key',): ['other error']}
