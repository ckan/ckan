'''Functional tests for the plugins in ckanext.example_theme.

These tests are pretty thin. They exist just so that if a change in CKAN
completely breaks one of the theming examples from the docs, hopefully one of
these tests will be failing.

'''
import webtest
import pylons.config as config
import bs4

import ckan.config.middleware
import ckan.plugins
import ckan.plugins.toolkit as toolkit
import ckan.new_tests.factories as factories


class ControllerTestBaseClass(object):
    '''A base class for controller test classes to inherit from.

    If you're overriding methods that this class provides, like setup_class()
    and teardown_class(), make sure to use super() to call this class's methods
    at the top of yours!

    '''
    @classmethod
    def setup_class(cls):
        # Make a copy of the Pylons config, so we can restore it in teardown.
        cls.original_config = config.copy()

    @classmethod
    def teardown_class(cls):
        # Restore the Pylons config to its original values, in case any tests
        # changed any config settings.
        config.clear()
        config.update(cls.original_config)


def _load_plugin(plugin):
    '''Add the given plugin to the ckan.plugins config setting.

    If the given plugin is already in the ckan.plugins setting, it won't be
    added a second time.

    :param plugin: the plugin to add, e.g. ``datastore``
    :type plugin: string

    '''
    plugins = set(config['ckan.plugins'].strip().split())
    plugins.add(plugin.strip())
    config['ckan.plugins'] = ' '.join(plugins)


def _unload_plugin(plugin):
    '''Remove the given plugin from the ckan.plugins config setting.

    If the given plugin is not in the ckan.plugins setting, nothing will be
    changed.

    :param plugin: the plugin to remove, e.g. ``datastore``
    :type plugin: string

    '''
    plugins = set(config['ckan.plugins'].strip().split())
    try:
        plugins.remove(plugin.strip())
    except KeyError:
        # Looks like the plugin was not in ckan.plugins.
        pass
    config['ckan.plugins'] = ' '.join(plugins)


def _get_test_app():
    '''Return a webtests.TestApp for CKAN, with legacy templates disabled.

    '''
    config['ckan.legacy_templates'] = False
    app = ckan.config.middleware.make_app(config['global_conf'], **config)
    app = webtest.TestApp(app)
    return app


class TestExampleEmptyPlugin(ControllerTestBaseClass):

    @classmethod
    def setup_class(cls):
        super(TestExampleEmptyPlugin, cls).setup_class()
        _load_plugin('example_theme_v01_empty_extension')
        cls.app = _get_test_app()

    def test_front_page_loads_okay(self):

        # The v01_empty_extension plugin doesn't do anything, so we just test
        # that the front page loads without crashing OK (i.e. CKAN has found
        # and loaded the plugin successfully).
        offset = toolkit.url_for(controller='home', action='index')
        result = self.app.get(offset)
        assert result.status == '200 OK'

    def test_that_plugin_is_loaded(self):
        ckan.plugins.plugin_loaded('example_theme_v01_empty_extension')


class TestExampleEmptyTemplatePlugin(ControllerTestBaseClass):

    @classmethod
    def setup_class(cls):
        super(TestExampleEmptyTemplatePlugin, cls).setup_class()
        _load_plugin('example_theme_v02_empty_template')
        cls.app = _get_test_app()

    def test_front_page_is_empty(self):
        offset = toolkit.url_for(controller='home', action='index')
        result = self.app.get(offset)
        assert result.body == '', 'The front page should be empty'


class TestExampleJinjaPlugin(ControllerTestBaseClass):

    @classmethod
    def setup_class(cls):
        super(TestExampleJinjaPlugin, cls).setup_class()
        _load_plugin('example_theme_v03_jinja')
        cls.app = _get_test_app()

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


class TestExampleCKANExtendsPlugin(ControllerTestBaseClass):

    @classmethod
    def setup_class(cls):
        super(TestExampleCKANExtendsPlugin, cls).setup_class()
        _load_plugin('example_theme_v04_ckan_extends')
        cls.app = _get_test_app()

    def test_front_page(self):

        offset = toolkit.url_for(controller='home', action='index')
        response = self.app.get(offset)
        soup = response.html

        # Just check for some random text from the default front page,
        # to test that {% ckan_extends %} worked.
        assert ("This is a nice introductory paragraph about CKAN or the site "
                "in general. We don't have any copy to go here yet but soon "
                "we will" in [s for s in soup.stripped_strings])

        # TODO: It would be better if we also tested that the custom template
        # was the template that was rendered, and it didn't just render the
        # default front page template directly.


class TestExampleBlockPlugin(ControllerTestBaseClass):

    @classmethod
    def setup_class(cls):
        super(TestExampleBlockPlugin, cls).setup_class()
        _load_plugin('example_theme_v05_block')
        cls.app = _get_test_app()

    def test_front_page(self):
        offset = toolkit.url_for(controller='home', action='index')
        result = self.app.get(offset)
        assert 'Hello block world!' in result.body


