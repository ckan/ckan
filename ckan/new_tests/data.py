'''A collection of static data for use in tests.

These are functions that return objects because the data is intended to be
read-only: if they were simply module-level objects then one test may modify
eg. a dict or list and then break the tests that follow it.

'''


def typical_user():
    return {'name': 'fred',
            'email': 'fred@fred.com',
            'password': 'wilma',
            }
