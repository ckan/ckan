import paginate

class TextFormat(object):

    def to_html(self, instr):
        raise NotImplementedError()


class MarkdownFormat(TextFormat):

    def to_html(self, instr):
        if instr is None:
            return ''
        # import markdown
        import webhelpers.markdown
        return webhelpers.markdown.markdown(instr)


# Todo: Substitute the Pylons webhelper Pagination classes for this class.
# Todo: Change this class to use underscore-separated names, ahem.

# TODO: (?) remove as we do not use our own paginate system but 3rd party one
# Disable for time being
class Paginate(object):

    def __init__(self, listRegister, pageLength=50):
        self.listRegister = listRegister
        self.pageLength = pageLength
        self.listIndex = 0
        self.list = None
        self.listLength = None
        self.pageList = None

    def getList(self):
        if self.list == None:
            self.list = self.listRegister.query.all()
        return self.list

    def getListLength(self):
        if self.listLength == None:
            self.listLength = len(self.getList())
        return self.listLength

    def hasPrevious(self):
        return self.listIndex != 0

    def hasNext(self):
        remainingLength = self.getListLength() - self.listIndex
        return remainingLength > self.pageLength

    def getPrevious(self):
        if not self.hasPrevious():
            return None
        else:
            return self.listIndex - self.pageLength

    def getNext(self):
        if not self.hasNext():
            return None
        else:
            return self.listIndex + self.pageLength

    def isSinglePage(self):
        return self.getListLength() <= self.pageLength

    def setListIndex(self, listIndex):
        listLength = self.getListLength()
        if listIndex >= listLength:
            self.listIndex = 0
        else:
            adjustment = listIndex % self.pageLength
            self.listIndex = listIndex - adjustment
        self.pageList = None

    def getPageList(self):
        fullList = self.getList()
        (start, stop) = self.getPageListIndexRange()
        pageList = fullList[start:stop]
        return pageList

    def getPageCount(self):
        return self.getListLength() / self.pageLength + 1

    def getPagesList(self):
        pages = []
        currentPageIndex = self.listIndex / self.pageLength + 1
        for i in range(0,self.getPageCount()):
            pageIndex = i+1
            listIndex = i * self.pageLength
            isCurrentPage = pageIndex == currentPageIndex
            pages.append((pageIndex,listIndex,isCurrentPage))
        return pages

    def getPageListIndexRange(self):
        start = self.listIndex
        stop = self.listIndex + self.pageLength
        listLength = self.getListLength()
        if stop > listLength:
            stop = listLength
        return (start, stop)

