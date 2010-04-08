import cgi

from paste.fixture import AppError

from ckan.tests import *
import ckan.model as model
from ckan.lib.create_test_data import CreateTestData

package_form = 'gov'

class TestPackageBase(TestController):
    def _assert_form_errors(self, res):
        self.check_tag(res, '<form', 'class="has-errors"')
        assert 'class="field_error"' in res, res

class TestRead(TestPackageBase):
    # TODO: reinstate
    # disable for time being
    __test__ = False
    @classmethod
    def setup_class(self):
        CreateTestData.create_gov_test_data(extra_users=[u'testadmin'])

        pkg = model.Package.by_name(u'private-fostering-england-2009')
        model.setup_default_user_roles(pkg, [model.User.by_name(u'testadmin')])
        model.repo.commit_and_remove()

    @classmethod
    def teardown_class(self):
        CreateTestData.delete()

    def test_read(self):
        name = u'private-fostering-england-2009'
        offset = url_for(controller='package', action='read', id=name)
        res = self.app.get(offset)
        # only retrieve after app has been called
        self.anna = model.Package.by_name(name)
        print self.main_div(res)
        assert 'Packages - %s' % name in res
        assert name in res
        assert 'State:' not in res

    def test_read_as_admin(self):
        name = u'private-fostering-england-2009'
        offset = url_for(controller='package', action='read', id=name)
        res = self.app.get(offset, extra_environ={'REMOTE_USER':'testadmin'})
        main_res = self.main_div(res)
        assert 'State:' in main_res

class TestEdit(TestPackageBase):
    @classmethod
    def setup_class(self):
        model.Session.add(model.User(name=u'testadmin'))
        model.repo.commit_and_remove()

    @classmethod
    def teardown_class(self):
        model.Session.remove()
        model.repo.rebuild_db()


    def test_edit_bad_name(self):
        init_data = [{'name':'edittest',
                      'url':'testurl',
                      'admins':['testadmin']}]
        CreateTestData.create_arbitrary(init_data)

        editpkg = model.Package.by_name(unicode(init_data[0]['name']))
        self.pkgid = editpkg.id
        offset = url_for(controller='package', action='edit', id=init_data[0]['name'], package_form=package_form)
        self.res = self.app.get(offset)

        fv = self.res.forms[0]
        prefix = 'Package-%s-' % self.pkgid
        fv[prefix + 'name'] = u'a' # invalid name
        res = fv.submit('commit')
        assert 'Error' in res, res
        assert 'Name must be at least 2 characters long' in res, res
        self._assert_form_errors(res)
        
    # Disable temporarily
    # These look to be rather too verbose and fragile
    # It is usually sufficient to test a couple of items
    # Also wonder if there is a way to automate parts of this rather than long
    # listings ...
    def _test_edit_all_fields(self):
        # Create new item
        rev = model.repo.new_revision()
        pkg_name = u'new_editpkgtest'
        pkg = model.Package(name=pkg_name)
        model.Session.add(pkg)
        pkg.title = u'This is a Test Title'
        pkg.url = u'editpkgurl.com'
        pr1 = model.PackageResource(url=u'editpkgurl1',
              format=u'plain text', description=u'Full text')
        pr2 = model.PackageResource(url=u'editpkgurl2',
              format=u'plain text2', description=u'Full text2')
        model.Session.add(pr1)
        model.Session.add(pr2)        
        pkg.resources.append(pr1)
        pkg.resources.append(pr2)
        pkg.notes= u'this is editpkg'
        pkg.version = u'2.2'
        pkg.tags = [model.Tag(name=u'one'), model.Tag(name=u'two')]
        for tag in pkg.tags:
            model.Session.add(tag)
        pkg.state = model.State.DELETED
        tags_txt = ' '.join([tag.name for tag in pkg.tags])
        pkg.license = model.License.by_name(u'OKD Compliant::Other')
        external_reference = 'ref-test'
        date_released = '2009-07-30'
        date_updated = '1998-12-25'
        update_frequency = 'annually'
        geographic_granularity = 'local authority'
        geographic_coverage = '111000: England, Scotland, Wales'
        department = 'Department for Children, Schools and Families'
        temporal_granularity = 'years'
        temporal_coverage = ('2007-12', '2009-03')
        categories = 'Health, well-being and Care; '
        national_statistic = 'yes'
        precision = 'Nearest 1000'
        taxonomy_url = 'http://some.com/taxonomy'
        agency = 'FOGB'
        current_extras = {
            'external_reference':external_reference,
            'date_released':date_released,
            'date_updated':date_updated,
            'update_frequency':update_frequency,
            'geographic_granularity':geographic_granularity,
            'geographic_coverage':geographic_coverage,
            'department':department,
            'temporal_granularity':temporal_granularity,
            'temporal_coverage-from':temporal_coverage[0],
            'temporal_coverage-to':temporal_coverage[1],
            'categories':categories,
            'national_statistic':national_statistic,
            'precision':precision,
            'taxonomy_url':taxonomy_url,
            'agency':agency,
            }
        for key, value in current_extras.items():
            pkg.extras[unicode(key)] = unicode(value)
        model.repo.commit_and_remove()
        pkg = model.Package.by_name(pkg_name)
        admin = model.User.by_name(u'testadmin')
        assert admin
        model.setup_default_user_roles(pkg, [admin])

        # Edit it
        offset = url_for(controller='package', action='edit', id=pkg.name, package_form=package_form)
        res = self.app.get(offset, status=200, extra_environ={'REMOTE_USER':'testadmin'})
        assert 'Packages - Edit' in res, res
        
        # Check form is correctly filled
        prefix = 'Package-%s-' % pkg.id
        main_res = self.main_div(res)
        self.check_tag(main_res, prefix + 'name', 'value="%s"' % pkg.name)
        self.check_tag(main_res, prefix + 'title', 'value="%s"' % pkg.title)
