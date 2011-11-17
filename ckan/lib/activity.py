from sqlalchemy.orm.session import SessionExtension
import logging
logger = logging.getLogger(__name__)

def activity_stream_item(obj, activity_type, revision_id):
    try:
        return obj.activity_stream_item(activity_type, revision_id)
    except (AttributeError, TypeError):
        logger.debug("Object did not have a suitable "
            "activity_stream_item() method, it must not be a package.")
        return None

def activity_stream_detail(obj, activity_id, activity_type):
    try:
        return obj.activity_stream_detail(activity_id, activity_type)
    except (AttributeError, TypeError):
        logger.debug("Object did not have a suitable  "
            "activity_stream_detail() method.")
        return None

class DatasetActivitySessionExtension(SessionExtension):

    def before_commit(self, session):

        session.flush()

        try:
            obj_cache = session._object_cache
            revision = session.revision
        except AttributeError:
            return

        # The top-level objects that we will append to the activity table. The
        # keys hare are package IDs, and the values are model.activity:Activity
        # objects.
        activities = {}

        # The second-level objects that we will append to the activity_detail
        # table. Each row in the activity table has zero or more related rows
        # in the activity_detail table. The keys here are activity IDs, and the
        # values are lists of model.activity:ActivityDetail objects.
        activity_details = {}

        for activity_type in ('new', 'changed', 'deleted'):
            objects = obj_cache[activity_type]
            for obj in objects:
                logger.debug("Processing %s object %s" % (activity_type, obj))
                
                # Try to get an activity stream item from the object, this will
                # work if the object is a Package.
                activity = None
                if obj.id in activities:
                    activity = activities[obj.id]
                else:
                    activity = activity_stream_item(obj, activity_type, 
                        revision.id)
                    if activity is not None:
                        activities[obj.id] = activity
                
                if activity is not None:
                    logger.debug("Looks like this object is a package")
                    logger.debug("activity: %s" % activity)
                    activity_detail = activity_stream_detail(obj,
                        activity.id, activity_type)
                    if activity_detail is not None:
                        logger.debug("activity_detail: %s" % activity_detail)
                        if activity_details.has_key(activity.id):
                            activity_details[activity.id].append(
                                activity_detail)
                        else:
                            activity_details[activity.id] = [activity_detail]
                
                else:
                    logger.debug("Looks like this object is not a Package")
                    try:
                        related_packages = obj.related_packages()
                        logger.debug("related_packages: %s" % related_packages)
                    except (AttributeError, TypeError):
                        logger.debug("Object did not have a suitable "
                                "related_packages() method, skipping it.")
                        continue

                    for package in related_packages:
                        if package is None: continue
                        activity = activity_stream_item(package, 
                            "changed", revision.id)
                        assert activity is not None
                        logger.debug("activity: %s" % activity)
                        activities[package.id] = activity
                        activity_detail = activity_stream_detail(obj, 
                            activity.id, activity_type)
                        if activity_detail is not None:
                            if activity_details.has_key(activity.id):
                                activity_details[activity.id].append(
                                    activity_detail)
                            else:
                                activity_details[activity.id] = \
                                    [activity_detail]
                        
        for key, activity in activities.items():
            session.add(activity)

        session.flush()

        for key, activity_detail_list in activity_details.items():
            for activity_detail_obj in activity_detail_list:
                session.add(activity_detail_obj)

        session.flush()
