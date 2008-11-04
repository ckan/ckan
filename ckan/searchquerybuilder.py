import dateutil.parser
import datetime
import sqlalchemy

import ckan.model as model

class QuerySpec(object):

    def __init__(self, count=20, offset=0):
        self.count = count
        self.offset = offset

class SearchQuerySpec(QuerySpec):

    def __init__(self, **kwds):
        super(SearchQuerySpec, self).__init__(**kwds)
        self.content = []

    def __str__(self):
        return str(self.content)

class SearchQueryBuilder(object):
    tokens = [ 'title', 'notes', 'tags']

    def __init__(self, mode):
        self.mode = mode

    def execute(self):
        query_spec = self.convert_request_data_to_spec()
        return self.create_query_from_spec(query_spec)

    def convert_request_data_to_spec(self):
        self.spec = SearchQuerySpec()
        query_str = ''
        if self.mode.request_data:
            if self.mode.request_data.has_key('count'):
                self.spec.count = self.mode.request_data['count']
            # Get the query string from request data.
            query_str = self.mode.request_data.get('q', '')
        # Go through the query string, looking for 'qualifying' tokens.
        #     - an example of a qualifying token would be 'title:'.
        spec_raw = {}
        current_token = 'unqualified'
        current_value = ''
        word = ''
        for ch in query_str:
            if ch == ':' and word in self.tokens:
                if current_value:
                    spec_raw[current_token] = current_value.strip()
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
            spec_raw[current_token] = value.strip()
        # Go through the raw values of the tokens, looking for 'operators'.
        for (token, value) in spec_raw.items():
            operator = '='  # The default.
            # Append specification.
            self.spec.content.append({
                'name': token,
                'value': value,
                'operator': operator,
            })
        return self.spec
    
    def create_query_from_spec(self, query_spec):
        register = self.mode.get_register()
        query = register.query
        if len(query_spec.content) == 0:
            return None 
        for part in query_spec.content:
            k = part['name']
            v = part['value']
            o = part['operator']
            if k == 'unqualified':
                query = register.text_search(query, v)
            elif k == 'tags':
                query = self.filter_by_tags(query, v.split())
            else:
                model_attr = getattr(register, k)
                make_like = lambda x,y: x.ilike('%' + y + '%')
                query = query.filter(make_like(model_attr,v))
        query = query.limit(query_spec.count)
        return query

    def filter_by_tags(self, query, taglist):
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