#        self.check_tag(main_res, prefix + 'version', 'value="%s"' % pkg.version)
        self.check_tag(main_res, prefix + 'url', 'value="%s"' % pkg.url)
        for i, resource in enumerate(pkg.resources):
            self.check_tag(main_res, prefix + 'resources-%i-url' % i, 'value="%s"' % resource.url)
            self.check_tag(main_res, prefix + 'resources-%i-format' % i, 'value="%s"' % resource.format)
            self.check_tag(main_res, prefix + 'resources-%i-description' % i, 'value="%s"' % resource.description)
        self.check_tag_and_data(main_res, '<textarea', 'id="%snotes"' % prefix,  '%s' % pkg.notes)
        self.check_named_element(main_res, 'select', prefix+'license', pkg.license.name)
        self.check_tag(main_res, prefix + 'tags', 'value="%s"' % tags_txt.lower())
        self.check_tag(main_res, prefix + 'external_reference', 'value="%s"' % external_reference)
        self.check_tag(main_res, prefix + 'date_released', 'value="%s"' % '30/7/2009')
        self.check_tag(main_res, prefix + 'date_updated', 'value="%s"' % '25/12/1998')
        self.check_tag(main_res, prefix + 'update_frequency', 'value="%s"' % update_frequency)
        self.check_named_element(main_res, 'select', prefix + 'geographic_granularity', 'value="%s"' % geographic_granularity)
        self.check_tag(main_res, prefix + 'geographic_coverage-england', 'checked')
        self.check_tag(main_res, prefix + 'geographic_coverage-scotland', 'checked')
        self.check_tag(main_res, prefix + 'geographic_coverage-wales', 'checked')
        self.check_tag(main_res, prefix + 'geographic_coverage-northern_ireland', '!checked')
        self.check_tag(main_res, prefix + 'geographic_coverage-overseas', '!checked')
        self.check_tag(main_res, prefix + 'geographic_coverage-global', '!checked')
        self.check_tag(main_res, 'option value="%s" selected' % department)
        self.check_tag(main_res, prefix + 'department-other', 'value=""')
        self.check_named_element(main_res, 'select', prefix + 'temporal_granularity', 'value="%s"' % temporal_granularity)
        self.check_tag(main_res, prefix + 'temporal_coverage-from', 'value="%s"' % '12/2007')
        self.check_tag(main_res, prefix + 'temporal_coverage-to', 'value="%s"' % '3/2009')
        self.check_tag(main_res, prefix + 'categories', 'value="%s"' % categories)
        self.check_tag(main_res, prefix + 'national_statistic', 'checked' if national_statistic=='yes' else '!checked')
        self.check_tag(main_res, prefix + 'precision', 'value="%s"' % precision)
        self.check_tag(main_res, prefix + 'taxonomy_url', 'value="%s"' % taxonomy_url)
        self.check_tag(main_res, prefix + 'agency', 'value="%s"' % agency)

        # Amend form
        name = u'test_name'
        title = u'Test Title'
