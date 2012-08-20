from sqlalchemy.orm.session import SessionExtension
import logging
logger = logging.getLogger(__name__)

def activity_stream_item(obj, activity_type, revision, user_id):
    method = getattr(obj, "activity_stream_item", None)
    if callable(method):
        return method(activity_type, revision, user_id)
    else:
        logger.debug("Object did not have a suitable "
            "activity_stream_item() method, it must not be a package.")
        return None

def activity_stream_detail(obj, activity_id, activity_type):
    method = getattr(obj, "activity_stream_detail",
            None)
    if callable(method):
        return method(activity_id, activity_type)
    else:
        logger.debug("Object did not have a suitable  "
            "activity_stream_detail() method.")
        return None

class DatasetActivitySessionExtension(SessionExtension):
    """Session extension that emits activity stream activities for packages
    and related objects.

    An SQLAlchemy SessionExtension that watches for new, changed or deleted
    Packages or objects with related packages (Resources, PackageExtras..)
    being committed to the SQLAlchemy session and creates Activity and
    ActivityDetail objects for these activities.

    For most types of activity the Activity and ActivityDetail objects are
    created in the relevant ckan/logic/action/ functions, but for Packages and
    objects with related packages they are created by this class instead.

    """
    def before_commit(self, session):

        session.flush()

        try:
            object_cache = session._object_cache
            revision = session.revision
        except AttributeError:
            logger.debug('session had no _object_cache or no revision,'
                    ' skipping this commit', exc_info=True)
            return

        if revision.user:
            user_id = revision.user.id
        else:
            # If the user is not logged in then revision.user is None and
            # revision.author is their IP address. Just log them as 'not logged
            # in' rather than logging their IP address.
            user_id = 'not logged in'
        logger.debug('user_id: %s' % user_id)

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
        for obj in object_cache['new']:
            logger.debug("Looking at object %s" % obj)
            activity = activity_stream_item(obj, 'new', revision, user_id)
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
            objects = object_cache[activity_type]
            for obj in objects:
                logger.debug("Looking at %s object %s" % (activity_type, obj))

                if not hasattr(obj,"id"):
                    logger.debug("Object has no id, skipping...")
                    continue


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
                                revision, user_id)
                        if activity is None: continue
                    logger.debug("activity: %s" % activity)

                    activity_detail = activity_stream_detail(obj, activity.id,
                            activity_type)
                    logger.debug("activity_detail: %s" % activity_detail)
                    if activity_detail is not None:
                        if not package.id in activities:
                            activities[package.id] = activity
                        if activity_details.has_key(activity.id):
                            activity_details[activity.id].append(
                                    activity_detail)
                        else:
                            activity_details[activity.id] =  [activity_detail]

        for key, activity in activities.items():
            logger.debug("Emitting activity: %s %s"
                    % (activity.id, activity.activity_type))
            session.add(activity)

        for key, activity_detail_list in activity_details.items():
            for activity_detail_obj in activity_detail_list:
                logger.debug("Emitting activity detail: %s %s %s"
                        % (activity_detail_obj.activity_id,
                            activity_detail_obj.activity_type,
                            activity_detail_obj.object_type))
                session.add(activity_detail_obj)

        session.flush()
