from base import WebAppTest
from oktest import ok
from ckan.tests import url_for


class TestAddDataset(WebAppTest):
    def test_create_requires_login(self):
        self.app.reset()
        res = self.app.get(url_for(controller='package', action='new'), status=302).follow()

        ok(res.lxml.xpath('//h1[contains(text(), "Login")]')).length(1)
        ok(res.pyquery('h1.page_heading').text()) == 'Login to CKAN'

    def test_add_dataset(self):
        res = self.log_in()

        res = res.click(description="Add a dataset", index=0)
        ok(res.pyquery('h1.page_heading').text()) == 'Add a Dataset'

        form = res.forms['dataset-edit']

        form['title'] = 'New Resource'
        #form['url'] = 'http://www.okfn.org/'
        form['name'] = 'new-resource'
        form['notes'] = 'A new test resource'
        form['tag_string'] = 'foo, far, baz'

        res = form.submit(name='save').follow()
        ok(res.pyquery('h1.page_heading').text()) == 'New Resource'
