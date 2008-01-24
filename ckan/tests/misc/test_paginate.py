from ckan.tests import *
from ckan.misc import Paginate

class TestPaginate(TestController2):

    def test_page(self):
        listRegister = self.get_model().packages
        paginate = Paginate(listRegister=listRegister, pageLength=50)
        assert paginate.pageLength == 50
        assert paginate.getListLength() == 2
        assert paginate.isSinglePage()
        assert paginate.listIndex == 0
        assert not paginate.hasPrevious()
        assert not paginate.hasNext()
        assert paginate.getPrevious() == None
        assert paginate.getNext() == None
        paginate.setListIndex(50)
        assert paginate.listIndex == 0
        pageList = paginate.getPageList()
        assert len(pageList) == 2
        assert pageList[1] == listRegister.list()[1]
 
    def setup_method(self, method):
        if method.__name__ == 'test_page_multi':
            self.create_100_packages()

    def teardown_method(self, method):
        if method.__name__ == 'test_page_multi':
            self.purge_100_packages()

    def test_page_multi(self):
        listRegister = self.get_model().packages
        paginate = Paginate(listRegister=listRegister, pageLength=50)
        assert paginate.pageLength == 50
        assert paginate.getListLength() == 102
        assert not paginate.isSinglePage()
        assert paginate.listIndex == 0
        assert not paginate.hasPrevious()
        assert paginate.hasNext()
        assert paginate.getPrevious() == None
        assert paginate.getNext() == 50
        pageList = paginate.getPageList()
        assert len(pageList) == 50
        assert pageList[0] == listRegister.list()[0]
        assert pageList[1] == listRegister.list()[1]
        assert pageList[49] == listRegister.list()[49]
        paginate.setListIndex(50)
        assert paginate.listIndex == 50
        assert paginate.hasPrevious()
        assert paginate.hasNext()
        assert paginate.getPrevious() == 0
        assert paginate.getNext() == 100
        pageList = paginate.getPageList()
        assert len(pageList) == 50
        assert pageList[0] == listRegister.list()[50]
        assert pageList[1] == listRegister.list()[51]
        assert pageList[49] == listRegister.list()[99]
        paginate.setListIndex(100)
        assert paginate.listIndex == 100
        assert paginate.hasPrevious()
        assert not paginate.hasNext()
        assert paginate.getPrevious() == 50
        assert paginate.getNext() == None
        pageList = paginate.getPageList()
        assert len(pageList) == 2
        assert pageList[0] == listRegister.list()[100]
        assert pageList[1] == listRegister.list()[101]
        paginate.setListIndex(150)
        assert paginate.listIndex == 0

 
