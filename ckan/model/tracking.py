from meta import *
from domain_object import DomainObject

tracking_summary_table = Table('tracking_summary', metadata,
        Column('url', UnicodeText, primary_key=True, nullable=False),
        Column('package_id', UnicodeText),
        Column('tracking_type', Unicode(10), nullable=False),
        Column('count', Integer, nullable=False),
        Column('running_total', Integer, nullable=False),
        Column('recent_views', Integer, nullable=False),
        Column('tracking_date', DateTime),
    )

class TrackingSummary(DomainObject):

    @classmethod
    def get_for_package(cls, package_id):
        obj = Session.query(cls).autoflush(False)
        obj = obj.filter_by(package_id=package_id)
        data = obj.order_by('tracking_date desc').first()
        if data:
            return {'total' : data.running_total,
                    'recent': data.recent_views}

        return {'total' : 0, 'recent' : 0}


    @classmethod
    def get_for_resource(cls, url):
        obj = Session.query(cls).autoflush(False)
        data = obj.filter_by(url=url).order_by('tracking_date desc').first()
        if data:
            return {'total' : data.running_total,
                    'recent': data.recent_views}

        return {'total' : 0, 'recent' : 0}

mapper(TrackingSummary, tracking_summary_table)
