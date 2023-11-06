from ckan import model
from ckan.types import DataDict
from ckanext.activity.model.activity import Activity, QActivity


def _parse_data_dict_to_query(data_dict: DataDict) -> QActivity:
    q = model.Session.query(Activity.id)

    if data_dict.get('before'):
        # type_ignore_reason: incomplete SQLAlchemy types
        q = q.filter(Activity.timestamp <
                     data_dict.get('before'))  # type: ignore

    if data_dict.get('after'):
        # type_ignore_reason: incomplete SQLAlchemy types
        q = q.filter(Activity.timestamp >
                     data_dict.get('after'))  # type: ignore

    if data_dict.get('activity_types'):
        q = q.filter(
                Activity.activity_type
                # type_ignore_reason: incomplete SQLAlchemy types
                .in_(data_dict.get('activity_types')  # type: ignore
            ))

    if data_dict.get('exclude_activity_types'):
        q = q.filter(
                Activity.activity_type
                # type_ignore_reason: incomplete SQLAlchemy types
                .notin_(data_dict.get('exclude_activity_types')  # type: ignore
            ))

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
    model.Session.query(Activity).filter(
        # type_ignore_reason: incomplete SQLAlchemy types
        Activity.id.in_(ids)).delete()  # type: ignore
    model.Session.commit()
