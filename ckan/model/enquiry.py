from meta import *

import uuid
def make_uuid():
    return str(uuid.uuid4())

enquiry_table = Table('enquiry', metadata,
        Column('id', types.String(36), default=make_uuid, primary_key=True),
        Column('to', types.UnicodeText),
        Column('subject', types.UnicodeText),
        Column('body', types.UnicodeText),
        )

class Enquiry(object):
    pass

mapper(Enquiry, enquiry_table,
    order_by=enquiry_table.c.id)