#        version = u'1.1'
        url = u'http://something.com/somewhere.zip'
        resources = ((u'http://something.com/somewhere-else.xml', u'xml', u'Best'),
                     (u'http://something.com/somewhere-else2.xml', u'xml2', u'Best2'),
#                     (u'http://something.com/somewhere-else3.xml', u'xml3', u'Best3'),
                     )
        notes = u'Very important'
        license_id = 4
        license = u'OKD Compliant::Creative Commons CCZero'
        state = model.State.ACTIVE
        tags = (u'tag1', u'tag2', u'tag3')
        tags_txt = u' '.join(tags)
        extra_changed = 'key1', 'value1 CHANGED'
        extra_new = 'newkey', 'newvalue'
        log_message = 'This is a comment'
        external_reference = 'ref-test-changed'
        date_released = '2009-07-31'
        date_updated = '1998-12-26'
        update_frequency = 'Monthly'
        geographic_granularity = 'Country'
        geographic_coverage = '001000: Wales'
        department = 'Crown Estate'
        temporal_granularity = 'months'
        temporal_coverage = ('2004-12', '2005-03')
        categories = 'Economy' #; Government'
        national_statistic = 'yes'
        precision = 'Nearest 10'
        taxonomy_url = 'http://some.com/taxonomy/CHANGED'
        agency = 'EOGB'
        current_extras = {
            'external_reference':external_reference,
            'date_released':date_released,
            'date_updated':date_updated,
            'update_frequency':update_frequency,
            'geographic_granularity':geographic_granularity,
            'geographic_coverage':geographic_coverage,
            'department':department,
            'temporal_granularity':temporal_granularity,
            'temporal_coverage-from':temporal_coverage[0],
            'temporal_coverage-to':temporal_coverage[1],
            'categories':categories,
            'national_statistic':national_statistic,
            'precision':precision,
            'taxonomy_url':taxonomy_url,
            'agency':agency,
            }
        assert not model.Package.by_name(name)
        fv = res.forms[0]
        prefix = 'Package-%s-' % pkg.id
        fv[prefix+'name'] = name
        fv[prefix+'title'] = title
#        fv[prefix+'version'] = version
        fv[prefix+'url'] = url
        for res_index, resource in enumerate(resources):
            for field_index, res_field in enumerate(('url', 'format', 'description')):
                fv[prefix+'resources-%s-%s' % (res_index, res_field)] = resource[field_index]
        fv[prefix+'notes'] = notes
        fv[prefix+'license_id'] = license_id
        fv[prefix+'tags'] = tags_txt
        fv[prefix+'external_reference'] = external_reference
        fv[prefix+'date_released'] = '31/7/2009'
        fv[prefix+'date_updated'] = '26/12/1998'
        fv[prefix+'update_frequency'] = update_frequency
        fv[prefix+'geographic_granularity'] = 'other'
        fv[prefix+'geographic_granularity-other'] = geographic_granularity
        fv[prefix+'geographic_coverage-england'] = False
        fv[prefix+'geographic_coverage-scotland'] = False
        fv[prefix+'geographic_coverage-wales'] = True
        fv[prefix+'department'] = department
        fv[prefix+'temporal_granularity'] = temporal_granularity
        fv[prefix+'temporal_coverage-from'] = '12/2004'
        fv[prefix+'temporal_coverage-to'] = '3/2005'
        fv[prefix+'categories'] = categories
        fv[prefix+'national_statistic'] = True if national_statistic == 'yes' else False
        fv[prefix+'precision'] = precision
        fv[prefix+'taxonomy_url'] = taxonomy_url
        fv[prefix+'agency'] = agency
        fv[prefix+'state'] = state
        fv['log_message'] = log_message
        res = fv.submit('preview', extra_environ={'REMOTE_USER':'testadmin'})
        assert not 'Error' in res, res

        # Check preview is correct
        res1 = str(res).replace('</strong>', '')
        preview =  res1[res1.find('<div id="preview"'):res1.find('<div id="footer">')]
        assert 'Preview' in preview, preview
        assert 'Title: %s' % str(title) in preview, preview
