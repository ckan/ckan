'''Unit tests for ckan/logic/action/update.py.

'''
import ckan.model as model
import ckan.new_tests.logic as logic
import ckan.new_tests.test_data as test_data

def setup_module():
    model.Session.close_all()
    model.repo.clean_db()
    model.repo.init_db()

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
    user = logic.call_action('user_create', **test_data.FRED)

    # Execute
    user['name'] = 'updated_name'
    user['about'] = 'updated_about'
    logic.call_action('user_update', **user)

    # Assert
    updated_user = logic.call_action('user_show', id=user['id'])
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
