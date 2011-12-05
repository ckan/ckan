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
        # keys here are package IDs, and the values are model.activity:Activity
        # objects.
        activities = {}

        # The second-level objects that we will append to the activity_detail
        # table. Each row in the activity table has zero or more related rows
        # in the activity_detail table. The keys here are activity IDs, and the
        # values are lists of model.activity:ActivityDetail objects.
        activity_details = {}

        # Log new packages first to prevent them from getting incorrectly
        # logged as changed packages.
        logger.debug("Looking for new packages...")
        for obj in obj_cache['new']:
            logger.debug("Looking at object %s" % obj)
            activity = activity_stream_item(obj, 'new', revision.id)
            if activity is None:
                continue
            # If the object returns an activity stream item we know that the
            # object is a package.
            logger.debug("Looks like this object is a package")
            logger.debug("activity: %s" % activity)
            activities[obj.id] = activity

            activity_detail = activity_stream_detail(obj, activity.id, "new")
            if activity_detail is not None:
                logger.debug("activity_detail: %s" % activity_detail)
                activity_details[activity.id] = [activity_detail]

        # Now process other objects.
        logger.debug("Looking for other objects...")
        for activity_type in ('new', 'changed', 'deleted'):
            objects = obj_cache[activity_type]
            for obj in objects:
                logger.debug("Looking at %s object %s" % (activity_type, obj))
                if activity_type == "new" and obj.id in activities:
                    logger.debug("This object was already logged as a new "
                            "package")
                    continue

                try:
                    related_packages = obj.related_packages()
                    logger.debug("related_packages: %s" % related_packages)
                except (AttributeError, TypeError):
                    logger.debug("Object did not have a suitable "
                            "related_packages() method, skipping it.")
                    continue

                for package in related_packages:
                    if package is None: continue

                    if package.id in activities:
                        activity = activities[package.id]
                    else:
                        activity = activity_stream_item(package, "changed",
                                revision.id)
                        activities[package.id] = activity
                    assert activity is not None
                    logger.debug("activity: %s" % activity)

                    activity_detail = activity_stream_detail(obj, activity.id,
                            activity_type)
                    logger.debug("activity_detail: %s" % activity_detail)
                    if activity_detail is not None:
                        if activity_details.has_key(activity.id):
                            activity_details[activity.id].append(
                                    activity_detail)
                        else:
                            activity_details[activity.id] =  [activity_detail]

        for key, activity in activities.items():
            logger.debug("Emitting activity: %s %s"
                    % (activity.id, activity.activity_type))
            session.add(activity)

        session.flush()

        for key, activity_detail_list in activity_details.items():
            for activity_detail_obj in activity_detail_list:
                logger.debug("Emitting activity detail: %s %s %s"
                        % (activity_detail_obj.activity_id,
                            activity_detail_obj.activity_type,
                            activity_detail_obj.object_type))
                session.add(activity_detail_obj)

        session.flush()
