import copy

class StatsCount(dict):
    # {category:count}
    _init_value = 0
    report_value_limit = 150
    
    def _init_category(self, category):
        if not self.has_key(category):
            self[category] = copy.deepcopy(self._init_value)
        
    def increment(self, category):
        self._init_category(category)
        self[category] += 1

    def report_value(self, category):
        value = repr(self[category])
        if len(value) > self.report_value_limit:
            value = value[:self.report_value_limit] + '...'
        return value

    def report(self, indent=1):
        lines = []
        categories = self.keys()
        categories.sort()
        indent_str = '\t' * indent
        for category in categories:
            value = self.report_value(category)
            lines.append(indent_str + '%s: %s' % (category, value))
        if not categories:
            lines = [indent_str + 'None']
        return '\n'.join(lines)

class StatsList(StatsCount):
    # {category:count}
    _init_value = []

    def add(self, category, value):
        self._init_category(category)
        self[category].append(value)

    def report_value(self, category):
        value = self[category]
        value_str = '%i %r' % (len(value), value)
        if len(value_str) > self.report_value_limit:
            value_str = value_str[:self.report_value_limit] + '...'
        return value_str
