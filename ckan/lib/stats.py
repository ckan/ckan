from sqlalchemy import *

from ckan import model

def table(name):
    return Table(name, model.metadata, autoload=True)

class Stats(object):
    @classmethod
    def top_rated_packages(self):
        # NB Not using sqlalchemy as sqla 0.4 doesn't work using both group_by
        # and apply_avg
        #         SELECT package.id AS package_id, AVG(rating.rating) FROM package
        #         JOIN rating ON package.id = rating.package_id
        #         GROUP BY package.id
        #         ORDER BY AVG(rating.rating) DESC
        #         LIMIT 10
        package = table('package')
        rating = table('rating')
        sql = select([package.c.id, func.avg(rating.c.rating)], from_obj=[package.join(rating)]).\
              group_by(package.c.id).\
              order_by(func.avg(rating.c.rating).desc()).\
              limit(10)
        res_ids = model.Session.execute(sql).fetchall()
        res_pkgs = [(model.Session.query(model.Package).get(unicode(pkg_id)), avg) for pkg_id, avg in res_ids]
        return res_pkgs
            
    def most_edited_packages(self):
        package_revision = table('package_revision')
        s = select([package_revision.c.id, func.count(package_revision.c.revision_id)]).\
            group_by(package_revision.c.id).\
            order_by(func.count(package_revision.c.revision_id).desc()).\
            limit(10)
        res_ids = model.Session.execute(s).fetchall()        
        res_pkgs = [(model.Session.query(model.Package).get(unicode(pkg_id)), val) for pkg_id, val in res_ids]
        return res_pkgs
        
    def largest_groups(self):
        package_group = table('package_group')
        s = select([package_group.c.group_id, func.count(package_group.c.package_id)]).\
            group_by(package_group.c.group_id).\
            order_by(func.count(package_group.c.package_id).desc()).\
            limit(10)
        res_ids = model.Session.execute(s).fetchall()        
        res_groups = [(model.Session.query(model.Group).get(unicode(group_id)), val) for group_id, val in res_ids]
        return res_groups

