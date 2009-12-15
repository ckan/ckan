import cgi

from paste.fixture import AppError

from ckan.tests import *
import ckan.model as model
from ckan.lib.create_test_data import CreateTestData

package_form = 'gov'

class TestRead(TestController):

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

class TestEdit(TestController):
    @classmethod
    def setup_class(self):
        model.User(name=u'testadmin')
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
        # Ensure there is an error at the top of the form and by the field
        assert 'class="form-errors"' in res, res
        assert 'class="field_error"' in res, res

    def test_edit_all_fields(self):
        # Create new item
        rev = model.repo.new_revision()
        pkg_name = u'new_editpkgtest'
        pkg = model.Package(name=pkg_name)
        pkg.title = u'This is a Test Title'
        pkg.url = u'editpkgurl.com'
        pkg.resources.append(model.PackageResource(url=u'editpkgurl1',
              format=u'plain text', description=u'Full text'))
        pkg.resources.append(model.PackageResource(url=u'editpkgurl2',
              format=u'plain text2', description=u'Full text2'))
        pkg.notes= u'this is editpkg'
        pkg.version = u'2.2'
        pkg.tags = [model.Tag(name=u'one'), model.Tag(name=u'two')]
        pkg.state = model.State.query.filter_by(name='deleted').one()
        tags_txt = ' '.join([tag.name for tag in pkg.tags])
        pkg.license = model.License.byName(u'OKD Compliant::Other')
        external_reference = 'ref-test'
        date_released = '2009-07-30'
        date_updated = '1998-12-25'
        update_frequency = 'Annually'
        geographic_granularity = 'Local Authority'
        geographic_coverage = 'England' #TBD
        department = 'Department for Children, Schools and Families'
        temporal_granularity = 'Years'
        categories = 'Health, well-being and Care; '
        national_statistic = 'No'
        precision = 'Nearest 1000'
        taxonomy_url = 'http://some.com/taxonomy'
        agency = 'FOGB'
        current_extras = {
            'external_reference':external_reference,
            'date_released':date_released,
##            'date_updated':date_updated,
##            'update_frequency':update_frequency,
##            'geographic_granularity':geographic_granularity,
##            'geographic_coverage':geographic_coverage,
            'department':department,
##            'temporal_granularity':temporal_granularity,
##            'categories':categories,
##            'national_statistic':national_statistic,
##            'precision':precision,
##            'taxonomy_url':taxonomy_url,
##            'agency':agency,
            }
        for key, value in current_extras.items():
            pkg.extras[unicode(key)] = unicode(value)
        model.repo.commit_and_remove()
        pkg = model.Package.by_name(pkg_name)
        admin = model.User.by_name(u'testadmin')
        model.setup_default_user_roles(pkg, [admin])

        # Edit it
        offset = url_for(controller='package', action='edit', id=pkg.name, package_form=package_form)
        res = self.app.get(offset, status=200, extra_environ={'REMOTE_USER':'testadmin'})
        assert 'Packages - Edit' in res, res
        
        # Check form is correctly filled
        prefix = 'Package-%s-' % pkg.id
        main_res = self.main_div(res)
        assert 'name="%sname" size="40" type="text" value="%s"' % (prefix, pkg.name) in res, res
        assert 'name="%stitle" size="40" type="text" value="%s"' % (prefix, pkg.title) in res, res
