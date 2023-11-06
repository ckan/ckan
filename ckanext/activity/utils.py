from ckan import model
from ckan.types import DataDict, Query
from ckanext.activity.model import Activity


def _parse_data_dict_to_query(data_dict: DataDict) -> Query:
    q = model.Session.query(Activity.id)

    if data_dict.get('before'):
        q = q.filter(Activity.timestamp < data_dict.get('before'))

    if data_dict.get('after'):
        q = q.filter(Activity.timestamp > data_dict.get('after'))

    if data_dict.get('activity_types'):
        q = q.filter(Activity.activity_type.in_(data_dict.get('activity_types')))

    if data_dict.get('exclude_activity_types'):
        q = q.filter(Activity.activity_type
                     .notin_(data_dict.get('exclude_activity_types'))) \

    if data_dict.get('offset'):
        q = q.offset(data_dict.get('offset'))

    if data_dict.get('limit'):
        q = q.limit(data_dict.get('limit'))

    return q


def get_activity_count(data_dict: DataDict) -> int:
    return _parse_data_dict_to_query(data_dict).count()


def delete_activities(data_dict: DataDict):
    # query.delete() cannot be used with offset and limit.
    # need to do another query with IN ids to delete them.
    ids = set(id[0] for id in _parse_data_dict_to_query(data_dict).all())
    model.Session.query(Activity).filter(Activity.id.in_(ids)).delete()
    model.Session.commit()
