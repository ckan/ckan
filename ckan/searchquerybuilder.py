import dateutil.parser
import datetime
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
    # attributes you can query on e.g. 'title', 'description' etc
    tokens_datetime = ['start', 'end']  # Could pull these from the model?
    tokens = [ 'title', 'description', 'factlets'] + tokens_datetime
    operators = ['=', '>', '<', '~']

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
            isYearDurationInferred = False
            if token in self.tokens_datetime:
                if len(value) > 0 and value[0] in self.operators:
                    operator = value[0]
                    value = value[1:]
                # Infer year duration?
                if len(value) == 4 and operator == '=':
                    isYearDurationInferred = True
                    operator = '>'
                # Year intervals?
                elif len(value) == 10 and value[4] in [',', ' '] and value[5] in ['>', '<']:
                    # Append specification with second limit.
                    operator2 = value[5]
                    value2 = value[6:10]
                    try:
                        default = datetime.datetime(1,1,1)
                        value2 = dateutil.parser.parse(value2, default=default)
                        self.spec.content.append({
                            'name': token,
                            'value': value2,
                            'operator': operator2,
                        })
                    except ValueError, inst:
                        if not str(inst) == 'unknown string format':
                            raise
                    value = value[0:4]
                try:
                    default = datetime.datetime(1,1,1)
                    value = dateutil.parser.parse(value, default=default)
                except ValueError, inst:
                    if not str(inst) == 'unknown string format':
                        raise
                    else:
                        continue
            if isYearDurationInferred:
                # Append specification with upper limit.
                year_end = datetime.datetime(value.year, 12, 31, 23, 59, 59)
                self.spec.content.append({
                    'name': token,
                    'value': year_end,
                    'operator': '<',
                })
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
            elif k == 'factlets':
                # List of factlets, or thread_factlets.
                singular = k[:-1]
                target_object = getattr(model, singular.capitalize())
                try:
                    query = query.join(k)
                except:
                    # It's a list of thread_factlets.
                    attr_name = self.mode.get_register_name() + '_' + k
                    query = query.join(attr_name)
                # v is currently a string containing ids
                v = v.split()
                if len(v) > 1:
                    msg = 'Filtering by more than 2 items is not supported'
                    raise NotImplementedError(msg)
                for entity_id in v:
                    query = query.filter(target_object.id == entity_id)
            elif isinstance(v, datetime.datetime):
                model_attr = getattr(register, k)
                if o == '=':
                    query = query.filter(model_attr==v)
                elif o == '>':
                    query = query.filter(model_attr>=v)
                elif o == '<':
                    query = query.filter(model_attr<=v)
                elif o == '~':
                    # Todo: Something better than '=='.   :-)
                    query = query.filter(model_attr==v)
            else:
                model_attr = getattr(register, k)
                make_like = lambda x,y: x.ilike('%' + y + '%')
                query = query.filter(make_like(model_attr,v))

        query = query.limit(query_spec.count)
        return query

# Notes related to above method....
#
# at present cannot do more than 1 item
# want to do:
# select thread where thread_2_factlet contains
# thread, factlet1 and thread, factlet2 and ...
# however with simple join do
# select thread.id from thread join thread_2_factlet where
# factlet.id = id1 and factlet.id = id2
# this obviously always give zero results


