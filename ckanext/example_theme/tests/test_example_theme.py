'''Functional tests for the plugins in ckanext.example_theme.

These tests are pretty thin. They exist just so that if a change in CKAN
completely breaks one of the theming examples from the docs, hopefully one of
these tests will be failing.

'''
import webtest
import pylons.config as config
import bs4

import ckan.config.middleware
import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import ckan.new_tests.factories as factories
import ckan.new_tests.helpers as helpers


def get_test_app(plugin):

    # Disable the legacy templates feature.
    config['ckan.legacy_templates'] = False
    wsgiapp = ckan.config.middleware.make_app(config['global_conf'],
                                              **config)
    app = webtest.TestApp(wsgiapp)

    plugins.load(plugin)

    return app


class TestExampleEmptyPlugin(object):

    @classmethod
    def setup_class(cls):
        cls.app = get_test_app('example_theme_v01_empty_extension')

    @classmethod
    def teardown_class(cls):
        plugins.unload('example_theme_v01_empty_extension')

    def test_front_page_loads_okay(self):

        # The v01_empty_extension plugin doesn't do anything, so we just test
        # that the front page loads without crashing OK (i.e. CKAN has found
        # and loaded the plugin successfully).
        offset = toolkit.url_for(controller='home', action='index')
        result = self.app.get(offset)
        F
        assert result.status == '200 OK'

    def test_that_plugin_is_loaded(self):
        plugins.plugin_loaded('example_theme_v01_empty_extension')


class TestExampleEmptyTemplatePlugin(object):

    @classmethod
    def setup_class(cls):
        cls.app = get_test_app('example_theme_v02_empty_template')

    @classmethod
    def teardown_class(cls):
        plugins.unload('example_theme_v02_empty_template')

    def test_front_page_is_empty(self):
        offset = toolkit.url_for(controller='home', action='index')
        result = self.app.get(offset)
        assert result.body == '', 'The front page should be empty'


class TestExampleJinjaPlugin(object):

    @classmethod
    def setup_class(cls):
        cls.app = get_test_app('example_theme_v03_jinja')

    @classmethod
    def teardown_class(cls):
        plugins.unload('example_theme_v03_jinja')

    def test_site_title(self):
        offset = toolkit.url_for(controller='home', action='index')
        result = self.app.get(offset)
        site_title = config.get('ckan.site_title')
        assert ('The title of this site is: {site_title}'.format(
            site_title=site_title) in result.body)

    def test_plugins(self):
        offset = toolkit.url_for(controller='home', action='index')
        result = self.app.get(offset)
        for plugin in toolkit.aslist(config.get('ckan.plugins')):
            assert plugin in result.body

    def test_page_view_tracking_enabled(self):
        config['ckan.tracking_enabled'] = True
        offset = toolkit.url_for(controller='home', action='index')
        result = self.app.get(offset)
        assert toolkit.asbool(config.get('ckan.tracking_enabled')) is True
        assert ("CKAN's page-view tracking feature is enabled." in
                result.body)

    def test_comment(self):
        offset = toolkit.url_for(controller='home', action='index')
        result = self.app.get(offset)
        assert ('This text will not appear in the output when this template '
                'is rendered' not in result.body)


class TestExampleCKANExtendsPlugin(object):

    @classmethod
    def setup_class(cls):
        cls.app = get_test_app('example_theme_v04_ckan_extends')

    @classmethod
    def teardown_class(cls):
        plugins.unload('example_theme_v04_ckan_extends')

    def test_front_page(self):

        offset = toolkit.url_for(controller='home', action='index')
        response = self.app.get(offset)
        soup = response.html

        # Just check for some random text from the default front page,
        # to test that {% ckan_extends %} worked.
        assert ("This is a nice introductory paragraph about CKAN or the site "
                "in general. We don't have any copy to go here yet but soon "
                "we will" in [s.strip() for s in soup.strings])

        # TODO: It would be better if we also tested that the custom template
        # was the template that was rendered, and it didn't just render the
        # default front page template directly.


class TestExampleBlockPlugin(object):

    @classmethod
    def setup_class(cls):
        cls.app = get_test_app('example_theme_v05_block')

    @classmethod
    def teardown_class(cls):
        plugins.unload('example_theme_v05_block')

    def test_front_page(self):
        offset = toolkit.url_for(controller='home', action='index')
        result = self.app.get(offset)
        assert 'Hello block world!' in result.body