#        assert 'Version: %s' % str(version) in preview, preview
        assert 'URL: <a href="%s">' % str(url) in preview, preview
        for res_index, resource in enumerate(resources):
            res_html = '<tr> <td><a href="%s">%s</a></td><td>%s</td><td>%s</td>' % (resource[0], resource[0], resource[1], resource[2]) 
            assert res_html in preview, preview + res_html
        assert '<p>%s' % str(notes) in preview, preview
        assert 'License: %s' % str(license) in preview, preview
        assert 'External reference: %s' % str(external_reference) in preview, preview
        assert 'Date released: 31/7/2009' in preview, preview
        assert 'Date updated: 26/12/1998' in preview, preview
        assert 'Update frequency: %s' % update_frequency in preview, preview
        assert 'Geographic granularity: %s' % geographic_granularity in preview, preview
        assert 'Geographic coverage: %s' % 'Wales' in preview, preview
        assert 'Department: %s' % department in preview, preview
        assert 'Temporal granularity: %s' % temporal_granularity in preview, preview
        assert 'Categories: %s' % categories in preview, preview
        assert 'National statistic: %s' % national_statistic in preview, preview
        assert 'Precision: %s' % precision in preview, preview
        assert 'Taxonomy URL: <a href="%s">%s</a>' % (taxonomy_url, taxonomy_url) in preview, preview
        assert 'Agency: %s' % agency in preview, preview
        tags_html_list = ['<a href="/tag/read/%s">%s</a>' % (str(tag), str(tag)) for tag in tags]
        tags_html_preview = ' '.join(tags_html_list)
        assert 'Tags: %s' % tags_html_preview in preview, preview + tags_html_preview
        groups_html = ''
#        assert 'Groups:\n%s' % groups_html in preview, preview + groups_html
        assert 'State: %s' % str(state) in preview, preview
        assert '<li><strong>:</strong> </li>' not in preview, preview

        # Check form is correctly filled
        main_res = self.main_div(res)
        self.check_tag(main_res, prefix + 'name', 'value="%s"' % name)
        self.check_tag(main_res, prefix + 'title', 'value="%s"' % title)
