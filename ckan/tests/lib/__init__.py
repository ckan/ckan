from nose.tools import assert_equal

from ckan import model
import ckan.lib.search as search


def check_search_results(terms, expected_count, expected_packages=[]):
    # setting ext_boolean = 'any' makes sets search operator to OR instead
    # of the default AND
    query = {
        'q': unicode(terms),
        'extras': {'ext_boolean': 'all'}
    }
    result = search.query_for(model.Package).run(query)
    pkgs = result['results']
    count = result['count']
    assert_equal(count, expected_count)
    for expected_pkg in expected_packages:
        assert expected_pkg in pkgs, '%s : %s' % (expected_pkg, result)
