'''Unit tests for ckan/logic/action/update.py.

'''
import ckan.new_tests.helpers as helpers
import ckan.new_tests.data as data


def setup_module():
    helpers.reset_db()

# Tests for user_update:
#
# - Test for success:
#   - Typical values
#   - Edge cases
#   - If multiple params, test with different combinations
# - Test for failure:
#   - Common mistakes
#   - Bizarre input
#   - Unicode
# - Cover the interface
# - Can we somehow mock user_create?
#
# Correct and incorrect ID


def test_user_update():
    '''Test that updating a user's metadata fields works successfully.

    '''
    # Prepare
    user = helpers.call_action('user_create', **data.TYPICAL_USER)

    # Execute
    user['name'] = 'updated_name'
    user['about'] = 'updated_about'
    helpers.call_action('user_update', **user)

    # Assert
    updated_user = helpers.call_action('user_show', id=user['id'])
    # Note that we check each updated field seperately, we don't compare the
    # entire dicts, only assert what we're actually testing.
    assert user['name'] == updated_user['name']
    assert user['about'] == updated_user['about']


def test_user_update_with_invalid_id():
    pass


def test_user_update_with_nonexistent_id():
    pass


def test_user_update_with_no_id():
    pass


def test_user_update_with_custom_schema():
    pass


def test_user_update_with_invalid_name():
    pass


def test_user_update_with_invalid_password():
    pass


def test_user_update_with_deferred_commit():
    pass


# TODO: Valid and invalid values for other fields.


def test_user_update_activity_stream():
    pass