#        self.check_tag(main_res, prefix + 'version', 'value="%s"' % version)
        self.check_tag(main_res, prefix + 'url', 'value="%s"' % url)
        for i, resource in enumerate(resources):
            self.check_tag(main_res, prefix + 'resources-%i-url' % i, 'value="%s"' % resource[0])
            self.check_tag(main_res, prefix + 'resources-%i-format' % i, 'value="%s"' % resource[1])
            self.check_tag(main_res, prefix + 'resources-%i-description' % i, 'value="%s"' % resource[2])
        self.check_tag_and_data(main_res, '<textarea', 'id="%snotes"' % prefix,  '%s' % notes)
        self.check_named_element(main_res, 'select', prefix+'license', license)
        self.check_tag(main_res, prefix + 'tags', 'value="%s"' % tags_txt.lower())
        self.check_tag(main_res, prefix + 'external_reference', 'value="%s"' % external_reference)
        self.check_tag(main_res, prefix + 'date_released', 'value="%s"' % '31/7/2009')
        self.check_tag(main_res, prefix + 'date_updated', 'value="%s"' % '26/12/1998')
        self.check_tag(main_res, prefix + 'update_frequency', 'value="%s"' % update_frequency)
        self.check_tag(main_res, prefix + 'geographic_granularity-other', 'value="%s"' % geographic_granularity)
        self.check_tag(main_res, prefix + 'geographic_coverage-england', '!checked')
        self.check_tag(main_res, prefix + 'geographic_coverage-scotland', '!checked')
        self.check_tag(main_res, prefix + 'geographic_coverage-wales', 'checked')
        self.check_tag(main_res, prefix + 'geographic_coverage-northern_ireland', '!checked')
        self.check_tag(main_res, prefix + 'geographic_coverage-overseas', '!checked')
        self.check_tag(main_res, prefix + 'geographic_coverage-global', '!checked')
        self.check_tag(main_res, 'option value="%s" selected' % department)
        self.check_named_element(main_res, 'select', prefix + 'department', 'value="%s"' % department)
        self.check_tag(main_res, prefix + 'department-other', '')
        self.check_named_element(main_res, 'select', prefix + 'temporal_granularity', 'value="%s"' % temporal_granularity)
        self.check_tag(main_res, prefix + 'temporal_coverage-from', 'value="%s"' % '12/2004')
        self.check_tag(main_res, prefix + 'temporal_coverage-to', 'value="%s"' % '3/2005')
        self.check_named_element(main_res, 'select', prefix + 'categories', 'value="%s"' % categories, 'select')
        self.check_tag(main_res, prefix + 'national_statistic', 'checked' if national_statistic=='yes' else '!checked')
        self.check_tag(main_res, prefix + 'precision', 'value="%s"' % precision)
        self.check_tag(main_res, prefix + 'taxonomy_url', 'value="%s"' % taxonomy_url)
        self.check_tag(main_res, prefix + 'agency', 'value="%s"' % agency)
        assert log_message in res

        # Submit
        res = fv.submit('commit', extra_environ={'REMOTE_USER':'testadmin'})

        # Check package page
        assert not 'Error' in res, res
        res = res.follow(extra_environ={'REMOTE_USER':'testadmin'})
        main_res = self.main_div(res).replace('</strong>', '')
        sidebar = self.sidebar(res)
        res1 = (main_res + sidebar).decode('ascii', 'ignore')
        assert 'Packages - %s' % str(name) in res, res
        assert str(name) in res1, res1
        assert str(title) in res1, res1
#        assert str(version) in res1, res1
        assert '<a href="%s">' % str(url).lower() in res1.lower(), res1
        for res_index, resource in enumerate(resources):
            res_html = '<tr> <td><a href="%s">%s</a></td><td>%s</td><td>%s</td>' % (resource[0], resource[0], resource[1], resource[2]) 
            assert res_html in preview, preview + res_html
        assert '<p>%s' % str(notes) in res1, res1
        assert 'License: %s' % str(license) in res1, res1
        for tag_html in tags_html_list:
            assert tag_html in res1, tag_html + res1
        assert groups_html in res1, res1 + groups_html
        assert 'State: %s' % str(state) in res1, res1
        for key, value in current_extras.items():
            self.check_named_element(res1, 'li', '%s:' % key.capitalize(), value)

        # Check package object
        pkg = model.Package.by_name(name)
        assert pkg.name == name
        assert pkg.title == title
#        assert pkg.version == version
        assert pkg.url == url
        for res_index, resource in enumerate(resources):
            for field_index, res_field in enumerate(('url', 'format', 'description')):
                assert getattr(pkg.resources[res_index], res_field) == resource[field_index]
        assert pkg.notes == notes
        assert pkg.license_id == license_id
        saved_tagnames = [str(tag.name) for tag in pkg.tags]
        assert saved_tagnames == list(tags)
        assert pkg.state == state
        assert len(pkg.extras) == len(current_extras), '%i!=%i\n%s' % (len(pkg.extras), len(current_extras), pkg.extras)
        for key, value in current_extras.items():
            assert pkg.extras[key] == value

        # for some reason environ['REMOTE_ADDR'] is undefined
        rev = model.Revision.youngest()
        assert rev.author == 'testadmin', rev.author
        assert rev.message == log_message
        # TODO: reinstate once fixed in code
        exp_log_message = u'Creating package %s' % name
        #assert rev.message == exp_log_message