class TestExampleSuperPlugin(ControllerTestBaseClass):

    @classmethod
    def setup_class(cls):
        super(TestExampleSuperPlugin, cls).setup_class()
        _load_plugin('example_theme_v06_super')
        cls.app = _get_test_app()

    def test_front_page(self):

        # Create a couple of groups, so we have some featured groups on the
        # front page.
        user = factories.User()
        factories.Group(user=user)
        factories.Group(user=user)

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

        # Find the HTML comment that marks the start of the
        # featured_groups.html snippet.
        def is_featured_groups_snippet_start(text):
            if not isinstance(text, bs4.Comment):
                return False
            return 'featured_group.html start' in text
        matches = soup.find_all(text=is_featured_groups_snippet_start)
        assert len(matches) == 1
        snippet_start = matches[0]

        # Find the HTML comment that marks the end of the
        # featured_groups.html snippet.
        def is_featured_groups_snippet_end(text):
            if not isinstance(text, bs4.Comment):
                return False
            return 'featured_group.html end' in text
        matches = soup.find_all(text=is_featured_groups_snippet_end)
        assert len(matches) == 1
        snippet_end = matches[0]

        # Get the 'This paragraph will be added to the bottom' paragraph.
        matches = [p for p in soup.find_all('p')
                   if p.get_text(' ', strip=True) == 'This paragraph will be '
                   'added to the bottom of the featured_group block.']
        assert len(matches) == 1
        bottom = matches[0]

        assert snippet_start in top.next_elements, (
            'The first paragraph should appear before the start of the '
            'snippet')
        assert bottom in snippet_end.next_elements, (
            'The second paragraph should appear after the end of the snippet')


class TestExampleHelperFunctionPlugin(ControllerTestBaseClass):

    @classmethod
    def setup_class(cls):
        super(TestExampleHelperFunctionPlugin, cls).setup_class()
        _load_plugin('example_theme_v07_helper_function')
        cls.app = _get_test_app()

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


class TestExampleCustomHelperFunctionPlugin(ControllerTestBaseClass):

    @classmethod
    def setup_class(cls):
        super(TestExampleCustomHelperFunctionPlugin, cls).setup_class()
        _load_plugin('example_theme_v08_custom_helper_function')
        cls.app = _get_test_app()

    def test_most_popular_groups(self):

        # Create three groups with 3, 2 and 1 datasets each.
        user = factories.User()
        most_popular_group = factories.Group(user=user)
        factories.Dataset(user=user, groups=[{'id': most_popular_group['id']}])
        factories.Dataset(user=user, groups=[{'id': most_popular_group['id']}])
        factories.Dataset(user=user, groups=[{'id': most_popular_group['id']}])
        second_most_popular_group = factories.Group(user=user)
        factories.Dataset(user=user,
                          groups=[{'id': second_most_popular_group['id']}])
        factories.Dataset(user=user,
                          groups=[{'id': second_most_popular_group['id']}])
        third_most_popular_group = factories.Group(user=user)
        factories.Dataset(user=user,
                          groups=[{'id': third_most_popular_group['id']}])

        offset = toolkit.url_for(controller='home', action='index')
        response = self.app.get(offset)
        soup = response.html

        # Find the 'most popular groups' list.
        h = soup.find('h3', text='Most popular groups')
        ul = h.find_next_sibling('ul')

        # Assert that the three groups are listed in the right order.
        list_items = ul.find_all('li')
        assert len(list_items) == 3
        assert list_items[0].get_text() == most_popular_group['title']
        assert list_items[1].get_text() == second_most_popular_group['title']
        assert list_items[2].get_text() == third_most_popular_group['title']


class TestExampleSnippetPlugin(ControllerTestBaseClass):

    @classmethod
    def setup_class(cls):
        super(TestExampleSnippetPlugin, cls).setup_class()
        _load_plugin('example_theme_v09_snippet')
        cls.app = _get_test_app()

    def test_snippet(self):

        offset = toolkit.url_for(controller='home', action='index')
        response = self.app.get(offset)
        soup = response.html

        # Just test that the snippet was used.
        comments = soup.find_all(
            text=lambda text: isinstance(text, bs4.Comment))
        assert 'Snippet group/snippets/group_list.html start' in (
            comment.strip() for comment in comments)


