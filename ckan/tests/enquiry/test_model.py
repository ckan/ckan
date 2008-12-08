import ckan.model as model

class TestModel(object):
    @classmethod
    def setup_class(self):
        for enq in model.Enquiry.query.all():
            model.Session.delete(enq)
        model.Session.commit()
        model.Session.remove()

    def test_1(self):
        subj = u'testing email'
        enq = model.Enquiry(subject=subj)
        model.Session.commit()
        id = enq.id
        model.Session.clear()
        out = model.Enquiry.query.get(id)
        assert out.subject == subj