class TestNew(TestPackageBase):
    pkgname = u'testpkg'

    @classmethod
    def teardown_class(self):
        model.Session.remove()
        pkg = model.Package.by_name(self.pkgname)
        if pkg:
            pkg.purge()
        model.Session.commit()
        model.Session.remove()

    def test_new_simple(self):
        # new package
        prefix = 'Package--'
        name = u'test_simple'
        offset = url_for(controller='package', action='new', package_form=package_form)
        res = self.app.get(offset)
        fv = res.forms[0]
        fv[prefix+'name'] = name
        res = fv.submit('commit')

        # check package page
        assert not 'Error' in res, res
        res = res.follow()

        # check object created
        pkg = model.Package.by_name(name)
        assert pkg
        assert pkg.name == name

    # Disable temporarily
    def _test_new_all_fields(self):
        name = u'test_name2'
        title = u'Test Title'
#        version = u'1.1'
        url = u'http://something.com/somewhere.zip'
        download_url = u'http://something.com/somewhere-else.zip'
        download_format = u'zip'
        notes = u'Very important'
        license_id = 4
        license = u'OKD Compliant::Creative Commons CCZero'
        tags = (u'tag1', u'tag2', u'tag3', u'SomeCaps')
        tags_txt = u' '.join(tags)
        # new fields
        external_reference = 'ref-test'
        date_released = '2009-07-30'
        date_updated = '1998-12-25'
        update_frequency = 'annually'
        geographic_granularity = 'local authority'
        geographic_coverage = '100000: England'
        department = 'Department for Children, Schools and Families'
        temporal_granularity = 'years'
        temporal_coverage = ('2007-12', '2009-03')
        categories = 'Health, well-being and Care; '
        national_statistic = 'no'
        precision = 'Nearest 1000'
        taxonomy_url = 'http://some.com/taxonomy'
        agency = 'FOGB'
        # end of new fields
        log_message = 'This is a comment'
        assert not model.Package.by_name(name)
        offset = url_for(controller='package', action='new', package_form=package_form)
        res = self.app.get(offset)
        assert 'Packages - New' in res
        fv = res.forms[0]
        prefix = 'Package--'
        fv[prefix+'name'] = name
        fv[prefix+'title'] = title
#        fv[prefix+'version'] = version
        fv[prefix+'url'] = url
        fv[prefix+'resources-0-url'] = download_url
        fv[prefix+'resources-0-format'] = download_format
        fv[prefix+'notes'] = notes
        fv[prefix+'license_id'] = license_id
        fv[prefix+'tags'] = tags_txt
        fv[prefix+'external_reference'] = external_reference
        fv[prefix+'date_released'] = '30/7/2009'
        fv[prefix+'date_updated'] = '25/12/1998'
        fv[prefix+'update_frequency'] = update_frequency
        fv[prefix+'geographic_granularity'] = geographic_granularity
        fv[prefix+'geographic_coverage-england'] = True
        fv[prefix+'department'] = department
        fv[prefix+'temporal_granularity'] = temporal_granularity
        fv[prefix+'temporal_coverage-from'] = '12/2007'
        fv[prefix+'temporal_coverage-to'] = '3/2009'
        fv[prefix+'categories-other'] = categories
        fv[prefix+'national_statistic'] = True if national_statistic == 'yes' else False
        fv[prefix+'precision'] = precision
        fv[prefix+'taxonomy_url'] = taxonomy_url
        fv[prefix+'agency'] = agency
        fv['log_message'] = log_message
        res = fv.submit('preview')
        assert not 'Error' in res, res

        # Check preview is correct
        res1 = str(res).replace('</strong>', '')
        preview =  res1[res1.find('<div id="preview"'):res1.find('<div id="footer">')]
        assert 'Preview' in res
        assert 'Title: %s' % str(title) in preview, preview
