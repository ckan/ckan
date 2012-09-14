import ckan
import ckan.lib.create_test_data
import paste.fixture
import paste.deploy
import routes
import ckan.tests
import ckan.config.middleware


class TestExampleIOrganizationFormPlugin:

    @classmethod
    def setup(cls):
        # Make a test app with the legacy templates turned off.
        config = paste.deploy.appconfig('config:test.ini',
                relative_to=ckan.tests.conf_dir)
        config.local_conf['ckan.legacy_templates'] = 'no'
        wsgiapp = ckan.config.middleware.make_app(
                config.global_conf, **config.local_conf)
        cls.app = paste.fixture.TestApp(wsgiapp)

        # This doesn't seem to work.
        ckan.plugins.load('example_iorganizationform')

        ckan.lib.create_test_data.CreateTestData.create()

    @classmethod
    def teardown(cls):
        ckan.model.repo.rebuild_db()

    def test_example_iorganizationform_plugin(self):

        # Get the new organization page.
        offset = routes.url_for(controller='organization', action='new')
        extra_environ = {'REMOTE_USER': 'tester'}
        response = self.app.get(offset, extra_environ=extra_environ)

        # Check that the custom Country Code field and its possible values
        # are there.
        assert '<select id="field-country-code" name="country_code">' in response
        assert '<option value="de">de</option>' in response
        assert '<option value="en">en</option>' in response
        assert '<option value="fr">fr</option>' in response
        assert '<option value="nl">nl</option>' in response

        # Check that the custom Website IRL field is there.
        assert '<input id="field-website-url" type="url" name="website_url" value=""' in response

        # Fill out the form and submit it.
        form = response.forms['organization-form']
        form['name'] = 'iorganizationform_test_organization'
        form['title'] = 'IOrganizationForm Test Organization'
        # Our custom Country Code field:
        form['country_code'] = 'fr'
        # Our custom Website URL field:
        form['website_url'] = 'ckan.org'
        response = form.submit('save', extra_environ=extra_environ)

        # The response from submitting the form should be a 302 Redirect to the
        # read page for the new organization.
        assert response.status == 302
        response = response.follow(extra_environ=extra_environ)
        assert response.status == 200
        assert response.request.url.endswith(
                '/organization/iorganizationform_test_organization')

        # Test the contents of the organization read page.
        assert '<h2 class="module-heading">Country Code</h2>' in response
        assert '<p class="module-content">fr</p>' in response
        assert '<h2 class="module-heading">Website</h2>' in response
        assert '<p class="module-content"><a href="http://ckan.org">http://ckan.org</a></p>' in response

        # Update the organization, changing the custom Country Code field.
        offset = routes.url_for(controller='organization', action='edit',
                id='iorganizationform_test_organization')
        response = self.app.get(offset, extra_environ=extra_environ)
        assert '<option value="fr" selected="selected">fr</option>' in (
                response)
        form = response.forms['organization-form']
        form['country_code'] = 'en'
        form['website_url'] = 'thedatahub.org'
        response = form.submit('save', extra_environ=extra_environ)
        assert response.status == 302
        response = response.follow(extra_environ=extra_environ)
        assert response.status == 200
        assert response.request.url.endswith(
                '/organization/iorganizationform_test_organization')

        # Test the contents of the updated organization read page.
        assert '<h2 class="module-heading">Country Code</h2>' in response
        assert '<p class="module-content">en</p>' in response
        assert '<h2 class="module-heading">Website</h2>' in response
        assert '<p class="module-content"><a href="http://thedatahub.org">http://thedatahub.org</a></p>' in response

        # Fetch the organization index page, just to test that the plugin's
        # search_template() method gets called.
        offset = routes.url_for(controller='organization', action='index')
        response = self.app.get(offset)
        assert response.status == 200

        # Fetch the organization history page, just to test that the plugin's
        # history_template() method gets called.
        offset = routes.url_for(controller='organization', action='history',
                id='iorganizationform_test_organization')
        response = self.app.get(offset)
        assert response.status == 200

        # TODO: It might be better to test that custom templates returned by
        # these methods are actually used, not just that the methods get
        # called.
        from ckanext.example_iorganizationform.plugin import \
                ExampleIOrganizationFormPlugin
        assert ExampleIOrganizationFormPlugin.num_times_organization_form_called == 2
        assert ExampleIOrganizationFormPlugin.num_times_edit_template_called == 1
        assert ExampleIOrganizationFormPlugin.num_times_read_template_called == 2
        assert ExampleIOrganizationFormPlugin.num_times_new_template_called == 1
        assert ExampleIOrganizationFormPlugin.num_times_index_template_called == 1
        assert ExampleIOrganizationFormPlugin.num_times_history_template_called == 1
