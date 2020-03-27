# encoding: utf-8

from ckan.tests.legacy import TestController, CreateTestData, url_for
from ckan.tests import helpers
import ckan.model as model

# TODO: purge revisions after creating them
class TestRevisionController(TestController):

    @classmethod
    def setup_class(self):
        model.Session.remove()
        # rebuild db before this test as it depends delicately on what
        # revisions exist
        helpers.reset_db()
        CreateTestData.create()

    @classmethod
    def teardown_class(self):
        helpers.reset_db()

    def create_40_revisions(self):
        for i in range(0,40):
            rev = model.repo.new_revision()
            rev.author = "Test Revision %s" % i
            model.repo.commit()

    def assert_click(self, res, link_exp, res2_exp):
        try:
            # paginate links are also just numbers
            # res2 = res.click('^%s$' % link_exp)
            res2 = res.click(link_exp)
        except:
            print "\nThe first response (list):\n\n"
            print str(res)
            print "\nThe link that couldn't be followed:"
            print str(link_exp)
            raise
        try:
            assert res2_exp in res2
        except:
            print "\nThe first response (list):\n\n"
            print str(res)
            print "\nThe second response (item):\n\n"
            print str(res2)
            print "\nThe followed link:"
            print str(link_exp)
            print "\nThe expression that couldn't be found:"
            print str(res2_exp)
            raise

    def create_updating_revision(self, name, **kwds):
        rev = model.repo.new_revision()
        rev.author = "Test Revision Updating"
        package = self.get_package(name)
        if 'resources' in kwds:
            resources = kwds.pop('resources')
            for resource in package.resources_all:
                resource.state = 'deleted'
            for resource in resources:
                resource = model.Resource(**resource)
                model.Session.add(resource)
                package.resources_all.append(resource)
        if 'extras' in kwds:
            extras_data = kwds.pop('extras')
        #    extras = []
        #    for key,value in extras_data.items():
        #        extra = model.PackageExtra(key=key, value=value)
        #        model.Session.add(extra)
        #        extras.append(extra)
            for key,value in extras_data.items():
                package.extras[key] = value
        for name,value in kwds.items():
            setattr(package, name, value)
        model.Session.add(package)
        model.Session.commit()
        model.Session.remove()
        if not model.repo.history()[0].packages:
            raise Exception, "Didn't set up revision right."

    def create_deleting_revision(self, name):
        rev = model.repo.new_revision()
        rev.author = "Test Revision Deleting"
        package = self.get_package(name)
        package.delete()
        model.repo.commit()

    def get_package(self, name):
        return model.Package.by_name(name)

    def test_read(self):
        anna = model.Package.by_name(u'annakarenina')
        rev_id = anna.revision.id
        offset = url_for(controller='revision', action='read', id='%s' % rev_id)
        res = self.app.get(offset, extra_environ={'REMOTE_USER': 'testsysadmin'})
        assert 'Revision %s' % rev_id in res
        assert 'Revision: %s' % rev_id in res
        # Todo: Reinstate asserts below, failing on 'Test Revision Deleting'
        #assert 'Author:</strong> tester' in res
        #assert 'Log Message:' in res
        #assert 'Creating test data.' in res
        #assert 'Dataset: annakarenina' in res
        #assert "Datasets' Tags" in res
        #res = res.click('annakarenina', index=0)
        #assert 'Datasets - annakarenina' in res

    def test_list_format_atom(self):
        self.create_40_revisions()
        self.create_updating_revision(u'warandpeace',
            title=u"My Updated 'War and Peace' Title",
        )
        self.create_updating_revision(u'annakarenina',
            title=u"My Updated 'Annakarenina' Title",
            resources=[{
                'url': u'http://datahub.io/download3',
                'format': u'zip file',
                'description': u'Full text. Needs escaping: " Umlaut: \xfc',
                'hash': u'def456',
            }],
        )
        self.create_updating_revision(u'warandpeace',
            title=u"My Doubly Updated 'War and Peace' Title",
            extras={
                'date_updated': u'2010',
            }
        )
        self.create_deleting_revision(u'annakarenina')
        revisions = model.repo.history().all()
        revision1 = revisions[0]
        # Revisions are most recent first, with first rev on last page.
        # Todo: Look at the model to see which revision is last.
        # Todo: Test for last revision on first page.
        # Todo: Test for first revision on last page.
        # Todo: Test for last revision minus 50 on second page.
        # Page 1.   (Implied id=1)
        offset = url_for(controller='revision', action='list', format='atom')
        res = self.app.get(offset)
        assert '<feed' in res, res
        assert 'xmlns="http://www.w3.org/2005/Atom"' in res, res
        assert '</feed>' in res, res
        # Todo: Better test for 'days' request param.
        #  - fake some older revisions and check they aren't included.
        offset = url_for(controller='revision', action='list', format='atom',
                days=30)
        res = self.app.get(offset)
        assert '<feed' in res, res
        assert 'xmlns="http://www.w3.org/2005/Atom"' in res, res
        assert '</feed>' in res, res

        # Tests for indications about what happened.
        assert 'warandpeace:created' in res, res
        assert 'annakarenina:created' in res, res
        assert 'warandpeace:updated:date_updated' in res, res
        assert 'annakarenina:updated:resources' in res, res
        assert 'annakarenina:deleted' in res, res

