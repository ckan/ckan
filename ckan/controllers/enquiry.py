from ckan.lib.base import *
from ckan.controllers.base import CkanBaseController

class EnquiryController(CkanBaseController):

    def index(self):
        c.package_count = model.Package.query.count()
        return render('enquiry/index')
    
    def choose(self):
        return render('enquiry/choose')

    def create(self, template=''):
        c.email_template = template_2
        if not ('preview' in request.params or 'commit' in request.params):
            return render('enquiry/create')

        c.to = request.params['subject']
        c.subject = request.params['subject']
        c.body = request.params['body']
        if 'preview' in request.params:
            return render('enquiry/preview')
        if 'commit' in request.params:
            enq = model.Enquiry(
                    to=c.to,
                    subject=c.subject,
                    body=c.body
                    )
            model.Session.commit()
            c.enquiry = enq
            return render('enquiry/sent')

    def view(self, id=''):
        enq = model.Enquiry.query.get(id)
        if enq is None:
            abort(404)
        c.enquiry = enq
        return render('enquiry/view')

follow_up_email = '''It might also be good to apply a specific 'open data' licence --
you can find examples of such licenses at: ...
'''

template_2 = \
'''Dear Editor,

I am a [[INSERT INFORMATION INCLUDING DISCIPLINE]].

I am writing on behalf of the Open Scientific Data Working Group of the Open Knowledge Foundation. We are seeking clarification of the 'openness' of the scientific data associated with your publications.

We weren't able to find an explicit statement of this fact such as a reference to an open knowledge license[3] so we're writing to find out what the exact situation is, specifically to ask you whether the material can be made available under an open license of some kind[3].

Regards,

[[INSERT NAME HERE]]

[1]: [[INSERT LINK HERE]]
[2]: http://www.opendefinition.org/1.0/
[3]: http://www.opendefinition.org/licenses/
'''

