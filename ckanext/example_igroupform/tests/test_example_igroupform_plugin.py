import ckan
import ckan.lib.create_test_data
import paste.fixture
import pylons.test
import routes


class TestExampleIGroupFormPlugin:

    @classmethod
    def setup(cls):
        cls.app = paste.fixture.TestApp(pylons.test.pylonsapp)
        ckan.plugins.load('example_igroupform')
        ckan.lib.create_test_data.CreateTestData.create()

    @classmethod
    def teardown(cls):
        ckan.model.repo.rebuild_db()

    def test_example_igroupform_plugin(self):

        # Get the new group page.
        offset = routes.url_for(controller='group', action='new')
        extra_environ = {'REMOTE_USER': 'tester'}
        response = self.app.get(offset, extra_environ=extra_environ)

        # Check that the custom Country Code field and its possible values
        # are there.
        assert '<select id="country_code" name="country_code">' in response
        assert '<option value="de">de</option' in response
        assert '<option value="en">en</option' in response
        assert '<option value="fr">fr</option' in response
        assert '<option value="nl">nl</option' in response

        # Check that the custom Website IRL field is there.
        assert '<input id="website_url" name="website_url" type="text" value="" />' in response

        # Fill out the form and submit it.
        form = response.forms['group-edit']
        form['name'] = 'igroupform_test_group'
        form['title'] = 'IGroupForm Test Group'
        # Our custom Country Code field:
        form['country_code'] = 'fr'
        # Our custom Website URL field:
        form['website_url'] = 'ckan.org'
        response = form.submit('save', extra_environ=extra_environ)

        # The response from submitting the form should be a 302 Redirect to the
        # read page for the new group.
        assert response.status == 302
        response = response.follow(extra_environ=extra_environ)
        assert response.status == 200
        assert response.request.url.endswith(
                '/group/igroupform_test_group')

        # Test the contents of the group read page.
        assert '<h3>Group Country Code</h3>' in response
        assert '<span id="country_code">fr</span>' in response
        assert '<h3>Group Website</h3>' in response
        assert '<a href="http://ckan.org">http://ckan.org</a>' in response

        # Update the group, changing the custom Country Code field.
        offset = routes.url_for(controller='group', action='edit',
                id='igroupform_test_group')
        response = self.app.get(offset, extra_environ=extra_environ)
        assert '<option value="fr" selected="selected">fr</option>' in (
                response)
        form = response.forms['group-edit']
        form['country_code'] = 'en'
        form['website_url'] = 'thedatahub.org'
        response = form.submit('save', extra_environ=extra_environ)
        assert response.status == 302
        response = response.follow(extra_environ=extra_environ)
        assert response.status == 200
        assert response.request.url.endswith(
                '/group/igroupform_test_group')

        # Test the contents of the updated group read page.
        assert '<h3>Group Country Code</h3>' in response
        assert '<span id="country_code">en</span>' in response
        assert '<h3>Group Website</h3>' in response
        assert '<a href="http://thedatahub.org">http://thedatahub.org</a>' in response

        # Fetch the group index page, just to test that the plugin's
        # search_template() method gets called.
        offset = routes.url_for(controller='group', action='index')
        response = self.app.get(offset)
        assert response.status == 200

        # Fetch the group history page, just to test that the plugin's
        # history_template() method gets called.
        offset = routes.url_for(controller='group', action='history',
                id='igroupform_test_group')
        response = self.app.get(offset)
        assert response.status == 200

        # TODO: It might be better to test that custom templates returned by
        # these methods are actually used, not just that the methods get
        # called.
        from ckanext.example_igroupform.plugin import \
                ExampleIGroupFormPlugin
        assert ExampleIGroupFormPlugin.num_times_group_form_called == 2
        assert ExampleIGroupFormPlugin.num_times_edit_template_called == 1
        assert ExampleIGroupFormPlugin.num_times_read_template_called == 2
        assert ExampleIGroupFormPlugin.num_times_new_template_called == 1
        assert ExampleIGroupFormPlugin.num_times_index_template_called == 1
        assert ExampleIGroupFormPlugin.num_times_history_template_called == 1
