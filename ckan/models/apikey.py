import sqlobject 

class ApiKey(sqlobject.SQLObject):

    name = sqlobject.UnicodeCol(alternateID=True)
    key = sqlobject.UnicodeCol()

