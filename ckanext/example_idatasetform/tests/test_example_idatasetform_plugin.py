import ckan
import ckan.lib.create_test_data
import paste.fixture
import pylons.test
import routes


class TestExampleIDatasetFormPlugin:

    @classmethod
    def setup(cls):
        cls.app = paste.fixture.TestApp(pylons.test.pylonsapp)
        ckan.plugins.load('example_idatasetform')
        ckan.lib.create_test_data.CreateTestData.create()

    @classmethod
    def teardown(cls):
        ckan.model.repo.rebuild_db()

    def test_example_idatasetform_plugin(self):

        # Get the new dataset stage 1 page.
        offset = routes.url_for(controller='package', action='new')
        extra_environ = {'REMOTE_USER': 'tester'}
        response = self.app.get(offset, extra_environ=extra_environ)

        # Fill out the new dataset stage 1 form and submit it.
        form = response.forms[1]
        form['name'] = 'idatasetform_test_dataset'
        form['title'] = 'IDatasetForm Test Dataset'
        # Submit the form and get a redirected to the stage 2 form.
        response = form.submit('save', extra_environ=extra_environ)
        assert response.status == 302
        response = response.follow(extra_environ=extra_environ)
        assert response.status == 200

        # Fill out the new dataset stage 2 form and submit it.
        form = response.forms[1]
        form['name'] = 'idatasetform_test_resource'
        form['resource_type'] = 'api'
        form['url'] = 'www.example.com'
        response = form.submit('save', 3, extra_environ=extra_environ)
        assert response.status == 302
        response = response.follow(extra_environ=extra_environ)
        assert response.status == 200

        # Check that the custom Country Code field and its possible values
        # are on the new dataset stage 3 page.
        assert '<select id="field-country_code" name="country_code"' in (
                response)
        assert '<option value="de"' in response
        assert '<option value="es"' in response
        assert '<option value="fr"' in response
        assert '<option value="ie"' in response
        assert '<option value="uk"' in response

        # Fill out the new dataset stage 3 form and submit it.
        form = response.forms[1]
        form['country_code'] = 'uk'
        response = form.submit('save', 3, extra_environ=extra_environ)
        assert response.status == 302
        response = response.follow(extra_environ=extra_environ)
        assert response.status == 200
        assert response.request.url.endswith(
                '/dataset/idatasetform_test_dataset')

        # Check that the custom Country Code field appears with the correct
        # value on the dataset read page.
        assert '<p><strong>Country Code</strong>: uk</p>' in response

        # Get the edit dataset page for the dataset we just created.
        offset = routes.url_for(controller='package', action='edit',
                id='idatasetform_test_dataset')
        response = self.app.get(offset, extra_environ=extra_environ)

        # Check that the custom country_code field is on the page.
        assert '<select id="field-country_code" name="country_code"' in (
                response)
        # Check that the right value is selected by default.
        assert '<option value="uk" selected="selected">uk</option>' in (
                response)

        # Fill out the form and submit it, changing the country_code value and
        # some other values.
        form = response.forms[1]
        form['tag_string'] = 'testing, idatasetform, test_update_tag'
        form['country_code'] = 'fr'
        form['notes'] = 'updated notes'
        form['author'] = 'updated author'
        form['author_email'] = 'updated author_email'
        form['maintainer'] = 'updated maintainer'
        form['maintainer_email'] = 'updated maintainer_email'
        form['title'] = 'updated title'
        response = form.submit('save', extra_environ=extra_environ)
        assert response.status == 302
        response = response.follow(extra_environ=extra_environ)
        assert response.status == 200
        assert response.request.url.endswith(
                '/dataset/idatasetform_test_dataset')

        # Test the contents of the updated dataset read page.
        assert '<p><strong>Country Code</strong>: fr</p>' in response
        for tag in ('test_update_tag', 'idatasetform', 'testing'):
            assert 'href="/dataset?tags={0}"'.format(tag) in response
        assert 'updated notes' in response
        assert 'updated author' in response
        assert 'updated author_email' in response
        assert 'updated maintainer' in response
        assert 'updated maintainer_email' in response
        assert 'updated title' in response

        # Fetch the dataset search page, just to test that the plugin's
        # search_template() method gets called.
        offset = routes.url_for(controller='package', action='search')
        response = self.app.get(offset)
        assert response.status == 200

        # Fetch the dataset history page, just to test that the plugin's
        # history_template() method gets called.
        offset = routes.url_for(controller='package', action='history',
                id='idatasetform_test_dataset')
        response = self.app.get(offset)
        assert response.status == 200

        # TODO: It might be better to test that custom templates returned by
        # these methods are actually used, not just that the methods get
        # called.
        import ckanext.example_idatasetform.plugin as plugin
        assert plugin.ExampleIDatasetFormPlugin.num_times_new_template_called == 1
        assert plugin.ExampleIDatasetFormPlugin.num_times_read_template_called == 2
        assert plugin.ExampleIDatasetFormPlugin.num_times_edit_template_called == 1
        assert plugin.ExampleIDatasetFormPlugin.num_times_comments_template_called == 0
        assert plugin.ExampleIDatasetFormPlugin.num_times_search_template_called == 1
        assert plugin.ExampleIDatasetFormPlugin.num_times_history_template_called == 1
        assert plugin.ExampleIDatasetFormPlugin.num_times_package_form_called == 2
        assert plugin.ExampleIDatasetFormPlugin.num_times_check_data_dict_called == 3
