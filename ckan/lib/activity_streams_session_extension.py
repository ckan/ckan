# encoding: utf-8

from ckan.common import config
from sqlalchemy.orm.session import SessionExtension
from paste.deploy.converters import asbool
import logging

log = logging.getLogger(__name__)


def activity_stream_item(obj, activity_type, revision, user_id):
    method = getattr(obj, "activity_stream_item", None)
    if callable(method):
        return method(activity_type, revision, user_id)
    else:
        # Object did not have a suitable activity_stream_item() method; it must
        # not be a package
        return None


class DatasetActivitySessionExtension(SessionExtension):
    """Session extension that emits activity stream activities for packages
    and related objects.

    An SQLAlchemy SessionExtension that watches for new, changed or deleted
    Packages or objects with related packages (Resources, PackageExtras..)
    being committed to the SQLAlchemy session and creates Activity objects for
    these activities.

    For most types of activity the Activity objects are created in the relevant
    ckan/logic/action/ functions, but for Packages and objects with related
    packages they are created by this class instead.

    """
    def before_commit(self, session):
        from ckan.model import Member  # imported here to avoid dependency hell
        if not asbool(config.get('ckan.activity_streams_enabled', 'true')):
            return

        session.flush()

        try:
            object_cache = session._object_cache
            revision = session.revision
        except AttributeError:
            # session had no _object_cache or no revision; skipping this commit
            return

        if revision.user:
            user_id = revision.user.id
        else:
            # If the user is not logged in then revision.user is None and
            # revision.author is their IP address. Just log them as 'not logged
            # in' rather than logging their IP address.
            user_id = 'not logged in'

        # The top-level objects that we will append to the activity table. The
        # keys here are package IDs, and the values are model.activity:Activity
        # objects.
        activities = {}

        # Log new packages first to prevent them from getting incorrectly
        # logged as changed packages.
        # Looking for new packages...
        for obj in object_cache['new']:
            activity = activity_stream_item(obj, 'new', revision, user_id)
            if activity is None:
                continue
            # The object returns an activity stream item, so we know that the
            # object is a package.

            # Don't create activities for private datasets.
            if obj.private:
                continue

            activities[obj.id] = activity

        # Now process other objects.
        for activity_type in ('new', 'changed', 'deleted'):
            objects = object_cache[activity_type]
            for obj in objects:

                if not hasattr(obj, "id"):
                    # Object has no id; skipping
                    continue

                if (activity_type in ('new', 'changed') and
                        obj.id in activities):
                    # This object was already logged as a new package
                    continue

                try:
                    related_packages = obj.related_packages()
                except (AttributeError, TypeError):
                    # Object did not have a suitable related_packages() method;
                    # skipping it
                    continue

                if isinstance(obj, Member):
                    # When you add a package to a group/org, it should only be
                    # in the group's activity stream, not the related packages
                    continue

                for package in related_packages:
                    if package is None:
                        continue

                    # Don't create activities for private datasets.
                    if package.private:
                        continue

                    if package.id in activities:
                        continue

                    activity = activity_stream_item(
                        package, "changed", revision, user_id)
                    if activity is None:
                        continue
                    activities[package.id] = activity

        for key, activity in activities.items():
            # Emitting activity
            session.add(activity)

        session.flush()
