from collections import defaultdict

class Status:
    '''When looping through objects and doing operations to them,
    this is a useful object to keep track of what happens and
    summarise the numbers at the end.'''
    def __init__(self, obj_type_str=None):
        self.obj_type_str = obj_type_str
        self.pkg_status = defaultdict(list) # reason: [pkgs]
        
    def record(self, status_category, pkg_name, do_print=True):
        self.pkg_status[status_category].append(pkg_name)
        if do_print:
            print '%s: %s' % (pkg_name, status_category)
        
    def __str__(self):
        status = '\nStatus'
        if self.obj_type_str:
            status += ' of: %s' % self.obj_type_str
        status += '\n'
        status += '\n'.join([ \
            '%s: %i (e.g. %s)' % (category, len(pkg_names), sorted(pkg_names)[0]) \
            for (category, pkg_names) in self.pkg_status.items()])
        status += '\nTotal: %i\n' % sum([len(pkg_names) for pkg_names in self.pkg_status.values()])
        return status
        
