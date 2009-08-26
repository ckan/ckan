import sqlalchemy

import ckan.model as model

MAX_RESULTS = 20

class Search:
    tokens = [ 'name', 'title', 'notes', 'tags']

    def run(self, query_str, options=None):
        
        # split query into terms
        # format: * double quotes enclose a single term. e.g. "War and Peace"
        #         * field:term or field:"longer term" means search only in that
        #           particular field for that term.
        terms = []
        inside_quote = False
        buf = ''
        for ch in query_str:
            if ch == ' ' and not inside_quote:
                if buf:
                    terms.append(buf.strip())
                buf = ''
            elif ch == '"':
                inside_quote = not inside_quote
            else:
                buf += ch
        if buf:
            terms.append(buf)
                
        # Search on every search term and award point for every match
        scores = {} # package:score
        tags_terms = []
        for term in terms:
            query = model.Package.query
            
            # Look for 'token:'
            token = None
            colon_pos = term.find(':')
            if colon_pos != -1:
                token = term[:colon_pos]
                if token in self.tokens:
                    term = term[colon_pos+1:]
                else:
                    token = None

            # Filter by token
            if token == 'tags':
                query = self._filter_by_tags(query, term.split())
                tags_terms.append(term)
            elif token:
                model_attr = getattr(model.Package, token)
                make_like = lambda x,y: x.ilike('%' + y + '%')
                query = query.filter(make_like(model_attr, term))
            else:
                query = model.Package.text_search(query, term)
                tags_terms.append(term)

            # Run the query
            query = query.limit(MAX_RESULTS)
            results = query.all()
            for result in results:
                if not scores.has_key(result):
                    scores[result] = 0
                scores[result] += 1

        # Look for tags in the terms (apart from ones with other tokens)
        tags = []
        for term in tags_terms:
            tags_found = model.Tag.search_by_name(term).all()
            if tags_found:
                tags.extend(tags_found)

        # Sort results by scores
        results = [(score, pkg) for pkg, score in scores.items()]
        results.sort()
        results.reverse()
        pkgs = [pkg for score, pkg in results]

        # Filter results according to options
        pkgs = self._filter_by_options(pkgs, options)
        
        return pkgs, tags

    def get_query(self, query_str):
        # Process query_str into value and spec
        spec = {}
        current_token = 'unqualified'
        current_value = ''
        word = ''
        for ch in query_str:
            if ch == ':' and word in self.tokens:
                if current_value:
                    spec[current_token] = current_value.strip()
                # reset
                current_token = word
                current_value = ''
                word = ''
            elif ch in [ ' ', '\n' ]:
                current_value += word + ch
                word = ''
            else:
                word += ch
        if current_value or word:
            value = current_value + word
            spec[current_token] = value.strip()

        query_spec = spec
        query = model.Package.query
        if len(query_spec) == 0:
            return None 
        for k, v in query_spec.items():
            if k == 'unqualified':
                query = model.Package.text_search(query, v)
            elif k == 'tags':
                query = self._filter_by_tags(query, v.split())
            else:
                model_attr = getattr(model.Package, k)
                make_like = lambda x,y: x.ilike('%' + y + '%')
                query = query.filter(make_like(model_attr,v))
        query = query.limit(MAX_RESULTS)
        return query

    def _filter_by_options(self, packages, options):
        if options:
            open_only, downloadable_only = options
            if open_only:
                packages_filtered = []
                for package in packages:
                    if package.isopen():
                        packages_filtered.append(package)
                packages = packages_filtered
            if downloadable_only:
                packages_filtered = []
                for package in packages:
                    if package.download_url:
                        packages_filtered.append(package)
                packages = packages_filtered
        return packages

    def _filter_by_tags(self, query, taglist):
        taglist = [ tagname.strip() for tagname in taglist ]
        for name in taglist:
            tag = model.Tag.by_name(name)
            if tag:
                tag_id = tag.id
                # need to keep joining for us 
                # tag should be active hence state_id requirement
                query = query.join('package_tags', aliased=True
                    ).filter(sqlalchemy.and_(
                        model.PackageTag.state_id==1,
                        model.PackageTag.tag_id==tag_id))
        return query
        
