from sqlalchemy import or_
from ckan.lib.search.query import SearchQuery
import ckan.model as model

class PackageSearchQuery(SearchQuery):
    def get_all_entity_ids(self, max_results=100):
        """
        Return a list of the IDs of all indexed packages.
        """
        # could make this a pure sql query which would be much more efficient!
        q = model.Session.query(model.Package).filter_by(state='active').limit(max_results)

        return [r.id for r in q]

    def run(self, query):
        assert isinstance(query, dict)
        # no support for faceting atm
        self.facets = {}
        limit = min(1000, int(query.get('rows', 10)))

        q = query.get('q')
        ourq = model.Session.query(model.Package.id).filter_by(state='active')

        def makelike(field):
            _attr = getattr(model.Package, field)
            return _attr.ilike('%' + term + '%')
        if q and q not in ('""', "''", '*:*'):
            terms = q.split()
            # TODO: tags ...?
            fields = ['name', 'title', 'notes']
            for term in terms:
                args = [makelike(field) for field in fields]
                subq = or_(*args)
                ourq = ourq.filter(subq)
        self.count = ourq.count()
        ourq = ourq.limit(limit)
        self.results = [{'id': r[0]} for r in ourq.all()]

        return {'results': self.results, 'count': self.count}