class TestExampleSuperPlugin(object):

    @classmethod
    def setup_class(cls):
        cls.app = get_test_app('example_theme_v06_super')

    @classmethod
    def teardown_class(cls):
        plugins.unload('example_theme_v06_super')

    def test_front_page(self):
        offset = toolkit.url_for(controller='home', action='index')
        response = self.app.get(offset)

        # We're going to parse the response using beautifulsoup.
        soup = response.html

        # Get the 'This paragraph will be added to the top' paragraph.
        matches = [p for p in soup.find_all('p')
                   if p.get_text(' ', strip=True) == 'This paragraph will be '
                   'added to the top of the featured_group block.']
        assert len(matches) == 1
        top = matches[0]

        # Get the 'This paragraph will be added to the bottom' paragraph.
        matches = [p for p in soup.find_all('p')
                   if p.get_text(' ', strip=True) == 'This paragraph will be '
                   'added to the bottom of the featured_group block.']
        assert len(matches) == 1
        bottom = matches[0]

        # Find the featured_groups div.
        matches = soup.select('#featured_groups')
        assert len(matches) == 1
        div = matches[0]

        # Assert that the three elements appear in the order they should.
        assert div in top.next_elements
        assert bottom in div.next_elements


class TestExampleHelperFunctionPlugin(object):

    @classmethod
    def setup_class(cls):
        cls.app = get_test_app('example_theme_v07_helper_function')

    @classmethod
    def teardown_class(cls):
        plugins.unload('example_theme_v07_helper_function')

    def test_helper_function(self):

        # Make a user and a dataset, so we have some activities in our
        # activity stream.
        user = factories.User()
        dataset = factories.Dataset(user=user)

        offset = toolkit.url_for(controller='home', action='index')
        response = self.app.get(offset)
        soup = response.html

        # Test that the activity stream is being rendered, for testing for
        # some text we know should be on the page.
        assert [e for e in soup.find_all()
                if e.get_text(' ', strip=True).startswith(
                    '{user} created the dataset {dataset}'.format(
                        user=user['fullname'], dataset=dataset['title']))]


class TestExampleCustomHelperFunctionPlugin(object):

    @classmethod
    def setup_class(cls):
        cls.app = get_test_app('example_theme_v08_custom_helper_function')

    @classmethod
    def teardown_class(cls):
        plugins.unload('example_theme_v08_custom_helper_function')

    def test_most_popular_groups(self):

        # Create three groups with 3, 2 and 1 datasets each.
        user = factories.User()
        most_popular_group = factories.Group(user=user)
        # FIXME: Add the datasets to the groups!
        dataset_one = factories.Dataset(user=user)
        dataset_two = factories.Dataset(user=user)
        dataset_three = factories.Dataset(user=user)
        second_most_popular_group = factories.Group(user=user)
        dataset_four = factories.Dataset(user=user)
        dataset_five = factories.Dataset(user=user)
        third_most_popular_group = factories.Group(user=user)
        dataset_six = factories.Dataset(user=user)

        offset = toolkit.url_for(controller='home', action='index')
        response = self.app.get(offset)
        soup = response.html

        # Find the 'most popular groups' list.
        matches = soup.select('ul#most-popular-groups')
        assert len(matches) == 1
        ul = matches[0]

        # Assert that the three groups are listed in the right order.
        list_items = ul.find_all('li')
        assert len(list_items) == 3
        assert list_items[0].get_text() == most_popular_group['title']
        assert list_items[1].get_text() == second_most_popular_group['title']
        assert list_items[2].get_text() == third_most_popular_group['title']


class TestExampleSnippetPlugin(object):

    @classmethod
    def setup_class(cls):
        cls.app = get_test_app('example_theme_v09_snippet')

    @classmethod
    def teardown_class(cls):
        plugins.unload('example_theme_v09_snippet')

    def test_snippet(self):

        offset = toolkit.url_for(controller='home', action='index')
        response = self.app.get(offset)
        soup = response.html

        # Just test that the snippet was used.
        comments = soup.findAll(text=lambda text:isinstance(text, bs4.Comment))
        assert 'Snippet group/snippets/group_list.html start' in (
                comment.strip() for comment in comments)


class TestExampleCustomSnippetPlugin(object):

    @classmethod
    def setup_class(cls):
        cls.app = get_test_app('example_theme_v10_custom_snippet')

    @classmethod
    def teardown_class(cls):
        plugins.unload('example_theme_v10_custom_snippet')

    def test_most_popular_groups(self):

        # Create three groups with 3, 2 and 1 datasets each.
        user = factories.User()
        most_popular_group = factories.Group(user=user)
        # FIXME: Add the datasets to the groups!
        factories.Dataset(user=user)
        factories.Dataset(user=user)
        factories.Dataset(user=user)
        second_most_popular_group = factories.Group(user=user)
        factories.Dataset(user=user)
        factories.Dataset(user=user)
        third_most_popular_group = factories.Group(user=user)
        factories.Dataset(user=user)

        offset = toolkit.url_for(controller='home', action='index')
        response = self.app.get(offset)
        soup = response.html

        # Find the 'most popular groups' list and check that it has the right
        # number of groups in the right order.
        matches = [h for h in soup.find_all('h3')
                   if h.text == 'Most popular groups']
        assert len(matches) == 1
        h = matches[0]
        ul = h.find_next_sibling()
        list_items = ul.find_all('li')
        assert len(list_items) == 3
        assert (list_items[0].find_all('h3')[0].text
                == most_popular_group['title'])
        assert (list_items[1].find_all('h3')[0].text
                == second_most_popular_group['title'])
        assert (list_items[2].find_all('h3')[0].text
                == third_most_popular_group['title'])


