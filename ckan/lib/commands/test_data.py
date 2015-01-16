
from ckan.lib.commands import CkanCommand


class CreateTestDataCommand(CkanCommand):
    '''Create test data in the database.
    Tests can also delete the created objects easily with the delete() method.

    create-test-data              - annakarenina and warandpeace
    create-test-data search       - realistic data to test search
    create-test-data gov          - government style data
    create-test-data family       - package relationships data
    create-test-data user         - create a user 'tester' with api key
                                    'tester'
    create-test-data translations - annakarenina, warandpeace, and some test
                                    translations of terms
    create-test-data vocabs       - annakerenina, warandpeace, and some test
                                    vocabularies
    create-test-data hierarchy    - hierarchy of groups
    '''
    summary = __doc__.split('\n')[0]
    usage = __doc__
    max_args = 1
    min_args = 0

    def command(self):
        self._load_config()
        self._setup_app()
        from create_test_data import CreateTestData

        if self.args:
            cmd = self.args[0]
        else:
            cmd = 'basic'
        if self.verbose:
            print 'Creating %s test data' % cmd
        if cmd == 'basic':
            CreateTestData.create_basic_test_data()
        elif cmd == 'user':
            CreateTestData.create_test_user()
            print 'Created user %r with password %r and apikey %r' % \
                ('tester', 'tester', 'tester')
        elif cmd == 'search':
            CreateTestData.create_search_test_data()
        elif cmd == 'gov':
            CreateTestData.create_gov_test_data()
        elif cmd == 'family':
            CreateTestData.create_family_test_data()
        elif cmd == 'translations':
            CreateTestData.create_translations_test_data()
        elif cmd == 'vocabs':
            CreateTestData.create_vocabs_test_data()
        elif cmd == 'hierarchy':
            CreateTestData.create_group_hierarchy_test_data()
        else:
            print 'Command %s not recognized' % cmd
            raise NotImplementedError
        if self.verbose:
            print 'Creating %s test data: Complete!' % cmd