#        assert 'Version: %s' % str(version) in preview, preview
        assert 'URL: <a href="%s">' % str(url) in preview, preview
        res_html = '<tr> <td><a href="%s">%s</a></td><td>%s</td><td>%s</td>' % (str(download_url), str(download_url), str(download_format), '') 
        assert res_html in preview, preview + res_html
        assert '<p>%s' % str(notes) in preview, preview
        assert 'License: %s' % str(license) in preview, preview
        assert 'External reference: %s' % str(external_reference) in preview, preview
        assert 'Date released: 30/7/2009' in preview, preview
        assert 'Date updated: 25/12/1998' in preview, preview
        assert 'Update frequency: %s' % update_frequency in preview, preview
        assert 'Geographic granularity: %s' % geographic_granularity in preview, preview
        assert 'Geographic coverage: %s' % 'England' in preview, preview
        assert 'Department: %s' % department in preview, preview
        assert 'Temporal granularity: %s' % temporal_granularity in preview, preview
        assert 'Temporal coverage: 12/2007 - 3/2009' in preview, preview
        assert 'Categories: %s' % categories in preview, preview
        assert 'National statistic: %s' % national_statistic in preview, preview
        assert 'Precision: %s' % precision in preview, preview
        assert 'Taxonomy URL: <a href="%s">%s</a>' % (taxonomy_url, taxonomy_url) in preview, preview
        assert 'Agency: %s' % agency in preview, preview
        for tag in tags:
            assert '%s</a>' % tag.lower() in preview

        assert '<li><strong>:</strong> </li>' not in preview, preview

        # Check form is correctly filled
        main_res = self.main_div(res)
        prefix = 'Package--'
        self.check_tag(main_res, prefix + 'title', 'value="%s"' % title)
        self.check_tag(main_res, prefix + 'title', 'value="%s"' % title)
#        self.check_tag(main_res, prefix + 'version', 'value="%s"' % version)
        self.check_tag(main_res, prefix + 'url', 'value="%s"' % url)
        self.check_tag(main_res, prefix + 'resources-0-url', 'value="%s"' % download_url)
        self.check_tag(main_res, prefix + 'resources-0-format', 'value="%s"' % download_format)
        self.check_tag_and_data(main_res, '<textarea', 'id="%snotes"' % prefix,  '%s' % notes)
        self.check_named_element(main_res, 'select', prefix+'license', str(license_id))
        self.check_tag(main_res, prefix + 'tags', 'value="%s"' % tags_txt.lower())
        self.check_tag(main_res, prefix + 'external_reference', 'value="%s"' % external_reference)
        self.check_tag(main_res, prefix + 'date_released', 'value="%s"' % '30/7/2009')
        self.check_tag(main_res, prefix + 'date_updated', 'value="%s"' % '25/12/1998')
        self.check_tag(main_res, prefix + 'update_frequency', 'value="%s"' % update_frequency)
        self.check_named_element(main_res, 'select', prefix + 'geographic_granularity', 'value="%s"' % geographic_granularity)
        self.check_tag(main_res, prefix + 'geographic_coverage-england', 'checked')
        self.check_tag(main_res, prefix + 'geographic_coverage-scotland', '!checked')
        self.check_tag(main_res, prefix + 'geographic_coverage-wales', '!checked')
        self.check_tag(main_res, prefix + 'geographic_coverage-northern_ireland', '!checked')
        self.check_tag(main_res, prefix + 'geographic_coverage-overseas', '!checked')
        self.check_tag(main_res, prefix + 'geographic_coverage-global', '!checked')
        self.check_tag(main_res, 'option value="%s" selected' % department)
        self.check_tag(main_res, prefix + 'department-other', 'value=""')
        self.check_named_element(main_res, 'select', prefix + 'temporal_granularity', 'value="%s"' % temporal_granularity)
        self.check_tag(main_res, prefix + 'temporal_coverage-from', 'value="%s"' % '12/2007')
        self.check_tag(main_res, prefix + 'temporal_coverage-to', 'value="%s"' % '3/2009')
        self.check_tag(main_res, prefix + 'categories', 'value="%s"' % categories)
        self.check_tag(main_res, prefix + 'national_statistic', 'checked' if national_statistic=='yes' else '!checked')
        self.check_tag(main_res, prefix + 'precision', 'value="%s"' % precision)
        self.check_tag(main_res, prefix + 'taxonomy_url', 'value="%s"' % taxonomy_url)
        self.check_tag(main_res, prefix + 'agency', 'value="%s"' % agency)

        assert log_message in main_res

        # Submit
        res = fv.submit('commit')

        # Check package page
        assert not 'Error' in res, res
        res = res.follow()
        main_res = self.main_div(res).replace('</strong>', '')
        sidebar = self.sidebar(res)
        res1 = main_res + sidebar.decode('ascii', 'ignore')
        assert 'Packages - %s' % str(name) in res, res
        assert  str(name) in res1, res1
        assert str(title) in res1, res1
