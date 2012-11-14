from ckan import plugins
import ckan.tests as tests
import ckanext.jsonpreview.plugin as previewplugin


class TestMyPlugin(tests.TestCase):

    @classmethod
    def setup_class(cls):
        plugins.load('json_preview')

        cls.p = previewplugin.JsonPreview()

    @classmethod
    def teardown_class(cls):
        plugins.reset()

    def test_can_preview(self):
        data_dict = {
            'resource': {
                'format': 'jsonp'
            }
        }
        assert self.p.can_preview(data_dict)

        data_dict = {
            'resource': {
                'format': 'json',
                'on_same_domain': True
            }
        }
        assert self.p.can_preview(data_dict)

        data_dict = {
            'resource': {
                'format': 'json',
                'on_same_domain': True
            }
        }
        assert not self.p.can_preview(data_dict)
