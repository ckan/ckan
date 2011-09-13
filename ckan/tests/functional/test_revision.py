from ckan.tests import search_related, TestController, CreateTestData, url_for
import ckan.model as model

# TODO: purge revisions after creating them
class TestRevisionController(TestController):

    @classmethod
    def setup_class(self):
        model.Session.remove()
        # rebuild db before this test as it depends delicately on what
        # revisions exist
        model.repo.init_db()
        CreateTestData.create()

    @classmethod
    def teardown_class(self):
        model.repo.rebuild_db()

    def create_40_revisions(self):
        for i in range(0,40):
            rev = model.repo.new_revision()
            rev.author = "Test Revision %s" % i
            model.repo.commit()

    def test_paginated_list(self):
        # Ugh. Why is the number of items per page hard-coded? A designer might
        # decide that 20 is the right number of revisions to display per page,
        # (in fact I did) but would be forced to stick to 50 because changing
        # this test is so laborious.
        #
        # TODO: do we even need to test pagination in such excruciating detail
        # every time we use it? It's the same (hard-coded) test code N times over.
        #
        # </rant> -- NS 2009-12-17

        self.create_40_revisions()
        revisions = model.repo.history().all()
        revision1 = revisions[0]
        revision2 = revisions[20]
        revision3 = revisions[40]
        revision4 = revisions[-1]
        # Revisions are most recent first, with first rev on last page.
        # Todo: Look at the model to see which revision is last.
        # Todo: Test for last revision on first page.
        # Todo: Test for first revision on last page.
        # Todo: Test for last revision minus 50 on second page.
        # Page 1.   (Implied id=1)
        offset = url_for(controller='revision', action='list')
        res = self.app.get(offset)
        self.assert_click(res, revision1.id, 'Revision: %s' % revision1.id)

        # Page 1.
        res = self.app.get(offset, params={'page':1})
        self.assert_click(res, revision1.id, 'Revision: %s' % revision1.id)

        # Page 2.
        res = self.app.get(offset, params={'page':2})
        self.assert_click(res, revision2.id, 'Revision: %s' % revision2.id)

        # Page 3.
        res = self.app.get(offset, params={'page':3})
        self.assert_click(res, revision3.id, 'Revision: %s' % revision3.id)

        # Last page.
        last_id = 1 + len(revisions) / 20
        res = self.app.get(offset, params={'page':last_id})

        assert 'Revision History' in res
        assert '1' in res
        assert 'Author' in res
        assert 'tester' in res
        assert 'Log Message' in res
        assert 'Creating test data.' in res


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
            package.resource_groups[0].resources = []
            for resource in resources:
                resource = model.Resource(**resource)
                model.Session.add(resource)
                package.resources.append(resource)
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
        res = self.app.get(offset)
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
                'url': u'http://www.annakarenina.com/download3',
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

