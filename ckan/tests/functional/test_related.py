import json

from ckan.tests import *
import ckan.model as model

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
        model.Session.add(r)
