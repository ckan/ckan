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

        # Get the new dataset page.
        offset = routes.url_for(controller='package', action='new')
        extra_environ = {'REMOTE_USER': 'tester'}
        response = self.app.get(offset, extra_environ=extra_environ)

        # Check that the custom Country Code field and its possible values
        # are there.
        assert '<select id="country_code" name="country_code">' in response
        assert '<option value="de">de</option' in response
        assert '<option value="es">es</option' in response
        assert '<option value="fr">fr</option' in response
        assert '<option value="ie">ie</option' in response
        assert '<option value="uk">uk</option' in response

        # Fill out the form and submit it.
        form = response.forms['dataset-edit']
        form['name'] = 'idatasetform_test_dataset'
        form['title'] = 'IDatasetForm Test Dataset'
        form['author'] = 'tester'
        form['author_email'] = 'tester@testing.com'
        form['tag_string'] = 'testing, idatasetform'
        # Our custom Country Code field:
        form['country_code'] = 'fr'
        response = form.submit('save', extra_environ=extra_environ)

        # The response from submitting the form should be a 302 Redirect to the
        # read page for the new dataset.
        assert response.status == 302
        response = response.follow(extra_environ=extra_environ)
        assert response.status == 200
        assert response.request.url.endswith(
                '/dataset/idatasetform_test_dataset')

        # Test the contents of the dataset read page.
        assert '<td class="dataset-label">Country Code</td>' in response
        assert '<td class="dataset-details">fr</td>' in response
        assert '<a href="/tag/idatasetform">idatasetform</a>' in response
        assert '<a href="/tag/testing">testing</a>' in response

        # Update the dataset, changing the custom Country Code field.
        offset = routes.url_for(controller='package', action='edit',
                id='idatasetform_test_dataset')
        response = self.app.get(offset, extra_environ=extra_environ)
        assert '<option value="fr" selected="selected">fr</option>' in (
                response)
        form = response.forms['dataset-edit']
        form['tag_string'] = 'testing, idatasetform, test_update_tag'
        form['country_code'] = 'uk'
        response = form.submit('save', extra_environ=extra_environ)
        assert response.status == 302
        response = response.follow(extra_environ=extra_environ)
        assert response.status == 200
        assert response.request.url.endswith(
                '/dataset/idatasetform_test_dataset')

        # Test the contents of the updated dataset read page.
        assert '<td class="dataset-label">Country Code</td>' in response
        assert '<td class="dataset-details">uk</td>' in response
        assert '<a href="/tag/idatasetform">idatasetform</a>' in response
        assert '<a href="/tag/testing">testing</a>' in response
        assert '<a href="/tag/test_update_tag">test_update_tag</a>' in response

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
        from ckanext.example_idatasetform.plugin import \
                ExampleIDatasetFormPlugin
        assert ExampleIDatasetFormPlugin.num_times_package_form_called == 2
        assert ExampleIDatasetFormPlugin.num_times_read_template_called == 2
        assert ExampleIDatasetFormPlugin.num_times_edit_template_called == 2
        assert ExampleIDatasetFormPlugin.num_times_new_template_called == 1
        assert ExampleIDatasetFormPlugin.num_times_index_template_called == 1
        assert ExampleIDatasetFormPlugin.num_times_history_template_called == 1

        # TODO: Test IDatasetForm's comments_template() method.
        # (I think this requires the disqus plugin?)
