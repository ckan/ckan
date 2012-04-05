import json

from ckan.tests import *
import ckan.model as model
import ckan.logic as logic

class TestRelated:

    @classmethod
    def setup_class(self):
        model.Session.remove()
        CreateTestData.create()

    @classmethod
    def teardown_class(self):
        model.repo.rebuild_db()

    def test_create(self):
        p = model.Package.get('warandpeace')
        r = model.Related()
        p.related.append(r)

        assert len(p.related) == 1, p.related
        assert len(r.datasets) == 1, r.datasets

        model.Session.add(p)
        model.Session.add(r)
        model.Session.commit()

        # To get the RelatedDataset objects (for state change)
        assert len(model.Related.get_for_dataset(p)) == 1
        assert len(model.Related.get_for_dataset(p,status='inactive')) == 0
        p.related.remove(r)
        model.Session.delete(r)

        assert len(p.related) == 0


    def test_inactive_related(self):
        p = model.Package.get('warandpeace')
        r = model.Related()
        p.related.append(r)
        assert len(p.related) == 1, p.related
        model.Session.add(r)
        model.Session.commit()

        # To get the RelatedDataset objects (for state change)
        assert len(model.Related.get_for_dataset(p,status='active')) == 1
        assert len(model.Related.get_for_dataset(p,status='inactive')) == 0
        r.deactivate( p )
        r.deactivate( p ) # Does nothing.
        model.Session.refresh(p)
        assert len(model.Related.get_for_dataset(p,status='active')) == 0
        assert len(model.Related.get_for_dataset(p,status='inactive')) == 1

        model.Session.refresh(p) # Would like to get rid of the need for this
        assert len(p.related) == 0, p.related # not sure inactive item ...
        model.Session.delete(r)


    def _related_create(self, title, description, type, url, image_url):
        usr = logic.get_action('get_site_user')({'model':model,'ignore_auth': True},{})

        context = dict(model=model, user=usr['name'], session=model.Session)
        data_dict = dict(title=title,description=description,
                         url=url,image_url=image_url,type=type)
        return logic.get_action("related_create")( context, data_dict )

    def test_related_create(self):
        rel = self._related_create("Title", "Description",
                        "visualization",
                        "http://ckan.org",
                        "http://ckan.org/files/2012/03/ckanlogored.png")
        assert rel['title'] == "Title", rel
        assert rel['description'] == "Description", rel
        assert rel['type'] == "visualization", rel
        assert rel['url'] == "http://ckan.org", rel
        assert rel['image_url'] == "http://ckan.org/files/2012/03/ckanlogored.png", rel

    def test_related_create_fail(self):
        try:
            rel = self._related_create("Title", "Description",
                        None,
                        "http://ckan.org",
                        "http://ckan.org/files/2012/03/ckanlogored.png")
            assert False, "Create succeeded with missing field"
        except logic.ValidationError, e:
            assert 'type' in e.error_dict and e.error_dict['type'] == [u'Missing value']

    def test_related_delete(self):
        rel = self._related_create("Title", "Description",
                        "visualization",
                        "http://ckan.org",
                        "http://ckan.org/files/2012/03/ckanlogored.png")
        usr = logic.get_action('get_site_user')({'model':model,'ignore_auth': True},{})
        context = dict(model=model, user=usr['name'], session=model.Session)
        data_dict = dict(id=rel['id'])
        logic.get_action('related_delete')(context, data_dict)

        # Check it doesn't exist
        r = model.Related.get(rel['id'])
        assert r is None, r

    def test_related_update(self):
        rel = self._related_create("Title", "Description",
                        "visualization",
                        "http://ckan.org",
                        "http://ckan.org/files/2012/03/ckanlogored.png")

        usr = logic.get_action('get_site_user')({'model':model,'ignore_auth': True},{})
        context = dict(model=model, user=usr['name'], session=model.Session)
        data_dict = rel
        data_dict['title'] = "New Title"
        result = logic.get_action('related_update')(context,data_dict)
        assert result['title'] == 'New Title'