class TestExampleCustomSnippetPlugin(ControllerTestBaseClass):

    @classmethod
    def setup_class(cls):
        super(TestExampleCustomSnippetPlugin, cls).setup_class()
        _load_plugin('example_theme_v10_custom_snippet')
        cls.app = _get_test_app()

    def test_most_popular_groups(self):

        # Create three groups with 3, 2 and 1 datasets each.
        user = factories.User()
        most_popular_group = factories.Group(user=user)
        factories.Dataset(user=user, groups=[{'id': most_popular_group['id']}])
        factories.Dataset(user=user, groups=[{'id': most_popular_group['id']}])
        factories.Dataset(user=user, groups=[{'id': most_popular_group['id']}])
        second_most_popular_group = factories.Group(user=user)
        factories.Dataset(user=user,
                          groups=[{'id': second_most_popular_group['id']}])
        factories.Dataset(user=user,
                          groups=[{'id': second_most_popular_group['id']}])
        third_most_popular_group = factories.Group(user=user)
        factories.Dataset(user=user,
                          groups=[{'id': third_most_popular_group['id']}])

        offset = toolkit.url_for(controller='home', action='index')
        response = self.app.get(offset)
        soup = response.html

        # Find the 'most popular groups' list and check that it has the right
        # number of groups in the right order.
        h = soup.find('h3', text='Most popular groups')
        ul = h.find_next_sibling('ul')
        list_items = ul.find_all('li')
        assert len(list_items) == 3
        assert (list_items[0].find_all('h3')[0].text
                == most_popular_group['title'])
        assert (list_items[1].find_all('h3')[0].text
                == second_most_popular_group['title'])
        assert (list_items[2].find_all('h3')[0].text
                == third_most_popular_group['title'])


class TestExampleHTMLAndCSSPlugin(ControllerTestBaseClass):

    @classmethod
    def setup_class(cls):
        super(TestExampleHTMLAndCSSPlugin, cls).setup_class()
        _load_plugin('example_theme_v11_HTML_and_CSS')
        cls.app = _get_test_app()

    def test_most_popular_groups(self):

        # Create three groups with 3, 2 and 1 datasets each.
        user = factories.User()
        most_popular_group = factories.Group(user=user)
        factories.Dataset(user=user, groups=[{'id': most_popular_group['id']}])
        factories.Dataset(user=user, groups=[{'id': most_popular_group['id']}])
        factories.Dataset(user=user, groups=[{'id': most_popular_group['id']}])
        second_most_popular_group = factories.Group(user=user)
        factories.Dataset(user=user,
                          groups=[{'id': second_most_popular_group['id']}])
        factories.Dataset(user=user,
                          groups=[{'id': second_most_popular_group['id']}])
        third_most_popular_group = factories.Group(user=user)
        factories.Dataset(user=user,
                          groups=[{'id': third_most_popular_group['id']}])

        offset = toolkit.url_for(controller='home', action='index')
        response = self.app.get(offset)
        soup = response.html

        # Find the 'most popular groups' list and check that it has the right
        # number of groups in the right order.
        h = soup.find('h3', text='Most popular groups')
        ul = h.find_next('ul')
        list_items = ul.find_all('li')
        assert len(list_items) == 3
        assert (list_items[0].find_all('h3')[0].text
                == most_popular_group['title'])
        assert (list_items[1].find_all('h3')[0].text
                == second_most_popular_group['title'])
        assert (list_items[2].find_all('h3')[0].text
                == third_most_popular_group['title'])


class TestExampleCustomCSSPlugin(ControllerTestBaseClass):

    @classmethod
    def setup_class(cls):
        super(TestExampleCustomCSSPlugin, cls).setup_class()
        _load_plugin('example_theme_v13_custom_css')
        cls.app = _get_test_app()

    def test_custom_css(self):

        offset = toolkit.url_for(controller='home', action='index')
        response = self.app.get(offset)
        soup = response.html

        link = soup.find('link', rel='stylesheet', href='/example_theme.css')
        url = link['href']
        response = self.app.get(url)
        assert response.status == '200 OK'


class TestExampleMoreCustomCSSPlugin(ControllerTestBaseClass):

    @classmethod
    def setup_class(cls):
        super(TestExampleMoreCustomCSSPlugin, cls).setup_class()
        _load_plugin('example_theme_v14_more_custom_css')
        cls.app = _get_test_app()

    def test_custom_css(self):

        offset = toolkit.url_for(controller='home', action='index')
        response = self.app.get(offset)
        soup = response.html

        link = soup.find('link', rel='stylesheet', href='/example_theme.css')
        url = link['href']
        response = self.app.get(url)
        assert response.status == '200 OK'


class TestExampleFanstaticPlugin(ControllerTestBaseClass):

    @classmethod
    def setup_class(cls):
        super(TestExampleFanstaticPlugin, cls).setup_class()
        _load_plugin('example_theme_v15_fanstatic')
        cls.app = _get_test_app()

    def test_fanstatic(self):

        offset = toolkit.url_for(controller='home', action='index')
        response = self.app.get(offset)
        soup = response.html

        # Test that Fanstatic has inserted one <link> tag for the
        # example_theme.css file.
        link = soup.find('link', rel='stylesheet',
                         href=lambda h: 'example_theme.css' in h)

        # Test that there is something at the <link> tag's URL.
        url = link['href']
        response = self.app.get(url)
        assert response.status == '200 OK'