#        assert 'name="%sversion" size="40" type="text" value="%s"' % (prefix, pkg.version) in res, res
        assert 'name="%surl" size="40" type="text" value="%s"' % (prefix, pkg.url) in res, res
        res_html = 'id="%sresources-0-url" type="text" value="%s"' % (prefix, pkg.resources[0].url)
        assert res_html in res, self.main_div(res) + res_html
        for res_index, resource in enumerate(pkg.resources):
            for res_field in ('url', 'format', 'description'):
                expected_value = getattr(resource, res_field)
                assert 'id="%sresources-%s-%s" type="text" value="%s"' % (prefix, res_index, res_field, expected_value) in res, res
        assert '<textarea cols="60" id="%snotes" name="%snotes" rows="15">%s</textarea>' % (prefix, prefix, pkg.notes) in res, res
        license_html = '<option value="%s" selected>%s' % (pkg.license_id, pkg.license.name)
        assert license_html in res, str(res) + license_html
        tags_html = 'name="%stags" size="60" type="text" value="%s"' % (prefix, tags_txt)
        assert tags_html in res, str(res) + tags_html
        state_html = '<option value="%s" selected>%s' % (pkg.state.id, pkg.state.name)
        assert state_html in res, str(res) + state_html
        assert prefix + 'external_reference" size="40" type="text" value="%s"' % external_reference in main_res, main_res
        assert prefix + 'date_released" size="40" type="text" value="%s"' % '30/7/2009' in main_res, main_res
##        assert prefix + 'date_updated" size="40" type="text" value="%s"' % '25/12/1998' in main_res, main_res
##        assert prefix + 'update_frequency" size="40" type="text" value="%s"' % update_frequency in main_res, main_res
##        assert prefix + 'geographic_granularity" size="40" type="text" value="%s"' % geographic_granularity in main_res, main_res
##        assert prefix + 'geographic coverage" size="40" type="text" value="%s"' % geographic_coverage in main_res, main_res
        assert 'option value="%s" selected' % department in main_res, main_res
        assert prefix + 'department-other" type="text" value=""' in main_res, main_res
