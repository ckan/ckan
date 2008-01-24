class TextFormat(object):

    def to_html(self, instr):
        raise NotImplementedError()


class MarkdownFormat(TextFormat):

    def to_html(self, instr):
        if instr is None:
            return ''
        import markdown
        return markdown.markdown(instr)


# Todo: Change this class to use underscore-separated names, ahem.

class Paginate(object):

    def __init__(self, listRegister, pageLength=50):
        self.listRegister = listRegister
        self.pageLength = pageLength
        self.listIndex = 0
        self.list = None
        self.listLength = None

    def getList(self):
        if self.list == None:
            self.list = self.listRegister.list()
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

    def getPageList(self):
        fullList = self.getList()
        start = self.listIndex
        end = start + self.pageLength
        pageList = fullList[start:end]
        return pageList

