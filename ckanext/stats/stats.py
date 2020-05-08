# encoding: utf-8

import datetime
import logging
from ckan.common import config
from six import text_type
from sqlalchemy import Table, select, join, func, and_

import ckan.plugins as p
import ckan.model as model

log = logging.getLogger(__name__)
cache_enabled = p.toolkit.asbool(
    config.get('ckanext.stats.cache_enabled', False)
)

if cache_enabled:
    log.warn(
        'ckanext.stats does not support caching in current implementations'
    )

DATE_FORMAT = '%Y-%m-%d'


def table(name):
    return Table(name, model.meta.metadata, autoload=True)


def datetime2date(datetime_):
    return datetime.date(datetime_.year, datetime_.month, datetime_.day)


class Stats(object):

    @classmethod
    def top_rated_packages(cls, limit=10):
        # NB Not using sqlalchemy as sqla 0.4 doesn't work using both group_by
        # and apply_avg
        package = table('package')
        rating = table('rating')
        sql = select(
            [
                package.c.id,
                func.avg(rating.c.rating),
                func.count(rating.c.rating)
            ],
            from_obj=[package.join(rating)]
        ).where(and_(package.c.private == False, package.c.state == 'active')
                ).group_by(package.c.id).order_by(
                    func.avg(rating.c.rating).desc(),
                    func.count(rating.c.rating).desc()
                ).limit(limit)
        res_ids = model.Session.execute(sql).fetchall()
        res_pkgs = [(
            model.Session.query(model.Package).get(text_type(pkg_id)), avg, num
        ) for pkg_id, avg, num in res_ids]
        return res_pkgs

    @classmethod
    def largest_groups(cls, limit=10):
        member = table('member')
        package = table('package')

        j = join(member, package, member.c.table_id == package.c.id)

        s = select(
            [member.c.group_id,
             func.count(member.c.table_id)]
        ).select_from(j).group_by(member.c.group_id).where(
            and_(
                member.c.group_id != None, member.c.table_name == 'package',
                package.c.private == False, package.c.state == 'active'
            )
        ).order_by(func.count(member.c.table_id).desc()).limit(limit)

        res_ids = model.Session.execute(s).fetchall()
        res_groups = [
            (model.Session.query(model.Group).get(text_type(group_id)), val)
            for group_id, val in res_ids
        ]
        return res_groups

    @classmethod
    def top_tags(cls, limit=10, returned_tag_info='object'):  # by package
        assert returned_tag_info in ('name', 'id', 'object')
        tag = table('tag')
        package_tag = table('package_tag')
        package = table('package')
        if returned_tag_info == 'name':
            from_obj = [package_tag.join(tag)]
            tag_column = tag.c.name
        else:
            from_obj = None
            tag_column = package_tag.c.tag_id
        j = join(
            package_tag, package, package_tag.c.package_id == package.c.id
        )
        s = select([tag_column,
                    func.count(package_tag.c.package_id)],
                   from_obj=from_obj).select_from(j).where(
                       and_(
                           package_tag.c.state == 'active',
                           package.c.private == False,
                           package.c.state == 'active'
                       )
                   )
        s = s.group_by(tag_column).order_by(
            func.count(package_tag.c.package_id).desc()
        ).limit(limit)
        res_col = model.Session.execute(s).fetchall()
        if returned_tag_info in ('id', 'name'):
            return res_col
        elif returned_tag_info == 'object':
            res_tags = [
                (model.Session.query(model.Tag).get(text_type(tag_id)), val)
                for tag_id, val in res_col
            ]
            return res_tags

    @classmethod
    def top_package_creators(cls, limit=10):
        userid_count = model.Session.query(
            model.Package.creator_user_id,
            func.count(model.Package.creator_user_id)
        ).filter(model.Package.state == 'active'
                 ).filter(model.Package.private == False).group_by(
                     model.Package.creator_user_id
                 ).order_by(func.count(model.Package.creator_user_id).desc()
                            ).limit(limit).all()
        user_count = [
            (model.Session.query(model.User).get(text_type(user_id)), count)
            for user_id, count in userid_count
            if user_id
        ]
        return user_count