##        assert prefix + 'temporal_granularity" size="40" type="text" value="%s"' % temporal_granularity in main_res, main_res
##        assert prefix + 'categories" size="40" type="text" value="%s"' % categories in main_res, main_res
##        assert prefix + 'national_statistic" size="40" type="text" value="%s"' % national_statistic in main_res, main_res
##        assert prefix + 'precision" size="40" type="text" value="%s"' % precision in main_res, main_res
##        assert prefix + 'taxonomy_url" size="40" type="text" value="%s"' % taxonomy_url in main_res, main_res
##        assert prefix + 'agency" size="40" type="text" value="%s"' % agency in main_res, main_res

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
        state = model.State.query.filter_by(name='active').one()
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
        geographic_coverage = 'Wales' #TBD
        department = 'Crown Estate'
        temporal_granularity = 'Months'
        categories = 'Economy; Government'
        national_statistic = 'Yes'
        precision = 'Nearest 10'
        taxonomy_url = 'http://some.com/taxonomy/CHANGED'
        agency = 'EOGB'
        current_extras = {
            'external_reference':external_reference,
            'date_released':date_released,
##            'date_updated':date_updated,
##            'update_frequency':update_frequency,
##            'geographic_granularity':geographic_granularity,
##            'geographic_coverage':geographic_coverage,
            'department':department,
##            'temporal_granularity':temporal_granularity,
##            'categories':categories,
##            'national_statistic':national_statistic,
##            'precision':precision,
##            'taxonomy_url':taxonomy_url,
##            'agency':agency,
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
##        fv[prefix+'date_updated'] = '26/12/1998'
##        fv[prefix+'update_frequency'] = update_frequency
##        fv[prefix+'geographic_granularity'] = geographic_granularity
##        fv[prefix+'geographic_coverage'] = geographic_coverage
        fv[prefix+'department'] = department
##        fv[prefix+'temporal_granularity'] = temporal_granularity
##        fv[prefix+'categories'] = categories
##        fv[prefix+'national_statistic'] = False
##        fv[prefix+'precision'] = precision
##        fv[prefix+'taxonomy_url'] = taxonomy_url
##        fv[prefix+'agency'] = agency
        fv[prefix+'state_id'] = state.id
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
##        assert 'Date updated: 26/12/1998' in preview, preview
##        assert 'Update freqency: %s' % update_frequency in preview, preview
##        assert 'Geographic granularity: %s' % geographic_granularity in preview, preview
##        assert 'Geographic coverage: %s' % geographic_coverage in preview, preview
        assert 'Department: %s' % department in preview, preview
##        assert 'Temporal granularity: %s' temporal_granularity %  in preview, preview
##        assert 'Categories: %s' % categories in preview, preview
##        assert 'National statistic: %s' % national_statistic in preview, preview
##        assert 'Precision: %s' % precision in preview, preview
##        assert 'Taxonomy URL: %s' % taxonomy_url in preview, preview
##        assert 'Agency: %s' % agency in preview, preview
        tags_html_list = ['<a href="/tag/read/%s">%s</a>' % (str(tag), str(tag)) for tag in tags]
        tags_html_preview = ' '.join(tags_html_list)
        assert 'Tags: %s' % tags_html_preview in preview, preview + tags_html_preview
        groups_html = ''
#        assert 'Groups:\n%s' % groups_html in preview, preview + groups_html
        assert 'State: %s' % str(state.name) in preview, preview
        assert '<li><strong>:</strong> </li>' not in preview, preview

        # Check form is correctly filled
        main_res = self.main_div(res)
        assert 'name="%stitle" size="40" type="text" value="%s"' % (prefix, title) in main_res, main_res
#        assert 'name="%sversion" size="40" type="text" value="%s"' % (prefix, version) in main_res, main_res
        assert 'name="%surl" size="40" type="text" value="%s"' % (prefix, url) in main_res, main_res
        res_html = 'id="%sresources-0-url" type="text" value="%s"' % (prefix, resources[0][0])
        assert res_html in res, self.main_div(res) + res_html
        for res_index, resource in enumerate(resources):
            for field_index, res_field in enumerate(('url', 'format', 'description')):
                expected_value = resource[field_index]
                assert 'id="%sresources-%s-%s" type="text" value="%s"' % (prefix, res_index, res_field, expected_value) in main_res, main_res
        assert '<textarea cols="60" id="%snotes" name="%snotes" rows="15">%s</textarea>' % (prefix, prefix, notes) in main_res, main_res
        license_html = '<option value="%s" selected>%s' % (license_id, license)
        assert license_html in res, str(res) + license_html
        assert 'name="%stags" size="60" type="text" value="%s"' % (prefix, tags_txt) in main_res, main_res
        state_html = '<option value="%s" selected>%s' % (state.id, state.name)
        assert state_html in res, str(res) + state_html
        assert prefix + 'external_reference" size="40" type="text" value="%s"' % external_reference in main_res, main_res
        assert prefix + 'date_released" size="40" type="text" value="%s"' % '31/7/2009' in main_res, main_res
##        assert prefix + 'date_updated" size="40" type="text" value="%s"' % '26/12/1998' in main_res, main_res
##        assert prefix + 'update_frequency" size="40" type="text" value="%s"' % update_frequency in main_res, main_res
##        assert prefix + 'geographic_granularity" size="40" type="text" value="%s"' % geographic_granularity in main_res, main_res
##        assert prefix + 'geographic coverage" size="40" type="text" value="%s"' % geographic_coverage in main_res, main_res
        assert 'option value="%s" selected' % department in main_res, main_res
        assert prefix + 'department-other" type="text" value=""' in main_res, main_res
##        assert prefix + 'temporal_granularity" size="40" type="text" value="%s"' % temporal_granularity in main_res, main_res
##        assert prefix + 'categories" size="40" type="text" value="%s"' % categories in main_res, main_res
##        assert prefix + 'national_statistic" size="40" type="text" value="%s"' % national_statistic in main_res, main_res
##        assert prefix + 'precision" size="40" type="text" value="%s"' % precision in main_res, main_res
##        assert prefix + 'taxonomy_url" size="40" type="text" value="%s"' % taxonomy_url in main_res, main_res
##        assert prefix + 'agency" size="40" type="text" value="%s"' % agency in main_res, main_res
        assert log_message in res

        # Submit
        res = fv.submit('commit', extra_environ={'REMOTE_USER':'testadmin'})

        # Check package page
        assert not 'Error' in res, res
        res = res.follow(extra_environ={'REMOTE_USER':'testadmin'})
        res1 = self.main_div(res).replace('</strong>', '')
        assert 'Packages - %s' % str(name) in res, res
        assert 'Package: %s' % str(name) in res1, res1
        assert 'Title: %s' % str(title) in res1, res1
#        assert 'Version: %s' % str(version) in res1, res1
        assert 'url: <a href="%s">' % str(url).lower() in res1.lower(), res1
        for res_index, resource in enumerate(resources):
            res_html = '<tr> <td><a href="%s">%s</a></td><td>%s</td><td>%s</td>' % (resource[0], resource[0], resource[1], resource[2]) 
            assert res_html in preview, preview + res_html
        assert '<p>%s' % str(notes) in res1, res1
        assert 'License: %s' % str(license) in res1, res1
        assert 'Tags:' in res1, res1
        for tag_html in tags_html_list:
            assert tag_html in res1, tag_html + res1
        assert 'Groups:\n%s' % groups_html in res1, res1 + groups_html
        assert 'State: %s' % str(state.name) in res1, res1
        for key, value in current_extras.items():
            extras_html = '%(key)s: %(value)s' % {'key':key.capitalize(), 'value':value}
            assert extras_html in res1, str(res) + extras_html

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
        assert pkg.state_id == state.id
        assert len(pkg.extras) == len(current_extras)
        for key, value in current_extras.items():
            assert pkg.extras[key] == value

        # for some reason environ['REMOTE_ADDR'] is undefined
        rev = model.Revision.youngest()
        assert rev.author == 'testadmin', rev.author
        assert rev.message == log_message
        # TODO: reinstate once fixed in code
        exp_log_message = u'Creating package %s' % name
        #assert rev.message == exp_log_message


class TestNew(TestController):
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

    def test_new_all_fields(self):
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
        update_frequency = 'Annually'
        geographic_granularity = 'Local Authority'
        geographic_coverage = 'England' #TBD
        department = 'Department for Children, Schools and Families'
        temporal_granularity = 'Years'
        categories = 'Health, well-being and Care; '
        national_statistic = 'No'
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
        fv[prefix+'geographic_coverage'] = geographic_coverage
        fv[prefix+'department'] = department
        fv[prefix+'temporal_granularity'] = temporal_granularity
        fv[prefix+'categories'] = categories
        fv[prefix+'national_statistic'] = True
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
        assert 'Update freqency: %s' % update_frequency in preview, preview
        assert 'Geographic granularity: %s' % geographic_granularity in preview, preview
        assert 'Geographic coverage: %s' % geographic_coverage in preview, preview
        assert 'Department: %s' % department in preview, preview
        assert 'Temporal granularity: %s' % temporal_granularity in preview, preview
        assert 'Categories: %s' % categories in preview, preview
        assert 'National statistic: %s' % national_statistic in preview, preview
        assert 'Precision: %s' % precision in preview, preview
        assert 'Taxonomy URL: %s' % taxonomy_url in preview, preview
        assert 'Agency: %s' % agency in preview, preview
        for tag in tags:
            assert '%s</a>' % tag.lower() in preview

        assert '<li><strong>:</strong> </li>' not in preview, preview

        # Check form is correctly filled
        main_res = self.main_div(res)
        prefix = 'Package--'
        assert prefix + 'title" size="40" type="text" value="%s"' % title in main_res, main_res
#        assert prefix + 'version" size="40" type="text" value="%s"' % version in main_res, main_res
        assert prefix + 'url" size="40" type="text" value="%s"' % url in main_res, main_res
        assert prefix + 'resources-0-url" type="text" value="%s"' % download_url in main_res, main_res
        assert prefix + 'resources-0-format" type="text" value="%s"' % download_format in main_res, main_res
        assert '<textarea cols="60" id="Package--notes" name="Package--notes" rows="15">%s</textarea>' % notes in main_res, main_res
        license_html = '<option value="%s" selected>%s' % (license_id, license)
        assert license_html in main_res, str(main_res) + license_html
        assert prefix + 'tags" size="60" type="text" value="%s"' % tags_txt.lower() in main_res, main_res
        assert prefix + 'external_reference" size="40" type="text" value="%s"' % external_reference in main_res, main_res
        assert prefix + 'date_released" size="40" type="text" value="%s"' % '30/7/2009' in main_res, main_res
        assert prefix + 'date_updated" size="40" type="text" value="%s"' % '25/12/1998' in main_res, main_res
        assert prefix + 'update_frequency" size="40" type="text" value="%s"' % update_frequency in main_res, main_res
        assert prefix + 'geographic_granularity" size="40" type="text" value="%s"' % geographic_granularity in main_res, main_res
        assert prefix + 'geographic coverage" size="40" type="text" value="%s"' % geographic_coverage in main_res, main_res
        assert 'option value="%s" selected' % department in main_res, main_res
        assert prefix + 'department-other" type="text" value=""' in main_res, main_res
        assert prefix + 'temporal_granularity" size="40" type="text" value="%s"' % temporal_granularity in main_res, main_res
        assert prefix + 'categories" size="40" type="text" value="%s"' % categories in main_res, main_res
        assert prefix + 'national_statistic" size="40" type="text" value="%s"' % national_statistic in main_res, main_res
        assert prefix + 'precision" size="40" type="text" value="%s"' % precision in main_res, main_res
        assert prefix + 'taxonomy_url" size="40" type="text" value="%s"' % taxonomy_url in main_res, main_res
        assert prefix + 'agency" size="40" type="text" value="%s"' % agency in main_res, main_res

        assert log_message in main_res

        # Submit
        res = fv.submit('commit')

        # Check package page
        assert not 'Error' in res, res
        res = res.follow()
        res1 = self.main_div(res).replace('</strong>', '')
        assert 'Packages - %s' % str(name) in res, res
        assert 'Package: %s' % str(name) in res1, res1
        assert 'Title: %s' % str(title) in res1, res1
#        assert 'Version: %s' % str(version) in res1, res1
        assert 'url: <a href="%s">' % str(url).lower() in res1.lower(), res1
        assert '<td><a href="%s">' % str(download_url) in res1, res1
        assert '<td>%s</td>' % str(download_format) in res1, res1
        assert '<p>%s' % str(notes) in res1, res1
        assert 'License: %s' % str(license) in res1, res1
        assert 'Tags:' in res1, res1
        for tag in tags:
            assert '%s</a>' % tag.lower() in res
        assert 'Groups:' in res1, res1
        current_extras = {
            'external_reference':external_reference,
            'date_released':date_released,
            'date_updated':date_updated,
            'update_frequency':update_frequency,
            'geographic_granularity':geographic_granularity,
            'geographic_coverage':geographic_coverage,
            'department':department,
            'temporal_granularity':temporal_granularity,
            'categories':categories,
            'national_statistic':national_statistic,
            'precision':precision,
            'taxonomy_url':taxonomy_url,
            'agency':agency,
            }
        for key, value in current_extras.items():
            extras_html = '%(key)s: %(value)s' % {'key':key.capitalize(), 'value':value}
            assert extras_html in res1, str(res) + extras_html

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
        fv = res.forms[0]
        res = fv.submit('commit')
        assert 'Error' in res, res
        assert 'Package name already exists in database' in res, res
        # Ensure there is an error at the top of the form and by the field
        assert 'class="form-errors"' in res, res
        assert 'class="field_error"' in res, res
        
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
        # Ensure there is an error at the top of the form and by the field
        assert 'class="form-errors"' in res, res
        assert 'class="field_error"' in res, res
        # Ensure fields are prefilled
        assert 'value="A Test Package"' in res, res
        assert 'value="test tags"' in res, res
#        assert 'value="test groups"' in res, res
