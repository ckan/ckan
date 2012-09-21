from ckan.tests import url_for
import ckan.tests as tests
import helpers


class TestAddDataset(tests.WsgiWebAppCase):
    def test_create_requires_login(self):
        self.app.reset()
        res = self.app.get(url_for(controller='package', action='new'), status=302).follow()

        assert len(res.lxml.xpath('//h1[contains(text(), "Login")]')) == 1
        assert res.pyquery('h1.page_heading').text() == 'Login to CKAN'

    def test_add_dataset(self):
        res = helpers.log_in(self.app)

        res = res.click(description="Add a dataset", index=0)
        assert res.pyquery('h1.page_heading').text() == 'Add a Dataset'

        form = res.forms['dataset-edit']

        form['title'] = 'New Resource'
        #form['url'] = 'http://www.okfn.org/'
        form['name'] = 'new-resource'
        form['notes'] = 'A new test resource'
        form['tag_string'] = 'foo, far, baz'

        res = form.submit(name='save').follow()
        assert res.pyquery('h1.page_heading').text() == 'New Resource'