#        assert str(version) in res1, res1
        assert '<a href="%s">' % str(url).lower() in res1.lower(), res1
        assert '<td><a href="%s">' % str(download_url) in res1, res1
        assert '<td>%s</td>' % str(download_format) in res1, res1
        assert '<p>%s' % str(notes) in res1, res1
        assert str(license) in res1, res1
        for tag in tags:
            assert '%s</a>' % tag.lower() in res
        current_extras = {
            'external_reference':external_reference,
            'date_released':date_released,
            'date_updated':date_updated,
            'update_frequency':update_frequency,
            'geographic_granularity':geographic_granularity,
            'geographic_coverage':geographic_coverage,
            'department':department,
            'temporal_granularity':temporal_granularity,
            'temporal_coverage-from':temporal_coverage[0],
            'temporal_coverage-to':temporal_coverage[1],
            'categories':categories,
            'national_statistic':national_statistic,
            'precision':precision,
            'taxonomy_url':taxonomy_url,
            'agency':agency,
            }
        for key, value in current_extras.items():
            self.check_named_element(res1, 'li', '%s:' % key.capitalize(), value)

        # Check package object
        pkg = model.Package.by_name(name)
        assert pkg.name == name
        assert pkg.title == title
#        assert pkg.version == version
        assert pkg.url == url
        assert pkg.resources[0].url == download_url
        assert pkg.resources[0].format == download_format
        assert pkg.notes == notes
        assert pkg.license_id == license_id
        saved_tagnames = [str(tag.name) for tag in pkg.tags]
        assert saved_tagnames == [tag.lower() for tag in list(tags)]
        saved_groupnames = [str(group.name) for group in pkg.groups]
        assert len(pkg.extras) == len(current_extras)
        for key, value in current_extras.items():
            assert pkg.extras[key] == value

        # for some reason environ['REMOTE_ADDR'] is undefined
        rev = model.Revision.youngest()
        assert rev.author == 'Unknown IP Address'
        assert rev.message == log_message
        # TODO: reinstate once fixed in code
        exp_log_message = u'Creating package %s' % name
        # assert rev.message == exp_log_message

    def test_new_existing_name(self):
        # test creating a package with an existing name results in error'
        # create initial package
        assert not model.Package.by_name(self.pkgname)
        offset = url_for(controller='package', action='new', package_form=package_form)
        res = self.app.get(offset)
        assert 'Packages - New' in res
        fv = res.forms[0]
        prefix = 'Package--'
        fv[prefix + 'name'] = self.pkgname
        res = fv.submit('commit')
        assert not 'Error' in res, res
        assert model.Package.by_name(self.pkgname)

        # create duplicate package
        res = self.app.get(offset)
        assert 'Packages - New' in res
        fv = res.forms[0]
        fv[prefix+'name'] = self.pkgname
        res = fv.submit('preview')
        assert 'Preview' in res
        assert 'Error' in res, res
        assert 'Package name already exists in database' in res, res
        fv = res.forms[0]
        res = fv.submit('commit')
        assert 'Error' in res, res
        assert 'Package name already exists in database' in res, res
        self._assert_form_errors(res)
        
    def test_new_bad_name(self):
        offset = url_for(controller='package', action='new', package_form=package_form)
        res = self.app.get(offset)
        assert 'Packages - New' in res
        fv = res.forms[0]
        prefix = 'Package--'
        # should result in error as need >= 2 chars
        fv[prefix + 'name'] = 'a'
        fv[prefix + 'title'] = 'A Test Package'
        fv[prefix + 'tags'] = 'test tags'
#        fv[prefix + 'groups'] = 'test groups'
        res = fv.submit('commit')
        assert 'Error' in res, res
        assert 'Name must be at least 2 characters long' in res, res
        self._assert_form_errors(res)
        # Ensure fields are prefilled
        assert 'value="A Test Package"' in res, res
        assert 'value="test tags"' in res, res
#        assert 'value="test groups"' in res, res