class TestExampleHTMLAndCSSPlugin(object):

    @classmethod
    def setup_class(cls):
        cls.app = get_test_app('example_theme_v11_HTML_and_CSS')

    @classmethod
    def teardown_class(cls):
        plugins.unload('example_theme_v11_HTML_and_CSS')

    def test_most_popular_groups(self):

        # Create three groups with 3, 2 and 1 datasets each.
        user = factories.User()
        most_popular_group = factories.Group(user=user)
        # FIXME: Add the datasets to the groups!
        factories.Dataset(user=user)
        factories.Dataset(user=user)
        factories.Dataset(user=user)
        second_most_popular_group = factories.Group(user=user)
        factories.Dataset(user=user)
        factories.Dataset(user=user)
        third_most_popular_group = factories.Group(user=user)
        factories.Dataset(user=user)

        offset = toolkit.url_for(controller='home', action='index')
        response = self.app.get(offset)
        soup = response.html

        # Find the 'most popular groups' list and check that it has the right
        # number of groups in the right order.
        matches = [h for h in soup.find_all('h3')
                   if h.text == 'Most popular groups']
        assert len(matches) == 1
        h = matches[0]
        ul = h.find_next('ul')
        list_items = ul.find_all('li')
        assert len(list_items) == 3
        assert (list_items[0].find_all('h3')[0].text
                == most_popular_group['title'])
        assert (list_items[1].find_all('h3')[0].text
                == second_most_popular_group['title'])
        assert (list_items[2].find_all('h3')[0].text
                == third_most_popular_group['title'])


class TestExampleCustomCSSPlugin(object):

    @classmethod
    def setup_class(cls):
        cls.app = get_test_app('example_theme_v13_custom_css')

    @classmethod
    def teardown_class(cls):
        plugins.unload('example_theme_v13_custom_css')

    def test_custom_css(self):

        offset = toolkit.url_for(controller='home', action='index')
        response = self.app.get(offset)
        soup = response.html

        matches = soup.find_all('link', rel='stylesheet',
                                href='/example_theme.css')
        assert len(matches) == 1
        link = matches[0]
        url = link['href']
        # FIXME: It looks like static files aren't working in tests?
        response = self.app.get(url)
        assert response.status == '200 OK'


class TestExampleMoreCustomCSSPlugin(object):

    @classmethod
    def setup_class(cls):

        # Disable the legacy templates feature.
        config['ckan.legacy_templates'] = False
        wsgiapp = ckan.config.middleware.make_app(config['global_conf'],
                                                  **config)
        cls.app = webtest.TestApp(wsgiapp)

        plugins.load('example_theme_v14_more_custom_css')

    @classmethod
    def teardown_class(cls):
        plugins.unload('example_theme_v14_more_custom_css')

    def test_custom_css(self):

        offset = toolkit.url_for(controller='home', action='index')
        response = self.app.get(offset)
        soup = response.html

        matches = soup.find_all('link', rel='stylesheet',
                                href='/example_theme.css')
        assert len(matches) == 1
        link = matches[0]
        url = link['href']
        # FIXME: It looks like static files aren't working in tests?
        response = self.app.get(url)
        assert response.status == '200 OK'


class TestExampleFanstaticPlugin(object):

    @classmethod
    def setup_class(cls):

        # Disable the legacy templates feature.
        config['ckan.legacy_templates'] = False
        wsgiapp = ckan.config.middleware.make_app(config['global_conf'],
                                                  **config)
        cls.app = webtest.TestApp(wsgiapp)

        plugins.load('example_theme_v15_fanstatic')

    @classmethod
    def teardown_class(cls):
        plugins.unload('example_theme_v15_fanstatic')

    def test_fanstatic(self):

        offset = toolkit.url_for(controller='home', action='index')
        response = self.app.get(offset)
        soup = response.html

        # Test that Fanstatic has inserted one <link> tag for the
        # example_theme.css file.
        matches = [link for link in soup.find_all('link', rel='stylesheet')
                   if 'example_theme.css' in link['href']]
        assert len(matches) == 1
        link = matches[0]

        # Test that there is something at the <link> tag's URL.
        url = link['href']
        response = self.app.get(url)
        assert response.status == '200 OK'
