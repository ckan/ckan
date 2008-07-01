import sqlobject 
import uuid

def make_uuid():
    return str(uuid.uuid4())

class ApiKey(sqlobject.SQLObject):

    name = sqlobject.UnicodeCol(alternateID=True)
    key = sqlobject.UnicodeCol(default=make_uuid)

