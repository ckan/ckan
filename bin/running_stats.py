# encoding: utf-8

'''Tool for a script to keep track changes performed on a large number
of objects.

StatsCount - when you are counting incidences of a small set of outcomes
StatsList - when you also want to remember an ID associated with each incidence

Examples:

from running_stats import StatsCount
package_stats = StatsCount()
for package in packages:
    if package.enabled:
        package.delete()
        package_stats.increment('deleted')
    else:
        package_stats.increment('not deleted')    
print package_stats.report()
> deleted: 30
> not deleted: 70
    
from running_stats import StatsList
package_stats = StatsList()
for package in packages:
    if package.enabled:
        package.delete()
        package_stats.add('deleted', package.name)
    else:
        package_stats.add('not deleted' package.name)
print package_stats.report()
> deleted: 30 pollution-uk, flood-regions, river-quality, ...
> not deleted: 70 spending-bristol, ... 

'''

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
