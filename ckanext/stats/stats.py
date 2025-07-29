# encoding: utf-8
from __future__ import annotations

import datetime
import logging
from typing import Any, ClassVar, Optional, Union

from sqlalchemy import Table, select, join, func, and_

from ckan.common import config
import ckan.model as model

log = logging.getLogger(__name__)

DATE_FORMAT = "%Y-%m-%d"


def table(name: str):
    return Table(name, model.meta.metadata, autoload=True)


def datetime2date(datetime_: datetime.datetime):
    return datetime.date(datetime_.year, datetime_.month, datetime_.day)


class Stats(object):
    _cumulative_num_pkgs: ClassVar[int]

    @classmethod
    def largest_groups(cls, limit: int = 10) -> list[tuple[Optional[model.Group], int]]:
        package = table("package")
        activity = table("activity")

        j = join(activity, package, activity.c["object_id"] == package.c["id"])

        s = (
            select([package.c["owner_org"], func.count(package.c["id"])])
            .select_from(j)
            .group_by(package.c["owner_org"])
            .where(
                and_(
                    package.c["owner_org"] != None,  # type: ignore
                    activity.c["activity_type"] == "new package",
                    package.c["private"] == False,
                    package.c["state"] == "active",
                )
            )
            .order_by(func.count(package.c["id"]).desc())
            .limit(limit)
        )

        res_ids = model.Session.execute(s).fetchall()

        res_groups: list[tuple[Optional[model.Group], int]] = [
            (model.Session.query(model.Group).get(str(group_id)), val)
            for group_id, val in res_ids
        ]
        return res_groups

    @classmethod
    def top_tags(cls, limit: int = 10,
                 returned_tag_info: str = 'object'
                 ) -> Optional[list[Any]]:  # by package
        assert returned_tag_info in ("name", "id", "object")
        tag = table("tag")
        package_tag = table("package_tag")
        package = table("package")
        if returned_tag_info == "name":
            from_obj = [package_tag.join(tag)]
            tag_column = tag.c["name"]
        else:
            from_obj = None
            tag_column = package_tag.c["tag_id"]
        j = join(
            package_tag, package, package_tag.c["package_id"] == package.c["id"]
        )
        s = (
            select(
                [tag_column, func.count(package_tag.c["package_id"])],
                from_obj=from_obj,
            )
            .select_from(j)
            .where(
                and_(
                    package_tag.c["state"] == "active",
                    package.c["private"] == False,
                    package.c["state"] == "active",
                )
            )
        )
        s = (
            s.group_by(tag_column)
            .order_by(func.count(package_tag.c["package_id"]).desc())
            .limit(limit)
        )
        res_col = model.Session.execute(s).fetchall()
        if returned_tag_info in ("id", "name"):
            return res_col
        elif returned_tag_info == "object":
            res_tags = [
                (model.Session.query(model.Tag).get(str(tag_id)), val)
                for tag_id, val in res_col
            ]
            return res_tags

    @classmethod
    def top_package_creators(cls, limit: int = 10) -> list[tuple[Optional[model.User], int]]:
        if not config.get('ckan.auth.public_user_details'):
            log.debug(
                "Top package creators stats are not available because "
                "ckan.auth.public_user_details is not set to True."
            )
            return []

        userid_count = (
            model.Session.query(
                model.Package.creator_user_id,
                func.count(model.Package.creator_user_id),
            )
            .filter(model.Package.state == "active")
            .filter(model.Package.private == False)
            .group_by(model.Package.creator_user_id)
            .order_by(func.count(model.Package.creator_user_id).desc())
            .limit(limit)
            .all()
        )
        user_count = [
            (model.Session.query(model.User).get(str(user_id)), count)
            for user_id, count in userid_count
            if user_id
        ]
        return user_count

    @classmethod
    def most_edited_packages(cls, limit: int = 10) -> list[tuple[model.Package, int]]:
        package = table("package")
        activity = table("activity")

        s = (
            select(
                [package.c["id"], func.count(activity.c["id"])],
                from_obj=[
                    activity.join(
                        package, activity.c["object_id"] == package.c["id"]
                    )
                ],
            )
            .where(
                and_(
                    package.c["private"] == False,
                    activity.c["activity_type"] == "changed package",
                    package.c["state"] == "active",
                )
            )
            .group_by(package.c["id"])
            .order_by(func.count(activity.c["id"]).desc())
            .limit(limit)
        )
        res_ids = model.Session.execute(s).fetchall()

        res_pkgs: list[tuple[model.Package, int]] = []
        for pkg_id, val in res_ids:
            pkg = model.Session.query(model.Package).get(str(pkg_id))
            assert pkg
            res_pkgs.append((pkg, val))

        return res_pkgs

    @classmethod
    def get_package_revisions(cls) -> list[Any]:
        """
        @return: Returns list of revisions and date of them, in
                 format: [(id, date), ...]
        """
        package = table("package")
        activity = table("activity")
        s = select(
            [package.c["id"], activity.c["timestamp"]],
            from_obj=[
                activity.join(package, activity.c["object_id"] == package.c["id"])
            ],
        ).order_by(activity.c["timestamp"])
        res = model.Session.execute(s).fetchall()
        return res

    @classmethod
    def get_by_week(cls, object_type: str) -> list[tuple[str, list[str], int, int]]:
        cls._object_type = object_type

        def objects_by_week() -> list[tuple[str, list[str], int, int]]:
            if cls._object_type == "new_packages":
                objects = cls.get_new_packages()

                def get_date(object_date: int) -> datetime.date:  # type: ignore
                    return datetime.date.fromordinal(object_date)

            elif cls._object_type == "deleted_packages":
                objects = cls.get_deleted_packages()

                def get_date(object_date: int) -> datetime.date:  # type: ignore
                    return datetime.date.fromordinal(object_date)

            elif cls._object_type == "package_revisions":
                objects = cls.get_package_revisions()

                def get_date(object_date: datetime.datetime):
                    return datetime2date(object_date)

            else:
                raise NotImplementedError()
            first_date = (
                get_date(objects[0][1])
                if objects else datetime.date.today()
            )
            week_commences = cls.get_date_week_started(first_date)
            week_ends = week_commences + datetime.timedelta(days=7)
            weekly_pkg_ids: list[tuple[str, list[str], int, int]] = []
            pkg_id_stack = []
            cls._cumulative_num_pkgs = 0

            def build_weekly_stats(week_commences: datetime.date, pkg_ids: list[str]) -> tuple[str, list[str], int, int]:
                num_pkgs = len(pkg_ids)
                cls._cumulative_num_pkgs += num_pkgs
                return (
                    week_commences.strftime(DATE_FORMAT),
                    pkg_ids,
                    num_pkgs,
                    cls._cumulative_num_pkgs,
                )

            for pkg_id, date_field in objects:
                date_ = get_date(date_field)
                if date_ >= week_ends:
                    weekly_pkg_ids.append(
                        build_weekly_stats(week_commences, pkg_id_stack)
                    )
                    pkg_id_stack = []
                    week_commences = week_ends
                    week_ends = week_commences + datetime.timedelta(days=7)
                pkg_id_stack.append(pkg_id)
            weekly_pkg_ids.append(
                build_weekly_stats(week_commences, pkg_id_stack)
            )
            today = datetime.date.today()
            while week_ends <= today:
                week_commences = week_ends
                week_ends = week_commences + datetime.timedelta(days=7)
                weekly_pkg_ids.append(build_weekly_stats(week_commences, []))
            return weekly_pkg_ids

        return objects_by_week()

    @classmethod
    def get_new_packages(cls) -> list[tuple[str, int]]:
        """
        @return: Returns list of new pkgs and date when they were created, in
                 format: [(id, date_ordinal), ...]
        """

        def new_packages() -> list[tuple[str, int]]:
            # Can't filter by time in select because 'min' function has to
            # be 'for all time' else you get first revision in the time period.
            package = table("package")
            activity = table("activity")
            s = (
                select(
                    [package.c["id"], func.min(activity.c["timestamp"])],
                    from_obj=[
                        activity.join(
                            package, activity.c["object_id"] == package.c["id"]
                        )
                    ],
                )
                .group_by(package.c["id"])
                .order_by(func.min(activity.c["timestamp"]))
            )
            res = model.Session.execute(s).fetchall()
            res_pickleable: list[tuple[str, int]] = []
            for pkg_id, created_datetime in res:
                res_pickleable.append((pkg_id, created_datetime.toordinal()))
            return res_pickleable

        return new_packages()

    @classmethod
    def get_date_week_started(cls, date_: Union[datetime.datetime, datetime.date]):
        assert isinstance(date_, datetime.date)
        if isinstance(date_, datetime.datetime):
            date_ = datetime2date(date_)
        return date_ - datetime.timedelta(days=datetime.date.weekday(date_))

    @classmethod
    def get_num_packages_by_week(cls):
        def num_packages() -> list[tuple[str, int, int]]:
            new_packages_by_week = cls.get_by_week("new_packages")
            deleted_packages_by_week = cls.get_by_week("deleted_packages")
            first_date = (
                min(
                    datetime.datetime.strptime(
                        new_packages_by_week[0][0], DATE_FORMAT
                    ),
                    datetime.datetime.strptime(
                        deleted_packages_by_week[0][0], DATE_FORMAT
                    ),
                )
            ).date()
            cls._cumulative_num_pkgs = 0
            new_pkgs = []
            deleted_pkgs = []

            def build_weekly_stats(
                week_commences: datetime.date, new_pkg_ids: list[str], deleted_pkg_ids: list[str]
            ) -> tuple[str, int, int]:
                num_pkgs = len(new_pkg_ids) - len(deleted_pkg_ids)
                new_pkgs.extend(
                    pkg.name for pkg in
                    [model.Session.query(model.Package).get(id)
                     for id in new_pkg_ids] if pkg
                )
                deleted_pkgs.extend(
                    pkg.name for pkg in
                    [model.Session.query(model.Package).get(id)
                     for id in deleted_pkg_ids] if pkg
                )
                cls._cumulative_num_pkgs += num_pkgs
                return (
                    week_commences.strftime(DATE_FORMAT),
                    num_pkgs,
                    cls._cumulative_num_pkgs,
                )

            week_ends = first_date
            today = datetime.date.today()
            new_package_week_index = 0
            deleted_package_week_index = 0
            # [(week_commences, num_packages, cumulative_num_pkgs])]
            weekly_numbers: list[tuple[str, int, int]] = []
            while week_ends <= today:
                week_commences = week_ends
                week_ends = week_commences + datetime.timedelta(days=7)
                if (
                    datetime.datetime.strptime(
                        new_packages_by_week[new_package_week_index][0],
                        DATE_FORMAT,
                    ).date()
                    == week_commences
                ):
                    new_pkg_ids = new_packages_by_week[new_package_week_index][
                        1
                    ]
                    new_package_week_index += 1
                else:
                    new_pkg_ids = []
                if (
                    datetime.datetime.strptime(
                        deleted_packages_by_week[deleted_package_week_index][
                            0
                        ],
                        DATE_FORMAT,
                    ).date()
                    == week_commences
                ):
                    deleted_pkg_ids = deleted_packages_by_week[
                        deleted_package_week_index
                    ][1]
                    deleted_package_week_index += 1
                else:
                    deleted_pkg_ids = []
                weekly_numbers.append(
                    build_weekly_stats(
                        week_commences, new_pkg_ids, deleted_pkg_ids
                    )
                )
            # just check we got to the end of each count
            assert new_package_week_index == len(new_packages_by_week)
            assert deleted_package_week_index == len(deleted_packages_by_week)
            return weekly_numbers

        return num_packages()

    @classmethod
    def get_deleted_packages(cls):
        """
        @return: Returns list of deleted pkgs and date when they were deleted,
                 in format: [(id, date_ordinal), ...]
        """

        def deleted_packages() -> list[tuple[str, int]]:
            # Can't filter by time in select because 'min' function has to
            # be 'for all time' else you get first revision in the time period.
            package = table("package")
            activity = table("activity")

            s = (
                select(
                    [package.c["id"], func.min(activity.c["timestamp"])],
                    from_obj=[
                        activity.join(
                            package, activity.c["object_id"] == package.c["id"]
                        )
                    ],
                )
                .where(activity.c["activity_type"] == "deleted package")
                .group_by(package.c["id"])
                .order_by(func.min(activity.c["timestamp"]))
            )
            res = model.Session.execute(s).fetchall()
            res_pickleable: list[tuple[str, int]] = []
            for pkg_id, deleted_datetime in res:
                res_pickleable.append((pkg_id, deleted_datetime.toordinal()))
            return res_pickleable

        return deleted_packages()
