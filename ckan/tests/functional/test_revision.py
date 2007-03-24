from ckan.tests import *

class TestHomeController(TestControllerTwill):

    def test_history(self):
        # order of running is not guaranteed so we only know that there are at
        # least 2 revisions in the system
        offset = url_for(controller='revision')
        url = self.siteurl + offset
        web.go(url)
        web.code(200)
        print web.show()
        web.title('Repository History')
        web.find('1')
        web.find('Author')
        web.find('tolstoy')
        

