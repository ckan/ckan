import ckan.model as model
from ckan.tests import *
from ckan.lib.create_test_data import CreateTestData

import ckan.model.user


class TestUser(object):

    @classmethod
    def setup_class(self):
        CreateTestData.create()

    @classmethod
    def teardown_class(self):
        model.Session.remove()
        model.repo.rebuild_db()

    def test_number_of_edits(self):
        # initially annafan won't have made any edits
        assert model.User.by_name(u'annafan').number_of_edits() == 0, \
                    "annafan shouldn't have made any edits"

        # so we'll get him to edit his package twice
        for i in [1,2]:

            rev = model.repo.new_revision()
            pkg = model.Package.by_name(u'annakarenina')
            pkg.notes = u'Changed notes %i' % i
            rev.author = u'annafan'
            model.repo.commit_and_remove()

            #and each time check that number_of_edits is correct
            assert model.User.by_name(u'annafan').number_of_edits() == i, \
                   "annafan should have made %i edit(s)" % i


    def test_number_of_administered_packages(self):
        model.User.by_name(u'annafan').number_administered_packages() == 1, \
            "annafan should own one package"
        model.User.by_name(u'joeadmin').number_administered_packages() == 0, \
            "joeadmin shouldn't own any packages"


    def test_search(self):
        anna_names = [a.name for a in  model.User.search('anna').all()]
        assert anna_names==['annafan'], \
            "Search for anna should find annafan only."

        test_names = [a.name for a in  model.User.search('test').all()]
        assert ( len(test_names) == 2 and
                 'tester' in test_names and
                 'testsysadmin' in test_names ), \
                 "Search for test should find tester and testsysadmin (only)"




