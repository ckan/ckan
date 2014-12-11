'''Functional tests for CKAN's builtin page view tracking feature.'''

import tempfile
import csv
import datetime
import routes

import ckan.tests as tests


class TestTracking(object):

    def tearDown(self):
        import ckan.model as model
        model.repo.rebuild_db()

    def _get_app(self):
        import paste.fixture
        import pylons.test
        return paste.fixture.TestApp(pylons.test.pylonsapp)

    def _create_sysadmin(self, app):
        '''Create a sysadmin user.

        Returns a tuple (sysadmin_user_object, api_key).

        '''
        # You can't create a user via the api
        # (ckan.auth.create_user_via_api = false is in test-core.ini) and you
        # can't make your first sysadmin user via either the api or the web
        # interface anyway, so access the model directly to make a sysadmin
        # user.
        import ckan.model as model
        user = model.User(name='joeadmin', email='joe@admin.net',
                          password='joe rules')
        user.sysadmin = True
        model.Session.add(user)
        model.repo.commit_and_remove()
        return (tests.call_action_api(app, 'user_show', id=user.id),
                user.apikey)

    def _create_package(self, app, apikey, name='look_to_windward'):
        '''Create a package via the action api.'''

        return tests.call_action_api(app, 'package_create', apikey=apikey,
                                     name=name)

    def _create_resource(self, app, package, apikey):
        '''Create a resource via the action api.'''

        return tests.call_action_api(app, 'resource_create', apikey=apikey,
                                     package_id=package['id'],
                                     url='http://example.com')

    def _post_to_tracking(self, app, url, type_='page', ip='199.204.138.90',
                          browser='firefox'):
        '''Post some data to /_tracking directly.

        This simulates what's supposed when you view a page with tracking
        enabled (an ajax request posts to /_tracking).

        '''
        params = {'url': url, 'type': type_}
        extra_environ = {
            # The tracking middleware crashes if these aren't present.
            'HTTP_USER_AGENT': browser,
            'REMOTE_ADDR': ip,
            'HTTP_ACCEPT_LANGUAGE': 'en',
            'HTTP_ACCEPT_ENCODING': 'gzip, deflate',
        }
        app.post('/_tracking', params=params, extra_environ=extra_environ)

    def _update_tracking_summary(self):
        '''Update CKAN's tracking summary data.

        This simulates calling `paster tracking update` on the command line.

        '''
        # FIXME: Can this be done as more of a functional test where we
        # actually test calling the command and passing the args? By calling
        # the method directly, we're not testing the command-line parsing.
        import ckan.lib.cli
        import ckan.model
        date = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime(
            '%Y-%m-%d')
        ckan.lib.cli.Tracking('Tracking').update_all(
            engine=ckan.model.meta.engine, start_date=date)

    def _rebuild_search_index(self):
        '''Rebuild CKAN's search index.

        This simulates calling `paster search-index rebuild` on the command
        line.

        '''
        import ckan.lib.cli
        ckan.lib.cli.SearchIndexCommand('SearchIndexCommand').rebuild()

    def test_package_with_0_views(self):
        app = self._get_app()
        sysadmin_user, apikey = self._create_sysadmin(app)
        package = self._create_package(app, apikey)

        # The API should return 0 recent views and 0 total views for the
        # unviewed package.
        package = tests.call_action_api(app, 'package_show',
                                        id=package['name'])
        tracking_summary = package['tracking_summary']
        assert tracking_summary['recent'] == 0, ("A package that has not "
                                                 "been viewed should have 0 "
                                                 "recent views")
        assert tracking_summary['total'] == 0, ("A package that has not "
                                                "been viewed should have 0 "
                                                "total views")

    def test_resource_with_0_views(self):
        app = self._get_app()
        sysadmin_user, apikey = self._create_sysadmin(app)
        package = self._create_package(app, apikey)
        resource = self._create_resource(app, package, apikey)

        # The package_show() API should return 0 recent views and 0 total
        # views for the unviewed resource.
        package = tests.call_action_api(app, 'package_show',
                                        id=package['name'])
        assert len(package['resources']) == 1
        resource = package['resources'][0]
        tracking_summary = resource['tracking_summary']
        assert tracking_summary['recent'] == 0, ("A resource that has not "
                                                 "been viewed should have 0 "
                                                 "recent views")
        assert tracking_summary['total'] == 0, ("A resource that has not "
                                                "been viewed should have 0 "
                                                "total views")

        # The resource_show() API should return 0 recent views and 0 total
        # views for the unviewed resource.
        resource = tests.call_action_api(app, 'resource_show',
                                         id=resource['id'])
        tracking_summary = resource['tracking_summary']
        assert tracking_summary['recent'] == 0, ("A resource that has not "
                                                 "been viewed should have 0 "
                                                 "recent views")
        assert tracking_summary['total'] == 0, ("A resource that has not "
                                                "been viewed should have 0 "
                                                "total views")

    def test_package_with_one_view(self):
        app = self._get_app()
        sysadmin_user, apikey = self._create_sysadmin(app)
        package = self._create_package(app, apikey)
        self._create_resource(app, package, apikey)

        url = routes.url_for(controller='package', action='read',
                             id=package['name'])
        self._post_to_tracking(app, url)

        self._update_tracking_summary()

        package = tests.call_action_api(app, 'package_show', id=package['id'])
        tracking_summary = package['tracking_summary']
        assert tracking_summary['recent'] == 1, ("A package that has been "
                                                 "viewed once should have 1 "
                                                 "recent view.")
        assert tracking_summary['total'] == 1, ("A package that has been "
                                                "viewed once should have 1 "
                                                "total view")

        assert len(package['resources']) == 1
        resource = package['resources'][0]
        tracking_summary = resource['tracking_summary']
        assert tracking_summary['recent'] == 0, ("Viewing a package should "
                                                 "not increase the recent "
                                                 "views of the package's "
                                                 "resources")
        assert tracking_summary['total'] == 0, ("Viewing a package should "
                                                "not increase the total views "
                                                "of the package's resources")

    def test_resource_with_one_preview(self):
        app = self._get_app()
        sysadmin_user, apikey = self._create_sysadmin(app)
        package = self._create_package(app, apikey)
        resource = self._create_resource(app, package, apikey)

        url = routes.url_for(controller='package', action='resource_read',
                             id=package['name'], resource_id=resource['id'])
        self._post_to_tracking(app, url)

        self._update_tracking_summary()

        package = tests.call_action_api(app, 'package_show', id=package['id'])
        assert len(package['resources']) == 1
        resource = package['resources'][0]

        assert package['tracking_summary']['recent'] == 0, ("Previewing a "
                                                            "resource should "
                                                            "not increase the "
                                                            "package's recent "
                                                            "views")
        assert package['tracking_summary']['total'] == 0, ("Previewing a "
                                                           "resource should "
                                                           "not increase the "
                                                           "package's total "
                                                           "views")
        # Yes, previewing a resource does _not_ increase its view count.
        assert resource['tracking_summary']['recent'] == 0, ("Previewing a "
                                                             "resource should "
                                                             "not increase "
                                                             "the resource's "
                                                             "recent views")
        assert resource['tracking_summary']['total'] == 0, ("Previewing a "
                                                            "resource should "
                                                            "not increase the "
                                                            "resource's "
                                                            "recent views")

    def test_resource_with_one_download(self):
        app = self._get_app()
        sysadmin_user, apikey = self._create_sysadmin(app)
        package = self._create_package(app, apikey)
        resource = self._create_resource(app, package, apikey)

        self._post_to_tracking(app, resource['url'], type_='resource')
        self._update_tracking_summary()

        package = tests.call_action_api(app, 'package_show', id=package['id'])
        assert len(package['resources']) == 1
        resource = package['resources'][0]
        assert package['tracking_summary']['recent'] == 0, (
            "Downloading a resource should not increase the package's recent "
            "views")
        assert package['tracking_summary']['total'] == 0, (
            "Downloading a resource should not increase the package's total "
            "views")
        assert resource['tracking_summary']['recent'] == 1, (
            "Downloading a resource should increase the resource's recent "
            "views")
        assert resource['tracking_summary']['total'] == 1, (
            "Downloading a resource should increase the resource's total "
            "views")

        # The resource_show() API should return the same result.
        resource = tests.call_action_api(app, 'resource_show',
                                         id=resource['id'])
        tracking_summary = resource['tracking_summary']
        assert tracking_summary['recent'] == 1, (
            "Downloading a resource should increase the resource's recent "
            "views")
        assert tracking_summary['total'] == 1, (
            "Downloading a resource should increase the resource's total "
            "views")

    def test_view_page(self):
        app = self._get_app()

        # Visit the front page.
        self._post_to_tracking(app, url='', type_='page')
        # Visit the /organization page.
        self._post_to_tracking(app, url='/organization', type_='page')
        # Visit the /about page.
        self._post_to_tracking(app, url='/about', type_='page')

        self._update_tracking_summary()

        # There's no way to export page-view (as opposed to resource or
        # dataset) tracking summaries, eg. via the api or a paster command, the
        # only way we can check them is through the model directly.
        import ckan.model as model
        for url in ('', '/organization', '/about'):
            q = model.Session.query(model.TrackingSummary)
            q = q.filter_by(url=url)
            tracking_summary = q.one()
            assert tracking_summary.count == 1, ("Viewing a page should "
                                                 "increase the page's view "
                                                 "count")
            # For pages (as opposed to datasets and resources) recent_views and
            # running_total always stay at 1. Shrug.
            assert tracking_summary.recent_views == 0, (
                "recent_views for a page is always 0")
            assert tracking_summary.running_total == 0, (
                "running_total for a page is always 0")

    def test_package_with_many_views(self):
        app = self._get_app()
        sysadmin_user, apikey = self._create_sysadmin(app)
        package = self._create_package(app, apikey)
        self._create_resource(app, package, apikey)

        url = routes.url_for(controller='package', action='read',
                             id=package['name'])

        # View the package three times from different IPs.
        self._post_to_tracking(app, url, ip='111.222.333.44')
        self._post_to_tracking(app, url, ip='111.222.333.55')
        self._post_to_tracking(app, url, ip='111.222.333.66')

        self._update_tracking_summary()

        package = tests.call_action_api(app, 'package_show', id=package['id'])
        tracking_summary = package['tracking_summary']
        assert tracking_summary['recent'] == 3, (
            "A package that has been viewed 3 times recently should have 3 "
            "recent views")
        assert tracking_summary['total'] == 3, (
            "A package that has been viewed 3 times should have 3 total views")

        assert len(package['resources']) == 1
        resource = package['resources'][0]
        tracking_summary = resource['tracking_summary']
        assert tracking_summary['recent'] == 0, (
            "Viewing a package should not increase the recent views of the "
            "package's resources")
        assert tracking_summary['total'] == 0, (
            "Viewing a package should not increase the total views of the "
            "package's resources")

    def test_resource_with_many_downloads(self):
        app = self._get_app()
        sysadmin_user, apikey = self._create_sysadmin(app)
        package = self._create_package(app, apikey)
        resource = self._create_resource(app, package, apikey)
        url = resource['url']

        # Download the resource three times from different IPs.
        self._post_to_tracking(app, url, type_='resource', ip='111.222.333.44')
        self._post_to_tracking(app, url, type_='resource', ip='111.222.333.55')
        self._post_to_tracking(app, url, type_='resource', ip='111.222.333.66')

        self._update_tracking_summary()

        package = tests.call_action_api(app, 'package_show', id=package['id'])
        assert len(package['resources']) == 1
        resource = package['resources'][0]
        tracking_summary = resource['tracking_summary']
        assert tracking_summary['recent'] == 3, (
            "A resource that has been downloaded 3 times recently should have "
            "3 recent downloads")
        assert tracking_summary['total'] == 3, (
            "A resource that has been downloaded 3 times should have 3 total "
            "downloads")

        tracking_summary = package['tracking_summary']
        assert tracking_summary['recent'] == 0, (
            "Downloading a resource should not increase the resource's "
            "package's recent views")
        assert tracking_summary['total'] == 0, (
            "Downloading a resource should not increase the resource's "
            "package's total views")

    def test_page_with_many_views(self):
        app = self._get_app()

        # View each page three times, from three different IPs.
        for ip in ('111.111.11.111', '222.222.22.222', '333.333.33.333'):
            # Visit the front page.
            self._post_to_tracking(app, url='', type_='page', ip=ip)
            # Visit the /organization page.
            self._post_to_tracking(app, url='/organization', type_='page',
                                   ip=ip)
            # Visit the /about page.
            self._post_to_tracking(app, url='/about', type_='page', ip=ip)

        self._update_tracking_summary()

        # There's no way to export page-view (as opposed to resource or
        # dataset) tracking summaries, eg. via the api or a paster command, the
        # only way we can check them if through the model directly.
        import ckan.model as model
        for url in ('', '/organization', '/about'):
            q = model.Session.query(model.TrackingSummary)
            q = q.filter_by(url=url)
            tracking_summary = q.one()
            assert tracking_summary.count == 3, (
                "A page that has been viewed three times should have view "
                "count 3")
            # For pages (as opposed to datasets and resources) recent_views and
            # running_total always stay at 1. Shrug.
            assert tracking_summary.recent_views == 0, ("recent_views for "
                                                        "pages is always 0")
            assert tracking_summary.running_total == 0, ("running_total for "
                                                         "pages is always 0")

    def test_recent_views_expire(self):
        # TODO
        # Test that package, resource and page views (maybe 3 different tests)
        # older than 14 days are counted as total views but not as recent
        # views.
        # Will probably have to access the model directly to insert tracking
        # data older than 14 days.
        pass

    def test_dataset_view_count_throttling(self):
        '''If the same user visits the same dataset multiple times on the same
        day, only one view should get counted.

        '''
        app = self._get_app()
        sysadmin_user, apikey = self._create_sysadmin(app)
        package = self._create_package(app, apikey)
        self._create_resource(app, package, apikey)
        url = routes.url_for(controller='package', action='read',
                             id=package['name'])

        # Visit the dataset three times from the same IP.
        self._post_to_tracking(app, url)
        self._post_to_tracking(app, url)
        self._post_to_tracking(app, url)

        self._update_tracking_summary()

        package = tests.call_action_api(app, 'package_show', id=package['id'])
        tracking_summary = package['tracking_summary']
        assert tracking_summary['recent'] == 1, ("Repeat dataset views should "
                                                 "not add to recent views "
                                                 "count")
        assert tracking_summary['total'] == 1, ("Repeat dataset views should "
                                                "not add to total views count")

    def test_resource_download_count_throttling(self):
        '''If the same user downloads the same resource multiple times on the
        same day, only one view should get counted.

        '''
        app = self._get_app()
        sysadmin_user, apikey = self._create_sysadmin(app)
        package = self._create_package(app, apikey)
        resource = self._create_resource(app, package, apikey)

        # Download the resource three times from the same IP.
        self._post_to_tracking(app, resource['url'], type_='resource')
        self._post_to_tracking(app, resource['url'], type_='resource')
        self._post_to_tracking(app, resource['url'], type_='resource')

        self._update_tracking_summary()

        resource = tests.call_action_api(app, 'resource_show',
                                         id=resource['id'])
        tracking_summary = resource['tracking_summary']
        assert tracking_summary['recent'] == 1, (
            "Repeat resource downloads should not add to recent views count")
        assert tracking_summary['total'] == 1, (
            "Repeat resource downloads should not add to total views count")

    def test_sorting_datasets_by_recent_views(self):
        # FIXME: Have some datasets with different numbers of recent and total
        # views, to make this a better test.
        import ckan.lib.search

        tests.setup_test_search_index()

        app = self._get_app()
        sysadmin_user, apikey = self._create_sysadmin(app)
        self._create_package(app, apikey, name='consider_phlebas')
        self._create_package(app, apikey, name='the_player_of_games')
        self._create_package(app, apikey, name='use_of_weapons')

        url = routes.url_for(controller='package', action='read',
                             id='consider_phlebas')
        self._post_to_tracking(app, url)

        url = routes.url_for(controller='package', action='read',
                             id='the_player_of_games')
        self._post_to_tracking(app, url, ip='111.11.111.111')
        self._post_to_tracking(app, url, ip='222.22.222.222')

        url = routes.url_for(controller='package', action='read',
                             id='use_of_weapons')
        self._post_to_tracking(app, url, ip='111.11.111.111')
        self._post_to_tracking(app, url, ip='222.22.222.222')
        self._post_to_tracking(app, url, ip='333.33.333.333')

        self._update_tracking_summary()
        ckan.lib.search.rebuild()

        response = tests.call_action_api(app, 'package_search',
                                         sort='views_recent desc')
        assert response['count'] == 3
        assert response['sort'] == 'views_recent desc'
        packages = response['results']
        assert packages[0]['name'] == 'use_of_weapons'
        assert packages[1]['name'] == 'the_player_of_games'
        assert packages[2]['name'] == 'consider_phlebas'

    def test_sorting_datasets_by_total_views(self):
        # FIXME: Have some datasets with different numbers of recent and total
        # views, to make this a better test.
        import ckan.lib.search

        tests.setup_test_search_index()

        app = self._get_app()
        sysadmin_user, apikey = self._create_sysadmin(app)
        self._create_package(app, apikey, name='consider_phlebas')
        self._create_package(app, apikey, name='the_player_of_games')
        self._create_package(app, apikey, name='use_of_weapons')

        url = routes.url_for(controller='package', action='read',
                             id='consider_phlebas')
        self._post_to_tracking(app, url)

        url = routes.url_for(controller='package', action='read',
                             id='the_player_of_games')
        self._post_to_tracking(app, url, ip='111.11.111.111')
        self._post_to_tracking(app, url, ip='222.22.222.222')

        url = routes.url_for(controller='package', action='read',
                             id='use_of_weapons')
        self._post_to_tracking(app, url, ip='111.11.111.111')
        self._post_to_tracking(app, url, ip='222.22.222.222')
        self._post_to_tracking(app, url, ip='333.33.333.333')

        self._update_tracking_summary()
        ckan.lib.search.rebuild()

        response = tests.call_action_api(app, 'package_search',
                                         sort='views_total desc')
        assert response['count'] == 3
        assert response['sort'] == 'views_total desc'
        packages = response['results']
        assert packages[0]['name'] == 'use_of_weapons'
        assert packages[1]['name'] == 'the_player_of_games'
        assert packages[2]['name'] == 'consider_phlebas'

    def test_popular_package(self):
        # TODO
        # Test that a package with > 10 views is marked as 'popular'.
        # Currently the popular logic is in the templates, will have to move
        # that into the logic and add 'popular': True/False to package dicts
        # to make this testable.
        # Also test that a package with < 10 views is not marked as popular.
        # Test what kind of views count towards popularity, recent or total,
        # and which don't.
        pass

    def test_popular_resource(self):
        # TODO
        # Test that a resource with > 10 views is marked as 'popular'.
        # Currently the popular logic is in the templates, will have to move
        # that into the logic and add 'popular': True/False to resource dicts
        # to make this testable.
        # Also test that a resource with < 10 views is not marked as popular.
        # Test what kind of views count towards popularity, recent or total,
        # and which don't.
        pass

    def test_same_user_visiting_different_pages_on_same_day(self):
        # TODO
        # Test that if the same user visits multiple pages on the same say,
        # each visit gets counted (this should not get throttled)
        # (May need to test for packages, resources and pages separately)
        pass

    def test_same_user_visiting_same_page_on_different_days(self):
        # TODO
        # Test that if the same user visits the same page on different days,
        # each visit gets counted (this should not get throttled)
        # (May need to test for packages, resources and pages separately)
        # (Probably need to access the model directly to insert old visits
        # into tracking_raw)
        pass

    def test_posting_bad_data_to_tracking(self):
        # TODO: Test how /_tracking handles unexpected and invalid data.
        pass

    def _export_tracking_summary(self):
        '''Export CKAN's tracking data and return it.

        This simulates calling `paster tracking export` on the command line.

        '''
        # FIXME: Can this be done as more of a functional test where we
        # actually test calling the command and passing the args? By calling
        # the method directly, we're not testing the command-line parsing.
        import ckan.lib.cli
        import ckan.model
        f = tempfile.NamedTemporaryFile()
        ckan.lib.cli.Tracking('Tracking').export_tracking(
            engine=ckan.model.meta.engine, output_filename=f.name)
        lines = [line for line in csv.DictReader(open(f.name, 'r'))]
        return lines

    def test_export(self):
        '''`paster tracking export` should export tracking data for all
        datasets in CSV format.

        Only dataset tracking data is output to CSV file, not resource or page
        views.

        '''
        app = self._get_app()
        sysadmin_user, apikey = self._create_sysadmin(app)

        # Create a couple of packages.
        package_1 = self._create_package(app, apikey)
        package_2 = self._create_package(app, apikey, name='another_package')

        # View the package_1 three times from different IPs.
        url = routes.url_for(controller='package', action='read',
                             id=package_1['name'])
        self._post_to_tracking(app, url, ip='111.222.333.44')
        self._post_to_tracking(app, url, ip='111.222.333.55')
        self._post_to_tracking(app, url, ip='111.222.333.66')

        # View the package_2 twice from different IPs.
        url = routes.url_for(controller='package', action='read',
                             id=package_2['name'])
        self._post_to_tracking(app, url, ip='111.222.333.44')
        self._post_to_tracking(app, url, ip='111.222.333.55')

        self._update_tracking_summary()
        lines = self._export_tracking_summary()

        assert len(lines) == 2
        package_1_data = lines[0]
        assert package_1_data['total views'] == '3'
        assert package_1_data['recent views (last 2 weeks)'] == '3'
        package_2_data = lines[1]
        assert package_2_data['total views'] == '2'
        assert package_2_data['recent views (last 2 weeks)'] == '2'

    def test_tracking_urls_with_languages(self):
        # TODO
        # Test that posting to eg /de/dataset/foo is counted the same as
        # /dataset/foo.
        # May need to test for dataset pages, resource previews, resource
        # downloads, and other page views separately.
        pass

    def test_templates_tracking_enabled(self):
        # TODO
        # Test the the page view tracking JS is in the templates when
        # ckan.tracking_enabled = true.
        # Test that the sort by populatiy option is shown on the datasets page.
        pass

    def test_templates_tracking_disabled(self):
        # TODO
        # Test the the page view tracking JS is not in the templates when
        # ckan.tracking_enabled = false.
        # Test that the sort by populatiy option is not on the datasets page.
        pass

    def test_tracking_disabled(self):
        # TODO
        # Just to make sure, set ckan.tracking_enabled = false and then post
        # a bunch of stuff to /_tracking and test that no tracking data is
        # recorded. Maybe /_tracking should return something other than 200,
        # as well.
        # Could also test that 'tracking_summary' is _not_ in package and
        # resource dicts from api when tracking is disabled.
        pass
