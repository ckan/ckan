
from ckan.lib.commands import CkanCommand


class PluginInfo(CkanCommand):
    '''Provide info on installed plugins.
    '''

    summary = __doc__.split('\n')[0]
    usage = __doc__
    max_args = 0
    min_args = 0

    def command(self):
        self.get_info()

    def get_info(self):
        ''' print info about current plugins from the .ini file'''
        import ckan.plugins as p
        self._load_config()
        interfaces = {}
        plugins = {}
        for name in dir(p):
            item = getattr(p, name)
            try:
                if issubclass(item, p.Interface):
                    interfaces[item] = {'class': item}
            except TypeError:
                pass

        for interface in interfaces:
            for plugin in p.PluginImplementations(interface):
                name = plugin.name
                if name not in plugins:
                    plugins[name] = {'doc': plugin.__doc__,
                                     'class': plugin,
                                     'implements': []}
                plugins[name]['implements'].append(interface.__name__)

        for plugin in plugins:
            p = plugins[plugin]
            print plugin + ':'
            print '-' * (len(plugin) + 1)
            if p['doc']:
                print p['doc']
            print 'Implements:'
            for i in p['implements']:
                extra = None
                if i == 'ITemplateHelpers':
                    extra = self.template_helpers(p['class'])
                if i == 'IActions':
                    extra = self.actions(p['class'])
                print '    %s' % i
                if extra:
                    print extra
            print

    def actions(self, cls):
        ''' Return readable action function info. '''
        actions = cls.get_actions()
        return self.function_info(actions)

    def template_helpers(self, cls):
        ''' Return readable helper function info. '''
        helpers = cls.get_helpers()
        return self.function_info(helpers)

    def function_info(self, functions):
        ''' Take a dict of functions and output readable info '''
        import inspect
        output = []
        for function_name in functions:
            fn = functions[function_name]
            args_info = inspect.getargspec(fn)
            params = args_info.args
            num_params = len(params)
            if args_info.varargs:
                params.append('*' + args_info.varargs)
            if args_info.keywords:
                params.append('**' + args_info.keywords)
            if args_info.defaults:
                offset = num_params - len(args_info.defaults)
                for i, v in enumerate(args_info.defaults):
                    params[i + offset] = params[i + offset] + '=' + repr(v)
            # is this a classmethod if so remove the first parameter
            if inspect.ismethod(fn) and inspect.isclass(fn.__self__):
                params = params[1:]
            params = ', '.join(params)
            output.append('        %s(%s)' % (function_name, params))
            # doc string
            if fn.__doc__:
                bits = fn.__doc__.split('\n')
                for bit in bits:
                    output.append('            %s' % bit)
        return ('\n').join(output)
